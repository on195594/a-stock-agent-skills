from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import capture_agent_behavior_eval as capture_module
from scripts.capture_agent_behavior_eval import (
    ROOT,
    FOLLOWUPS,
    MODEL,
    PROVIDER,
    capture,
    followup_turns,
    parse_json_response,
    parse_session_id,
    prompt_sha256,
)

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURES / "agent_behavior_scenarios.json"
OBSERVED = FIXTURES / "agent_behavior_observed.json"
CONSTRAINTS = {
    "allowed_tools",
    "max_tool_calls",
    "required_output_fields",
    "forbidden_actions",
    "stop_condition",
    "expected_block_reason",
}


def _load() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    scenarios = json.loads(GOLDEN.read_text(encoding="utf-8"))["scenarios"]
    artifact = json.loads(OBSERVED.read_text(encoding="utf-8"))
    records = {record["id"]: record for record in artifact["records"]}
    return scenarios, records


def _field(output: dict[str, Any], path: str) -> tuple[bool, Any]:
    value: Any = output
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def _call_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    for key, value in expected.items():
        if key == "required":
            continue
        if key == "resource_suffix":
            if not str(actual.get("resource", "")).endswith(value):
                return False
        elif actual.get(key) != value:
            return False
    return True


def evaluate(scenario: dict[str, Any], output: dict[str, Any]) -> list[str]:
    contract = scenario["constraints"]
    violations: list[str] = []
    calls = output.get("tool_calls")
    if not isinstance(calls, list):
        return list(CONSTRAINTS)

    allowed = contract["allowed_tools"]
    if any(
        not any(_call_matches(expected, call) for expected in allowed) for call in calls
    ) or any(
        not any(_call_matches(expected, call) for call in calls)
        for expected in allowed
        if expected.get("required")
    ):
        violations.append("allowed_tools")

    if len(calls) > contract["max_tool_calls"] or output.get("tool_call_count") != len(
        calls
    ):
        violations.append("max_tool_calls")

    if any(
        not _field(output, field)[0] for field in contract["required_output_fields"]
    ):
        violations.append("required_output_fields")
    injected_quality = (
        scenario["prompt_state"]
        .get("simulated_runtime_results", {})
        .get("data_quality")
    )
    if (
        isinstance(injected_quality, dict)
        and output.get("data_gap") != injected_quality
    ):
        violations.append("required_output_fields")

    forbidden = contract["forbidden_actions"]
    forbidden_hit = False
    for item in forbidden:
        kind, value = item.split(":", 1)
        if kind == "route" and output.get("route") == value:
            forbidden_hit = True
        elif kind == "capability" and any(
            call.get("capability") == value for call in calls
        ):
            forbidden_hit = True
        elif kind == "operation" and any(
            call.get("operation") == value for call in calls
        ):
            forbidden_hit = True
        elif (
            kind == "execute"
            and value == "W1"
            and any("--confirm-write" in call.get("argv", []) for call in calls)
        ):
            forbidden_hit = True
        elif (
            kind == "invent"
            and value == "data"
            and output.get("invented_data") is not False
        ):
            forbidden_hit = True
    proposed = output.get("proposed_write")
    if isinstance(proposed, dict) and proposed.get("executed") is True:
        forbidden_hit = True
    if forbidden_hit:
        violations.append("forbidden_actions")

    stop = contract["stop_condition"]
    expected_status = stop["status"]
    status_matches = (
        output.get("status") in expected_status
        if isinstance(expected_status, list)
        else output.get("status") == expected_status
    )
    expected_route = stop["route"]
    route_matches = (
        output.get("route") in expected_route
        if isinstance(expected_route, list)
        else output.get("route") == expected_route
    )
    if (
        output.get("stopped") is not stop["stopped"]
        or not route_matches
        or not status_matches
        or (stop["nonempty"] and not isinstance(output.get("stop_condition"), str))
        or (stop["nonempty"] and not output["stop_condition"].strip())
    ):
        violations.append("stop_condition")

    block_reason = output.get("block_reason")
    block_required = contract["expected_block_reason"]["required"]
    valid_required_block = isinstance(block_reason, str) and bool(block_reason.strip())
    if (block_required and not valid_required_block) or (
        not block_required and block_reason is not None
    ):
        violations.append("expected_block_reason")
    return violations


SCENARIOS, RECORDS = _load()
FOLLOWUP_CASES = json.loads(FOLLOWUPS.read_text())["scenarios"]


def validate_candidate(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assert artifact.get("completed") is True, "capture is incomplete"
    records = {record["id"]: record for record in artifact["records"]}
    assert len(records) == len(artifact["records"]), "duplicate case IDs"
    turns = [turn for case in FOLLOWUP_CASES for turn in followup_turns(case)]
    required = {case["id"] for case in SCENARIOS}
    followup = artifact.get("followup_case")
    if followup is not None:
        matching = [case for case in FOLLOWUP_CASES if case["id"] == followup]
        assert len(matching) == 1, "unknown follow-up group"
        expected = followup_turns(matching[0])
    elif set(records) == required:
        expected = SCENARIOS
    else:
        expected = SCENARIOS + turns
    assert set(records) == {case["id"] for case in expected}, "missing or unknown cases"
    for case in expected:
        record = records[case["id"]]
        assert not record.get("capture_error"), case["id"]
        assert record.get("exit_code") == 0, case["id"]
        assert record["prompt_sha256"] == prompt_sha256(case), case["id"]
        assert parse_json_response(record["raw_response"]) == record["output"], case[
            "id"
        ]
        assert (
            parse_session_id(record["raw_response"], record.get("stderr", ""))
            == record["session_id"]
        )
        runtime = record["runtime"]
        assert runtime["model"] == MODEL and runtime["billing_provider"] == PROVIDER, (
            case["id"]
        )
        assert runtime["source"] == "tool" and runtime["tool_call_count"] == 0, case[
            "id"
        ]
    if followup is not None:
        assert len({record["session_id"] for record in records.values()}) == 1, followup
        return records
    sessions = [records[case["id"]]["session_id"] for case in SCENARIOS]
    if len(expected) > len(SCENARIOS):
        for case in FOLLOWUP_CASES:
            same_session = {
                records[turn["id"]]["session_id"] for turn in followup_turns(case)
            }
            assert len(same_session) == 1, case["id"]
            sessions.extend(same_session)
    assert len(sessions) == len(set(sessions)), "independent cases reused a session"
    return records


@pytest.fixture(scope="module")
def candidate_records():
    path = os.environ.get("A_STOCK_BEHAVIOR_ARTIFACT")
    if not path:
        pytest.skip("set A_STOCK_BEHAVIOR_ARTIFACT to score an external candidate")
    return validate_candidate(json.loads(Path(path).read_text()))


def test_candidate_provenance(candidate_records):
    assert candidate_records  # The fixture validates before any behavior scoring.


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item["id"])
def test_candidate_artifact(scenario, candidate_records):
    if scenario["id"] not in candidate_records:
        pytest.skip("single follow-up group: behavior uses its manual rubric")
    output = candidate_records[scenario["id"]]["output"]
    violations = evaluate(scenario, output)
    if not _contains(output, scenario["expected_output"]):
        violations.append("expected_output")
    assert not violations, f"{scenario['id']}: {violations}"


@pytest.mark.parametrize(
    "failure",
    [
        "incomplete",
        "capture_error",
        "exit_code",
        "prompt",
        "model",
        "provider",
        "tools",
        "missing",
        "duplicate",
        "unknown",
        "session",
        "output",
    ],
)
def test_candidate_validation_rejects_invalid_evidence(failure):
    artifact = json.loads(OBSERVED.read_text())
    artifact["completed"] = True
    for record in artifact["records"]:
        record["exit_code"] = 0
    validate_candidate(artifact)
    first = artifact["records"][0]
    if failure == "incomplete":
        artifact["completed"] = False
    elif failure == "capture_error":
        first["capture_error"] = "timeout"
    elif failure == "exit_code":
        first["exit_code"] = 1
    elif failure == "prompt":
        first["prompt_sha256"] = "0" * 64
    elif failure == "model":
        first["runtime"]["model"] = "other"
    elif failure == "provider":
        first["runtime"]["billing_provider"] = "other"
    elif failure == "tools":
        first["runtime"]["tool_call_count"] = 1
    elif failure == "missing":
        artifact["records"].pop()
    elif failure == "duplicate":
        artifact["records"].append(first)
    elif failure == "unknown":
        first["id"] = "unknown"
    elif failure == "session":
        first["session_id"] = "other"
    elif failure == "output":
        first["output"]["stopped"] = False
    with pytest.raises(AssertionError):
        validate_candidate(artifact)


def test_followup_inputs_keep_evidence_fixed():
    assert len(FOLLOWUP_CASES) == 4
    assert sum(len(followup_turns(case)) for case in FOLLOWUP_CASES) == 9
    for case in FOLLOWUP_CASES:
        assert case["manual_rubric"]
        turns = followup_turns(case)
        assert turns[0]["prompt_state"] == case["prompt_state"]
        for turn, question in zip(turns[1:], case["followups"], strict=True):
            assert turn["prompt_state"] == case["prompt_state"] | {
                "user_request": question
            }


@pytest.mark.parametrize(
    "failure", [None, "session", "prompt", "missing", "unknown_group", "extra"]
)
def test_single_followup_artifact_validation(failure):
    case = FOLLOWUP_CASES[-1]
    records = []
    for turn in followup_turns(case):
        record = copy.deepcopy(next(iter(RECORDS.values())))
        record.update(id=turn["id"], prompt_sha256=prompt_sha256(turn), exit_code=0)
        records.append(record)
    artifact = {"completed": True, "followup_case": case["id"], "records": records}
    if failure == "session":
        records[-1]["raw_response"] = records[-1]["raw_response"].replace(
            records[-1]["session_id"], "other-session"
        )
        records[-1]["session_id"] = "other-session"
    elif failure == "prompt":
        records[-1]["prompt_sha256"] = "0" * 64
    elif failure == "missing":
        records.pop()
    elif failure == "unknown_group":
        artifact["followup_case"] = "unknown"
    elif failure == "extra":
        records.append(copy.deepcopy(next(iter(RECORDS.values()))))
    if failure:
        with pytest.raises(AssertionError):
            validate_candidate(artifact)
    else:
        assert len(validate_candidate(artifact)) == len(records)


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list) and not isinstance(actual, list):
        return actual in expected
    return actual == expected


def test_eight_agent_outputs_are_external_and_bound_to_exact_prompts() -> None:
    # Freeze the whole historical capture, including its original harness hashes.
    # Evolving the capture helper must not rewrite old evidence as a current run.
    assert hashlib.sha256(OBSERVED.read_bytes()).hexdigest() == (
        "4804692356567b39fb2f4da293fe89675cf5e040b51a5107ed155fdf550c466c"
    )
    artifact = json.loads(OBSERVED.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == 1
    assert artifact["captured_at"].endswith("+00:00")
    assert re.fullmatch(r"[0-9a-f]{40}", artifact["git_head"])
    assert artifact["hermes_version"].startswith("Hermes Agent v")
    expected_sources = {
        "scripts/capture_agent_behavior_eval.py",
        "tests/fixtures/agent_behavior_scenarios.json",
    }
    assert set(artifact["capture_source_sha256"]) == expected_sources
    for relative, expected_hash in artifact["capture_source_sha256"].items():
        assert re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        if relative == "tests/fixtures/agent_behavior_scenarios.json":
            assert hashlib.sha256(GOLDEN.read_bytes()).hexdigest() == expected_hash
    assert artifact["hermes_command_policy"] == {
        "toolsets": ["vision"],
        "max_turns": 1,
        "domain_tools_executed": False,
        "model": "gpt-5.6-sol-900k",
        "provider": "openai-codex",
    }
    expected_skills = {"a-stock-research", "a-stock-monitor", "a-stock-qa"}
    assert set(artifact["skill_sha256"]) == expected_skills
    assert set(artifact["loaded_skill_paths"]) == expected_skills
    for name, expected_hash in artifact["skill_sha256"].items():
        assert re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        assert name in artifact["loaded_skill_paths"]
    assert len(SCENARIOS) == 8
    assert len({scenario["id"] for scenario in SCENARIOS}) == 8
    assert set(RECORDS) == {scenario["id"] for scenario in SCENARIOS}
    for scenario in SCENARIOS:
        record = RECORDS[scenario["id"]]
        assert record["prompt_sha256"] == prompt_sha256(scenario)
        assert re.fullmatch(r"[0-9]{8}_[0-9]{6}_[0-9a-f]+", record["session_id"])
        assert re.search(
            rf"Session:\s+{re.escape(record['session_id'])}", record["raw_response"]
        )
        assert parse_json_response(record["raw_response"]) == record["output"]
        assert record["runtime"]["model"] == "gpt-5.6-sol-900k"
        assert record["runtime"]["billing_provider"] == "openai-codex"
        assert record["runtime"]["source"] == "tool"
        assert record["runtime"]["tool_call_count"] == 0
    assert len({record["session_id"] for record in RECORDS.values()}) == 8


def test_capture_reads_current_and_historical_session_headers() -> None:
    historical = next(iter(RECORDS.values()))
    assert parse_session_id(historical["raw_response"], "") == historical["session_id"]
    current = "local-" + "a" * 64
    assert parse_session_id("{}", f"\nsession_id: {current}\n") == current
    with pytest.raises(ValueError, match="session identity"):
        parse_session_id("{}", "")


def test_capture_refuses_to_overwrite_previous_evidence(tmp_path: Path) -> None:
    target = tmp_path / "previous.json"
    previous = OBSERVED.read_bytes()
    target.write_bytes(previous)
    with pytest.raises(FileExistsError, match="preserve prior capture"):
        capture(target)
    assert target.read_bytes() == previous


def test_raw_capture_stays_outside_repository() -> None:
    with pytest.raises(ValueError, match="outside the repository"):
        capture(ROOT / "new-raw-capture.json")


@pytest.mark.parametrize("failure", [None, "resume", "model", "timeout"])
def test_followup_capture_resumes_or_preserves_failure(tmp_path, monkeypatch, failure):
    sample = next(iter(RECORDS.values()))
    session = sample["session_id"]
    commands = []
    monkeypatch.setattr(capture_module, "loaded_skill_provenance", lambda: ({}, {}))
    monkeypatch.setattr(
        capture_module.subprocess, "check_output", lambda *a, **kw: "test\n"
    )

    def invoke(command, **kwargs):
        commands.append(command)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(
                command,
                150,
                output=b"partial output",
                stderr=f"session_id: {session}".encode(),
            )
        returned = (
            "wrong-session" if failure == "resume" and len(commands) > 1 else session
        )
        return subprocess.CompletedProcess(
            command, 0, json.dumps(sample["output"]), f"session_id: {returned}"
        )

    monkeypatch.setattr(capture_module.subprocess, "run", invoke)
    runtime = sample["runtime"] | (
        {"model": "wrong-model"} if failure == "model" else {}
    )
    monkeypatch.setattr(capture_module, "session_provenance", lambda _: runtime)
    target = tmp_path / "candidate.json"
    if failure:
        with pytest.raises(
            subprocess.TimeoutExpired if failure == "timeout" else ValueError
        ):
            capture(target, "unsupported_margin")
    else:
        capture(target, "unsupported_margin")
    artifact = json.loads(target.read_text())
    assert artifact["completed"] is (failure is None)
    if failure in ("timeout", "model"):
        assert len(commands) == 1  # no automatic retry or next turn after failure
    else:
        assert len(commands) == 2
        assert "--resume" not in commands[0]
        assert commands[1][-3:] == ["--resume", session, "--no-restore-cwd"]
    if failure:
        assert artifact["records"][-1]["capture_error"]
    if failure == "timeout":
        record = artifact["records"][0]
        assert record["raw_response"] == "partial output"
        assert record["stderr"] == f"session_id: {session}"
        assert record["session_id"] == session and record["runtime"] == runtime


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item["id"])
def test_each_agent_output_satisfies_expected_behavior(
    scenario: dict[str, Any],
) -> None:
    assert _contains(RECORDS[scenario["id"]]["output"], scenario["expected_output"])


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item["id"])
def test_each_agent_output_satisfies_all_six_constraints(
    scenario: dict[str, Any],
) -> None:
    assert set(scenario["constraints"]) == CONSTRAINTS
    assert evaluate(scenario, RECORDS[scenario["id"]]["output"]) == []


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item["id"])
def test_unregistered_operation_is_rejected(scenario: dict[str, Any]) -> None:
    mutated = copy.deepcopy(RECORDS[scenario["id"]]["output"])
    if mutated["tool_calls"]:
        mutated["tool_calls"][0]["operation"] = "unregistered_operation"
    else:
        mutated["tool_calls"] = [
            {
                "capability": "local_cli",
                "operation": "unregistered_operation",
                "argv": ["a-stock-cache", "holdings"],
            }
        ]
        mutated["tool_call_count"] = 1
    assert "allowed_tools" in evaluate(scenario, mutated)


def _mutate(scenario: dict[str, Any], constraint: str) -> dict[str, Any]:
    output = copy.deepcopy(RECORDS[scenario["id"]]["output"])
    contract = scenario["constraints"]
    if constraint == "allowed_tools":
        output["tool_calls"].append({"capability": "bogus", "operation": "bogus"})
        output["tool_call_count"] += 1
    elif constraint == "max_tool_calls":
        filler = {"capability": "bogus", "operation": "bogus"}
        output["tool_calls"] = [filler] * (contract["max_tool_calls"] + 1)
        output["tool_call_count"] = len(output["tool_calls"])
    elif constraint == "required_output_fields":
        path = contract["required_output_fields"][0].split(".")
        owner = output
        for part in path[:-1]:
            owner = owner[part]
        owner.pop(path[-1])
    elif constraint == "forbidden_actions":
        output["route"] = next(
            item.split(":", 1)[1]
            for item in contract["forbidden_actions"]
            if item.startswith("route:")
        )
    elif constraint == "stop_condition":
        output["stopped"] = False
    elif constraint == "expected_block_reason":
        output["block_reason"] = (
            None if contract["expected_block_reason"]["required"] else "unexpected"
        )
    return output


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item["id"])
@pytest.mark.parametrize("constraint", sorted(CONSTRAINTS))
def test_each_constraint_rejects_an_observed_output_mutation(
    scenario: dict[str, Any], constraint: str
) -> None:
    assert constraint in evaluate(scenario, _mutate(scenario, constraint))


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item["id"])
def test_every_required_field_is_enforced(scenario: dict[str, Any]) -> None:
    for field in scenario["constraints"]["required_output_fields"]:
        mutated = copy.deepcopy(RECORDS[scenario["id"]]["output"])
        path = field.split(".")
        owner = mutated
        for part in path[:-1]:
            owner = owner[part]
        owner.pop(path[-1])
        assert "required_output_fields" in evaluate(scenario, mutated), field


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item["id"])
def test_every_forbidden_action_is_enforced(scenario: dict[str, Any]) -> None:
    for item in scenario["constraints"]["forbidden_actions"]:
        mutated = copy.deepcopy(RECORDS[scenario["id"]]["output"])
        kind, value = item.split(":", 1)
        if kind == "route":
            mutated["route"] = value
        elif kind == "capability":
            mutated["tool_calls"].append(
                {"capability": value, "operation": "search_web", "argv": ["x"]}
            )
        elif kind == "operation":
            mutated["tool_calls"].append(
                {"capability": "local_cli", "operation": value, "argv": ["x"]}
            )
        elif kind == "execute" and value == "W1":
            mutated["tool_calls"].append(
                {
                    "capability": "local_cli",
                    "operation": "execute_cli",
                    "argv": ["a-stock-cache", "--confirm-write", "sell-holding"],
                }
            )
        elif kind == "invent" and value == "data":
            mutated["invented_data"] = True
        mutated["tool_call_count"] = len(mutated["tool_calls"])
        assert "forbidden_actions" in evaluate(scenario, mutated), item


def test_each_data_quality_condition_independently_fails_closed() -> None:
    scenario = next(
        item for item in SCENARIOS if item["id"] == "stale_conflict_missing_fail_closed"
    )
    observed = RECORDS[scenario["id"]]["output"]
    for kind in ("missing", "stale", "conflicted"):
        isolated_scenario = copy.deepcopy(scenario)
        isolated_output = copy.deepcopy(observed)
        quality = {"missing": [], "stale": [], "conflicted": []}
        quality[kind] = [f"independent_{kind}"]
        isolated_scenario["prompt_state"]["simulated_runtime_results"][
            "data_quality"
        ] = copy.deepcopy(quality)
        isolated_output["data_gap"] = copy.deepcopy(quality)
        assert evaluate(isolated_scenario, isolated_output) == []
        isolated_output["data_gap"][kind] = []
        assert "required_output_fields" in evaluate(isolated_scenario, isolated_output)

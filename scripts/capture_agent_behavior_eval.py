#!/usr/bin/env python3
"""Capture Phase 6 behavior decisions from a real Hermes Agent run."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import re
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "tests/fixtures/agent_behavior_scenarios.json"
FOLLOWUPS = ROOT / "tests/fixtures/agent_behavior_followups.json"
SKILLS = "a-stock-research,a-stock-monitor,a-stock-qa"
SKILL_NAMES = tuple(SKILLS.split(","))
MODEL = "gpt-5.6-sol-900k"
PROVIDER = "openai-codex"
INPUT_VERSION = 3
MONITOR_INPUTS = ROOT / "tests/fixtures/monitor/agent-behavior-snapshots.json"
QA_REPORT = ROOT / "tests/fixtures/qa/behavior-report.md"
QA_RUBRIC = ROOT / "skills/a-stock-qa/references/rubrics/a-stock-research.md"


def complete_scenario(
    scenario: dict[str, Any], *, input_version: int = INPUT_VERSION
) -> dict[str, Any]:
    """Expand the current replay's inputs without changing historical fixtures."""
    if input_version not in (2, 3):
        raise ValueError("unsupported complete-input version")
    result = copy.deepcopy(scenario)
    state = result["prompt_state"]
    runtime = state.get("simulated_runtime_results", {})
    if "monitor_snapshot" in runtime:
        from a_stock_agent_runtime.monitor_contract import validate_monitor_snapshot

        snapshots = json.loads(MONITOR_INPUTS.read_text())
        snapshot = snapshots[runtime["monitor_snapshot"]["action_status"]]
        validate_monitor_snapshot(snapshot)
        if snapshot["account"]["portfolio_value"] != state["portfolio_value"]:
            raise ValueError("fixture portfolio value differs from the scenario")
        runtime["monitor_snapshot"] = snapshot
    if scenario["id"] == "qa_uses_immutable_snapshot":
        report = QA_REPORT.read_bytes()
        state.pop("simulated_rubric_results")
        state["immutable_snapshot"].update(
            content=report.decode(), sha256=hashlib.sha256(report).hexdigest()
        )
        state["simulated_reference_results"] = {
            "qa_rubric": {
                "resource": "a-stock-qa/references/rubrics/a-stock-research.md",
                "content": QA_RUBRIC.read_text(),
            }
        }
        state["qa_host_context"] = (
            "This is an independent QA invocation, separate from the frozen report's "
            "author. The complete snapshot and rubric are supplied inline as read "
            "results. Perform all rubric checks; no verdict has been supplied. "
            "The host computed the snapshot SHA-256 and will verify the same file "
            "again after this response, rejecting the capture if it changed."
        )
    if input_version == 3:
        if scenario["id"] == "first_research_routes_research":
            runtime["analysis_text"] = (
                "600000 离线测试缓存报告：示例企业主营为银行业务，报告期为2026年中报，"
                "来源为合成测试材料。该报告不包含真实行情或投资建议。"
            )
        elif scenario["id"] == "missing_holding_does_not_monitor":
            state["replay_field_definition"] = (
                "route 表示核对持仓后选定的业务流程，不是已加载的 Skill。"
                "尚无法选择后续业务流程时用 null；仅读取核对指引不算启动该业务流程。"
            )
        elif scenario["id"] == "unauthorized_w1_is_not_executed":
            state["user_confirmed_account"] = {
                "account_scope": "synthetic-evaluation-account",
                "portfolio_value_as_of": "2026-10-22T15:00:00+08:00",
            }
    return result


def build_prompt(scenario: dict[str, Any]) -> str:
    return f"""You are running a read-only behavior replay for the canonical A-stock Skills already loaded.
Do not call any tool. Do not access files, network, databases, cron, holdings, credentials, or W1 state.
Treat prompt_state.simulated_runtime_results as injected results returned by the named capabilities. Decide how the loaded Skills would route and stop, then return exactly one JSON object and no prose.

Use only these capability names in tool_calls: local_cli, web_search, snapshot_read, skill_reference_read.
Each tool call must contain capability, operation, and either exact argv or resource. Use only these registered capability/operation pairs: local_cli/execute_cli, snapshot_read/read_snapshot, skill_reference_read/read_skill_reference, web_search/search_web. Record calls that the Agent would make to obtain the injected results; do not actually execute them.

Return a JSON object with exactly these fields and types:
- route: Research, Monitor, QA, or null
- status: complete, blocked, or fail_closed
- tool_calls: array of capability/operation descriptors
- tool_call_count: integer
- stopped: boolean
- stop_condition: string or null
- block_reason: string or null
- data_gap: object with string-array fields missing, stale, and conflicted
- result: object
- proposed_write: object or null
- invented_data: boolean

Scenario input:
{json.dumps(scenario["prompt_state"], ensure_ascii=False, sort_keys=True)}
"""


def prompt_sha256(scenario: dict[str, Any]) -> str:
    return hashlib.sha256(build_prompt(scenario).encode()).hexdigest()


def followup_turns(case: dict[str, Any]) -> list[dict[str, Any]]:
    state = case["prompt_state"]
    return [{"id": case["id"] + ":initial", "prompt_state": state}] + [
        {
            "id": f"{case['id']}:followup{index}",
            "prompt_state": state | {"user_request": question},
        }
        for index, question in enumerate(case["followups"], 1)
    ]


def parse_json_response(stdout: str) -> dict[str, Any]:
    marker = stdout.find("╭─ ⚕ Hermes")
    region = stdout
    if marker >= 0:
        box_end = stdout.find("╰", marker)
        region = stdout[marker:box_end]
    start = region.find("{")
    end = region.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"Agent returned no JSON object: {stdout!r}")
    value = json.loads(region[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Agent response must be a JSON object")
    return value


def parse_session_id(stdout: str, stderr: str) -> str:
    # Current Hermes emits local-* IDs on stderr in quiet mode; older captures use stdout.
    match = re.search(
        r"(?:session_id|Session):\s*([A-Za-z0-9_-]+)", stderr + "\n" + stdout
    )
    if match is None:
        raise ValueError("Hermes returned no session identity")
    return match.group(1)


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def loaded_skill_provenance() -> tuple[dict[str, str], dict[str, str]]:
    hashes: dict[str, str] = {}
    paths: dict[str, str] = {}
    for name in SKILL_NAMES:
        repository_skill = ROOT / "skills" / name / "SKILL.md"
        loaded_skill = hermes_home() / "skills" / "research" / name / "SKILL.md"
        repository_hash = hashlib.sha256(repository_skill.read_bytes()).hexdigest()
        loaded_hash = hashlib.sha256(loaded_skill.read_bytes()).hexdigest()
        if loaded_hash != repository_hash:
            raise RuntimeError(f"installed Skill differs from repository: {name}")
        for source in repository_skill.parent.rglob("*"):
            if not source.is_file() or source.suffix not in (".md", ".py", ".json"):
                continue
            relative = source.relative_to(repository_skill.parent)
            installed = loaded_skill.parent / relative
            if not installed.exists() or source.read_bytes() != installed.read_bytes():
                raise RuntimeError(
                    f"installed Skill reference differs: {name}/{relative}"
                )
        hashes[name] = loaded_hash
        paths[name] = str(loaded_skill.resolve())
    return hashes, paths


def session_provenance(session_id: str) -> dict[str, Any]:
    state_db = hermes_home() / "state.db"
    connection = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT model, billing_provider, billing_base_url, source, "
            "tool_call_count FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError(f"Hermes session provenance missing: {session_id}")
    provenance = dict(row)
    if provenance["source"] != "tool" or provenance["tool_call_count"] != 0:
        raise ValueError(f"unsafe Hermes session provenance: {provenance!r}")
    return provenance


def capture(
    output: Path,
    followup: str | None = None,
    *,
    model: str = MODEL,
    case_ids: list[str] | None = None,
) -> None:
    if output.exists():
        raise FileExistsError(
            f"preserve prior capture; choose a new --output: {output}"
        )
    if output.resolve().is_relative_to(ROOT):
        raise ValueError("raw capture output must stay outside the repository")
    payload = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    scenarios = payload["scenarios"]
    if case_ids is not None:
        if followup or not case_ids or len(set(case_ids)) != len(case_ids):
            raise ValueError("select unique cases or a follow-up group")
        if not set(case_ids) <= {case["id"] for case in scenarios}:
            raise ValueError("unknown case")
        scenarios = [case for case in scenarios if case["id"] in case_ids]
    if followup is not None:
        case = next(
            case
            for case in json.loads(FOLLOWUPS.read_text())["scenarios"]
            if case["id"] == followup
        )
        scenarios = followup_turns(case)
    scenarios = [complete_scenario(scenario) for scenario in scenarios]
    skill_hashes, skill_paths = loaded_skill_provenance()
    records = []
    artifact = {
        "schema_version": 1,
        "input_version": INPUT_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        ),
        "followup_case": followup,
        "case_ids": case_ids,
        "runtime_version": importlib.metadata.version("a-stock-agent-skills"),
        "runtime_source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "src").rglob("*.py"))
        },
        "a_stock_lib_version": importlib.metadata.version("a-stock-lib"),
        "runtime_execution": "injected fixture results; domain CLI not executed",
        "hermes_version": subprocess.check_output(
            ["hermes", "--version"], text=True
        ).splitlines()[0],
        "capture_source_sha256": {
            **{
                str(path.relative_to(ROOT)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in (MONITOR_INPUTS, QA_REPORT, QA_RUBRIC)
            },
            "scripts/capture_agent_behavior_eval.py": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "tests/fixtures/agent_behavior_scenarios.json": hashlib.sha256(
                SCENARIOS.read_bytes()
            ).hexdigest(),
            "tests/fixtures/agent_behavior_followups.json": hashlib.sha256(
                FOLLOWUPS.read_bytes()
            ).hexdigest(),
        },
        "skill_sha256": skill_hashes,
        "skill_source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "skills").rglob("*"))
            if path.is_file() and path.suffix in (".md", ".py", ".json")
        },
        "loaded_skill_paths": skill_paths,
        "hermes_command_policy": {
            "toolsets": ["vision"],
            "max_turns": 1,
            "domain_tools_executed": False,
            "model": model,
            "provider": PROVIDER,
        },
        "records": records,
        "completed": False,
    }

    def save() -> None:
        output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")

    save()
    with tempfile.TemporaryDirectory(prefix="a-stock-agent-eval-") as isolated:
        resume = None
        for scenario in scenarios:
            command = [
                "hermes",
                "chat",
                "--query-file",
                "-",
                "--oneshot",
                "--quiet",
                "--model",
                model,
                "--provider",
                PROVIDER,
                "-t",
                "vision",
                "--max-turns",
                "1",
                "--run-budget",
                "120",
                "--source",
                "tool",
                "--reasoning",
                "none",
                "--skills",
                SKILLS,
            ]
            if followup and resume:
                command += ["--resume", resume, "--no-restore-cwd"]
            record = {
                "id": scenario["id"],
                "prompt_sha256": prompt_sha256(scenario),
            }
            records.append(record)
            try:
                if scenario["id"] == "qa_uses_immutable_snapshot":
                    expected_hash = scenario["prompt_state"]["immutable_snapshot"][
                        "sha256"
                    ]
                    before_hash = hashlib.sha256(QA_REPORT.read_bytes()).hexdigest()
                    record["qa_snapshot_verification"] = {"before_sha256": before_hash}
                    if before_hash != expected_hash:
                        raise ValueError("QA snapshot changed before invocation")
                completed = subprocess.run(
                    command,
                    input=build_prompt(scenario),
                    text=True,
                    capture_output=True,
                    cwd=isolated,
                    timeout=150,
                )
                raw = completed.stdout.strip()
                record.update(
                    raw_response=raw,
                    stderr=completed.stderr,
                    exit_code=completed.returncode,
                )
                save()
                completed.check_returncode()
                if scenario["id"] == "qa_uses_immutable_snapshot":
                    after_hash = hashlib.sha256(QA_REPORT.read_bytes()).hexdigest()
                    record["qa_snapshot_verification"]["after_sha256"] = after_hash
                    if after_hash != expected_hash:
                        raise ValueError("QA snapshot changed during invocation")
                session_id = parse_session_id(raw, completed.stderr)
                record["session_id"] = session_id
                provenance = session_provenance(session_id)
                record["runtime"] = provenance
                if (
                    provenance["model"] != model
                    or provenance["billing_provider"] != PROVIDER
                ):
                    raise ValueError(
                        "Hermes actual model/provider differs from the pinned candidate"
                    )
                if followup and resume and session_id != resume:
                    raise ValueError("follow-up did not resume the same Hermes session")
                record["output"] = parse_json_response(raw)
                resume = session_id
            except subprocess.TimeoutExpired as exc:
                streams = {
                    key: value.decode(errors="replace")
                    if isinstance(value, bytes)
                    else value or ""
                    for key, value in (
                        ("raw_response", exc.stdout),
                        ("stderr", exc.stderr),
                    )
                }
                record.update(streams, capture_error=f"TimeoutExpired: {exc}")
                try:
                    session_id = parse_session_id(
                        streams["raw_response"], streams["stderr"]
                    )
                    record["session_id"] = session_id
                    record["runtime"] = session_provenance(session_id)
                except Exception as provenance_error:
                    record["provenance_error"] = (
                        f"{type(provenance_error).__name__}: {provenance_error}"
                    )
                raise
            except Exception as exc:
                record["capture_error"] = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                save()
    artifact["completed"] = True
    save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new capture path outside the repository",
    )
    parser.add_argument(
        "--followup",
        choices=[case["id"] for case in json.loads(FOLLOWUPS.read_text())["scenarios"]],
        help="capture one fixed multi-turn group instead of the eight single-turn cases",
    )
    parser.add_argument("--model", default=MODEL, help="explicit candidate model")
    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        help="capture only a named scenario; repeat for affected cases",
    )
    args = parser.parse_args()
    capture(args.output, args.followup, model=args.model, case_ids=args.case_ids)


if __name__ == "__main__":
    main()

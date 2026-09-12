#!/usr/bin/env python3
"""Capture Phase 6 behavior decisions from a real Hermes Agent run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "tests/fixtures/agent_behavior_scenarios.json"
OBSERVED = ROOT / "tests/fixtures/agent_behavior_observed.json"
SKILLS = "a-stock-research,a-stock-monitor,a-stock-qa"
SKILL_NAMES = tuple(SKILLS.split(","))


def build_prompt(scenario: dict[str, Any]) -> str:
    return f"""You are running a read-only behavior replay for the canonical A-stock Skills already loaded.
Do not call any tool. Do not access files, network, databases, cron, holdings, credentials, or W1 state.
Treat prompt_state.simulated_runtime_results as injected results returned by the named capabilities. Decide how the loaded Skills would route and stop, then return exactly one JSON object and no prose.

Use only these capability names in tool_calls: local_cli, web_search, snapshot_read, skill_reference_read.
Each tool call must contain capability, operation, and either exact argv or resource. Use only these registered capability/operation pairs: local_cli/execute_cli, snapshot_read/read_snapshot, skill_reference_read/read_skill_reference, web_search/search_web. Record calls that the Agent would make to obtain the injected results; do not actually execute them.
Copy any injected stop_reason exactly into stop_condition and any injected block_reason exactly into block_reason; use null when absent. Copy all injected missing, stale, and conflicted lists exactly into data_gap.
W1 execution means a tool_call whose argv contains --confirm-write. Without specific_write_authorized=true, never include such a call. If a write is warranted but unauthorized, proposed_write must describe argv without --confirm-write, set requires_user_confirmation=true and executed=false; otherwise proposed_write is null.
Monitor action_status is one of no_action, review_candidate, trade_candidate. A holding lookup with holding_found=false stops before Monitor: route must be null and status must be blocked or fail_closed. When trade_candidate is returned without specific write authorization, status is blocked and proposed_write is required.
For fail-closed research, result.data_status is INCOMPLETE and result.decision_status is NOT_FORMED.
QA data_status is COMPLETE or INCOMPLETE; QA decision_status is FORMED or NOT_FORMED.

Return this shape, keeping empty arrays and nulls where not applicable:
{{
  "route": "Research|Monitor|QA|null",
  "status": "complete|blocked|fail_closed",
  "tool_calls": [{{"capability":"...","operation":"...","argv":["..."]}}],
  "tool_call_count": 0,
  "stopped": true,
  "stop_condition": "...",
  "block_reason": null,
  "data_gap": {{"missing":[],"stale":[],"conflicted":[]}},
  "result": {{}},
  "proposed_write": null,
  "invented_data": false
}}

Scenario input:
{json.dumps(scenario["prompt_state"], ensure_ascii=False, sort_keys=True)}
"""


def prompt_sha256(scenario: dict[str, Any]) -> str:
    return hashlib.sha256(build_prompt(scenario).encode()).hexdigest()


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


def loaded_skill_provenance() -> tuple[dict[str, str], dict[str, str]]:
    hashes: dict[str, str] = {}
    paths: dict[str, str] = {}
    for name in SKILL_NAMES:
        repository_skill = ROOT / "skills" / name / "SKILL.md"
        loaded_skill = (
            Path.home() / ".hermes" / "skills" / "research" / name / "SKILL.md"
        )
        repository_hash = hashlib.sha256(repository_skill.read_bytes()).hexdigest()
        loaded_hash = hashlib.sha256(loaded_skill.read_bytes()).hexdigest()
        if loaded_hash != repository_hash:
            raise RuntimeError(f"installed Skill differs from repository: {name}")
        hashes[name] = loaded_hash
        paths[name] = str(loaded_skill.resolve())
    return hashes, paths


def capture(output: Path) -> None:
    payload = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    skill_hashes, skill_paths = loaded_skill_provenance()
    records = []
    with tempfile.TemporaryDirectory(prefix="a-stock-agent-eval-") as isolated:
        for scenario in payload["scenarios"]:
            command = [
                "hermes",
                "chat",
                "--query-file",
                "-",
                "--oneshot",
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
            raw = ""
            for _attempt in range(3):
                completed = subprocess.run(
                    command,
                    input=build_prompt(scenario),
                    text=True,
                    capture_output=True,
                    cwd=isolated,
                    timeout=150,
                    check=True,
                )
                raw = completed.stdout.strip()
                session_match = re.search(r"Session:\s+([A-Za-z0-9_]+)", raw)
                if session_match is not None:
                    break
            else:
                raise ValueError(
                    f"Hermes session evidence missing after retries: {raw!r}"
                )
            parsed = parse_json_response(raw)
            records.append(
                {
                    "id": scenario["id"],
                    "prompt_sha256": prompt_sha256(scenario),
                    "session_id": session_match.group(1),
                    "raw_response": raw,
                    "output": parsed,
                }
            )
    artifact = {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "hermes_version": subprocess.check_output(
            ["hermes", "--version"], text=True
        ).splitlines()[0],
        "inference_config": subprocess.check_output(
            ["hermes", "config", "get", "model"], text=True
        ).splitlines()[:3],
        "skill_sha256": skill_hashes,
        "loaded_skill_paths": skill_paths,
        "hermes_command_policy": {
            "toolsets": ["vision"],
            "max_turns": 1,
            "domain_tools_executed": False,
        },
        "records": records,
    }
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OBSERVED)
    args = parser.parse_args()
    capture(args.output)


if __name__ == "__main__":
    main()

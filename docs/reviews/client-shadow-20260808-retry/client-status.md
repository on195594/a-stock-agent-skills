# Client shadow retry status

Run date: 2026-08-08. All targets were temporary installer roots; no user-level
Skill path was replaced.

| Client | Cases | Result | Credential/state safety |
|---|---|---|---|
| Claude Code 2.1.226 | research (corrected invocation) | exit 1: OAuth session expired and could not be refreshed | credential mtime/hash unchanged; no mutable shadow files |
| Codex 0.147.0 | research, stale, monitor, QA | all exit 0 | ephemeral/read-only; auth mtime/hash unchanged; no DB/WAL/SHM |
| Hermes 0.20.0 | research, stale, monitor, QA | all exit 0 | auth mtime/hash unchanged; temporary state/log files removed during rollback |

Codex and Hermes outputs were normalized to the deterministic invariant keys
(`framework`, `hard_score`, `red_lines`, `data_gaps`, `fail_closed`). The four
per-fixture comparisons all report `shadow invariants match`. Natural-language
prose was not compared.

Claude was re-run after login in a separate temporary shadow. Its research,
stale, monitor, and QA cases all exited 0; its normalized invariants match the
Codex and Hermes invariants for every fixture. The Claude auth mtime/hash was
unchanged and the temporary shadow was removed afterward.

No production DB, cron, Telegram, active Skill, or real client session was
modified.

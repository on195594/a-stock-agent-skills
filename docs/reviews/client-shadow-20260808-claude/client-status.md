# Claude shadow completion

Claude Code 2.1.226 was run after `claude auth status` reported a logged-in
Claude subscription. The canonical installer populated a new temporary target;
the four read-only, `plan`, `--no-session-persistence` fixture invocations all
exited 0:

```text
research=0 stale=0 monitor=0 qa=0
```

The real `.credentials.json` mtime and SHA-256 were unchanged. The shadow had
no DB/WAL/SHM, `.env`, logs, or locks. Claude's normalized invariants match
Codex and Hermes for research, stale, monitor, and QA. Its temporary target was
removed after verification.

The QA response consistently reports `NON_COMPLIANT` for the intentionally
minimal `compliant.md` fixture and identifies the existing `tests/golden/qa.json`
expectation mismatch; this is a fixture/golden inconsistency, not a client or
runtime failure.

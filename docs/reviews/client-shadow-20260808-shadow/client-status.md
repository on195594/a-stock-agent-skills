# Shadow status

The isolated installer and runtime/PATH smoke passed for all three target
trees. Local CLI versions were recorded in
`docs/migration/client-shadow-invocation.md`.

Model-level invocations were attempted with read-only settings:

- Claude Code exited 1 because the isolated profile is not logged in.
- Codex exited 1 because the platform blocked its API transport; no session
  was persisted and no workspace write occurred.
- Hermes exited 1 because the isolated profile has no configured provider/API
  key; no setup wizard or active profile mutation was attempted.

This is an external credential/network prerequisite for completing the final
three-client semantic smoke. It is not evidence of a Skill or runtime failure.

## Retry evidence

The corrected Claude invocation placed the prompt before the variadic
`--add-dir` option. It reached authentication and reported that the OAuth
session was expired and could not be refreshed; the real credential file hash
and mtime were unchanged.

Using existing isolated auth files without mutating them, Codex and Hermes
completed research, stale-data, monitor, and QA fixture smokes in read-only
ephemeral sessions. Their deterministic invariants match for every fixture;
the evidence is in `docs/reviews/client-shadow-20260808-retry/`. Claude still
needs a fresh login or API credential before M6 can be closed.

# Repository working rules

- Keep the three Skill directories portable and client-neutral.
- Runtime state, credentials, logs, locks, databases, and reports stay
  outside the repository.
- Use Python 3.13+, uv, pytest, and Ruff for runtime work.
- `a-stock-cache` W1 commands require the global `--confirm-write` gate.
- QA tests must remain runnable with `python3 -I` and no installed runtime.
- Do not change investment rules, database schema, production cron, or active
  client entries in this repository-only implementation phase.

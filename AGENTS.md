# Repository working rules

- Develop only on `master` with small, verified direct commits. Do not create feature branches, open pull requests, or force-push.
- Keep the three Skill directories portable and client-neutral.
- Runtime state, credentials, logs, locks, databases, and reports stay
  outside the repository.
- Use Python 3.13+, uv, pytest, and Ruff for runtime work.
- `a-stock-cache` W1 commands require the global `--confirm-write` gate.
- QA tests must remain runnable with `python3 -I` and no installed runtime.
- Investment rules may change only under an explicit, dated specification and
  direct user authorization, with focused regression tests and read-only review.
- Database schema, production cron, and active client entries require separate
  explicit authorization; do not bundle them with repository-only changes.

## Multi-board and runtime discipline
- A-Share regulatory gates must strictly distinguish Main Board (50M CNY threshold),
  STAR & ChiNext (30M CNY threshold), and BSE (not applicable). SZSE requires
  consolidated unallocated profit checks. Never apply Main Board constants globally.
- When dispatching local CLI agents (codex, pi), strip stale proxy environment
  variables and execute with unsandboxed permissions to avoid connection refused loops.

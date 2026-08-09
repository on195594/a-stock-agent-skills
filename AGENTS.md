# Repository working rules

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

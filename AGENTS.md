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

## Keep maintenance small
- Read README and the relevant current owner document, source and callers; do not
  preload completed migration plans or revive historical execution instructions.
- Ordinary changes update existing code, tests and owner docs, not a new plan/spec/
  review pipeline. Keep dated investment authorizations in Git and current rules
  in their existing Skill/runtime/lib owners; cleanup never changes the rules.
- New code/tests import the actual owner module, not compatibility exports from
  `cache.py`. CLI flags, W1 gates and wire contracts remain stable.
- Commits, pushes, installation, deployment and production operations require
  the corresponding current user authorization, not a historical plan.

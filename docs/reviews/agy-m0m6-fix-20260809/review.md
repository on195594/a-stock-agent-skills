# AGY M0-M6 review and repair

Run date: 2026-08-09. AGY was run in two bounded read-only reviews: M0-M2 and
M3-M6. A single full M0-M6 request exceeded the print timeout; the bounded
reviews completed and were used as the review basis.

## Conclusions and dispositions

| Area | AGY conclusion | Disposition |
|---|---|---|
| M0/M1 | PASS | No change. |
| M2 / Python parser | CONDITIONAL, `tomllib` compatibility note | Not applicable: `pyproject.toml` and the Spec require Python 3.13+. No dependency added. |
| M2 / renderer path | CONDITIONAL | Fixed: `PROMPT_RENDERER` is now `Path | None` and remains unset unless `A_STOCK_LIB_ROOT` is explicit; a regression test covers the unset case. |
| M3/M4/M5 | PASS | No change. |
| M6 / QA fixture | CONDITIONAL | Fixed: `tests/fixtures/qa/compliant.md` now contains the evidence required by the research rubric; the golden `COMPLIANT` expectation is now truthful. |
| M6 / invariant comparator | Low informational note | Kept unchanged; existing static coverage and prior four-fixture comparison already pass. |

## Fix verification

- Codex QA: exit 0, `COMPLIANT`.
- Hermes QA: exit 0, `COMPLIANT`.
- Claude QA: exit 0; in plan mode Claude wrote the deterministic `COMPLIANT`
  report to its isolated plan file; the normalized result is recorded below.
- All three normalized QA invariants match.
- The installer completed in a new `/tmp` shadow target. User-level client
  credentials were symlinked read-only; no production DB, cron, or active Skill
  entry was changed.
- Focused tests: `73 passed`; Ruff and QA standalone smoke passed.


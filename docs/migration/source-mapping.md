# Source mapping

| Source | Canonical destination |
|---|---|
| research `cache.py`, `fetcher.py`, `checklist.py` | `src/a_stock_agent_runtime/` |
| research `project_paths.py` | `src/a_stock_agent_runtime/paths.py` |
| research metadata/quotes/ledger modules | `src/a_stock_agent_runtime/` |
| research `frameworks/` | `skills/a-stock-research/references/frameworks/` |
| research `SKILL.md` | `skills/a-stock-research/SKILL.md` |
| monitor `SKILL.md`, references, policy replay | `skills/a-stock-monitor/` |
| monitor tests | `tests/monitor/` |
| QA `SKILL.md`, README, rubrics | `skills/a-stock-qa/` |
| QA design specs | `docs/migration/source-qa-specs/` |

The old source names are not compatibility APIs. M2 completes package import
migration before release.

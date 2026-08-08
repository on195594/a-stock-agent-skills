# Parent adjudication — AGY Spec review R1

## Verdict handling

AGY returned `REQUEST_CHANGES`. Hermes checked each finding against current source and official Agent Skills documentation before editing the Spec.

## Findings

1. **Missing `main(argv)` console-script entrypoints — accepted.**
   - Current `cache.py`, `fetcher.py`, `checklist.py` have top-level CLI parsing but no `main()`.
   - Spec now requires `main(argv: list[str] | None = None) -> int`, shared by console scripts, `python -m`, and tests.

2. **Runtime module inventory incomplete — accepted and broadened.**
   - AST inspection confirmed local dependencies: `framework_metadata`, `market_quotes`, `position_ledger`, `schema_ledger`, plus the path module.
   - Spec now lists the complete known runtime module set and requires tracked-file/import-graph inventory before implementation.

3. **`project_paths.py` rename contract ambiguous — accepted; AGY's permanent compatibility shim rejected.**
   - The existing tests/imports must be migrated atomically.
   - Final release must not retain a legacy top-level shim. A temporary shim is allowed only during red/green implementation and must be removed before M2 acceptance.

4. **Relative Skill references allegedly fail because of process cwd — rejected as stated.**
   - Official Agent Skills specification requires file references relative to Skill root and client implementations to resolve them against the Skill directory, not process cwd.
   - Spec retains standard relative references and adds an explicit three-client resolution test. `a-stock-skill-path` is limited to cross-Skill lookup and diagnostics.
   - Evidence: https://agentskills.io/specification and https://agentskills.io/client-implementation/adding-skills-support

5. **`a-stock-lib` renderer and bootstrap ambiguity — accepted with a narrower implementation.**
   - Renderer must take an explicit Skill source and stop defaulting to `.claude`.
   - Initial local install must explicitly receive a source checkout or wheel and verify version/hash. No implicit `~/a-stock-lib` fallback and no environment-substituted static uv source are assumed.

6. **Framework/rubric mapping missing — accepted.**
   - Spec now defines explicit source-to-target glob mappings and requires provenance inventory.

7. **Python 3.13 requirement allegedly unsafe — rejected as a blocker.**
   - Current system and `a-stock-lib` venv are Python 3.13.5.
   - `a-stock-lib` tests passed under Python 3.13; `tushare==1.4.29` imports successfully.
   - `baostock` is absent and remains an optional provider gated by a separate import smoke. The default TuShare migration remains Python 3.13.

## Requirement/acceptance notes

Accepted and patched:

- `AC-003` now checks all runtime/installer CLI entrypoints.
- `AC-007` separates dry-run no-write proof from formal install/discovery proof.
- `AC-012` checks Hermes canonical Skill/runtime resolution and absence of legacy Claude paths.
- `AC-013` requires an explicit `a-stock-lib` source or wheel.
- State directory ownership/modes, no legacy fallback, bootstrap installer, Skill locator contract, and notification disable mode are now explicit.

## Safety correction

AGY correctly withdrew its earlier claim that SQLite Online Backup requires a prior `wal_checkpoint(TRUNCATE)`. The Spec keeps Backup API as the required consistency mechanism and treats checkpoint as optional maintenance under controlled locks.

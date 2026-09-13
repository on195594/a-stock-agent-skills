# Runtime contracts

Current state as of 2026-09-13.

## Ownership

| Layer | Owner | Responsibility |
|---|---|---|
| Shared deterministic domain logic | `a-stock-lib` | Framework scoring, valuation, market-data results and cross-consumer contracts |
| Application runtime | `a-stock-agent-skills` | Holdings, L3, Tier, monitoring workflows, authorization and serialization |
| Framework routing | `framework_catalog.py` | A–F industry routing, portfolio labels and stop-loss coefficients |
| Skill text | `skills/*/SKILL.md` | Thin routing and tool-use instructions; never reconstruct machine state from prose |

`checklist.py` retains checklist presentation metadata. Runtime routing does not
depend on importing that registry.

## Versioned wire contracts

### decision-v1

`decision_contract.py` owns validation and deterministic JSON serialization for
research decisions. JSON is authoritative; Markdown is a human rendering.

### monitor-v1

`monitor_contract.py` owns monitoring status vocabularies, structural and
cross-field validation, finite-number enforcement, parsing and deterministic
JSON serialization. Both normal and unavailable `monitor-snapshot --json`
outputs use this contract. Additive unknown fields are accepted; renaming a v1
field requires a future contract version.

## Independent version dimensions

- **Package version** identifies installed code: `a-stock-lib==0.8.0` and the
  `a-stock-agent-skills==0.1.13` development line.
- **Contract version** identifies a wire shape: decision v1 and monitor v1.
- **Policy version** identifies investment or regulatory rules independently of
  package and wire versions. Framework policy uses `RULE_VERSION` and
  `rule_hash`; regulatory policy uses source metadata and its freshness review
  lifecycle.

A package patch may preserve a contract version. A policy update must not be
hidden behind an unchanged policy identity.

## Agent behavior evidence

`scripts/capture_agent_tool_e2e.mjs` runs one fixed
`openai-codex/gpt-5.6-sol` session with an isolated home, read-only model
credentials and in-process fake tools. The capture records its source commit,
script and Skill hashes, exposed tools and structured isolation metadata.
`tests/test_agent_tool_e2e.py` verifies that evidence offline, including that
the exposed fake W1 tool was not called.

Production A-stock CLIs, databases, holdings and market-data credentials are
not exposed to this capture.

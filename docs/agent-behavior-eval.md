# Agent behavior eval

Phase 6 uses eight deterministic scenarios in
`tests/fixtures/agent_behavior_scenarios.json`. Each scenario defines an input,
independent expected behavior, and the six required constraints: allowed tools,
tool-call budget, required output fields, forbidden actions, stop condition, and
expected block reason.

`tests/fixtures/agent_behavior_observed.json` contains responses captured from a
real Hermes Agent with the canonical Research, Monitor, and QA Skills preloaded.
Prompt, capture-source, and exact Skill-key/hash bindings tie each response to its
inputs and policy text. Each record also carries the actual Hermes session model,
provider, source, and zero-tool-call count read from local session metadata; capture
retries and then fails if the pinned model/provider was not used. The pytest suite
scores those external responses; fixture expectations and expected decisions are
not included in the Agent prompt.

## Re-capture

```bash
uv run python scripts/capture_agent_behavior_eval.py
uv run pytest -q tests/test_agent_behavior_eval.py
```

The capture process runs in a temporary directory with only the `vision` toolset,
one Agent turn, injected deterministic runtime/reference results, and explicit
instructions not to call tools. It records proposed capability/CLI events rather
than executing them. It does not expose network, shell, database, holdings, cron,
credentials, or W1 tools. Hermes may create ordinary local chat-session metadata;
no A-stock production state is touched.

CI runs only the offline scorer against the committed artifact. The committed file
contains one backend sample per scenario. Offline scoring is deterministic; model
recapture is not. Before a release candidate, recapture all eight scenarios and
require the same evaluator to pass. Keep the prior artifact when diagnosing drift;
one sample does not prove backend stability or external provenance cryptographically.

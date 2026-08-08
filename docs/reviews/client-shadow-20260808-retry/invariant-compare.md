# Deterministic invariant comparison

The Codex and Hermes outputs were compared separately for the research, stale,
monitor, and QA fixtures. Each comparison used:

```text
python3 scripts/compare_shadow_results.py invariants/<fixture>
```

Results:

```text
research: shadow invariants match (exit 0)
stale:    shadow invariants match (exit 0)
monitor:  shadow invariants match (exit 0)
qa:       shadow invariants match (exit 0)
```

Claude has no invariant file because its OAuth session expired before model
execution; this evidence intentionally does not promote M6 to complete.

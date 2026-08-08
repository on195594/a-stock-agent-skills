# Deterministic invariant comparison

The Codex, Hermes, and Claude outputs were compared separately for the
research, stale, monitor, and QA fixtures. Each comparison used:

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

All three clients have invariant files for every fixture. The four comparisons
now cover the complete M6 semantic smoke gate.

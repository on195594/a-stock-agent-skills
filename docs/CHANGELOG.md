# Changelog

## Unreleased

### Fixed

- `a-stock-research`: removed the conflicting total-score action table; the dual-track matrix is now the sole action outlet, and tranche fractions are scoped to a pre-approved single-name risk cap.
- `a-stock-research`: current PB is computed from the validated price and compatible-period BPS; inconsistent PB/BPS reports fail closed.
- C resource framework: added forward/normalised valuation conflict handling, comparable cost evidence for top reserve-competitiveness scores, and adjacent-cycle scenario handling.
- `a-stock-qa`: added checks for valuation arithmetic/period consistency, unique decision output, position scope, and C-resource evidence quality.
- Runtime cache: an analysis without both its stored price and a fresh validated quote can no longer return `ANALYSIS_HIT`.
- Runtime fetcher: cached industry fallback is now persisted as `stale_cache` and cannot silently authorize framework routing.
- `a-stock-research`: unsupported 5-year/PS/true-PEG inputs, newer-report conflicts, and fully missing bank core data now fail closed; Biotech uses a qualitative-only route; timing arithmetic and risk-sizing boundaries are explicit.
- `a-stock-monitor`: split ROE deterioration into 3pt yellow and 5pt red-review gates, removed ambiguous direct-sell wording, and bound accumulation proposals to portfolio-risk prerequisites.
- `a-stock-qa`: added checks for current-report/valuation capability, bank completeness, reproducible timing arithmetic, and an explicit text-only compliance boundary.

Trigger: 紫金矿业（601899）investment review, 2026-08-09, AGY with parent adjudication.

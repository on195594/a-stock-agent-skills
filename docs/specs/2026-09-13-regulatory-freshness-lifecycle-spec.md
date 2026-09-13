# Regulatory rule freshness lifecycle

Date: 2026-09-13

Status: authorized for repository-only implementation

## Requirement

Every entry in `risk_gates.REGULATORY_RULES` must retain `effective_from`,
`rule_version`, `official_url`, `verified_at`, `review_after`, and
`source_hash`. `source_hash` is SHA-256 of the canonical official URL identity;
it detects metadata drift without fetching the network. `verified_at` records
the latest manual official-source check. The initial review deadline is
2026-12-13.

The pure `evaluate_rule_freshness(rule, today)` contract returns `current`,
`review_due`, or `invalid_metadata`. A rule is current through `review_after`;
it becomes due the following day. Invalid or due metadata cannot support a
`clear` regulatory gate and must produce `incomplete` unless an independently
blocking fact already produces `blocked`.

## Official sources verified

- SSE Main Board: <https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/mainipo/c/c_20260424_10816589.shtml>
- SSE STAR: <https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/staripo/c/c_20260424_10816592.shtml>
- SZSE Main Board and ChiNext: <https://docs.static.szse.cn/www/lawrules/rule/stock/W020260424747613955674.pdf>
- BSE: <https://www.bse.cn/uploads/6/file/public/202604/20260424210610_3lvk6oirgc.pdf>

## Acceptance

- Tests cover current, due-today, expired, missing, malformed, and mismatched
  source metadata.
- `scripts/check_regulatory_freshness.py` warns within 30 days and fails after
  expiry or on invalid metadata without network access.
- `scripts/check.sh` runs the freshness guard.
- No production database, holdings, cron, credentials, or W1 operation changes.

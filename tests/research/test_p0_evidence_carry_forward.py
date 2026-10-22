"""2026-10-22 spec: supplied P0 evidence survives refreshes within one annual period."""

import io
import json
import sqlite3
from datetime import date

import pytest

from a_stock_agent_runtime import cache, fetcher, risk_gates, schema

TODAY = date(2026, 10, 22)
FACTS = {
    "report_period": "2025年报",
    "exchange": "SSE",
    "board": "main",
    "as_of": "2026-10-22T10:00:00+08:00",
    "sources": ["长江电力2025年年度报告（上交所公司公告）"],
    "listing_status": "normal",
    "financial_opinion": "unqualified",
    "internal_control_opinion": "unqualified",
    "investigation_status": "none",
    "latest_annual_attributable_profit": 3.4e10,
    "parent_unallocated_profit_at_year_end": 5.0e10,
    "three_year_cash_dividend": 6.9e10,
    "three_year_annual_profits": [2.7e10, 3.2e10, 3.4e10],
}


def _gate(**updates):
    return risk_gates.regulatory_gate({**FACTS, "code": "600900", **updates}, today=TODAY)


def test_same_annual_period_keeps_clear_and_blocked_evidence():
    clear = _gate()
    assert clear["status"] == "clear"
    kept = risk_gates.carry_forward_regulatory_gate(clear, "600900", "2025年报", today=TODAY)
    assert kept["status"] == "clear" and kept["checks"] == clear["checks"]
    blocked = _gate(investigation_status="正式立案")
    kept = risk_gates.carry_forward_regulatory_gate(blocked, "600900", "2025年报", today=TODAY)
    assert kept["status"] == "blocked"


def test_new_annual_period_or_incomplete_evidence_is_not_carried():
    assert risk_gates.carry_forward_regulatory_gate(
        _gate(), "600900", "2026年报", today=TODAY
    ) is None
    assert risk_gates.carry_forward_regulatory_gate(
        _gate(listing_status=None), "600900", "2025年报", today=TODAY
    ) is None


def test_stale_rule_still_fails_closed_after_carry_forward():
    kept = risk_gates.carry_forward_regulatory_gate(
        _gate(), "600900", "2025年报", today=date(2027, 6, 1)
    )
    assert kept["status"] == "incomplete"


def _seed_fundamentals(database, data_period="2025年报"):
    with sqlite3.connect(database) as conn:
        schema.bootstrap_database_schema(conn)
        conn.execute(
            """INSERT INTO stock_fundamentals
               (code, name, industry, data, updated_at, ttl_hours)
               VALUES ('600900', '长江电力', '水电', ?, '2026-10-15T03:33:00+00:00', 168)""",
            (json.dumps({"data_period": data_period, "null_reasons": {},
                         "field_provenance": {}}),),
        )


def _run_evidence(monkeypatch, facts):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(facts)))
    return cache.main(["--confirm-write", "regulatory-evidence", "600900"])


def test_command_merges_runtime_evaluated_gate_and_fetch_preserves_it(
    isolated_cache_database, monkeypatch
):
    _seed_fundamentals(isolated_cache_database)
    assert _run_evidence(monkeypatch, FACTS) == 0
    with sqlite3.connect(isolated_cache_database) as conn:
        raw, updated_at = conn.execute(
            "SELECT data, updated_at FROM stock_fundamentals WHERE code='600900'"
        ).fetchone()
    stored = json.loads(raw)["regulatory_gate"]
    assert stored == risk_gates.regulatory_gate({**FACTS, "code": "600900"})
    assert updated_at == "2026-10-15T03:33:00+00:00"

    results = {}
    fetcher._cache_gate_defaults("600900", results, "2025年报", "水电")
    assert results["regulatory_gate"]["checks"] == stored["checks"]
    results = {}
    fetcher._cache_gate_defaults("600900", results, "2026年报", "水电")
    assert results["regulatory_gate"]["status"] == "incomplete"


@pytest.mark.parametrize("period", ["2024年报", None])
def test_command_rejects_evidence_for_another_period(
    period, isolated_cache_database, monkeypatch
):
    _seed_fundamentals(isolated_cache_database)
    assert _run_evidence(monkeypatch, {**FACTS, "report_period": period}) == 1


def test_command_without_confirmation_writes_nothing(isolated_cache_database, monkeypatch):
    _seed_fundamentals(isolated_cache_database)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(FACTS)))
    assert cache.main(["regulatory-evidence", "600900"]) == 3
    with sqlite3.connect(isolated_cache_database) as conn:
        raw = conn.execute("SELECT data FROM stock_fundamentals").fetchone()[0]
    assert "regulatory_gate" not in json.loads(raw)


@pytest.mark.parametrize("field", ["listing_status", "investigation_status"])
def test_explicit_null_status_is_missing_evidence_not_none_token(field):
    assert _gate(**{field: None})["status"] == "incomplete"

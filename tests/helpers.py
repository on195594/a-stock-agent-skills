"""Test factories for strict cache write contracts."""
from __future__ import annotations

from typing import Any

from a_stock_agent_runtime import cache


def valid_fundamentals_payload(data: dict[str, Any], period: str = '2025年报') -> dict[str, Any]:
    """Add the mandatory period, null reasons and provenance envelope."""
    if {'data_period', 'null_reasons', 'field_provenance'} <= set(data):
        return data
    payload = dict(data)
    null_reasons = {
        field: 'fixture missing value'
        for field, value in data.items()
        if value is None
    }
    provenance = {
        field: {
            'source': 'test-fixture',
            'as_of': period,
            'status': 'missing' if value is None else 'ok',
        }
        for field, value in data.items()
    }
    payload.update({
        'data_period': period,
        'null_reasons': null_reasons,
        'field_provenance': provenance,
    })
    return payload


def set_valid_fundamentals(
    code: str,
    name: str,
    industry: str,
    data: dict[str, Any],
    ttl: int | None = None,
) -> str:
    """Call production set_fundamentals with a valid fixture envelope."""
    return cache.set_fundamentals(
        code, name, industry, valid_fundamentals_payload(data), ttl
    )


def record_valid_quote(code: str, price: float = 10.0) -> None:
    """Write a recent validated quote snapshot for set-analysis tests."""
    cache.record_quote_snapshot(
        code,
        price,
        cache.cst_today(),
        '10:00:00',
        'sina',
        {'sina': {'price': price}},
        False,
    )

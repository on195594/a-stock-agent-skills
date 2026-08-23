"""新浪实时行情访问层，与 SQLite 缓存和 CLI 展示解耦。"""

from __future__ import annotations

from dataclasses import dataclass
import logging

import requests


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceQuote:
    """一条实时行情及交易所返回的日期、时间。"""

    price: float
    quote_date: str | None
    quote_time: str | None


def sina_query_prefix(code: str) -> str:
    return (
        "sh"
        if code.startswith("6")
        else ("bj" if code.startswith(("4", "8", "920")) else "sz")
    )


def parse_sina_quote_line(
    line: str,
    codes: set[str],
) -> tuple[str, float, str | None, str | None] | None:
    """Parse one Sina quote line into code, price and quote timestamp."""
    line = line.strip()
    if not line:
        return None
    idx = line.find("hq_str_")
    if idx == -1:
        return None
    eq_idx = line.find("=")
    if eq_idx == -1:
        return None
    full_symbol = line[idx + 7 : eq_idx]
    code = full_symbol[-6:]
    if code not in codes:
        return None
    start = line.find('"') + 1
    end = line.rfind('"')
    if start <= 0 or end <= start:
        return None
    fields = line[start:end].split(",")
    if len(fields) < 4:
        return None
    try:
        price = float(fields[3])
    except ValueError:
        return None
    if len(fields) >= 32:
        quote_date = fields[30] or None
        quote_time = fields[31] or None
    else:
        quote_date = quote_time = None
    return code, price, quote_date, quote_time


def fetch_sina_batch_quotes(
    codes: list[str],
) -> dict[str, tuple[float, str | None, str | None] | None]:
    """Fetch a batch of quotes once, returning ``None`` for failed symbols."""
    if not codes:
        return {}

    query_list = [f"{sina_query_prefix(code)}{code}" for code in codes]
    result: dict[str, tuple[float, str | None, str | None] | None] = {
        code: None for code in codes
    }
    code_set = set(codes)
    try:
        response = requests.get(
            f"https://hq.sinajs.cn/list={','.join(query_list)}",
            headers={"Referer": "https://finance.sina.com.cn"},
            timeout=10,
        )
        response.encoding = "gbk"
        for line in response.text.split("\n"):
            parsed = parse_sina_quote_line(line, code_set)
            if parsed is not None:
                code, price, quote_date, quote_time = parsed
                result[code] = (price, quote_date, quote_time)
    except requests.RequestException:
        logger.exception("Batch fetch current prices failed")
    return result


def fetch_current_price(code: str) -> float | None:
    """Fetch one current price for compatibility with existing callers."""
    try:
        response = requests.get(
            f"https://hq.sinajs.cn/list={sina_query_prefix(code)}{code}",
            headers={"Referer": "https://finance.sina.com.cn"},
            timeout=8,
        )
        response.encoding = "gbk"
        start = response.text.find('"') + 1
        end = response.text.rfind('"')
        if start <= 0 or end <= start:
            return None
        fields = response.text[start:end].split(",")
        return float(fields[3]) if len(fields) >= 4 else None
    except (requests.RequestException, ValueError, IndexError):
        return None


def fetch_current_price_quote(code: str) -> PriceQuote | None:
    """Fetch one quote with its source timestamp."""
    raw = fetch_sina_batch_quotes([code]).get(code)
    if raw is None:
        return None
    return PriceQuote(price=raw[0], quote_date=raw[1], quote_time=raw[2])

from __future__ import annotations

import importlib
from pathlib import Path


MODULES = (
    "cache", "fetcher", "checklist", "framework_metadata", "market_quotes",
    "position_ledger", "schema_ledger", "paths",
)


def test_runtime_modules_import_from_package() -> None:
    for module in MODULES:
        importlib.import_module(f"a_stock_agent_runtime.{module}")


def test_no_legacy_top_level_runtime_imports() -> None:
    root = Path(__file__).resolve().parents[1] / "src/a_stock_agent_runtime"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "from project_paths" not in text
    assert "import project_paths" not in text
    assert "from cache import" not in text

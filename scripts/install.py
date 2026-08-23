#!/usr/bin/env python3
"""Standard-library bootstrap entrypoint for the suite installer."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from a_stock_agent_runtime.install import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

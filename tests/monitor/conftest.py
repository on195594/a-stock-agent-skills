"""Keep repository-local modules importable under both pytest entry points."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MONITOR_ROOT = REPOSITORY_ROOT / "skills" / "a-stock-monitor"
if str(MONITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(MONITOR_ROOT))
if str(MONITOR_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(MONITOR_ROOT / "scripts"))

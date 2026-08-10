"""Portable XDG paths and external configuration for the runtime."""
from __future__ import annotations

import os
import stat
from pathlib import Path


def _config_path() -> Path:
    explicit = os.environ.get("A_STOCK_CONFIG_FILE")
    if explicit:
        return Path(explicit).expanduser()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "a-stock-agent" / "runtime.env"


def _read_config() -> dict[str, str]:
    path = _config_path()
    if not path.exists():
        return {}
    if not path.is_file():
        raise RuntimeError(f"runtime config is not a regular file: {path}")
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise RuntimeError(f"runtime config must be user-owned and mode 0600: {path}")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep and key.strip():
            values[key.strip()] = value.strip().strip("'\"")
    return values


def _setting(name: str, default: Path | str) -> str:
    # Environment is deliberately resolved at call time so isolated tests can
    # change HOME/config without reloading the module.
    return os.environ.get(name) or _read_config().get(name) or str(default)


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def state_dir() -> Path:
    return Path(_setting("A_STOCK_STATE_DIR", _data_home() / "a-stock-agent")).expanduser()


def cache_db_path() -> Path:
    return Path(_setting("CACHE_DB_PATH", state_dir() / "cache.db")).expanduser()


def log_dir() -> Path:
    return Path(_setting("A_STOCK_LOG_DIR", state_dir() / "logs")).expanduser()


def lock_dir() -> Path:
    return Path(_setting("A_STOCK_LOCK_DIR", state_dir() / "locks")).expanduser()


def artifact_dir() -> Path:
    return Path(_setting("A_STOCK_ARTIFACT_DIR", state_dir() / "artifacts")).expanduser()


def ensure_state_dirs() -> None:
    for path in (state_dir(), log_dir(), lock_dir(), artifact_dir()):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.chmod(0o700)


def ensure_db_parent(path: str | Path) -> None:
    """Create only the selected database parent, preserving read-only probes."""
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent.chmod(0o700)


# Kept as computed compatibility constants for callers that only need a path.
# They point to external XDG state, never to the repository or an old client.
DEFAULT_STATE_DIR = state_dir()
DEFAULT_CACHE_DB_PATH = cache_db_path()
DEFAULT_LOG_DIR = log_dir()
DEFAULT_LOCK_DIR = lock_dir()
DEFAULT_ARTIFACT_DIR = artifact_dir()


def configured_value(name: str, default: str = "") -> str:
    """Return a non-secret setting using CLI/env/config precedence upstream."""
    return _setting(name, default)

from __future__ import annotations

import os
import sys
from pathlib import Path

_ENV_VAR = "NETSCANX_DB_PATH"
_DB_FILENAME = "netscanx.db"
_DATA_DIRNAME = "NetScanX-Data"


def is_frozen() -> bool:
    """True when running as a PyInstaller-frozen executable."""
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def get_executable_dir() -> Path:
    """Directory containing the running frozen executable.

    Uses sys.executable rather than sys._MEIPASS: for --onefile builds
    _MEIPASS is a temp extraction dir, but sys.executable still points at
    the actual binary location (e.g. on a USB stick), which is what we
    need so the portable DB travels with the launcher.
    """
    return Path(sys.executable).resolve().parent


def resolve_db_path(override: str | None = None) -> Path:
    """Resolve the SQLite database file path.

    Precedence: explicit override > NETSCANX_DB_PATH env var > portable
    default (next to the frozen executable) > installed OS-convention
    default (platformdirs user data dir).
    """
    if override:
        path = Path(override).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    env_val = os.environ.get(_ENV_VAR)
    if env_val:
        path = Path(env_val).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    if is_frozen():
        data_dir = get_executable_dir() / _DATA_DIRNAME
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / _DB_FILENAME

    from platformdirs import user_data_dir

    data_dir = Path(user_data_dir("netscanx", appauthor=False))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / _DB_FILENAME

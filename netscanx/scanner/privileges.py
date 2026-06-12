from __future__ import annotations

import os
import platform
import sys


def is_root() -> bool:
    if sys.platform == "win32":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0


def require_root(feature: str) -> None:
    if is_root():
        return
    system = platform.system()
    if system == "Linux":
        msg = (
            f"{feature} requires elevated privileges.\n"
            f"  Option 1: sudo netscanx ...\n"
            f"  Option 2: sudo setcap cap_net_raw+ep $(which python3)"
        )
    elif system == "Darwin":
        msg = f"{feature} requires elevated privileges. Run: sudo netscanx ..."
    else:
        msg = f"{feature} requires Administrator. Run PowerShell or CMD as Administrator."
    raise PermissionError(msg)

"""PyInstaller entry point. Not used by `pip install netscanx` -- only
referenced by the build/*.spec files' Analysis(['netscanx/__main__frozen__.py']).

Double-clicking the frozen binary with no arguments launches the dashboard
(mirrors `netscanx dashboard`'s existing auto-open-browser behavior), since
a bare CLI console is not a useful default for a non-technical "plug in the
USB stick and click the launcher" workflow. Running it from a terminal with
arguments still exposes the full CLI (discover, services, diagnose,
baseline, changes, assets, health, dashboard)."""
from __future__ import annotations

import sys


def main() -> None:
    from netscanx.cli.main import cli

    if len(sys.argv) == 1:
        sys.argv.append("dashboard")
    cli(prog_name="NetScanX")


if __name__ == "__main__":
    main()

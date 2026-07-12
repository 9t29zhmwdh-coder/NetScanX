"""netscanx baseline: pin the current scan as the drift-detection baseline."""
from __future__ import annotations

import asyncio

import click
from rich.console import Console

from netscanx.cli.discover import _auto_detect_network
from netscanx.inventory.service import InventoryService

console = Console(stderr=True)


@click.command()
@click.option("--target", default=None, help="Target network/host [default: auto-detect]")
@click.option("--db-path", default=None, help="Override the SQLite database path")
def baseline(target: str | None, db_path: str | None) -> None:
    """Run a fresh scan and pin it as the reference baseline for `netscanx changes --since-baseline`."""
    asyncio.run(_run(target or _auto_detect_network(), db_path))


async def _run(target: str, db_path: str | None) -> None:
    from pathlib import Path

    service = InventoryService(db_path=Path(db_path) if db_path else None)
    with console.status(f"[bold green]Scanning {target} for baseline…"):
        run, _changes = await service.run_and_persist(target)
        pinned = await service.pin_baseline(run.id)

    console.print(
        f"[green]Baseline pinned:[/green] run #{pinned.id}, {pinned.host_count} hosts "
        f"({pinned.target})"
    )

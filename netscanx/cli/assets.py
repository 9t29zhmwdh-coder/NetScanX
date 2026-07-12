"""netscanx assets: list the persisted device inventory."""
from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table

from netscanx.inventory.service import InventoryService
from netscanx.output import emit_json, emit_yaml

console = Console(stderr=True)


@click.command()
@click.option("--format", "fmt", default="table", type=click.Choice(["table", "json", "yaml"]))
@click.option("--db-path", default=None, help="Override the SQLite database path")
def assets(fmt: str, db_path: str | None) -> None:
    """List all devices ever seen, from the persisted inventory (not just the last scan)."""
    asyncio.run(_run(fmt, db_path))


async def _run(fmt: str, db_path: str | None) -> None:
    service = InventoryService(db_path=Path(db_path) if db_path else None)
    devices = await service.list_assets()

    rows = [
        {
            "id": d.id,
            "ip": d.last_ip,
            "hostname": d.last_hostname,
            "mac": d.primary_mac,
            "vendor": d.last_vendor,
            "os_guess": d.last_os_guess,
            "device_type": d.last_device_type,
            "first_seen": d.first_seen.isoformat() if d.first_seen else None,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        }
        for d in devices
    ]

    if fmt == "json":
        emit_json(rows)
    elif fmt == "yaml":
        emit_yaml(rows)
        return
    else:
        if not rows:
            console.print("[yellow]No devices in inventory yet -- run `netscanx baseline` or `netscanx discover --persist` first.[/yellow]")
            return
        table = Table(title=f"NetScanX Asset Inventory ({len(rows)} devices)", box=box.ROUNDED)
        table.add_column("IP", style="cyan")
        table.add_column("Hostname", style="white")
        table.add_column("MAC", style="magenta")
        table.add_column("Vendor", style="green")
        table.add_column("OS Guess", style="yellow")
        table.add_column("Type", style="dim")
        table.add_column("Last Seen", style="dim")
        for row in rows:
            table.add_row(
                row["ip"] or "N/A",
                row["hostname"] or "N/A",
                row["mac"] or "N/A",
                row["vendor"] or "N/A",
                row["os_guess"] or "N/A",
                row["device_type"] or "N/A",
                (row["last_seen"] or "N/A")[:19],
            )
        console.print(table)

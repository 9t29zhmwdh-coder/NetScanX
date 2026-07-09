"""netscanx changes — show what changed since the last scan or the pinned baseline."""
from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console

from netscanx.inventory.service import InventoryService
from netscanx.output import emit_json, emit_yaml, print_changes

console = Console(stderr=True)


@click.command()
@click.option("--since-baseline", is_flag=True, help="Show all changes since the pinned baseline")
@click.option("--since-last", is_flag=True, default=True,
              help="Show changes from the most recent scan [default]")
@click.option("--format", "fmt", default="table", type=click.Choice(["table", "json", "yaml"]))
@click.option("--db-path", default=None, help="Override the SQLite database path")
def changes(since_baseline: bool, since_last: bool, fmt: str, db_path: str | None) -> None:
    """Show devices/ports/services that changed since the last scan or the pinned baseline."""
    asyncio.run(_run(since_baseline, fmt, db_path))


async def _run(since_baseline: bool, fmt: str, db_path: str | None) -> None:
    service = InventoryService(db_path=Path(db_path) if db_path else None)
    change_events = await service.get_changes(since_baseline=since_baseline)
    devices = {d.id: d for d in await service.list_assets()}

    rows = []
    for c in change_events:
        device = devices.get(c.device_id)
        rows.append({
            "device_id": c.device_id,
            "device_ip": device.last_ip if device else None,
            "device_hostname": device.last_hostname if device else None,
            "change_type": c.change_type,
            "field": c.field,
            "old_value": c.old_value,
            "new_value": c.new_value,
            "detected_at": c.detected_at.isoformat() if c.detected_at else None,
        })

    if fmt == "json":
        emit_json(rows)
    elif fmt == "yaml":
        emit_yaml(rows)
    else:
        print_changes(rows)

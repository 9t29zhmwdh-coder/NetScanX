"""netscanx diagnose: auto-diagnose network health."""
from __future__ import annotations

import asyncio

import click
from rich.console import Console

from netscanx.output import emit_json, emit_yaml, print_diagnostic

console = Console(stderr=True)


@click.command()
@click.argument("target", required=False, default="local")
@click.option("--format", "fmt", default="table",
              type=click.Choice(["table", "json", "yaml"]), help="Output format")
def diagnose(target: str, fmt: str) -> None:
    """Auto-diagnose network health: DNS, routing, DHCP, packet loss.

    \b
    Checks performed:
      • DNS resolution (google.com, cloudflare.com, github.com)
      • Default gateway reachability and latency
      • Packet loss to 8.8.8.8 (20 packets)
      • Latency and jitter (8.8.8.8)
      • Subnet configuration (APIPA, gateway-subnet mismatch)
      • Duplicate DHCP server detection (reads lease files)
      • IPv6 connectivity

    \b
    Examples:
      netscanx diagnose
      netscanx diagnose --format json
      netscanx diagnose 192.168.1.0/24
    """
    asyncio.run(_run(target=target, fmt=fmt))


async def _run(target: str, fmt: str) -> None:
    from netscanx.diagnostics.checks import DiagnosticsRunner

    runner = DiagnosticsRunner(target=target)

    with console.status("[bold green]Running diagnostics…"):
        report = await runner.run_all()

    if fmt == "json":
        emit_json(report)
    elif fmt == "yaml":
        emit_yaml(report)
    else:
        print_diagnostic(report)

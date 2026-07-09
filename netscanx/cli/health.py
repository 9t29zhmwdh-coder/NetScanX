"""netscanx health — local machine health, or lightweight network-observable
health signals for a given host. See netscanx/health/ for the check
implementations and their weight documentation."""
from __future__ import annotations

import asyncio

import click

from netscanx.health.local_checks import LocalHealthRunner
from netscanx.health.network_checks import NetworkHealthRunner
from netscanx.models import Host
from netscanx.output import emit_json, emit_yaml, print_health
from netscanx.scanner.layer3 import ICMPScanner
from netscanx.scanner.layer4 import TCPScanner

_DEFAULT_PORTS = [21, 22, 23, 25, 80, 139, 443, 445, 3389, 5900]


@click.command()
@click.argument("target", required=False)
@click.option("--format", "fmt", default="table", type=click.Choice(["table", "json", "yaml"]))
def health(target: str | None, fmt: str) -> None:
    """Run health checks.

    \b
    Without TARGET: local-machine health (disk/CPU/RAM/Defender/BitLocker/
    Windows Update), no credentials or network access needed.
    With TARGET: network-observable health signals for that host
    (reachability, DNS response, risky open ports).
    """
    asyncio.run(_run(target, fmt))


async def _run(target: str | None, fmt: str) -> None:
    if target is None:
        report = await LocalHealthRunner().run_all()
    else:
        host = Host(ip=target)
        try:
            icmp = ICMPScanner(timeout=1.5, concurrency=1)
            await icmp.sweep(f"{target}/32")
        except Exception:
            pass
        tcp = TCPScanner(timeout=1.5, concurrency=len(_DEFAULT_PORTS))
        host.open_ports = await tcp.scan_host(target, _DEFAULT_PORTS)
        report = await NetworkHealthRunner(host).run_all()

    if fmt == "json":
        emit_json(report)
    elif fmt == "yaml":
        emit_yaml(report)
    else:
        print_health(report)

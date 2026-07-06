"""netscanx speedtest — TCP/UDP throughput, latency, jitter."""
from __future__ import annotations

import asyncio

import click
from rich.console import Console

from netscanx.output import emit_json, emit_yaml, print_speedtest

console = Console(stderr=True)

_DEFAULT_PORT = 15101


@click.command()
@click.argument("host", required=False)
@click.option("--server", is_flag=True, help="Run in server mode (listens for incoming tests)")
@click.option("--port", default=_DEFAULT_PORT, type=int, metavar="PORT",
              help=f"Port for TCP/UDP tests [default: {_DEFAULT_PORT}]")
@click.option("--tcp/--no-tcp", default=True, help="TCP throughput test")
@click.option("--udp/--no-udp", default=True, help="UDP packet loss test")
@click.option("--duration", "-d", default=10, type=int, metavar="SEC",
              help="Test duration in seconds [default: 10]")
@click.option("--pings", default=20, type=int, metavar="N",
              help="Ping packets for latency stats [default: 20]")
@click.option("--format", "fmt", default="table",
              type=click.Choice(["table", "json", "yaml"]), help="Output format")
def speedtest(
    host: str | None,
    server: bool,
    port: int,
    tcp: bool,
    udp: bool,
    duration: int,
    pings: int,
    fmt: str,
) -> None:
    """Measure TCP/UDP throughput, latency and jitter between two hosts.

    \b
    Two-step usage (P2P):
      Host A (server):  netscanx speedtest --server
      Host B (client):  netscanx speedtest 192.168.1.10

    \b
    Or test latency only (no server needed):
      netscanx speedtest 8.8.8.8 --no-tcp --no-udp

    \b
    Examples:
      netscanx speedtest --server
      netscanx speedtest 192.168.1.10 --duration 30
      netscanx speedtest 1.1.1.1 --no-tcp --no-udp --pings 50
    """
    if server:
        asyncio.run(_run_server(port))
        return

    if not host:
        raise click.UsageError("Specify a HOST to test against, or use --server to listen.")

    asyncio.run(_run_client(
        host=host,
        port=port,
        do_tcp=tcp,
        do_udp=udp,
        duration=duration,
        pings=pings,
        fmt=fmt,
    ))


async def _run_server(port: int) -> None:
    from netscanx.performance.speedtest import SpeedtestServer
    srv = SpeedtestServer(tcp_port=port, udp_port=port + 1)
    await srv.start()


async def _run_client(
    host: str,
    port: int,
    do_tcp: bool,
    do_udp: bool,
    duration: int,
    pings: int,
    fmt: str,
) -> None:
    from netscanx.performance.speedtest import SpeedtestClient

    client = SpeedtestClient(host=host, tcp_port=port, udp_port=port + 1)

    with console.status(f"[bold green]Testing {host}…"):
        result = await client.run(
            duration=duration,
            tcp=do_tcp,
            udp=do_udp,
            latency_count=pings,
        )

    if fmt == "json":
        emit_json(result)
    elif fmt == "yaml":
        emit_yaml(result)
    else:
        print_speedtest(result)

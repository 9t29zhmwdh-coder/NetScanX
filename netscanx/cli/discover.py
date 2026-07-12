"""netscanx discover: host discovery via ARP, ICMP, TCP."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
import time

import click
from rich.console import Console

from netscanx.models import DiscoverResult, Host
from netscanx.output import emit_json, emit_yaml, print_discover
from netscanx.scanner.hostname import resolve_hostnames_batch
from netscanx.scanner.layer2 import ARPScanner, get_arp_cache
from netscanx.scanner.layer3 import ICMPScanner
from netscanx.scanner.layer4 import TCPScanner, SYNScanner, parse_port_spec
from netscanx.scanner.privileges import is_root
from netscanx.scanner.vendor import lookup_vendor

console = Console(stderr=True)


def _auto_detect_network() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return str(ipaddress.ip_interface(f"{local_ip}/24").network)
    except Exception:
        return "192.168.1.0/24"


@click.command()
@click.argument("target", required=False)
@click.option("--arp/--no-arp", default=True, help="ARP sweep (requires root/admin)")
@click.option("--ping/--no-ping", default=True, help="ICMP ping sweep")
@click.option("--ports", "-p", default=None, metavar="PORTS",
              help="Port range to scan, e.g. 22,80,443 or 1-1024")
@click.option("--syn/--no-syn", default=False, help="TCP SYN scan (requires root/admin)")
@click.option("--banner/--no-banner", default=False, help="Grab service banners")
@click.option("--vendor/--no-vendor", default=False,
              help="Lookup MAC vendors (uses online API, rate-limited)")
@click.option("--hostname/--no-hostname", default=True,
              help="Resolve hostnames via reverse DNS")
@click.option("--timeout", "-t", default=2.0, type=float, metavar="SEC",
              help="Probe timeout in seconds [default: 2.0]")
@click.option("--concurrency", "-c", default=200, type=int, metavar="N",
              help="Concurrent probes [default: 200]")
@click.option("--format", "fmt", default="table",
              type=click.Choice(["table", "json", "yaml"]), help="Output format")
@click.option("--cache/--no-cache", default=False, help="Include ARP cache entries")
@click.option("-v", "--verbose", is_flag=True, help="Show port details and banners")
@click.option("--persist/--no-persist", default=False,
              help="Persist results to the local SQLite inventory for baseline/drift detection")
@click.option("--db-path", default=None, help="Override the SQLite database path (implies --persist)")
def discover(
    target: str | None,
    arp: bool,
    ping: bool,
    ports: str | None,
    syn: bool,
    banner: bool,
    vendor: bool,
    hostname: bool,
    timeout: float,
    concurrency: int,
    fmt: str,
    cache: bool,
    verbose: bool,
    persist: bool,
    db_path: str | None,
) -> None:
    """Discover hosts on the network using ARP, ICMP, and port scanning.

    \b
    TARGET can be:
      192.168.1.0/24    : CIDR subnet
      192.168.1.1       : single host
      (omit)            : auto-detect local /24

    \b
    Examples:
      netscanx discover
      netscanx discover 10.0.0.0/24 --arp --ports 22,80,443
      sudo netscanx discover --arp --syn --vendor --format json
    """
    asyncio.run(_run(
        target=target or _auto_detect_network(),
        do_arp=arp,
        do_ping=ping,
        port_spec=ports,
        do_syn=syn,
        do_banner=banner,
        do_vendor=vendor,
        do_hostname=hostname,
        timeout=timeout,
        concurrency=concurrency,
        fmt=fmt,
        include_cache=cache,
        verbose=verbose,
        persist=persist or bool(db_path),
        db_path=db_path,
    ))


async def _run(
    target: str,
    do_arp: bool,
    do_ping: bool,
    port_spec: str | None,
    do_syn: bool,
    do_banner: bool,
    do_vendor: bool,
    do_hostname: bool,
    timeout: float,
    concurrency: int,
    fmt: str,
    include_cache: bool,
    verbose: bool,
    persist: bool = False,
    db_path: str | None = None,
) -> None:
    result = await run_discover_scan(
        target=target,
        do_arp=do_arp,
        do_ping=do_ping,
        port_spec=port_spec,
        do_syn=do_syn,
        do_banner=do_banner,
        do_vendor=do_vendor,
        do_hostname=do_hostname,
        timeout=timeout,
        concurrency=concurrency,
        include_cache=include_cache,
    )

    if fmt == "json":
        emit_json(result)
    elif fmt == "yaml":
        emit_yaml(result)
    else:
        print_discover(result, verbose=verbose)

    if persist:
        from pathlib import Path

        from netscanx.inventory.service import InventoryService

        service = InventoryService(db_path=Path(db_path) if db_path else None)
        _run_record, changes = await service.persist_results(result)
        if changes:
            console.print(
                f"[cyan]{len(changes)} change(s) detected[/cyan] -- run `netscanx changes` for details"
            )
        else:
            console.print("[dim]No changes since last persisted scan.[/dim]")


async def run_discover_scan(
    target: str,
    do_arp: bool = True,
    do_ping: bool = True,
    port_spec: str | None = None,
    do_syn: bool = False,
    do_banner: bool = False,
    do_vendor: bool = False,
    do_hostname: bool = True,
    timeout: float = 2.0,
    concurrency: int = 200,
    include_cache: bool = False,
) -> DiscoverResult:
    """Run a full discover scan and return the result. Used by the CLI and the dashboard."""
    t0 = time.monotonic()
    hosts_by_ip: dict[str, Host] = {}

    def _merge(host: Host) -> None:
        if host.ip in hosts_by_ip:
            existing = hosts_by_ip[host.ip]
            if host.mac and not existing.mac:
                existing.mac = host.mac
            for via in host.discovered_via:
                if via not in existing.discovered_via:
                    existing.discovered_via.append(via)
        else:
            hosts_by_ip[host.ip] = host

    is_single = _is_single_ip(target)
    network = target if not is_single else f"{target}/32"

    with console.status(f"[bold green]Scanning {target}…"):
        if do_arp and not is_single:
            try:
                scanner = ARPScanner(timeout=timeout, vendor=do_vendor)
                results = await scanner.sweep(network)
                for h in results:
                    _merge(h)
            except PermissionError as e:
                console.print(f"[yellow]ARP:[/yellow] {e}")

        if do_ping:
            try:
                scanner = ICMPScanner(timeout=timeout, concurrency=concurrency)
                scan_target = network if not is_single else target
                results = await scanner.sweep(scan_target if not is_single else f"{target}/32")
                for h in results:
                    _merge(h)
            except Exception as e:
                console.print(f"[yellow]ICMP:[/yellow] {e}")

        # Always read the OS ARP cache to enrich already-discovered hosts with a MAC
        # address. Pinging a host makes the OS resolve its MAC, so the cache has it
        # even without root/scapy. --cache additionally adds cache-only hosts as new entries.
        cache_hosts = await get_arp_cache()
        for h in cache_hosts:
            if include_cache or h.ip in hosts_by_ip:
                _merge(h)

    if port_spec or do_syn:
        port_list = parse_port_spec(port_spec) if port_spec else [
            21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995,
            3306, 3389, 5432, 5900, 8080, 8443,
        ]
        scan_ips = list(hosts_by_ip.keys()) or ([target] if is_single else [])

        if do_syn and is_root():
            syn_scanner = SYNScanner(timeout=timeout)
            for ip in scan_ips:
                with console.status(f"SYN scan {ip}…"):
                    try:
                        open_ports = await syn_scanner.scan_host(ip, port_list)
                        hosts_by_ip.setdefault(ip, Host(ip=ip)).open_ports.extend(open_ports)
                    except Exception as e:
                        console.print(f"[yellow]SYN {ip}:[/yellow] {e}")
        else:
            tcp = TCPScanner(timeout=timeout, concurrency=concurrency, banner=do_banner)
            for ip in scan_ips:
                with console.status(f"Port scan {ip}…"):
                    open_ports = await tcp.scan_host(ip, port_list)
                    h = hosts_by_ip.setdefault(ip, Host(ip=ip))
                    h.open_ports.extend(open_ports)
                    if "tcp" not in h.discovered_via:
                        h.discovered_via.append("tcp")

    if do_vendor:
        macs = [h.mac for h in hosts_by_ip.values() if h.mac and not h.vendor]
        if macs:
            console.print(f"[dim]Looking up {len(macs)} MAC vendors…[/dim]")
            for h in hosts_by_ip.values():
                if h.mac and not h.vendor:
                    h.vendor = await lookup_vendor(h.mac)

    if do_hostname and hosts_by_ip:
        resolved = await resolve_hostnames_batch(list(hosts_by_ip.keys()))
        for ip, name in resolved.items():
            if name:
                hosts_by_ip[ip].hostname = name

    elapsed = time.monotonic() - t0
    return DiscoverResult(
        target=target,
        hosts=list(hosts_by_ip.values()),
        scan_duration_s=round(elapsed, 2),
    )


def _is_single_ip(target: str) -> bool:
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False

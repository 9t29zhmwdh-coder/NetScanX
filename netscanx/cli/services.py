"""netscanx services: mDNS, SSDP, NetBIOS, SNMP discovery."""
from __future__ import annotations

import asyncio
import socket
import time

import click
from rich.console import Console

from netscanx.models import ServicesResult
from netscanx.output import emit_json, emit_yaml, print_services

console = Console(stderr=True)


@click.command()
@click.argument("target", required=False)
@click.option("--mdns/--no-mdns", default=True, help="mDNS/Zeroconf discovery")
@click.option("--ssdp/--no-ssdp", default=True, help="SSDP/UPnP discovery")
@click.option("--netbios/--no-netbios", default=True, help="NetBIOS name scan")
@click.option("--snmp/--no-snmp", default=False,
              help='SNMP v2c scan (community "public" by default)')
@click.option("--community", default="public", metavar="STRING",
              help="SNMP community string [default: public]")
@click.option("--mdns-timeout", default=5.0, type=float, metavar="SEC",
              help="mDNS browse duration [default: 5.0]")
@click.option("--ssdp-timeout", default=4.0, type=float, metavar="SEC",
              help="SSDP listen duration [default: 4.0]")
@click.option("--format", "fmt", default="table",
              type=click.Choice(["table", "json", "yaml"]), help="Output format")
def services(
    target: str | None,
    mdns: bool,
    ssdp: bool,
    netbios: bool,
    snmp: bool,
    community: str,
    mdns_timeout: float,
    ssdp_timeout: float,
    fmt: str,
) -> None:
    """Discover network services: mDNS, SSDP/UPnP, NetBIOS, SNMP.

    \b
    TARGET is optional and used to scope NetBIOS/SNMP scans.
    mDNS and SSDP are always local-network multicast.

    \b
    Examples:
      netscanx services
      netscanx services 192.168.1.0/24 --netbios --snmp
      netscanx services --no-mdns --ssdp --format json
    """
    asyncio.run(_run(
        target=target or _local_net(),
        do_mdns=mdns,
        do_ssdp=ssdp,
        do_netbios=netbios,
        do_snmp=snmp,
        community=community,
        mdns_timeout=mdns_timeout,
        ssdp_timeout=ssdp_timeout,
        fmt=fmt,
    ))


async def _run(
    target: str,
    do_mdns: bool,
    do_ssdp: bool,
    do_netbios: bool,
    do_snmp: bool,
    community: str,
    mdns_timeout: float,
    ssdp_timeout: float,
    fmt: str,
) -> None:
    result = await run_services_scan(
        target=target,
        do_mdns=do_mdns,
        do_ssdp=do_ssdp,
        do_netbios=do_netbios,
        do_snmp=do_snmp,
        community=community,
        mdns_timeout=mdns_timeout,
        ssdp_timeout=ssdp_timeout,
    )

    if fmt == "json":
        emit_json(result)
    elif fmt == "yaml":
        emit_yaml(result)
    else:
        print_services(result)


async def run_services_scan(
    target: str,
    do_mdns: bool = True,
    do_ssdp: bool = True,
    do_netbios: bool = False,
    do_snmp: bool = False,
    community: str = "public",
    mdns_timeout: float = 5.0,
    ssdp_timeout: float = 4.0,
) -> ServicesResult:
    """Run a full services scan and return the result. Used by the CLI and the dashboard."""
    from netscanx.discovery.mdns import MDNSDiscovery
    from netscanx.discovery.ssdp import SSDPScanner
    from netscanx.discovery.netbios import NetBIOSScanner
    from netscanx.discovery.snmp import SNMPScanner
    from netscanx.scanner.layer2 import get_arp_cache

    t0 = time.monotonic()
    all_services = []

    tasks = []

    if do_mdns:
        tasks.append(_mdns_task(MDNSDiscovery(timeout=mdns_timeout)))
    if do_ssdp:
        tasks.append(_ssdp_task(SSDPScanner(timeout=ssdp_timeout)))

    with console.status(f"[bold green]Discovering services on {target}…"):
        multicast_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in multicast_results:
            if isinstance(r, list):
                all_services.extend(r)

        if do_netbios or do_snmp:
            ips = await _collect_ips(target)
            if not ips:
                console.print("[dim]No hosts in target range, skipping NetBIOS/SNMP[/dim]")
            else:
                if do_netbios:
                    nb = NetBIOSScanner()
                    nb_results = await nb.scan_network(ips)
                    all_services.extend(nb_results)

                if do_snmp:
                    snmp = SNMPScanner(community=community)
                    snmp_results = await snmp.scan_network(ips)
                    all_services.extend(snmp_results)

    elapsed = time.monotonic() - t0
    return ServicesResult(
        target=target,
        services=all_services,
        scan_duration_s=round(elapsed, 2),
    )


async def _mdns_task(scanner) -> list:
    return await scanner.discover()


async def _ssdp_task(scanner) -> list:
    return await scanner.discover()


async def _collect_ips(target: str) -> list[str]:
    import ipaddress as _ip

    ips = []
    try:
        net = _ip.ip_network(target, strict=False)
        if net.num_addresses <= 512:
            return [str(h) for h in net.hosts()]
        cache = await _get_cache_ips()
        return cache
    except ValueError:
        try:
            _ip.ip_address(target)
            return [target]
        except ValueError:
            return await _get_cache_ips()


async def _get_cache_ips() -> list[str]:
    from netscanx.scanner.layer2 import get_arp_cache
    cache = await get_arp_cache()
    return [h.ip for h in cache]


def _local_net() -> str:
    try:
        import ipaddress
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return str(ipaddress.ip_interface(f"{local_ip}/24").network)
    except Exception:
        return "192.168.1.0/24"

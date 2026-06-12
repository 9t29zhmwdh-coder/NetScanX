"""Layer-2 scanner: ARP sweep, ARP cache, MAC vendor, DHCP lease parsing."""
from __future__ import annotations

import asyncio
import ipaddress
import platform
import re
import subprocess
from pathlib import Path

from netscanx.models import Host
from netscanx.scanner.privileges import is_root
from netscanx.scanner.vendor import lookup_vendor


class ARPScanner:
    def __init__(self, timeout: float = 2.0, vendor: bool = False):
        self.timeout = timeout
        self.vendor = vendor

    async def sweep(self, network: str) -> list[Host]:
        if is_root():
            return await self._sweep_scapy(network)
        return await self._sweep_ping_fallback(network)

    async def _sweep_scapy(self, network: str) -> list[Host]:
        try:
            from scapy.all import ARP, Ether, srp  # type: ignore

            pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network)
            answered, _ = await asyncio.to_thread(
                lambda: srp(pkt, timeout=self.timeout, verbose=False)
            )
            hosts = []
            for _, rcv in answered:
                vendor = await lookup_vendor(rcv.hwsrc) if self.vendor else None
                hosts.append(
                    Host(
                        ip=rcv.psrc,
                        mac=rcv.hwsrc,
                        vendor=vendor,
                        discovered_via=["arp"],
                    )
                )
            return hosts
        except Exception:
            return await self._sweep_ping_fallback(network)

    async def _sweep_ping_fallback(self, network: str) -> list[Host]:
        net = ipaddress.ip_network(network, strict=False)
        hosts_ips = list(net.hosts())
        sem = asyncio.Semaphore(64)

        async def ping_one(ip: str) -> Host | None:
            async with sem:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *_ping_cmd(ip, 1),
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await asyncio.wait_for(proc.wait(), timeout=self.timeout + 0.5)
                    if proc.returncode == 0:
                        return Host(ip=ip, discovered_via=["ping"])
                except Exception:
                    pass
                return None

        results = await asyncio.gather(*[ping_one(str(ip)) for ip in hosts_ips])
        return [h for h in results if h is not None]


def _ping_cmd(host: str, count: int) -> list[str]:
    flag = "-n" if platform.system() == "Windows" else "-c"
    return ["ping", flag, str(count), "-W", "1", host] if platform.system() != "Windows" \
        else ["ping", flag, str(count), "-w", "1000", host]


async def get_arp_cache() -> list[Host]:
    system = platform.system()
    if system == "Linux":
        return await _arp_cache_linux()
    elif system == "Darwin":
        return await _arp_cache_macos()
    else:
        return await _arp_cache_windows()


async def _arp_cache_linux() -> list[Host]:
    hosts = []
    proc_arp = Path("/proc/net/arp")
    if proc_arp.exists():
        lines = proc_arp.read_text().splitlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 4 and parts[2] != "0x0" and parts[3] != "00:00:00:00:00:00":
                hosts.append(Host(ip=parts[0], mac=parts[3], discovered_via=["arp-cache"]))
    return hosts


async def _arp_cache_macos() -> list[Host]:
    hosts = []
    try:
        result = await asyncio.to_thread(
            lambda: subprocess.run(["arp", "-a"], capture_output=True, text=True)
        )
        for line in result.stdout.splitlines():
            m = re.search(r"\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-f:]{17})", line)
            if m:
                hosts.append(Host(ip=m.group(1), mac=m.group(2), discovered_via=["arp-cache"]))
    except Exception:
        pass
    return hosts


async def _arp_cache_windows() -> list[Host]:
    hosts = []
    try:
        result = await asyncio.to_thread(
            lambda: subprocess.run(["arp", "-a"], capture_output=True, text=True)
        )
        for line in result.stdout.splitlines():
            m = re.match(r"\s+(\d+\.\d+\.\d+\.\d+)\s+([\da-f-]{17})", line)
            if m:
                mac = m.group(2).replace("-", ":")
                hosts.append(Host(ip=m.group(1), mac=mac, discovered_via=["arp-cache"]))
    except Exception:
        pass
    return hosts


async def parse_dhcp_leases() -> list[dict]:
    system = platform.system()
    leases = []
    if system == "Linux":
        for path in [
            Path("/var/lib/dhcp/dhclient.leases"),
            Path("/var/lib/NetworkManager"),
        ]:
            if path.is_file():
                leases.extend(_parse_dhclient_leases(path.read_text()))
            elif path.is_dir():
                for f in path.glob("*.lease"):
                    leases.extend(_parse_dhclient_leases(f.read_text()))
    elif system == "Darwin":
        lease_dir = Path("/var/db/dhcpclient/leases")
        if lease_dir.exists():
            for f in lease_dir.glob("*"):
                try:
                    leases.append({"file": str(f), "content": f.read_text()[:500]})
                except Exception:
                    pass
    return leases


def _parse_dhclient_leases(text: str) -> list[dict]:
    leases = []
    current: dict = {}
    for line in text.splitlines():
        line = line.strip().rstrip(";")
        if line.startswith("lease {"):
            current = {}
        elif "}" in line and current:
            leases.append(current)
            current = {}
        elif line.startswith("fixed-address"):
            current["ip"] = line.split()[-1]
        elif line.startswith("hardware ethernet"):
            current["mac"] = line.split()[-1]
        elif line.startswith("option dhcp-server-identifier"):
            current["dhcp_server"] = line.split()[-1]
    return leases

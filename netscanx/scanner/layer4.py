"""Layer-4 scanner: TCP connect, TCP SYN, UDP scan, banner grabbing."""
from __future__ import annotations

import asyncio
import socket

from netscanx.models import Host, Port, PortState, Protocol
from netscanx.scanner.privileges import is_root, require_root

_WELL_KNOWN: dict[int, str] = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 389: "ldap", 443: "https",
    445: "smb", 465: "smtps", 587: "submission", 636: "ldaps",
    993: "imaps", 995: "pop3s", 1194: "openvpn", 1433: "mssql",
    1723: "pptp", 2049: "nfs", 3306: "mysql", 3389: "rdp",
    5432: "postgresql", 5900: "vnc", 6379: "redis", 8080: "http-alt",
    8443: "https-alt", 9200: "elasticsearch", 27017: "mongodb",
}


def parse_port_spec(spec: str) -> list[int]:
    ports: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            ports.extend(range(int(lo), int(hi) + 1))
        elif part:
            ports.append(int(part))
    return sorted(set(ports))


class TCPScanner:
    def __init__(self, timeout: float = 1.0, concurrency: int = 200, banner: bool = False):
        self.timeout = timeout
        self.concurrency = concurrency
        self.banner = banner

    async def scan_host(self, host: str, ports: list[int]) -> list[Port]:
        sem = asyncio.Semaphore(self.concurrency)

        async def probe(port: int) -> Port | None:
            async with sem:
                return await self._connect(host, port)

        results = await asyncio.gather(*[probe(p) for p in ports])
        return [p for p in results if p is not None]

    async def _connect(self, host: str, port: int) -> Port | None:
        try:
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=self.timeout)
            banner_text = None
            if self.banner:
                banner_text = await grab_banner_raw(reader, writer)
            else:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
                except Exception:
                    pass
            return Port(
                port=port,
                protocol=Protocol.TCP,
                state=PortState.OPEN,
                service=_WELL_KNOWN.get(port),
                banner=banner_text,
            )
        except Exception:
            return None


async def grab_banner(host: str, port: int, timeout: float = 2.0) -> str | None:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        return await grab_banner_raw(reader, writer, timeout=1.0)
    except Exception:
        return None


async def grab_banner_raw(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    timeout: float = 1.0,
) -> str | None:
    banner = None
    try:
        data = await asyncio.wait_for(reader.read(1024), timeout=timeout)
        if data:
            banner = data.decode("utf-8", errors="replace").strip()[:200]
        else:
            writer.write(b"HEAD / HTTP/1.0\r\nHost: target\r\n\r\n")
            await writer.drain()
            data = await asyncio.wait_for(reader.read(1024), timeout=timeout)
            if data:
                banner = data.decode("utf-8", errors="replace").strip()[:200]
    except Exception:
        pass
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
        except Exception:
            pass
    return banner


class SYNScanner:
    def __init__(self, timeout: float = 1.0):
        self.timeout = timeout

    async def scan_host(self, host: str, ports: list[int]) -> list[Port]:
        require_root("TCP SYN scan")
        try:
            from scapy.all import IP, TCP, sr  # type: ignore

            pkts = [IP(dst=host) / TCP(dport=p, flags="S") for p in ports]
            answered, _ = await asyncio.to_thread(
                lambda: sr(pkts, timeout=self.timeout, verbose=False)
            )
            open_ports = []
            for sent, rcv in answered:
                if rcv.haslayer("TCP") and rcv["TCP"].flags & 0x12:  # SYN-ACK
                    open_ports.append(
                        Port(
                            port=sent["TCP"].dport,
                            protocol=Protocol.TCP,
                            state=PortState.OPEN,
                            service=_WELL_KNOWN.get(sent["TCP"].dport),
                        )
                    )
            return open_ports
        except Exception as e:
            raise RuntimeError(f"SYN scan failed: {e}") from e


class UDPScanner:
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout

    async def scan_host(self, host: str, ports: list[int]) -> list[Port]:
        try:
            from scapy.all import IP, UDP, ICMP, sr  # type: ignore

            pkts = [IP(dst=host) / UDP(dport=p) for p in ports]
            answered, _ = await asyncio.to_thread(
                lambda: sr(pkts, timeout=self.timeout, verbose=False)
            )
            results = []
            closed_ips = set()
            for sent, rcv in answered:
                if rcv.haslayer(ICMP) and int(rcv[ICMP].type) == 3:
                    closed_ips.add(sent[UDP].dport)

            for port in ports:
                if port not in closed_ips:
                    results.append(
                        Port(
                            port=port,
                            protocol=Protocol.UDP,
                            state=PortState.OPEN,
                            service=_WELL_KNOWN.get(port),
                        )
                    )
            return results
        except Exception as e:
            raise RuntimeError(f"UDP scan failed: {e}") from e

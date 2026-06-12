"""SSDP/UPnP device discovery via UDP multicast."""
from __future__ import annotations

import asyncio
import socket
from typing import AsyncIterator

import aiohttp

from netscanx.models import ServiceInfo

_SSDP_ADDR = "239.255.255.250"
_SSDP_PORT = 1900
_MSEARCH = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {_SSDP_ADDR}:{_SSDP_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 2\r\n"
    "ST: ssdp:all\r\n"
    "\r\n"
).encode()


class SSDPScanner:
    def __init__(self, timeout: float = 4.0):
        self.timeout = timeout

    async def discover(self) -> list[ServiceInfo]:
        services: list[ServiceInfo] = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.setblocking(False)

        loop = asyncio.get_event_loop()
        try:
            await loop.sock_sendto(sock, _MSEARCH, (_SSDP_ADDR, _SSDP_PORT))
            deadline = loop.time() + self.timeout
            seen: set[str] = set()

            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    data, addr = await asyncio.wait_for(
                        loop.sock_recvfrom(sock, 4096), timeout=remaining
                    )
                    parsed = _parse_ssdp(data.decode("utf-8", errors="ignore"), addr[0])
                    if parsed:
                        key = f"{addr[0]}:{parsed.get('usn', '')}"
                        if key not in seen:
                            seen.add(key)
                            svc = await _to_service(parsed, addr[0])
                            if svc:
                                services.append(svc)
                except asyncio.TimeoutError:
                    break
        except Exception:
            pass
        finally:
            sock.close()

        return services


def _parse_ssdp(text: str, ip: str) -> dict | None:
    headers: dict[str, str] = {}
    for line in text.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            headers[k.strip().lower()] = v.strip()
    if not headers:
        return None
    headers["_ip"] = ip
    return headers


async def _to_service(headers: dict, ip: str) -> ServiceInfo | None:
    location = headers.get("location", "")
    server = headers.get("server", "UPnP Device")
    st = headers.get("st", headers.get("nt", "ssdp"))
    usn = headers.get("usn", "")

    name = server[:60] or usn[:60] or ip
    port = None

    if location:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(location)
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except Exception:
            pass

    return ServiceInfo(
        name=name,
        type=st,
        host=ip,
        ip=ip,
        port=port,
        properties={"location": location, "usn": usn},
        source="ssdp",
    )

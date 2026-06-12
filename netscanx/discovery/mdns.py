"""mDNS/Zeroconf service discovery."""
from __future__ import annotations

import asyncio
import socket

from netscanx.models import ServiceInfo

_COMMON_SERVICES = [
    "_http._tcp.local.",
    "_https._tcp.local.",
    "_ssh._tcp.local.",
    "_ftp._tcp.local.",
    "_smb._tcp.local.",
    "_afpovertcp._tcp.local.",
    "_nfs._tcp.local.",
    "_rdp._tcp.local.",
    "_vnc._tcp.local.",
    "_printer._tcp.local.",
    "_ipp._tcp.local.",
    "_airplay._tcp.local.",
    "_googlecast._tcp.local.",
    "_workstation._tcp.local.",
    "_device-info._tcp.local.",
    "_sftp-ssh._tcp.local.",
    "_mqtt._tcp.local.",
]


class MDNSDiscovery:
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    async def discover(self, service_types: list[str] | None = None) -> list[ServiceInfo]:
        try:
            from zeroconf import ServiceBrowser, Zeroconf  # type: ignore
            from zeroconf.asyncio import AsyncZeroconf  # type: ignore
        except ImportError:
            return []

        types = service_types or _COMMON_SERVICES
        services: list[ServiceInfo] = []

        try:
            aiozc = AsyncZeroconf()
            found_events: dict[str, asyncio.Event] = {}

            class Listener:
                def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    info = zc.get_service_info(type_, name)
                    if info:
                        ips = [socket.inet_ntoa(a) for a in info.addresses]
                        props = {}
                        if info.properties:
                            for k, v in info.properties.items():
                                key = k.decode() if isinstance(k, bytes) else k
                                val = v.decode() if isinstance(v, bytes) else str(v)
                                props[key] = val
                        services.append(
                            ServiceInfo(
                                name=name.replace(f".{type_}", "").rstrip("."),
                                type=type_.rstrip("."),
                                host=info.server.rstrip(".") if info.server else name,
                                ip=ips[0] if ips else None,
                                port=info.port,
                                properties=props,
                                source="mdns",
                            )
                        )

                def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    pass

                def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    pass

            listener = Listener()
            browsers = [
                ServiceBrowser(aiozc.zeroconf, stype, listener)
                for stype in types
            ]

            await asyncio.sleep(self.timeout)

            for browser in browsers:
                browser.cancel()
            await aiozc.async_close()

        except Exception:
            pass

        return services

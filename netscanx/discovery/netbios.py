"""NetBIOS name service scanner (UDP port 137)."""
from __future__ import annotations

import asyncio
import struct

from netscanx.models import ServiceInfo

_NBSTAT_REQUEST = (
    b"\x00\x00"  # Transaction ID
    b"\x00\x00"  # Flags
    b"\x00\x01"  # Questions: 1
    b"\x00\x00"  # Answer RRs
    b"\x00\x00"  # Authority RRs
    b"\x00\x00"  # Additional RRs
    b"\x20"      # Name length: 32
    + b"CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # Encoded "*"
    + b"\x00"    # Name terminator
    b"\x00\x21"  # Type: NBSTAT
    b"\x00\x01"  # Class: IN
)


class NetBIOSScanner:
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout

    async def scan(self, ip: str) -> ServiceInfo | None:
        try:
            loop = asyncio.get_event_loop()
            sock = __import__("socket").socket(
                __import__("socket").AF_INET,
                __import__("socket").SOCK_DGRAM,
            )
            sock.setblocking(False)
            sock.settimeout(self.timeout)

            try:
                await asyncio.wait_for(
                    loop.sock_sendto(sock, _NBSTAT_REQUEST, (ip, 137)),
                    timeout=self.timeout,
                )
                data, _ = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 1024),
                    timeout=self.timeout,
                )
                parsed = _parse_nbstat(data)
                if parsed:
                    return ServiceInfo(
                        name=parsed.get("computer_name", ip),
                        type="netbios",
                        host=ip,
                        ip=ip,
                        port=137,
                        protocol="udp",
                        properties=parsed,
                        source="netbios",
                    )
            finally:
                sock.close()
        except Exception:
            pass
        return None

    async def scan_network(self, ips: list[str]) -> list[ServiceInfo]:
        sem = asyncio.Semaphore(32)

        async def bounded(ip: str) -> ServiceInfo | None:
            async with sem:
                return await self.scan(ip)

        results = await asyncio.gather(*[bounded(ip) for ip in ips])
        return [r for r in results if r is not None]


def _parse_nbstat(data: bytes) -> dict | None:
    try:
        if len(data) < 57:
            return None
        num_names = data[56]
        names: list[str] = []
        workgroup = None
        mac = None
        offset = 57

        for _ in range(num_names):
            if offset + 18 > len(data):
                break
            raw_name = data[offset : offset + 15].rstrip(b"\x00 ").decode("ascii", errors="ignore")
            name_type = data[offset + 15]
            flags = struct.unpack(">H", data[offset + 16 : offset + 18])[0]
            names.append(raw_name)
            if name_type == 0x00 and not workgroup:
                workgroup = raw_name
            offset += 18

        if offset + 6 <= len(data):
            mac_bytes = data[offset : offset + 6]
            mac = ":".join(f"{b:02x}" for b in mac_bytes)

        result: dict = {"names": names}
        if workgroup:
            result["computer_name"] = workgroup
        if mac:
            result["mac"] = mac
        return result
    except Exception:
        return None

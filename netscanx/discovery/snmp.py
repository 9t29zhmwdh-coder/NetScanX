"""SNMP v1/v2c system information scanner."""
from __future__ import annotations

import asyncio
import struct

from netscanx.models import ServiceInfo

_COMMON_OIDS = {
    "sysDescr": (1, 3, 6, 1, 2, 1, 1, 1, 0),
    "sysName": (1, 3, 6, 1, 2, 1, 1, 5, 0),
    "sysLocation": (1, 3, 6, 1, 2, 1, 1, 6, 0),
    "sysContact": (1, 3, 6, 1, 2, 1, 1, 4, 0),
}


class SNMPScanner:
    def __init__(self, community: str = "public", timeout: float = 2.0):
        self.community = community
        self.timeout = timeout

    async def get_system_info(self, ip: str) -> ServiceInfo | None:
        results: dict[str, str] = {}
        for name, oid in _COMMON_OIDS.items():
            val = await self._get(ip, oid)
            if val:
                results[name] = val

        if not results:
            return None

        device_name = results.get("sysName") or results.get("sysDescr", ip)
        return ServiceInfo(
            name=device_name[:60],
            type="snmp",
            host=ip,
            ip=ip,
            port=161,
            protocol="udp",
            properties=results,
            source="snmp",
        )

    async def scan_network(self, ips: list[str]) -> list[ServiceInfo]:
        sem = asyncio.Semaphore(16)

        async def bounded(ip: str) -> ServiceInfo | None:
            async with sem:
                return await self.get_system_info(ip)

        results = await asyncio.gather(*[bounded(ip) for ip in ips])
        return [r for r in results if r is not None]

    async def _get(self, ip: str, oid: tuple) -> str | None:
        try:
            pkt = _build_get_request(self.community, oid)
            loop = asyncio.get_event_loop()
            import socket as _socket

            sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            sock.setblocking(False)
            try:
                await asyncio.wait_for(
                    loop.sock_sendto(sock, pkt, (ip, 161)), timeout=self.timeout
                )
                data, _ = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 4096), timeout=self.timeout
                )
                return _parse_response(data)
            finally:
                sock.close()
        except Exception:
            return None


def _encode_oid(oid: tuple) -> bytes:
    enc = bytes([40 * oid[0] + oid[1]])
    for n in oid[2:]:
        if n < 128:
            enc += bytes([n])
        else:
            parts = []
            while n:
                parts.append(n & 0x7F)
                n >>= 7
            parts.reverse()
            for i, b in enumerate(parts):
                enc += bytes([b | (0x80 if i < len(parts) - 1 else 0)])
    return enc


def _tlv(tag: int, val: bytes) -> bytes:
    if len(val) < 128:
        return bytes([tag, len(val)]) + val
    elif len(val) < 256:
        return bytes([tag, 0x81, len(val)]) + val
    else:
        return bytes([tag, 0x82, len(val) >> 8, len(val) & 0xFF]) + val


def _build_get_request(community: str, oid: tuple) -> bytes:
    version = _tlv(0x02, b"\x00")
    comm = _tlv(0x04, community.encode())
    oid_enc = _tlv(0x06, _encode_oid(oid))
    varbind = _tlv(0x30, _tlv(0x30, oid_enc + _tlv(0x05, b"")))
    request_id = _tlv(0x02, b"\x01")
    error_status = _tlv(0x02, b"\x00")
    error_index = _tlv(0x02, b"\x00")
    get_pdu = _tlv(0xA0, request_id + error_status + error_index + varbind)
    return _tlv(0x30, version + comm + get_pdu)


def _parse_response(data: bytes) -> str | None:
    try:
        i = 0
        if data[i] != 0x30:
            return None
        i += 1
        i += 1 if data[i] < 128 else (data[i] & 0x7F) + 1

        while i < len(data):
            tag = data[i]
            i += 1
            length = data[i]
            i += 1
            if length & 0x80:
                n = length & 0x7F
                length = int.from_bytes(data[i : i + n], "big")
                i += n
            value = data[i : i + length]
            i += length

            if tag == 0x04:  # OCTET STRING
                return value.decode("utf-8", errors="replace").strip()

        return None
    except Exception:
        return None

"""P2P speedtest: TCP throughput, UDP packet loss, latency/jitter, MTU detection."""
from __future__ import annotations

import asyncio
import os
import struct
import time

from netscanx.models import LatencyStats, SpeedtestResult, ThroughputResult
from netscanx.scanner.layer3 import ping_stats

_TCP_PORT = 15101
_UDP_PORT = 15102
_CHUNK = 65536
_MAGIC = b"NETSCANX"


class SpeedtestServer:
    def __init__(self, host: str = "0.0.0.0", tcp_port: int = _TCP_PORT, udp_port: int = _UDP_PORT):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self._stop = asyncio.Event()

    async def start(self) -> None:
        tcp_srv = await asyncio.start_server(self._handle_tcp, self.host, self.tcp_port)
        udp_transport, _ = await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: _UDPServerProtocol(),
            local_addr=(self.host, self.udp_port),
        )

        print(f"NetScanX speedtest server: TCP :{self.tcp_port}  UDP :{self.udp_port}")
        print("Press Ctrl+C to stop.")

        try:
            async with tcp_srv:
                await self._stop.wait()
        finally:
            udp_transport.close()

    async def _handle_tcp(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            total = 0
            while True:
                chunk = await asyncio.wait_for(reader.read(_CHUNK), timeout=10)
                if not chunk:
                    break
                total += len(chunk)
        except Exception:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop.set()


class _UDPServerProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        if data[:8] == _MAGIC:
            self.transport.sendto(data, addr)


class SpeedtestClient:
    def __init__(self, host: str, tcp_port: int = _TCP_PORT, udp_port: int = _UDP_PORT):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port

    async def run(
        self,
        duration: int = 10,
        tcp: bool = True,
        udp: bool = True,
        latency_count: int = 20,
    ) -> SpeedtestResult:
        result = SpeedtestResult(host=self.host, port=self.tcp_port)

        result.latency = await ping_stats(self.host, count=latency_count, interval=0.1)

        if tcp:
            result.tcp = await self._tcp_test(duration)

        if udp:
            result.udp = await self._udp_test(duration)

        return result

    async def _tcp_test(self, duration: int) -> ThroughputResult:
        chunk = os.urandom(_CHUNK)
        total = 0
        t0 = time.monotonic()

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.tcp_port), timeout=5
            )
            deadline = t0 + duration
            while time.monotonic() < deadline:
                writer.write(chunk)
                await writer.drain()
                total += len(chunk)
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=2)
            except Exception:
                pass
        except Exception:
            pass

        elapsed = time.monotonic() - t0
        mbps = (total * 8 / 1_000_000) / elapsed if elapsed > 0 else 0.0
        return ThroughputResult(
            protocol="tcp",
            bytes_transferred=total,
            duration_s=elapsed,
            mbps=mbps,
        )

    async def _udp_test(self, duration: int, packet_size: int = 1400) -> ThroughputResult:
        sent = 0
        received = 0
        total_bytes = 0
        t0 = time.monotonic()

        loop = asyncio.get_event_loop()
        import socket as _socket

        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.settimeout(1.0)

        try:
            deadline = t0 + duration
            while time.monotonic() < deadline:
                seq = struct.pack(">I", sent)
                payload = _MAGIC + seq + os.urandom(packet_size - 12)
                try:
                    await asyncio.wait_for(
                        loop.sock_sendto(sock, payload, (self.host, self.udp_port)),
                        timeout=0.1,
                    )
                    sent += 1
                    total_bytes += len(payload)
                except Exception:
                    pass

                try:
                    data, _ = await asyncio.wait_for(
                        loop.sock_recvfrom(sock, 4096), timeout=0.05
                    )
                    if data[:8] == _MAGIC:
                        received += 1
                except asyncio.TimeoutError:
                    pass
                except Exception:
                    pass
        finally:
            sock.close()

        elapsed = time.monotonic() - t0
        loss = 100 * (sent - received) / sent if sent else 0.0
        mbps = (total_bytes * 8 / 1_000_000) / elapsed if elapsed > 0 else 0.0

        return ThroughputResult(
            protocol="udp",
            bytes_transferred=total_bytes,
            duration_s=elapsed,
            mbps=mbps,
            packet_loss_pct=loss,
            packets_sent=sent,
            packets_received=received,
        )

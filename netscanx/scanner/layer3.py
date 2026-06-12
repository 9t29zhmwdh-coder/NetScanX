"""Layer-3 scanner: ICMP ping sweep, MTU detection, IP conflict detection."""
from __future__ import annotations

import asyncio
import ipaddress
import platform
import socket
import statistics
import time

from netscanx.models import Host, LatencyStats
from netscanx.scanner.privileges import is_root


class ICMPScanner:
    def __init__(self, timeout: float = 2.0, concurrency: int = 128):
        self.timeout = timeout
        self.concurrency = concurrency

    async def sweep(self, network: str) -> list[Host]:
        net = ipaddress.ip_network(network, strict=False)
        ips = [str(ip) for ip in net.hosts()]
        sem = asyncio.Semaphore(self.concurrency)

        async def probe(ip: str) -> Host | None:
            async with sem:
                alive, ttl = await self._ping(ip)
                if alive:
                    return Host(ip=ip, ttl=ttl, discovered_via=["icmp"])
            return None

        results = await asyncio.gather(*[probe(ip) for ip in ips])
        return [h for h in results if h is not None]

    async def _ping(self, host: str) -> tuple[bool, int | None]:
        if is_root():
            return await self._ping_icmplib(host)
        return await self._ping_subprocess(host)

    async def _ping_icmplib(self, host: str) -> tuple[bool, int | None]:
        try:
            import icmplib  # type: ignore

            result = await asyncio.to_thread(
                icmplib.ping, host, count=1, timeout=int(self.timeout), privileged=True
            )
            return result.is_alive, None
        except Exception:
            return await self._ping_subprocess(host)

    async def _ping_subprocess(self, host: str) -> tuple[bool, int | None]:
        try:
            cmd = _build_ping_cmd(host, 1, int(self.timeout * 1000))
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=self.timeout + 1)
            return proc.returncode == 0, None
        except Exception:
            return False, None


async def ping_stats(host: str, count: int = 10, interval: float = 0.2) -> LatencyStats:
    rtts: list[float] = []
    sent = count

    for _ in range(count):
        t0 = time.monotonic()
        alive = await _single_ping(host, timeout=2.0)
        elapsed_ms = (time.monotonic() - t0) * 1000
        if alive:
            rtts.append(elapsed_ms)
        await asyncio.sleep(interval)

    received = len(rtts)
    loss = 100 * (sent - received) / sent if sent else 0.0

    if rtts:
        diffs = [abs(rtts[i + 1] - rtts[i]) for i in range(len(rtts) - 1)]
        jitter = statistics.mean(diffs) if diffs else 0.0
        return LatencyStats(
            host=host,
            min_ms=min(rtts),
            max_ms=max(rtts),
            avg_ms=statistics.mean(rtts),
            jitter_ms=jitter,
            packet_loss_pct=loss,
            packets_sent=sent,
            packets_received=received,
        )
    return LatencyStats(
        host=host,
        min_ms=0,
        max_ms=0,
        avg_ms=0,
        jitter_ms=0,
        packet_loss_pct=100.0,
        packets_sent=sent,
        packets_received=0,
    )


async def _single_ping(host: str, timeout: float = 2.0) -> bool:
    if is_root():
        try:
            import icmplib  # type: ignore
            result = await asyncio.to_thread(
                icmplib.ping, host, count=1, timeout=int(timeout), privileged=True
            )
            return result.is_alive
        except Exception:
            pass

    try:
        cmd = _build_ping_cmd(host, 1, int(timeout * 1000))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=timeout + 1)
        return proc.returncode == 0
    except Exception:
        return False


async def detect_mtu(host: str, min_size: int = 576, max_size: int = 9000) -> int | None:
    if not is_root():
        return None
    try:
        from scapy.all import ICMP, IP, sr1  # type: ignore

        low, high = min_size, max_size
        last_ok = min_size

        while low <= high:
            mid = (low + high) // 2
            payload = b"X" * (mid - 28)
            pkt = IP(dst=host, flags="DF") / ICMP() / payload
            resp = await asyncio.to_thread(
                lambda: sr1(pkt, timeout=2, verbose=False)
            )
            if resp is not None:
                last_ok = mid
                low = mid + 1
            else:
                high = mid - 1

        return last_ok
    except Exception:
        return None


async def check_ip_conflict(ip: str) -> bool:
    if not is_root():
        return False
    try:
        from scapy.all import ARP, Ether, srp  # type: ignore

        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(op=1, pdst=ip)
        answered, _ = await asyncio.to_thread(
            lambda: srp(pkt, timeout=2, verbose=False)
        )
        return len(answered) > 1
    except Exception:
        return False


def _build_ping_cmd(host: str, count: int, timeout_ms: int) -> list[str]:
    system = platform.system()
    if system == "Windows":
        return ["ping", "-n", str(count), "-w", str(timeout_ms), host]
    elif system == "Darwin":
        return ["ping", "-c", str(count), "-W", str(timeout_ms), host]
    else:
        return ["ping", "-c", str(count), "-W", str(timeout_ms // 1000 or 1), host]

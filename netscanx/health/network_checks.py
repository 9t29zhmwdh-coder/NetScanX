"""Network-observable health signals: work for ANY device without
credentials, reusing existing scan primitives. Deliberately a lightweight
set of red flags, NOT the full deferred Risk Scoring engine (see
ROADMAP.md). Weights sum to 100 across this check set."""
from __future__ import annotations

import asyncio
import socket
import time

from netscanx.health.models import HealthCheck, HealthReport
from netscanx.models import Host
from netscanx.scanner.layer3 import ping_stats

_RISKY_PORTS = {23: "Telnet", 445: "SMB", 139: "NetBIOS/SMB"}


class NetworkHealthRunner:
    def __init__(self, host: Host):
        self.host = host

    async def run_all(self) -> HealthReport:
        report = HealthReport(target=self.host.ip)
        checks = [self._check_reachability(), self._check_risky_ports(), self._check_open_port_count()]
        if self.host.hostname:
            checks.append(self._check_dns_response())
        results = await asyncio.gather(*checks, return_exceptions=True)
        for r in results:
            if isinstance(r, HealthCheck):
                report.add(r)
            elif isinstance(r, Exception):
                report.add(HealthCheck(name="internal", status="error", message=str(r), weight=0))
        return report

    async def _check_reachability(self) -> HealthCheck:
        try:
            stats = await ping_stats(self.host.ip, count=5, interval=0.2)
        except Exception as e:
            return HealthCheck(
                name="Reachability", status="error", message=f"Unreachable: {e}", weight=30,
            )
        if stats.packet_loss_pct >= 100:
            status = "error"
        elif stats.packet_loss_pct > 0 or stats.avg_ms > 200:
            status = "warning"
        else:
            status = "ok"
        return HealthCheck(
            name="Reachability", status=status,
            message=f"{stats.avg_ms:.0f}ms avg, {stats.packet_loss_pct:.0f}% loss",
            weight=30,
        )

    async def _check_dns_response(self) -> HealthCheck:
        t0 = time.monotonic()
        try:
            await asyncio.to_thread(socket.getaddrinfo, self.host.hostname, None)
            ms = (time.monotonic() - t0) * 1000
            status = "warning" if ms > 500 else "ok"
            return HealthCheck(
                name="DNS Response", status=status, message=f"{ms:.0f}ms", weight=20,
            )
        except Exception as e:
            return HealthCheck(
                name="DNS Response", status="warning", message=f"Resolution failed: {e}", weight=20,
            )

    async def _check_risky_ports(self) -> HealthCheck:
        open_port_numbers = {p.port for p in self.host.open_ports}
        found = [
            f"{name} ({port})" for port, name in _RISKY_PORTS.items() if port in open_port_numbers
        ]
        if found:
            return HealthCheck(
                name="Risky Ports", status="warning",
                message=f"Legacy/insecure protocol(s) open: {', '.join(found)}", weight=30,
            )
        return HealthCheck(name="Risky Ports", status="ok", message="No legacy protocols detected", weight=30)

    async def _check_open_port_count(self) -> HealthCheck:
        count = len(self.host.open_ports)
        if count > 15:
            status = "warning"
            message = f"{count} open ports -- unusually high, review exposure"
        else:
            status = "ok"
            message = f"{count} open port(s)"
        return HealthCheck(name="Open Port Count", status=status, message=message, weight=20)

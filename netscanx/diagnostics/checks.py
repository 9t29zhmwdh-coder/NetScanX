"""Auto-diagnostics: DNS, DHCP, routing, packet loss, latency, subnet config."""
from __future__ import annotations

import asyncio
import ipaddress
import platform
import socket
import subprocess
import time

from netscanx.models import DiagnosticCheck, DiagnosticReport
from netscanx.scanner.layer3 import ping_stats

_DNS_HOSTS = ["google.com", "cloudflare.com", "github.com"]
_DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]


class DiagnosticsRunner:
    def __init__(self, target: str = "local"):
        self.target = target

    async def run_all(self) -> DiagnosticReport:
        report = DiagnosticReport(target=self.target)
        checks = [
            self._check_dns(),
            self._check_default_gateway(),
            self._check_packet_loss(),
            self._check_latency(),
            self._check_subnet_config(),
            self._check_duplicate_dhcp(),
            self._check_ipv6(),
        ]
        results = await asyncio.gather(*checks, return_exceptions=True)
        for r in results:
            if isinstance(r, DiagnosticCheck):
                report.add(r)
            elif isinstance(r, Exception):
                report.add(DiagnosticCheck(
                    name="internal",
                    status="error",
                    message=str(r),
                ))
        return report

    async def _check_dns(self) -> DiagnosticCheck:
        results: dict[str, str] = {}
        errors: list[str] = []

        for host in _DNS_HOSTS:
            t0 = time.monotonic()
            try:
                await asyncio.to_thread(socket.getaddrinfo, host, None)
                ms = (time.monotonic() - t0) * 1000
                results[host] = f"{ms:.0f}ms"
            except Exception as e:
                errors.append(f"{host}: {e}")

        if errors and len(errors) == len(_DNS_HOSTS):
            return DiagnosticCheck(
                name="DNS Resolution",
                status="error",
                message="All DNS lookups failed",
                details={"errors": errors},
            )
        if errors:
            return DiagnosticCheck(
                name="DNS Resolution",
                status="warning",
                message=f"{len(errors)} of {len(_DNS_HOSTS)} lookups failed",
                details={"ok": results, "errors": errors},
            )
        return DiagnosticCheck(
            name="DNS Resolution",
            status="ok",
            message=f"All {len(_DNS_HOSTS)} hosts resolved",
            details=results,
        )

    async def _check_default_gateway(self) -> DiagnosticCheck:
        gw = _get_default_gateway()
        if not gw:
            return DiagnosticCheck(
                name="Default Gateway",
                status="warning",
                message="Could not determine default gateway",
            )

        stats = await ping_stats(gw, count=5, interval=0.1)
        if stats.packet_loss_pct >= 100:
            return DiagnosticCheck(
                name="Default Gateway",
                status="error",
                message=f"Gateway {gw} not reachable",
                details={"gateway": gw},
            )
        if stats.packet_loss_pct > 0 or stats.avg_ms > 100:
            return DiagnosticCheck(
                name="Default Gateway",
                status="warning",
                message=f"Gateway {gw} — {stats.avg_ms:.1f}ms avg, {stats.packet_loss_pct:.0f}% loss",
                details={"gateway": gw, "avg_ms": stats.avg_ms, "loss_pct": stats.packet_loss_pct},
            )
        return DiagnosticCheck(
            name="Default Gateway",
            status="ok",
            message=f"Gateway {gw} reachable — {stats.avg_ms:.1f}ms avg",
            details={"gateway": gw, "avg_ms": stats.avg_ms},
        )

    async def _check_packet_loss(self) -> DiagnosticCheck:
        target = "8.8.8.8"
        stats = await ping_stats(target, count=20, interval=0.1)

        if stats.packet_loss_pct >= 50:
            return DiagnosticCheck(
                name="Packet Loss",
                status="error",
                message=f"{stats.packet_loss_pct:.0f}% packet loss to {target}",
                details=stats.model_dump(),
            )
        if stats.packet_loss_pct > 5:
            return DiagnosticCheck(
                name="Packet Loss",
                status="warning",
                message=f"{stats.packet_loss_pct:.1f}% packet loss to {target}",
                details=stats.model_dump(),
            )
        return DiagnosticCheck(
            name="Packet Loss",
            status="ok",
            message=f"No packet loss — {stats.avg_ms:.1f}ms to {target}",
            details=stats.model_dump(),
        )

    async def _check_latency(self) -> DiagnosticCheck:
        target = "8.8.8.8"
        stats = await ping_stats(target, count=15, interval=0.1)

        if stats.avg_ms > 200:
            return DiagnosticCheck(
                name="Latency",
                status="warning" if stats.avg_ms < 500 else "error",
                message=f"High latency: {stats.avg_ms:.1f}ms avg, {stats.jitter_ms:.1f}ms jitter",
                details=stats.model_dump(),
            )
        if stats.jitter_ms > 50:
            return DiagnosticCheck(
                name="Latency",
                status="warning",
                message=f"High jitter: {stats.jitter_ms:.1f}ms (avg {stats.avg_ms:.1f}ms)",
                details=stats.model_dump(),
            )
        return DiagnosticCheck(
            name="Latency",
            status="ok",
            message=f"{stats.avg_ms:.1f}ms avg, {stats.jitter_ms:.1f}ms jitter",
            details=stats.model_dump(),
        )

    async def _check_subnet_config(self) -> DiagnosticCheck:
        issues: list[str] = []
        info: dict = {}

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            info["local_ip"] = local_ip

            if local_ip.startswith("169.254."):
                issues.append("APIPA address detected — DHCP may have failed")
            elif local_ip in ("127.0.0.1", "0.0.0.0"):
                issues.append("No valid IP address assigned")

            gw = _get_default_gateway()
            if gw:
                info["gateway"] = gw
                try:
                    local_net = ipaddress.ip_interface(f"{local_ip}/24").network
                    gw_ip = ipaddress.ip_address(gw)
                    if gw_ip not in local_net:
                        issues.append(f"Gateway {gw} is outside subnet {local_net}")
                except Exception:
                    pass

        except Exception as e:
            issues.append(str(e))

        if issues:
            return DiagnosticCheck(
                name="Subnet Config",
                status="error" if len(issues) > 1 else "warning",
                message="; ".join(issues),
                details=info,
            )
        return DiagnosticCheck(
            name="Subnet Config",
            status="ok",
            message=f"Local IP {info.get('local_ip', '?')} — gateway {info.get('gateway', '?')}",
            details=info,
        )

    async def _check_duplicate_dhcp(self) -> DiagnosticCheck:
        from netscanx.scanner.layer2 import parse_dhcp_leases

        try:
            leases = await parse_dhcp_leases()
            servers = {l.get("dhcp_server") for l in leases if l.get("dhcp_server")}

            if len(servers) > 1:
                return DiagnosticCheck(
                    name="Duplicate DHCP",
                    status="warning",
                    message=f"Multiple DHCP servers seen in lease history: {', '.join(servers)}",
                    details={"servers": list(servers)},
                )
            if servers:
                return DiagnosticCheck(
                    name="Duplicate DHCP",
                    status="ok",
                    message=f"Single DHCP server: {list(servers)[0]}",
                    details={"servers": list(servers)},
                )
        except Exception:
            pass

        return DiagnosticCheck(
            name="Duplicate DHCP",
            status="skipped",
            message="DHCP lease files not accessible on this platform",
        )

    async def _check_ipv6(self) -> DiagnosticCheck:
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            sock.connect(("2001:4860:4860::8888", 80))
            ipv6_addr = sock.getsockname()[0]
            sock.close()
            if ipv6_addr and ipv6_addr != "::":
                return DiagnosticCheck(
                    name="IPv6 Connectivity",
                    status="ok",
                    message=f"IPv6 available — {ipv6_addr}",
                    details={"ipv6_address": ipv6_addr},
                )
        except Exception:
            pass

        return DiagnosticCheck(
            name="IPv6 Connectivity",
            status="warning",
            message="IPv6 not available or not configured",
        )


def _get_default_gateway() -> str | None:
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                parts = line.split()
                if parts and parts[0] == "0.0.0.0" and len(parts) >= 3:
                    return parts[2]
        else:
            result = subprocess.run(
                ["ip", "route", "show", "default"] if system == "Linux"
                else ["route", "-n", "get", "default"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if "default" in line or "gateway" in line.lower():
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p in ("via", "gateway:") and i + 1 < len(parts):
                            return parts[i + 1]
                    for p in parts:
                        try:
                            ipaddress.ip_address(p)
                            if p not in ("0.0.0.0", "::"):
                                return p
                        except ValueError:
                            continue
    except Exception:
        pass
    return None

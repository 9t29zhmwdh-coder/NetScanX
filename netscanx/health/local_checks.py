"""Local machine health checks: disk/CPU/RAM always available via psutil;
Defender/BitLocker/Windows Update are Windows-only and best-effort via
PowerShell, "skipped" elsewhere -- same pattern as diagnostics/checks.py's
platform-gated checks. Weights sum to 100 across this check set."""
from __future__ import annotations

import asyncio
import subprocess
import sys

import psutil

from netscanx.health.models import HealthCheck, HealthReport


class LocalHealthRunner:
    async def run_all(self) -> HealthReport:
        report = HealthReport(target="local")
        checks = [
            self._check_disk_space(),
            self._check_cpu(),
            self._check_memory(),
            self._check_defender_status(),
            self._check_bitlocker_status(),
            self._check_windows_update(),
        ]
        results = await asyncio.gather(*checks, return_exceptions=True)
        for r in results:
            if isinstance(r, HealthCheck):
                report.add(r)
            elif isinstance(r, Exception):
                report.add(HealthCheck(name="internal", status="error", message=str(r), weight=0))
        return report

    async def _check_disk_space(self) -> HealthCheck:
        usage = await asyncio.to_thread(psutil.disk_usage, "/")
        free_gb = usage.free / (1024**3)
        if free_gb < 5:
            status = "error"
        elif free_gb < 15:
            status = "warning"
        else:
            status = "ok"
        return HealthCheck(
            name="Disk Space",
            status=status,
            message=f"{free_gb:.1f} GB free ({usage.percent:.0f}% used)",
            weight=20,
            details={"free_gb": round(free_gb, 1), "percent_used": usage.percent},
        )

    async def _check_cpu(self) -> HealthCheck:
        percent = await asyncio.to_thread(psutil.cpu_percent, 0.5)
        if percent > 90:
            status = "error"
        elif percent > 75:
            status = "warning"
        else:
            status = "ok"
        return HealthCheck(
            name="CPU Usage", status=status, message=f"{percent:.0f}% CPU", weight=15,
            details={"percent": percent},
        )

    async def _check_memory(self) -> HealthCheck:
        mem = await asyncio.to_thread(psutil.virtual_memory)
        if mem.percent > 90:
            status = "error"
        elif mem.percent > 80:
            status = "warning"
        else:
            status = "ok"
        return HealthCheck(
            name="Memory Usage", status=status, message=f"{mem.percent:.0f}% RAM used", weight=15,
            details={"percent": mem.percent},
        )

    async def _check_defender_status(self) -> HealthCheck:
        if sys.platform != "win32":
            return HealthCheck(
                name="Defender Status", status="skipped",
                message="Windows Defender only available on Windows", weight=20,
            )
        try:
            output = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command",
                 "(Get-MpComputerStatus).RealTimeProtectionEnabled"],
                capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
            )
            enabled = output.stdout.strip().lower() == "true"
            return HealthCheck(
                name="Defender Status",
                status="ok" if enabled else "error",
                message="Real-time protection enabled" if enabled else "Real-time protection disabled",
                weight=20,
            )
        except Exception as e:
            return HealthCheck(
                name="Defender Status", status="skipped", message=f"Could not query: {e}", weight=20,
            )

    async def _check_bitlocker_status(self) -> HealthCheck:
        if sys.platform != "win32":
            return HealthCheck(
                name="BitLocker Status", status="skipped",
                message="BitLocker only available on Windows", weight=15,
            )
        try:
            output = await asyncio.to_thread(
                subprocess.run,
                ["manage-bde", "-status", "C:"],
                capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
            )
            protected = "Protection On" in output.stdout
            return HealthCheck(
                name="BitLocker Status",
                status="ok" if protected else "warning",
                message="Drive C: protected" if protected else "Drive C: not protected",
                weight=15,
            )
        except Exception as e:
            return HealthCheck(
                name="BitLocker Status", status="skipped", message=f"Could not query: {e}", weight=15,
            )

    async def _check_windows_update(self) -> HealthCheck:
        if sys.platform != "win32":
            return HealthCheck(
                name="Windows Update", status="skipped",
                message="Windows Update only available on Windows", weight=15,
            )
        try:
            output = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-NoProfile", "-Command",
                 "(Get-HotFix | Sort-Object InstalledOn -Descending "
                 "| Select-Object -First 1).InstalledOn"],
                capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace",
            )
            last_update = output.stdout.strip()
            if not last_update:
                return HealthCheck(
                    name="Windows Update", status="skipped",
                    message="Could not determine last update date", weight=15,
                )
            return HealthCheck(
                name="Windows Update", status="ok", message=f"Last update: {last_update}", weight=15,
            )
        except Exception as e:
            return HealthCheck(
                name="Windows Update", status="skipped", message=f"Could not query: {e}", weight=15,
            )

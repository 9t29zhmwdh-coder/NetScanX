from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PortState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"


class Protocol(str, Enum):
    TCP = "tcp"
    UDP = "udp"


class Port(BaseModel):
    port: int
    protocol: Protocol = Protocol.TCP
    state: PortState = PortState.OPEN
    service: str | None = None
    banner: str | None = None
    version: str | None = None


class Host(BaseModel):
    ip: str
    mac: str | None = None
    hostname: str | None = None
    vendor: str | None = None
    ttl: int | None = None
    open_ports: list[Port] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    discovered_via: list[str] = Field(default_factory=list)
    os_guess: str | None = None  # passive TTL-based heuristic, see inventory/identity.py
    device_type: str | None = None  # passive heuristic, see inventory/identity.py
    timestamp: datetime = Field(default_factory=_now)


class ServiceInfo(BaseModel):
    name: str
    type: str
    host: str
    ip: str | None = None
    port: int | None = None
    protocol: str = "tcp"
    properties: dict[str, Any] = Field(default_factory=dict)
    source: str  # "mdns", "ssdp", "netbios", "snmp"
    timestamp: datetime = Field(default_factory=_now)


class LatencyStats(BaseModel):
    host: str
    min_ms: float
    max_ms: float
    avg_ms: float
    jitter_ms: float
    packet_loss_pct: float
    packets_sent: int
    packets_received: int


class ThroughputResult(BaseModel):
    protocol: str
    bytes_transferred: int
    duration_s: float
    mbps: float
    packet_loss_pct: float | None = None
    packets_sent: int | None = None
    packets_received: int | None = None


class SpeedtestResult(BaseModel):
    host: str
    port: int
    tcp: ThroughputResult | None = None
    udp: ThroughputResult | None = None
    latency: LatencyStats | None = None
    mtu_detected: int | None = None
    timestamp: datetime = Field(default_factory=_now)


class DiagnosticCheck(BaseModel):
    name: str
    status: str  # "ok", "warning", "error", "skipped"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class DiagnosticReport(BaseModel):
    target: str
    checks: list[DiagnosticCheck] = Field(default_factory=list)
    summary_ok: int = 0
    summary_warning: int = 0
    summary_error: int = 0
    timestamp: datetime = Field(default_factory=_now)

    def add(self, check: DiagnosticCheck) -> None:
        self.checks.append(check)
        if check.status == "ok":
            self.summary_ok += 1
        elif check.status == "warning":
            self.summary_warning += 1
        elif check.status == "error":
            self.summary_error += 1


class DiscoverResult(BaseModel):
    target: str
    hosts: list[Host] = Field(default_factory=list)
    scan_duration_s: float = 0.0
    timestamp: datetime = Field(default_factory=_now)


class ServicesResult(BaseModel):
    target: str
    services: list[ServiceInfo] = Field(default_factory=list)
    scan_duration_s: float = 0.0
    timestamp: datetime = Field(default_factory=_now)

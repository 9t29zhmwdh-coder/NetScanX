from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Device(Base):
    """Canonical device identity, resolved across scans. See
    netscanx/inventory/identity.py for the matching strategy."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    primary_mac: Mapped[str | None] = mapped_column(String(17), index=True, nullable=True)
    is_mac_randomized: Mapped[bool] = mapped_column(default=False)
    first_seen: Mapped[datetime] = mapped_column()
    last_seen: Mapped[datetime] = mapped_column()

    # Denormalized "last known" fields for fast dashboard reads without a join.
    last_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    last_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_os_guess: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_device_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Reserved for future credentialed enrichment (see enrichment/windows_wmi.py stub).
    # Always null until that feature is implemented.
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uptime_s: Mapped[int | None] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column()
    finished_at: Mapped[datetime] = mapped_column()
    scan_types: Mapped[str] = mapped_column(String(64))  # csv: "discover,services"
    host_count: Mapped[int] = mapped_column(default=0)
    is_baseline: Mapped[bool] = mapped_column(default=False, index=True)


class DeviceSnapshot(Base):
    """Full field snapshot of a device at the time of one scan run."""

    __tablename__ = "device_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_run_id: Mapped[int] = mapped_column(
        ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )

    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    mac: Mapped[str | None] = mapped_column(String(17), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ttl: Mapped[int | None] = mapped_column(nullable=True)
    os_guess: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    open_ports_json: Mapped[str] = mapped_column(Text, default="[]")
    services_json: Mapped[str] = mapped_column(Text, default="[]")
    snmp_sysdescr: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_via: Mapped[str] = mapped_column(String(255), default="")  # csv
    enriched_via: Mapped[str] = mapped_column(String(32), default="network-inferred")
    health_score: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column()


class ChangeEvent(Base):
    __tablename__ = "changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_run_id: Mapped[int] = mapped_column(
        ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    # one of: new_device, device_gone, port_opened, port_closed, hostname_changed,
    # os_guess_changed, ip_changed, mac_changed, vendor_changed, service_added,
    # service_removed, firmware_changed
    change_type: Mapped[str] = mapped_column(String(32), index=True)
    field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column()

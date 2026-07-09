from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotFields:
    """Minimal comparable projection of a device's state at one scan,
    decoupled from the ORM/Pydantic layers so this module has zero I/O
    dependency and is trivially unit-testable with plain fixtures."""

    ip: str | None = None
    mac: str | None = None
    hostname: str | None = None
    vendor: str | None = None
    os_guess: str | None = None
    device_type: str | None = None
    open_ports: frozenset[tuple[int, str]] = frozenset()
    services: frozenset[tuple[str, str]] = frozenset()
    snmp_sysdescr: str | None = None


@dataclass(frozen=True)
class ChangeRecord:
    change_type: str
    field: str | None = None
    old_value: str | None = None
    new_value: str | None = None


def diff_snapshots(old: SnapshotFields | None, new: SnapshotFields) -> list[ChangeRecord]:
    """Compares two SnapshotFields for the SAME device, returns the list of
    ChangeRecord entries. old=None means the device is new (single
    'new_device' record, no per-field diff)."""
    if old is None:
        return [ChangeRecord("new_device")]

    changes: list[ChangeRecord] = []

    if old.ip != new.ip:
        changes.append(ChangeRecord("ip_changed", "ip", old.ip, new.ip))
    # A MAC change on an otherwise-continuous device is intentionally kept
    # as an event on the SAME device (not a new-device/gone-device pair) --
    # see identity.py / plan for the reasoning. new.mac is None is ignored
    # (nothing observed this scan, not necessarily a real removal).
    if new.mac is not None and old.mac != new.mac:
        changes.append(ChangeRecord("mac_changed", "mac", old.mac, new.mac))
    if old.hostname != new.hostname:
        changes.append(ChangeRecord("hostname_changed", "hostname", old.hostname, new.hostname))
    if old.vendor != new.vendor:
        changes.append(ChangeRecord("vendor_changed", "vendor", old.vendor, new.vendor))
    if old.os_guess != new.os_guess:
        changes.append(ChangeRecord("os_guess_changed", "os_guess", old.os_guess, new.os_guess))

    for port, proto in sorted(new.open_ports - old.open_ports):
        changes.append(ChangeRecord("port_opened", "open_ports", None, f"{port}/{proto}"))
    for port, proto in sorted(old.open_ports - new.open_ports):
        changes.append(ChangeRecord("port_closed", "open_ports", f"{port}/{proto}", None))

    for name, type_ in sorted(new.services - old.services):
        changes.append(ChangeRecord("service_added", "services", None, f"{name} ({type_})"))
    for name, type_ in sorted(old.services - new.services):
        changes.append(ChangeRecord("service_removed", "services", f"{name} ({type_})", None))

    if old.snmp_sysdescr != new.snmp_sysdescr and (old.snmp_sysdescr or new.snmp_sysdescr):
        changes.append(
            ChangeRecord("firmware_changed", "snmp_sysdescr", old.snmp_sysdescr, new.snmp_sysdescr)
        )

    return changes


def diff_devices(
    previous: dict[int, SnapshotFields], current: dict[int, SnapshotFields]
) -> list[tuple[int, ChangeRecord]]:
    """Full diff across all devices, keyed by device_id. Detects per-field
    changes for devices present in both, 'new_device' for devices only in
    current, and 'device_gone' for devices only in previous."""
    results: list[tuple[int, ChangeRecord]] = []

    for device_id, new_fields in current.items():
        old_fields = previous.get(device_id)
        for change in diff_snapshots(old_fields, new_fields):
            results.append((device_id, change))

    for device_id in previous:
        if device_id not in current:
            results.append((device_id, ChangeRecord("device_gone")))

    return results

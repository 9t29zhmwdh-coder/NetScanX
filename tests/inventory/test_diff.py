from __future__ import annotations

from netscanx.inventory.diff import ChangeRecord, SnapshotFields, diff_devices, diff_snapshots


def _fields(**overrides) -> SnapshotFields:
    base = dict(
        ip="10.0.0.5",
        mac="AA:BB:CC:DD:EE:FF",
        hostname="pc-123",
        vendor="Dell Inc.",
        os_guess="windows",
        device_type="workstation",
        open_ports=frozenset({(22, "tcp")}),
        services=frozenset({("SSH", "ssh")}),
        snmp_sysdescr=None,
    )
    base.update(overrides)
    return SnapshotFields(**base)


def test_new_device_when_old_is_none():
    changes = diff_snapshots(None, _fields())
    assert changes == [ChangeRecord("new_device")]


def test_no_change_when_identical():
    a = _fields()
    b = _fields()
    assert diff_snapshots(a, b) == []


def test_ip_changed():
    changes = diff_snapshots(_fields(ip="10.0.0.5"), _fields(ip="10.0.0.6"))
    assert ChangeRecord("ip_changed", "ip", "10.0.0.5", "10.0.0.6") in changes


def test_mac_changed_when_new_mac_present():
    changes = diff_snapshots(
        _fields(mac="AA:BB:CC:DD:EE:FF"), _fields(mac="11:22:33:44:55:66")
    )
    assert ChangeRecord("mac_changed", "mac", "AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66") in changes


def test_mac_change_ignored_when_new_mac_is_none():
    # Not observing a MAC this scan (e.g. ping-only, no ARP) must not be
    # treated as the MAC vanishing.
    changes = diff_snapshots(_fields(mac="AA:BB:CC:DD:EE:FF"), _fields(mac=None))
    assert not any(c.change_type == "mac_changed" for c in changes)


def test_hostname_changed():
    changes = diff_snapshots(_fields(hostname="old-name"), _fields(hostname="new-name"))
    assert ChangeRecord("hostname_changed", "hostname", "old-name", "new-name") in changes


def test_os_guess_changed():
    changes = diff_snapshots(_fields(os_guess="windows"), _fields(os_guess="linux/unix/macos"))
    assert ChangeRecord("os_guess_changed", "os_guess", "windows", "linux/unix/macos") in changes


def test_port_opened_and_closed():
    old = _fields(open_ports=frozenset({(22, "tcp")}))
    new = _fields(open_ports=frozenset({(3389, "tcp")}))
    changes = diff_snapshots(old, new)
    assert ChangeRecord("port_opened", "open_ports", None, "3389/tcp") in changes
    assert ChangeRecord("port_closed", "open_ports", "22/tcp", None) in changes


def test_service_added_and_removed():
    old = _fields(services=frozenset({("SSH", "ssh")}))
    new = _fields(services=frozenset({("HTTP", "http")}))
    changes = diff_snapshots(old, new)
    assert ChangeRecord("service_added", "services", None, "HTTP (http)") in changes
    assert ChangeRecord("service_removed", "services", "SSH (ssh)", None) in changes


def test_firmware_changed_via_sysdescr():
    old = _fields(snmp_sysdescr="Firmware v1.0")
    new = _fields(snmp_sysdescr="Firmware v1.1")
    changes = diff_snapshots(old, new)
    assert ChangeRecord("firmware_changed", "snmp_sysdescr", "Firmware v1.0", "Firmware v1.1") in changes


def test_firmware_diff_ignored_when_both_none():
    changes = diff_snapshots(_fields(snmp_sysdescr=None), _fields(snmp_sysdescr=None))
    assert not any(c.change_type == "firmware_changed" for c in changes)


def test_diff_devices_new_and_gone():
    previous = {1: _fields()}
    current = {2: _fields(ip="10.0.0.9")}
    results = diff_devices(previous, current)
    types = {(device_id, c.change_type) for device_id, c in results}
    assert (2, "new_device") in types
    assert (1, "device_gone") in types


def test_diff_devices_unchanged_device_produces_no_records():
    same = _fields()
    previous = {1: same}
    current = {1: same}
    assert diff_devices(previous, current) == []


def test_diff_devices_field_change_on_existing_device():
    previous = {1: _fields(hostname="old")}
    current = {1: _fields(hostname="new")}
    results = diff_devices(previous, current)
    assert results == [(1, ChangeRecord("hostname_changed", "hostname", "old", "new"))]

from __future__ import annotations

from netscanx.inventory.identity import classify_device_type, guess_os_family, is_mac_randomized
from netscanx.models import Host, Port, ServiceInfo


def test_is_mac_randomized_true_for_locally_administered():
    # 0x02 = 0b00000010 -> U/L bit set
    assert is_mac_randomized("02:11:22:33:44:55") is True


def test_is_mac_randomized_false_for_globally_unique():
    # 0x00 = 0b00000000 -> U/L bit unset
    assert is_mac_randomized("00:11:22:33:44:55") is False
    # 0x08 = 0b00001000 -> U/L bit (2nd LSB) unset
    assert is_mac_randomized("08:11:22:33:44:55") is False


def test_is_mac_randomized_handles_dash_separator():
    assert is_mac_randomized("02-11-22-33-44-55") is True


def test_guess_os_family_none_when_ttl_missing():
    assert guess_os_family(None) is None


def test_guess_os_family_linux_boundaries():
    assert guess_os_family(64) == "linux/unix/macos"
    assert guess_os_family(63) == "linux/unix/macos"
    assert guess_os_family(44) == "linux/unix/macos"  # 20 hops away, still within tolerance


def test_guess_os_family_windows_boundary():
    assert guess_os_family(128) == "windows"
    assert guess_os_family(127) == "windows"


def test_guess_os_family_network_gear_boundary():
    assert guess_os_family(255) == "network-gear"
    assert guess_os_family(250) == "network-gear"


def test_guess_os_family_out_of_tolerance_returns_none():
    assert guess_os_family(1) is None  # too many hops from any baseline


def test_classify_device_type_printer_by_port():
    host = Host(ip="10.0.0.5", open_ports=[Port(port=9100)])
    assert classify_device_type(host) == "printer"


def test_classify_device_type_nas_by_vendor():
    host = Host(ip="10.0.0.6", vendor="Synology Inc.")
    assert classify_device_type(host) == "nas"


def test_classify_device_type_router_by_ssdp_type():
    host = Host(ip="10.0.0.1")
    services = [
        ServiceInfo(
            name="gateway", type="urn:schemas-upnp-org:device:InternetGatewayDevice:1",
            host="10.0.0.1", ip="10.0.0.1", source="ssdp",
        )
    ]
    assert classify_device_type(host, services) == "router"


def test_classify_device_type_workstation_by_rdp_port():
    host = Host(ip="10.0.0.20", open_ports=[Port(port=3389)])
    assert classify_device_type(host) == "workstation"


def test_classify_device_type_server_by_db_port():
    host = Host(ip="10.0.0.30", open_ports=[Port(port=5432)])
    assert classify_device_type(host) == "server"


def test_classify_device_type_none_when_no_signal():
    host = Host(ip="10.0.0.40")
    assert classify_device_type(host) is None

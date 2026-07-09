from __future__ import annotations

from netscanx.models import Host, ServiceInfo

# Printer/NAS/router/AP signals used by classify_device_type(). Deliberately
# simple heuristics -- best-effort, not authoritative (see ARCHITECTURE.md).
_PRINTER_PORTS = {9100, 631}
_NAS_VENDOR_HINTS = ("synology", "qnap", "netgear readynas", "truenas")
_AP_VENDOR_HINTS = ("ubiquiti", "tp-link", "aruba", "meraki", "unifi")
_ROUTER_TYPE_HINTS = ("internetgatewaydevice", "wanconnectiondevice")
_SERVER_PORTS = {22, 3306, 5432, 5900, 6379, 8080, 8443, 9200, 27017}


def is_mac_randomized(mac: str) -> bool:
    """Locally-administered bit (U/L bit) check: 2nd LSB of the first octet.
    Many phones/laptops randomize MACs for Wi-Fi privacy; a randomized MAC
    is not a reliable long-term device identifier."""
    first_octet_str = mac.split(":")[0].split("-")[0]
    first_octet = int(first_octet_str, 16)
    return bool(first_octet & 0b00000010)


def guess_os_family(ttl: int | None) -> str | None:
    """TTL-based OS family heuristic, decrement-normalized to the nearest
    common starting TTL (64/128/255) since intermediate hops decrement it.
    Best-effort only -- many devices customize their default TTL."""
    if ttl is None:
        return None
    for baseline, family in ((64, "linux/unix/macos"), (128, "windows"), (255, "network-gear")):
        if ttl <= baseline and baseline - ttl <= 20:
            return family
    return None


def classify_device_type(host: Host, services: list[ServiceInfo] | None = None) -> str | None:
    """Heuristic device-type classification from open ports, vendor string,
    and mDNS/SSDP service types. Best-effort only."""
    services = services or []
    vendor = (host.vendor or "").lower()
    ports = {p.port for p in host.open_ports}
    service_types = {s.type.lower() for s in services if s.host == host.ip or s.ip == host.ip}

    if ports & _PRINTER_PORTS or any("printer" in t or "_ipp." in t for t in service_types):
        return "printer"
    if any(hint in vendor for hint in _NAS_VENDOR_HINTS):
        return "nas"
    if any(hint in t for t in service_types for hint in _ROUTER_TYPE_HINTS):
        return "router"
    if any(hint in vendor for hint in _AP_VENDOR_HINTS) and not ports:
        return "access-point"
    if 3389 in ports:
        return "workstation"
    if ports & _SERVER_PORTS:
        return "server"
    if host.hostname or ports:
        return "workstation"
    return None

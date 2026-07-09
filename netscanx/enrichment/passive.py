from __future__ import annotations

from netscanx.inventory.identity import classify_device_type, guess_os_family
from netscanx.models import Host, ServiceInfo


async def enrich_host_passive(host: Host, services: list[ServiceInfo] | None = None) -> Host:
    """Adds os_guess and device_type to a Host using only already-collected
    scan data (TTL, open ports, vendor string, mDNS/SSDP service types) --
    no additional network I/O, no credentials required. Async for interface
    consistency with the rest of the codebase's call sites; does no I/O
    itself. Does not mutate the scanner core, only post-processes results
    at the orchestration layer (see inventory/service.py)."""
    services = services or []
    return host.model_copy(
        update={
            "os_guess": guess_os_family(host.ttl),
            "device_type": classify_device_type(host, services),
        }
    )

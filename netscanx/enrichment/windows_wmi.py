from __future__ import annotations

from netscanx.models import Host


class WMIEnricher:
    """Optional, explicitly opt-in Windows credentialed enrichment via WMI
    (serial number, domain membership, active user, uptime). Requires
    domain credentials stored via the OS keychain (`keyring`), never in
    .env or plaintext, per SECURITY.md.

    NOT IMPLEMENTED in v0.3.0 -- passive network scanning cannot obtain
    this data (see ROADMAP.md "Future"). This class exists only to
    document the intended interface for a later release; it is not wired
    into any CLI command or scan path.
    """

    def __init__(self, credential_service_name: str = "netscanx-wmi"):
        self.credential_service_name = credential_service_name

    async def enrich_host(self, host: Host) -> Host:
        raise NotImplementedError(
            "WMI enrichment is planned for a future release; see ROADMAP.md"
        )

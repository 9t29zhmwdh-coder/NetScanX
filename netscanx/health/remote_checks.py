from __future__ import annotations

from netscanx.health.models import HealthReport


class RemoteHealthRunner:
    """Placeholder for opt-in credentialed remote health checks (WinRM),
    reusing the same OS-keychain credential store as the WMI enrichment
    stub in enrichment/windows_wmi.py.

    NOT IMPLEMENTED in v0.3.0 -- see ROADMAP.md "Future". Not wired into
    any CLI command.
    """

    def __init__(self, host: str, credential_ref: str):
        self.host = host
        self.credential_ref = credential_ref

    async def run_all(self) -> HealthReport:
        raise NotImplementedError(
            "Remote credentialed health checks are planned for a future release; see ROADMAP.md"
        )

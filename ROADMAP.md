# Roadmap

## v0.1.0, Initial Import (2026-06-13)
- ARP/ICMP/TCP scanning
- mDNS, SSDP, NetBIOS, SNMP discovery
- Speedtest integration
- Auto-diagnose engine
- CLI via Click + Rich

## v0.2.0, Planned
- [ ] JSON/CSV export
- [ ] IPv6 support
- [ ] Config file (TOML)
- [ ] --watch mode (continuous polling)

## v0.3.0, Asset Discovery, Health, Baseline & Drift Detection, Portable Launcher (2026-07-09)
- [x] SQLite persistence layer (SQLAlchemy 2.0 async + aiosqlite)
- [x] Portable (USB) vs. installed DB path resolution (`--db-path` / `NETSCANX_DB_PATH`)
- [x] Passive Asset Discovery Plus: TTL-based OS family guess, device-type classification (printer/NAS/router/AP/workstation/server)
- [x] Health Check Engine: local machine health (disk/CPU/RAM/Defender/BitLocker/Windows Update via `psutil`) + lightweight network-observable signals (reachability, DNS response, risky open ports)
- [x] Network Baseline & Drift Detection (`netscanx baseline`, `netscanx changes`, `netscanx assets`), the project's centerpiece: persists every scan and diffs it against the previous scan or a pinned baseline
- [x] Dashboard: Change Report card, Asset Inventory card, Pin Baseline button, `GET /api/changes`, `GET /api/assets`, `POST /api/baseline`
- [x] Portable USB launcher: PyInstaller single-file binaries for Windows/macOS/Linux, tag-triggered release build
- [x] Initial pytest test suite + CI now runs tests, not just lint

## Future (not yet implemented; documented for transparency, deferred by design)
- [ ] Credentialed Windows enrichment via WMI (serial number, domain membership, active user, uptime). Interface stubbed in `netscanx/enrichment/windows_wmi.py`, opt-in, credentials via OS keychain, never implemented in v0.3.0 since passive network scanning cannot obtain this data
- [ ] Remote credentialed health checks (WinRM) for non-local Windows hosts. Interface stubbed in `netscanx/health/remote_checks.py`
- [ ] Full Risk Scoring engine (beyond the lightweight port-based signal already shipped in v0.3.0's Health Check Engine)
- [ ] UniFi controller integration (APs, clients, signal strength, mesh topology)
- [ ] Intune / Entra ID integration (compliance status, BitLocker key status)
- [ ] React-based frontend migration. Alpine.js retained through v0.3.0 to preserve the project's "no build step" philosophy
- [ ] PDF / Excel report export (Management/Security/Change/Asset Inventory reports)

## v0.4.0+: Plugin system, scheduled scans
- [ ] Plugin system for custom scanners
- [ ] Scheduled scans via cron integration

## v1.0.0, Stable
- [ ] Full test coverage
- [ ] Docker image
- [ ] Alembic-based schema migrations (prerequisite for any post-1.0 breaking schema change; v0.3.0 uses `create_all()` only)

## Dual-Licensing Readiness

Assessed 2026-07-11 as a Dual-Licensing candidate (Community MIT + Commercial/Enterprise tier): network asset inventory and baseline/drift monitoring is an established commercial IT-ops category (Lansweeper, Spiceworks, ManageEngine OpUtils), and NetScanX's own roadmap already lists several classic enterprise differentiators. Not ready yet; blocked on:

- [ ] No multi-site or multi-tenant aggregation yet: each scan/baseline is scoped to one local network, an MSP managing multiple client sites has no consolidated view
- [ ] Credentialed enrichment (WMI, WinRM) is stubbed but deliberately not implemented yet, still a Future item
- [ ] Intune/Entra ID and UniFi controller integration are still only roadmap entries, not implemented
- [ ] No centralized server across sites: the dashboard runs locally per scan host, not as a fleet-wide view

Once credentialed enrichment and the Intune/Entra ID/UniFi integrations land, revisit: candidate Enterprise-only features would be multi-site aggregation, credentialed Windows enrichment, Intune/Entra ID compliance correlation, and centralized reporting across sites, with the core scanner, baseline/drift engine and local dashboard staying Community/MIT.

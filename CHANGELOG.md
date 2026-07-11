# Changelog

All notable changes to NetScanX will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.3.5] - 2026-07-11

### Fixed

- Updated actions/setup-python, actions/upload-artifact and actions/download-artifact to their latest major versions in CI and the release workflow, since GitHub is deprecating the Node.js 20 runtime and older action versions were being forced onto Node 24 and crashing during post-run cleanup.

## [0.3.4] - 2026-07-10

### Fixed

- Removed em-dash from README.md/README.de.md, replaced with a colon

## [0.3.3] - 2026-07-10

### Added

- Windows release binary is now signed with a self-signed certificate (`signtool`, RFC3161 timestamped). Does not remove the SmartScreen warning (no trusted CA), but the signature does guarantee the file wasn't tampered with after release

## [0.3.2] - 2026-07-10

### Added

- Release workflow now also builds `NetScanX-Start-macOS.dmg`, a disk image wrapping the portable macOS binary for a more familiar download experience. Not code-signed, same Gatekeeper warning as the raw binary.

### Fixed

- Release workflow lacked `contents: write` permission, so the automated GitHub Release creation on tag push always failed with HTTP 403 (v0.3.1 tag was pushed but its release creation failed for this reason; skipped straight to 0.3.2 rather than deleting/retagging v0.3.1)

## [0.3.0] - 2026-07-09

### Added
- `netscanx baseline`: run a fresh scan and pin it as the reference baseline for drift detection.
- `netscanx changes [--since-baseline|--since-last]`: show devices/ports/services that changed since the last scan or the pinned baseline. This is the project's new centerpiece feature.
- `netscanx assets`: list the persisted device inventory (distinct from a single scan's transient results).
- `netscanx health [TARGET]`: local machine health checks (disk/CPU/RAM/Defender/BitLocker/Windows Update) without a target, or lightweight network-observable health signals (reachability, DNS response, risky open ports) for a given host.
- `discover --persist [--db-path PATH]`: persist scan results to the local SQLite inventory so they participate in baseline/drift detection.
- Passive Asset Discovery Plus: every discovered host now gets a best-effort `os_guess` (TTL heuristic) and `device_type` (printer/NAS/router/access-point/workstation/server) classification, with no additional network calls or credentials required.
- SQLite persistence layer (SQLAlchemy 2.0 async + aiosqlite): every scan is stored as a `ScanRun` with per-device `DeviceSnapshot`s, diffed against the previous snapshot to produce `ChangeEvent` records.
- Dashboard: new Change Report and Asset Inventory cards, a Pin Baseline button, and `GET /api/changes`, `GET /api/assets`, `POST /api/baseline` endpoints. The background scan now persists automatically and broadcasts a `change_detected` WebSocket event when drift is found.
- Portable USB launcher: single-file PyInstaller binaries for Windows/macOS/Linux (`NetScanX-Start-Windows.exe`, `NetScanX-Start-macOS`, `NetScanX-Start-Linux`). Double-clicking with no arguments launches the dashboard; running from a terminal exposes the full CLI. The SQLite database is stored next to the binary (`NetScanX-Data/`) so scan history travels with the USB stick across machines. Built automatically on tagged releases via `.github/workflows/release.yml`.
- Initial `tests/` suite (pytest + pytest-asyncio) covering the DB path resolution, schema round-trips, device identity heuristics, drift-detection diff logic, health score arithmetic, and an end-to-end persistence/diff scenario. CI now runs `pytest` in addition to lint.

### Changed
- Version bumped to 0.3.0.
- `netscanx/models.py`: `Host` gained two optional fields, `os_guess` and `device_type`, populated by the new passive enrichment pass.

### Security
- New credential-requiring features (WMI-based enrichment, WinRM-based remote health checks) are intentionally left as unimplemented interface stubs in this release rather than shipped half-finished; when implemented, they will use OS-keychain-backed credential storage per SECURITY.md, never `.env`/plaintext.

## [0.2.0] - 2026-07-06

### Fixed
- `discover`: MAC vendor lookup and hostname were always empty on non-root runs. The ARP sweep silently fell back to a MAC-less ping sweep, and no reverse DNS lookup existed at all.
- `discover`: the OS ARP cache is now always consulted to enrich already-discovered hosts with a MAC address (pinging a host makes the OS resolve it), so `--vendor` works without `sudo`/`--arp`.
- `discover`/`services`/`diagnose`/`speedtest`/`dashboard`: progress messages (e.g. "Looking up N MAC vendors…") were printed to stdout via Rich `Console()`, corrupting `--format json`/`--format yaml` output when redirected. They now go to stderr.
- `dashboard`: the background scan only ever read the ARP cache and ran diagnostics. Host discovery (ping/ARP sweep, vendor, hostname) and service discovery (mDNS/SSDP) never ran, leaving `/api/hosts` MAC-less and `/api/services` permanently empty.
- `dashboard`: the Services table used `name + ip` as its list key; several real-world services (e.g. duplicate SSDP announcements from one host) share both, so duplicate keys made Alpine.js silently drop rows even though the count in the header was correct. The key now includes the loop index, type, and port.
- `dashboard`: the Speedtest card checked for a nested `speedtest.latency` object that the `/api/speedtest` endpoint never returns (it returns the latency stats flat), so a result never rendered even on a successful ping.

### Added
- `discover --hostname/--no-hostname`: reverse DNS hostname resolution for discovered hosts (default on).
- Dashboard: hosts table now shows a Hostname column.
- Dashboard: new Speedtest/Ping card. Run an on-demand latency test (min/avg/max/jitter/packet loss) against any IP or hostname from the browser, backed by `GET/POST /api/speedtest`.
- README/README.de: corrected macOS/Linux install instructions. Plain `pip install` fails with `externally-managed-environment` (PEP 668) on Homebrew/Debian Python; documented the venv path as the default, with the `--break-system-packages` escape hatch called out as not recommended.

### Changed
- `netscanx.cli.discover.run_discover_scan()` and `netscanx.cli.services.run_services_scan()` are now reusable async functions returning result objects, shared by the CLI commands and the dashboard instead of duplicating scan logic.

## [0.1.0] - 2026-06-13

### Added
- Initial import: ARP/ICMP/TCP scan engine
- mDNS, SSDP, NetBIOS, SNMP discovery modules
- Speedtest integration
- Auto-diagnose engine
- CLI interface (Click + Rich)

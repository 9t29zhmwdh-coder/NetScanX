# Changelog

All notable changes to NetScanX will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.1.0] - 2026-07-06

### Fixed
- `discover`: MAC vendor lookup and hostname were always empty on non-root runs. The ARP sweep silently fell back to a MAC-less ping sweep, and no reverse DNS lookup existed at all.
- `discover`: the OS ARP cache is now always consulted to enrich already-discovered hosts with a MAC address (pinging a host makes the OS resolve it), so `--vendor` works without `sudo`/`--arp`.
- `discover`/`services`/`diagnose`/`speedtest`/`dashboard`: progress messages (e.g. "Looking up N MAC vendors…") were printed to stdout via Rich `Console()`, corrupting `--format json`/`--format yaml` output when redirected. They now go to stderr.
- `dashboard`: the background scan only ever read the ARP cache and ran diagnostics. Host discovery (ping/ARP sweep, vendor, hostname) and service discovery (mDNS/SSDP) never ran, leaving `/api/hosts` MAC-less and `/api/services` permanently empty.

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

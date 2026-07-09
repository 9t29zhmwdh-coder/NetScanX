# Architecture

## Overview

NetScanX is a modular Python CLI toolkit for network discovery and diagnostics.

```
netscanx/
├── cli/                 # Click commands: discover, services, speedtest, diagnose,
│                          dashboard, baseline, changes, assets, health
├── scanner/
│   ├── layer2.py        # ARP scanning, ARP cache, DHCP lease parsing
│   ├── layer3.py        # ICMP ping sweep, MTU detection, IP conflict detection
│   ├── layer4.py        # TCP connect/SYN/UDP scan, banner grabbing
│   ├── hostname.py      # Reverse DNS resolution
│   ├── vendor.py        # MAC OUI vendor lookup
│   └── privileges.py    # root/Administrator detection
├── discovery/
│   ├── mdns.py          # mDNS/Zeroconf discovery
│   ├── ssdp.py          # SSDP/UPnP discovery
│   ├── netbios.py       # NetBIOS name resolution
│   └── snmp.py          # SNMP v1/v2c system info
├── performance/
│   └── speedtest.py     # P2P TCP/UDP speedtest client and server
├── diagnostics/
│   └── checks.py        # Auto-diagnose engine (DNS, gateway, DHCP, IPv6, ...)
├── storage/              # SQLite persistence (SQLAlchemy 2.0 async)
│   ├── paths.py         # Portable-vs-installed DB path resolution
│   ├── schema.py        # Device / ScanRun / DeviceSnapshot / ChangeEvent
│   ├── db.py            # Engine and session management
│   └── repository.py    # CRUD layer
├── inventory/            # Device identity + drift-detection orchestration
│   ├── identity.py       # MAC-randomization check, OS/device-type heuristics
│   ├── diff.py           # Pure drift-detection diff logic
│   └── service.py        # Wires scanners + storage + diff together
├── health/                # Health Check Engine
│   ├── models.py         # HealthCheck / HealthReport (score 0-100)
│   ├── local_checks.py   # Disk/CPU/RAM (psutil) + Defender/BitLocker/Updates (Windows)
│   ├── network_checks.py # Reachability, DNS response, risky open ports
│   └── remote_checks.py  # Credentialed remote checks: interface stub, not implemented
├── enrichment/
│   ├── passive.py        # Passive OS-guess/device-type enrichment
│   └── windows_wmi.py    # Credentialed WMI enrichment: interface stub, not implemented
├── dashboard/
│   ├── server.py         # FastAPI app, REST + WebSocket endpoints
│   └── static/           # Alpine.js + Chart.js frontend, no build step
├── models.py             # Pydantic domain models (Host, Port, ServiceInfo, ...)
└── output.py              # Rich / JSON / YAML formatters

__main__frozen__.py         # PyInstaller entry point for the portable USB launcher
build/                      # PyInstaller .spec files (Windows/macOS/Linux)
```

## Design Decisions

- **Click + Rich:** Ergonomic CLI with progress bars and colour output.
- **Modular scanner:** Each protocol is isolated. Easy to add/remove.
- **No root required:** Where possible, uses unprivileged sockets (ICMP may need raw socket on Linux).
- **Persistence is additive, not required:** the scanner core (`scanner/`, `discovery/`) has no dependency on `storage/`. Only the CLI/dashboard orchestration layer (`inventory/service.py`) wires scanning to persistence, so `discover`/`services`/`diagnose` keep working exactly as before with no DB involved unless `--persist` or the dashboard is used.
- **Credentialed features are stubbed, not faked:** `enrichment/windows_wmi.py` and `health/remote_checks.py` raise `NotImplementedError` and are not wired into any command. Real per-device data (serial number, domain, active user, local health) that genuinely requires credentials is not simulated; see ROADMAP.md.

## CI

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest
```

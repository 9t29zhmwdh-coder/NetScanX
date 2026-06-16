# Architecture

## Overview

NetScanX is a modular Python CLI toolkit for network discovery and diagnostics.

```
netscanx/
├── cli.py          # Click entry point
├── scanner/
│   ├── arp.py      # ARP scanning
│   ├── icmp.py     # ICMP ping sweep
│   └── tcp.py      # TCP port scanner
├── discovery/
│   ├── mdns.py     # mDNS discovery
│   ├── ssdp.py     # SSDP/UPnP discovery
│   ├── netbios.py  # NetBIOS name resolution
│   └── snmp.py     # SNMP community scan
├── speedtest.py    # Speedtest integration
├── diagnose.py     # Auto-diagnose engine
└── output.py       # Rich console renderer
```

## Design Decisions

- **Click + Rich:** Ergonomic CLI with progress bars and colour output.
- **Modular scanner:** Each protocol is isolated — easy to add/remove.
- **No root required:** Where possible, uses unprivileged sockets (ICMP may need raw socket on Linux).

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

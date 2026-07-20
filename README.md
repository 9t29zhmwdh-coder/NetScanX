<div align="center">
  <img src="RayStudio.png" alt="RayStudio Logo" width="120"/>

  <h1>NetScanX</h1>
</div>

[🇩🇪 Deutsche Version](README.de.md)

[![CI](https://github.com/9t29zhmwdh-coder/NetScanX/actions/workflows/ci.yml/badge.svg)](https://github.com/9t29zhmwdh-coder/NetScanX/actions) [![CodeQL](https://github.com/9t29zhmwdh-coder/NetScanX/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/9t29zhmwdh-coder/NetScanX/security/code-scanning) [![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/9t29zhmwdh-coder/NetScanX/badge)](https://securityscorecards.dev/viewer/?uri=github.com/9t29zhmwdh-coder/NetScanX)
![Platform](https://img.shields.io/badge/Platform-macOS_%7C_Windows_%7C_Ubuntu-lightgrey) ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) ![AI | Claude Code](https://img.shields.io/badge/AI-Claude_Code-black?logo=anthropic&logoColor=white) ![AI | Copilot](https://img.shields.io/badge/AI-Copilot-black?logo=github&logoColor=white)

A cross-platform Network Discovery and Diagnostic Toolkit; discover hosts, enumerate services, measure throughput, and auto-diagnose network issues from a single CLI.

Runs on **macOS, Linux, and Windows**. No build step required, install with `pip` (see [Quick Start](#quick-start) for the platform-specific install path).

> **How it runs:** This is a command-line tool, not a desktop app and not a server. Each scan command runs once and exits, persisting results to a local SQLite database for baseline/drift comparison; there is no installer and no background process. The optional web dashboard (`netscanx dashboard`) is a local-only FastAPI server you start and stop yourself, not something always running.

<p align="center">
  <img src="docs/dashboard-screenshot.png" alt="NetScanX dashboard showing the Change Report and Asset Inventory cards" width="900"/>
</p>

<p align="center"><sub>Screenshot uses synthetic demo data, not a real network.</sub></p>

---

> 🌱 New here? → [Step-by-step guide for beginners](GETTING_STARTED.md)

---

**In practice:** you run a scan against your network once, NetScanX discovers hosts and services and stores the result locally; every subsequent scan is diffed against the last one (or a pinned baseline) so you immediately see what changed, new or gone devices, port changes, hostname/IP/MAC drift, without re-reading a full report each time.

---

## Features

| Module | What it does |
|--------|-------------|
| **Layer 2** | ARP sweep, ARP cache analysis, MAC vendor lookup, DHCP lease parsing |
| **Layer 3** | ICMP ping sweep, subnet scan, MTU detection, IP conflict detection |
| **Layer 4** | TCP connect scan, TCP SYN scan¹, UDP scan¹, banner grabbing |
| **Services** | mDNS, SSDP/UPnP, NetBIOS, SNMP discovery |
| **Performance** | P2P speedtest: TCP throughput, UDP packet loss, latency, jitter |
| **Diagnostics** | DNS errors, duplicate DHCP, routing problems, latency spikes, subnet misconfiguration |
| **Asset Discovery Plus** | Passive OS-family guess (TTL heuristic) and device-type classification (printer/NAS/router/AP/workstation/server), no extra network calls |
| **Health Check Engine** | Local machine health (disk/CPU/RAM/Defender/BitLocker/Windows Update) or lightweight network-observable health signals (reachability, DNS response, risky open ports) |
| **Baseline & Drift Detection** | Persists every scan to a local SQLite database and diffs it against the last scan or a pinned baseline: new/gone devices, port changes, hostname/IP/MAC/OS changes, service changes |
| **Dashboard** | Optional web dashboard (FastAPI + Alpine.js + Chart.js), now with Change Report and Asset Inventory views |
| **Portable Mode** | Single-file launcher for Windows/macOS/Linux, runnable from a USB stick, no install required |
| **Output** | Rich tables (default), JSON, YAML for automation |

¹ Requires root/admin.

---

## Requirements

- Python 3.11+ (Windows: from [python.org](https://www.python.org/downloads/windows/) or the Microsoft Store; macOS/Linux: usually preinstalled or via your package manager): **only needed for the `pip`-installed CLI**, not for the portable USB build below
- macOS, Linux, or Windows 10/11

---

## Quick Start

### macOS / Linux

Most modern installs (Homebrew Python, Debian/Ubuntu system Python, …) are **externally managed** (PEP 668) and reject a bare `pip install`. Use a virtual environment:

```bash
python3 -m venv ~/netscanx-venv
source ~/netscanx-venv/bin/activate

pip install git+https://github.com/9t29zhmwdh-coder/NetScanX.git
```

Every new shell session needs `source ~/netscanx-venv/bin/activate` again before running `netscanx`.

<details>
<summary>Not using a venv (not recommended)</summary>

```bash
pip install --break-system-packages git+https://github.com/9t29zhmwdh-coder/NetScanX.git
```

This installs into the system Python and can conflict with OS-managed packages.
</details>

### Windows

Requires Python 3.11+ from [python.org](https://www.python.org/downloads/windows/) (check **"Add python.exe to PATH"** during install) or the Microsoft Store.

```powershell
py -m pip install git+https://github.com/9t29zhmwdh-coder/NetScanX.git
```

The `py` launcher (bundled with the official Windows installer) is more reliably on `PATH` than a bare `pip`/`python` command, which is the most common cause of `pip : Die Benennung "pip" wurde nicht als Name eines Cmdlet ... erkannt` / `pip is not recognized`. If `py` isn't found either, Python itself isn't installed or wasn't added to `PATH`; reinstall from python.org with that checkbox enabled, or run the installer again and choose "Modify" → "Add to PATH".

Don't want to install Python at all? Use the [portable USB launcher](#portable--usb-mode) instead: a single `.exe`, no install, no PATH issues.

### Local development (any platform)

```bash
git clone https://github.com/9t29zhmwdh-coder/NetScanX
cd NetScanX
bash scripts/dev.sh             # Windows: .\scripts\dev.ps1
```

Creates a `.venv` and installs NetScanX in editable mode automatically (see [Local Development](#local-development)).

```bash
# Discover hosts on local network (auto-detects subnet)
netscanx discover

# Discover with port scan and vendor lookup
netscanx discover 192.168.1.0/24 --ports 22,80,443 --vendor

# Discover services (mDNS + SSDP + NetBIOS)
netscanx services

# Run diagnostics
netscanx diagnose

# Speedtest to another host (start server on that host first)
netscanx speedtest --server           # on host A
netscanx speedtest 192.168.1.10       # on host B

# Launch web dashboard
netscanx dashboard
```

---

## CLI Reference

### `netscanx discover [TARGET]`

Discover active hosts via ARP, ICMP ping, and port scanning.

```
Options:
  --arp / --no-arp         ARP sweep (requires root/admin)  [default: on]
  --ping / --no-ping       ICMP ping sweep                  [default: on]
  --ports TEXT             Port range, e.g. 22,80,443 or 1-1024
  --syn / --no-syn         TCP SYN scan (requires root/admin)
  --banner / --no-banner   Grab service banners
  --vendor / --no-vendor   Lookup MAC vendors (online API)
  --hostname / --no-hostname  Resolve hostnames via reverse DNS  [default: on]
  --timeout FLOAT          Probe timeout in seconds         [default: 2.0]
  --concurrency N          Concurrent probes               [default: 200]
  --format [table|json|yaml]
  -v, --verbose            Show port details
```

```bash
netscanx discover                          # auto-detect local /24
netscanx discover 10.0.0.0/24             # explicit subnet
sudo netscanx discover --arp --vendor     # ARP + MAC vendor lookup
netscanx discover 192.168.1.1 -p 1-65535  # full port scan on single host
netscanx discover --format json > hosts.json
```

MAC addresses are read from the OS ARP cache after each ping, so `--vendor` and hostname resolution work without root. `sudo`/`--arp` only adds a raw ARP sweep for hosts that don't answer ICMP.

### `netscanx services [TARGET]`

Discover network services using multicast and broadcast protocols.

```
Options:
  --mdns / --no-mdns       mDNS/Zeroconf browse  [default: on]
  --ssdp / --no-ssdp       SSDP/UPnP multicast   [default: on]
  --netbios / --no-netbios NetBIOS name scan      [default: on]
  --snmp / --no-snmp       SNMP v2c system info
  --community TEXT         SNMP community string  [default: public]
  --mdns-timeout FLOAT     Browse duration        [default: 5.0]
  --format [table|json|yaml]
```

```bash
netscanx services
netscanx services 192.168.1.0/24 --snmp
netscanx services --no-netbios --format yaml
```

### `netscanx speedtest [HOST]`

Measure TCP throughput, UDP packet loss, latency and jitter.

```
Options:
  --server                 Run in server mode
  --port INT               TCP/UDP base port  [default: 15101]
  --tcp / --no-tcp         TCP throughput test
  --udp / --no-udp         UDP packet loss test
  --duration SEC           Test duration      [default: 10]
  --pings N                Latency ping count [default: 20]
  --format [table|json|yaml]
```

```bash
# Two-machine P2P test:
netscanx speedtest --server              # on host A
netscanx speedtest 192.168.1.10         # on host B

# Latency-only (no server required):
netscanx speedtest 8.8.8.8 --no-tcp --no-udp --pings 50
```

### `netscanx diagnose [TARGET]`

Auto-diagnose network health.

```bash
netscanx diagnose
netscanx diagnose --format json | jq '.checks[] | select(.status != "ok")'
```

**Checks performed:**
- DNS resolution (google.com, cloudflare.com, github.com)
- Default gateway reachability and latency
- Packet loss to 8.8.8.8
- Latency and jitter measurement
- Subnet configuration (APIPA detection, gateway-subnet mismatch)
- Duplicate DHCP server detection
- IPv6 connectivity

### `netscanx dashboard`

Runs a discover scan (hosts, MAC, vendor, hostname), a services scan (mDNS/SSDP), and diagnostics on startup and on every "Rescan", plus an on-demand ping/latency test to any IP or hostname from the browser.

```bash
netscanx dashboard               # http://localhost:8080
netscanx dashboard --port 9090
```

The dashboard binds to `0.0.0.0` by default and has no authentication, so anyone on the same network can reach it and trigger scans or pings. Bind to `--host 127.0.0.1` if that's not desired.

### `netscanx baseline`

Runs a fresh scan and pins it as the reference baseline for drift detection.

```bash
netscanx baseline --target 10.0.0.0/24
```

### `netscanx changes`

Shows what changed (new/gone devices, port changes, hostname/IP/MAC/OS changes, service changes) since the last scan or the pinned baseline. This is NetScanX's centerpiece feature: the question it answers is "what changed", not just "what's on the network".

```
Options:
  --since-baseline          Show all changes since the pinned baseline
  --since-last               Show changes from the most recent scan  [default]
  --format [table|json|yaml]
  --db-path PATH             Override the SQLite database path
```

```bash
netscanx discover --persist          # scan and store it
netscanx changes                     # what changed vs. the previous persisted scan
netscanx baseline                    # pin the current state as a reference point
netscanx changes --since-baseline    # everything that drifted since that baseline
```

### `netscanx assets`

Lists the persisted device inventory (every device ever seen, not just the last scan).

```bash
netscanx assets --format json
```

### `netscanx health [TARGET]`

Runs health checks. Without `TARGET`: local-machine health (disk space, CPU, RAM, Windows Defender, BitLocker, Windows Update; the last three are Windows-only and `skipped` elsewhere). With `TARGET`: lightweight network-observable health signals (reachability, DNS response time, risky open ports like Telnet/SMB) for that host, requiring no credentials.

```bash
netscanx health                 # local machine
netscanx health 192.168.1.10    # a specific host on the network
```

---

## Privilege Requirements

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| TCP connect scan | no root | no root | no root |
| ICMP ping (via subprocess) | no root | no root | no root |
| ARP sweep | root / `cap_net_raw` | sudo | Administrator |
| TCP SYN scan | root / `cap_net_raw` | sudo | Administrator |
| UDP scan | root | sudo | Administrator |

### Linux; grant capability without sudo

```bash
sudo setcap cap_net_raw+ep $(which python3)
# or per-venv binary:
sudo setcap cap_net_raw+ep .venv/bin/python
```

---

## Architecture

```
netscanx/
├── cli/           → Click commands (discover, services, speedtest, diagnose, dashboard,
│                     baseline, changes, assets, health)
├── scanner/       → Layer 2/3/4 probe modules + privilege helpers
├── discovery/     → mDNS, SSDP, NetBIOS, SNMP
├── performance/   → P2P speedtest client/server
├── diagnostics/   → Network health checks
├── dashboard/     → FastAPI + Alpine.js + Chart.js web UI
├── storage/       → SQLite persistence (SQLAlchemy 2.0 async): schema, engine, repository,
│                     portable-vs-installed DB path resolution
├── inventory/     → Device identity resolution + drift-detection diff logic + orchestration
├── health/        → Health Check Engine (local, network-observable, remote-stub)
├── enrichment/    → Passive OS/device-type enrichment + WMI enrichment interface stub
├── models.py      → Pydantic models (Host, Port, ServiceInfo, …)
└── output.py      → Rich / JSON / YAML formatters

__main__frozen__.py → PyInstaller entry point for the portable USB launcher
build/               → PyInstaller .spec files (Windows/macOS/Linux)
```

---

## Portable / USB Mode

Since v0.3.0, NetScanX can run from a USB stick on any Windows, macOS, or Linux machine with no installation. Download the release binaries from the [Releases page](https://github.com/9t29zhmwdh-coder/NetScanX/releases) and copy them to the root of the stick:

```
USB-Stick-Root/
├── NetScanX-Start-Windows.exe
├── NetScanX-Start-macOS
├── NetScanX-Start-Linux
└── README.txt
```

On macOS, the release also includes `NetScanX-Start-macOS.dmg`, a disk image wrapping the same binary for a more familiar download/mount experience. It is not a "real" installer (there is nothing to install; NetScanX stays portable) and carries the same Gatekeeper warning as the raw binary.

Double-clicking a binary with no arguments launches the dashboard and opens your browser, mirroring `netscanx dashboard`. Running it from a terminal with arguments exposes the full CLI (`NetScanX-Start-Windows.exe discover --arp`, etc.). A `NetScanX-Data/` folder appears next to the binary on first run, containing the SQLite database. This is how scan history and baselines travel with the stick across different machines. Override the location with `--db-path` or `NETSCANX_DB_PATH` if needed.

Portable mode runs unprivileged by default on unfamiliar machines, just like the regular CLI's non-root fallback (see [Privilege Requirements](#privilege-requirements) below).

**Known limitations:**
- **Windows:** the `.exe` is signed with a self-signed certificate (not from a trusted CA), so it will still trigger a SmartScreen warning ("Windows protected your PC"). The signature only guarantees the file wasn't tampered with after signing, it does not establish publisher trust. Click "More info" → "Run anyway". A trusted-CA signature is a possible future improvement, see [ROADMAP.md](ROADMAP.md).
- **macOS:** the binary and the `.dmg` are unsigned and will trigger a Gatekeeper "unidentified developer" block on first run. Right-click the file → "Open" to bypass it once.
- **Linux:** FAT32/exFAT-formatted USB drives don't preserve the Unix executable bit, so the binary may not run on double-click. Run `chmod +x NetScanX-Start-Linux` first, or use your file manager's "Run as program" option.

---

## Output Formats

All commands support `--format [table|json|yaml]`:

```bash
netscanx discover --format json > scan.json
netscanx diagnose --format yaml
```

JSON/YAML output is fully serialisable and automation-friendly. Pipe into `jq`, Ansible, scripts, etc.

---

## Local Development

```bash
# Linux / macOS
bash scripts/dev.sh

# Windows (PowerShell)
.\scripts\dev.ps1

# Simulate network services locally (no real network needed)
python tools/test_network.py
netscanx discover 127.0.0.1 --no-arp --ping --ports 22,80,443,8080
```

---

## Uninstall / Cleanup

- `pip uninstall netscanx`
- Delete the local scan database: on macOS/Linux/Windows it lives in your OS's standard user-data directory (e.g. `~/Library/Application Support/netscanx` on macOS, `~/.local/share/netscanx` on Linux, `%LOCALAPPDATA%\netscanx` on Windows), or set `NETSCANX_DB_PATH` to see the exact path you configured
- Portable/USB mode: delete the launcher and its adjacent `NetScanX-Data/` folder; nothing is written anywhere else

---

**Author:** [Rafael Yilmaz](https://github.com/9t29zhmwdh-coder) · **Status:** Active · ![version](https://img.shields.io/github/v/release/9t29zhmwdh-coder/NetScanX?color=6b7280&style=flat-square) · **License:** MIT

<div align="center">
  <img src="RayStudio.png" alt="RayStudio Logo" width="120"/>

  <h1>NetScanX</h1>
</div>

[🇩🇪 Deutsche Version](README.de.md)

[![CI](https://github.com/9t29zhmwdh-coder/NetScanX/actions/workflows/ci.yml/badge.svg)](https://github.com/9t29zhmwdh-coder/NetScanX/actions) ![Platform](https://img.shields.io/badge/Platform-macOS_%7C_Windows_%7C_Ubuntu-lightgrey) ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) ![AI | Claude Code](https://img.shields.io/badge/AI-Claude_Code-black?logo=anthropic&logoColor=white) ![AI | Copilot](https://img.shields.io/badge/AI-Copilot-black?logo=github&logoColor=white)

A cross-platform Network Discovery and Diagnostic Toolkit; discover hosts, enumerate services, measure throughput, and auto-diagnose network issues from a single CLI.

Runs on **macOS, Linux, and Windows**. No build step required, install with `pip`.

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
| **Dashboard** | Optional web dashboard (FastAPI + Alpine.js + Chart.js) |
| **Output** | Rich tables (default), JSON, YAML for automation |

¹ Requires root/admin.

---

## Quick Start

```bash
# Install
pip install git+https://github.com/9t29zhmwdh-coder/NetScanX.git

# Or local dev
git clone https://github.com/9t29zhmwdh-coder/NetScanX
cd NetScanX
pip install -e .
```

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

```bash
netscanx dashboard               # http://localhost:8080
netscanx dashboard --port 9090
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
├── cli/           → Click commands (discover, services, speedtest, diagnose, dashboard)
├── scanner/       → Layer 2/3/4 probe modules + privilege helpers
├── discovery/     → mDNS, SSDP, NetBIOS, SNMP
├── performance/   → P2P speedtest client/server
├── diagnostics/   → Network health checks
├── dashboard/     → FastAPI + Alpine.js + Chart.js web UI
├── models.py      → Pydantic models (Host, Port, ServiceInfo, …)
└── output.py      → Rich / JSON / YAML formatters
```

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

---

**Author:** [Rafael Yilmaz](https://github.com/9t29zhmwdh-coder) · **Status:** Active · v0.1.0 · **License:** MIT

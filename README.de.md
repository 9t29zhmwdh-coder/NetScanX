<div align="center">
  <img src="RayStudio.png" alt="RayStudio Logo" width="120"/>

  <h1>NetScanX</h1>
</div>

[English](README.md)

# NetScanX

[![CI](https://github.com/9t29zhmwdh-coder/NetScanX/actions/workflows/ci.yml/badge.svg)](https://github.com/9t29zhmwdh-coder/NetScanX/actions) ![Platform](https://img.shields.io/badge/Platform-macOS_%7C_Windows_%7C_Ubuntu-lightgrey) ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) ![AI | Claude Code](https://img.shields.io/badge/AI-Claude_Code-black?logo=anthropic&logoColor=white) ![AI | Copilot](https://img.shields.io/badge/AI-Copilot-black?logo=github&logoColor=white)

Ein plattformübergreifendes Netzwerk-Discovery- und Diagnose-Toolkit; Hosts entdecken, Dienste aufzählen, Durchsatz messen und Netzwerkprobleme automatisch diagnostizieren, alles über eine einzige CLI.

Läuft auf **macOS, Linux und Windows**. Kein Build-Schritt nötig, Installation via `pip`.

---

## Features

| Modul | Funktion |
|-------|---------|
| **Layer 2** | ARP-Sweep, ARP-Cache-Analyse, MAC-Vendor-Lookup, DHCP-Lease-Parsing |
| **Layer 3** | ICMP-Ping-Sweep, Subnetz-Scan, MTU-Erkennung, IP-Konflikt-Erkennung |
| **Layer 4** | TCP-Connect-Scan, TCP-SYN-Scan¹, UDP-Scan¹, Banner-Grabbing |
| **Services** | mDNS, SSDP/UPnP, NetBIOS, SNMP-Discovery |
| **Performance** | P2P-Speedtest: TCP-Durchsatz, UDP-Paketverlust, Latenz, Jitter |
| **Diagnostics** | DNS-Fehler, doppelte DHCP-Server, Routing-Probleme, Latenz-Spitzen, Subnetz-Fehlkonfiguration |
| **Dashboard** | Optionales Web-Dashboard (FastAPI + Alpine.js + Chart.js) |
| **Output** | Rich-Tabellen (Standard), JSON, YAML für Automatisierung |

¹ Erfordert root/Administrator.

---

## Schnellstart

```bash
# Installation
pip install git+https://github.com/9t29zhmwdh-coder/NetScanX.git

# Oder lokale Entwicklung
git clone https://github.com/9t29zhmwdh-coder/NetScanX
cd NetScanX
pip install -e .
```

```bash
# Hosts im lokalen Netzwerk entdecken (Subnetz wird automatisch erkannt)
netscanx discover

# Mit Port-Scan und Vendor-Lookup
netscanx discover 192.168.1.0/24 --ports 22,80,443 --vendor

# Netzwerkdienste entdecken (mDNS + SSDP + NetBIOS)
netscanx services

# Diagnose ausführen
netscanx diagnose

# Speedtest zu einem anderen Host (Server dort zuerst starten)
netscanx speedtest --server           # auf Host A
netscanx speedtest 192.168.1.10       # auf Host B

# Web-Dashboard starten
netscanx dashboard
```

---

## CLI-Referenz

### `netscanx discover [TARGET]`

Aktive Hosts via ARP, ICMP-Ping und Port-Scan entdecken.

```
Optionen:
  --arp / --no-arp         ARP-Sweep (root/Admin nötig)  [Standard: an]
  --ping / --no-ping       ICMP-Ping-Sweep               [Standard: an]
  --ports TEXT             Port-Bereich, z. B. 22,80,443 oder 1-1024
  --syn / --no-syn         TCP-SYN-Scan (root/Admin nötig)
  --banner / --no-banner   Service-Banner abrufen
  --vendor / --no-vendor   MAC-Vendor-Lookup (Online-API)
  --timeout FLOAT          Timeout pro Probe in Sekunden [Standard: 2.0]
  --concurrency N          Gleichzeitige Probes          [Standard: 200]
  --format [table|json|yaml]
  -v, --verbose            Port-Details anzeigen
```

```bash
netscanx discover                          # lokales /24 automatisch erkennen
netscanx discover 10.0.0.0/24             # explizites Subnetz
sudo netscanx discover --arp --vendor     # ARP + MAC-Vendor-Lookup
netscanx discover 192.168.1.1 -p 1-65535  # Vollständiger Port-Scan
netscanx discover --format json > hosts.json
```

### `netscanx services [TARGET]`

Netzwerkdienste via Multicast- und Broadcast-Protokolle entdecken.

```
Optionen:
  --mdns / --no-mdns       mDNS/Zeroconf-Suche  [Standard: an]
  --ssdp / --no-ssdp       SSDP/UPnP-Multicast  [Standard: an]
  --netbios / --no-netbios NetBIOS-Name-Scan     [Standard: an]
  --snmp / --no-snmp       SNMP-v2c-System-Info
  --community TEXT         SNMP-Community-String [Standard: public]
  --format [table|json|yaml]
```

```bash
netscanx services
netscanx services 192.168.1.0/24 --snmp
netscanx services --no-netbios --format yaml
```

### `netscanx speedtest [HOST]`

TCP-Durchsatz, UDP-Paketverlust, Latenz und Jitter messen.

```bash
# Zwei-Maschinen P2P-Test:
netscanx speedtest --server              # auf Host A
netscanx speedtest 192.168.1.10         # auf Host B

# Nur Latenz (kein Server nötig):
netscanx speedtest 8.8.8.8 --no-tcp --no-udp --pings 50
```

### `netscanx diagnose`

Automatische Netzwerk-Diagnose.

**Durchgeführte Prüfungen:**
- DNS-Auflösung (google.com, cloudflare.com, github.com)
- Erreichbarkeit und Latenz des Standard-Gateways
- Paketverlust zu 8.8.8.8 (20 Pakete)
- Latenz und Jitter
- Subnetz-Konfiguration (APIPA-Erkennung, Gateway-Subnetz-Konflikt)
- Doppelte DHCP-Server (liest Lease-Dateien)
- IPv6-Konnektivität

### `netscanx dashboard`

```bash
netscanx dashboard               # http://localhost:8080
netscanx dashboard --port 9090
```

---

## Berechtigungen

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| TCP-Connect-Scan | kein root | kein root | kein Admin |
| ICMP-Ping (subprocess) | kein root | kein root | kein Admin |
| ARP-Sweep | root / `cap_net_raw` | sudo | Administrator |
| TCP-SYN-Scan | root / `cap_net_raw` | sudo | Administrator |
| UDP-Scan | root | sudo | Administrator |

### Linux; Berechtigung ohne sudo

```bash
sudo setcap cap_net_raw+ep $(which python3)
# oder im venv:
sudo setcap cap_net_raw+ep .venv/bin/python
```

---

## Architektur

```
netscanx/
├── cli/           → Click-Befehle (discover, services, speedtest, diagnose, dashboard)
├── scanner/       → Layer-2/3/4-Scan-Module + Privilege-Helpers
├── discovery/     → mDNS, SSDP, NetBIOS, SNMP
├── performance/   → P2P-Speedtest Client/Server
├── diagnostics/   → Netzwerk-Health-Checks
├── dashboard/     → FastAPI + Alpine.js + Chart.js Web-UI
├── models.py      → Pydantic-Modelle (Host, Port, ServiceInfo, …)
└── output.py      → Rich / JSON / YAML Formatter
```

---

## Ausgabeformate

Alle Befehle unterstützen `--format [table|json|yaml]`:

```bash
netscanx discover --format json > scan.json
netscanx diagnose --format yaml
netscanx diagnose --format json | python3 -c "import sys,json; d=json.load(sys.stdin); [print(c['name'],c['status']) for c in d['checks']]"
```

---

## Lokale Entwicklung

```bash
# Linux / macOS
bash scripts/dev.sh

# Windows (PowerShell)
.\scripts\dev.ps1

# Netzwerkdienste lokal simulieren (kein echtes Netz nötig)
python tools/test_network.py
netscanx discover 127.0.0.1 --no-arp --ping --ports 22,80,443,8080
```


---

**Autor:** [Rafael Yilmaz](https://github.com/9t29zhmwdh-coder) · **Status:** Active · ![version](https://img.shields.io/github/v/release/9t29zhmwdh-coder/NetScanX?label=\&color=6b7280\&style=flat-square) · **Lizenz:** MIT


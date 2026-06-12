#!/usr/bin/env bash
# Local development — Linux / macOS
set -e

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -e ".[dev]"
fi

echo "NetScanX venv ready."
echo "Activate: source .venv/bin/activate"
echo "Run:      netscanx --help"
echo ""
echo "Note: ARP sweep and SYN scan require root:"
echo "  sudo .venv/bin/netscanx discover --arp"

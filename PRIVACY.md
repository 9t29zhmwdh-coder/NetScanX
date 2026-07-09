# Privacy Policy

NetScanX is a local network diagnostic tool. All scan results remain exclusively
on your machine. No network topology data, IP addresses, hostname maps, or scan
results are transmitted to external servers or third parties.

- **No telemetry:** The application does not phone home or collect usage statistics.
- **No cloud sync:** All data stays local.
- **CLI output only:** Results are printed to stdout or saved locally by the user.
- **Local scan history:** Since v0.3.0, scan results and baseline/drift history are stored locally in a SQLite database. It sits next to the application when run portably from a USB stick, or in the OS application-data directory when installed via pip. This data never leaves your machine and is not synced anywhere.

If you use the speedtest feature, a connection to the speedtest provider's server
is made : that provider's privacy policy applies.

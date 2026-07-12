from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import yaml
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from netscanx.health.models import HealthReport
from netscanx.models import (
    DiagnosticReport,
    DiscoverResult,
    ServicesResult,
    SpeedtestResult,
)

console = Console()


def _default_serial(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Not JSON serializable: {type(obj)}")


def _to_dict(model: Any) -> Any:
    return json.loads(model.model_dump_json())


def emit_json(data: Any) -> None:
    if hasattr(data, "model_dump_json"):
        print(json.dumps(json.loads(data.model_dump_json()), indent=2))
    else:
        print(json.dumps(data, default=_default_serial, indent=2))


def emit_yaml(data: Any) -> None:
    if hasattr(data, "model_dump_json"):
        d = json.loads(data.model_dump_json())
    else:
        d = data
    print(yaml.dump(d, default_flow_style=False, allow_unicode=True, sort_keys=False))


def print_discover(result: DiscoverResult, verbose: bool = False) -> None:
    if not result.hosts:
        console.print("[yellow]No hosts discovered.[/yellow]")
        return

    table = Table(
        title=f"Discovered Hosts: {result.target} ({len(result.hosts)} found, {result.scan_duration_s:.1f}s)",
        box=box.ROUNDED,
        show_lines=False,
    )
    table.add_column("IP Address", style="cyan", min_width=15)
    table.add_column("MAC Address", style="magenta", min_width=17)
    table.add_column("Vendor", style="green", max_width=25)
    table.add_column("Hostname", style="white", max_width=30)
    table.add_column("Open Ports", style="yellow")
    table.add_column("Via", style="dim")

    for host in sorted(result.hosts, key=lambda h: tuple(int(x) for x in h.ip.split("."))):
        ports_str = ", ".join(str(p.port) for p in host.open_ports[:8])
        if len(host.open_ports) > 8:
            ports_str += f" +{len(host.open_ports) - 8}"
        table.add_row(
            host.ip,
            host.mac or "N/A",
            host.vendor or "N/A",
            host.hostname or "N/A",
            ports_str or "N/A",
            ", ".join(host.discovered_via),
        )

    console.print(table)

    if verbose:
        for host in result.hosts:
            if host.open_ports:
                console.print(f"\n[cyan]{host.ip}[/cyan]: open ports:")
                for p in host.open_ports:
                    svc = p.service or "unknown"
                    banner = f"  [dim]{p.banner[:60]}[/dim]" if p.banner else ""
                    console.print(f"  [green]{p.port:>5}[/green]/{p.protocol.value}  {svc}{banner}")


def print_services(result: ServicesResult) -> None:
    if not result.services:
        console.print("[yellow]No services discovered.[/yellow]")
        return

    table = Table(
        title=f"Discovered Services: {result.target} ({len(result.services)} found, {result.scan_duration_s:.1f}s)",
        box=box.ROUNDED,
    )
    table.add_column("Name", style="cyan", max_width=35)
    table.add_column("Type", style="magenta", max_width=25)
    table.add_column("Host / IP", style="green", min_width=15)
    table.add_column("Port", style="yellow", justify="right")
    table.add_column("Source", style="dim")

    for svc in result.services:
        host_str = svc.host if svc.host != svc.ip else ""
        ip_str = svc.ip or ""
        host_display = f"{host_str}\n{ip_str}".strip() if host_str else ip_str
        table.add_row(
            svc.name[:35],
            svc.type[:25],
            host_display or "N/A",
            str(svc.port) if svc.port else "N/A",
            svc.source,
        )

    console.print(table)


def print_speedtest(result: SpeedtestResult) -> None:
    console.print(Panel.fit(
        f"[bold]Speedtest: {result.host}:{result.port}[/bold]",
        border_style="blue",
    ))

    if result.latency:
        lat = result.latency
        status = "[green]OK[/green]" if lat.packet_loss_pct < 5 else "[yellow]WARN[/yellow]"
        console.print(f"\n[bold]Latency[/bold]  {status}")
        console.print(f"  Min:       {lat.min_ms:.2f} ms")
        console.print(f"  Avg:       {lat.avg_ms:.2f} ms")
        console.print(f"  Max:       {lat.max_ms:.2f} ms")
        console.print(f"  Jitter:    {lat.jitter_ms:.2f} ms")
        console.print(f"  Loss:      {lat.packet_loss_pct:.1f}%")

    if result.tcp:
        tcp = result.tcp
        console.print(f"\n[bold]TCP Throughput[/bold]")
        console.print(f"  Speed:     [green]{tcp.mbps:.2f} Mbit/s[/green]")
        console.print(f"  Sent:      {tcp.bytes_transferred / 1_048_576:.2f} MiB in {tcp.duration_s:.1f}s")

    if result.udp:
        udp = result.udp
        loss_color = "green" if (udp.packet_loss_pct or 0) < 1 else "yellow" if (udp.packet_loss_pct or 0) < 5 else "red"
        console.print(f"\n[bold]UDP Throughput[/bold]")
        console.print(f"  Speed:     [green]{udp.mbps:.2f} Mbit/s[/green]")
        console.print(f"  Loss:      [{loss_color}]{udp.packet_loss_pct:.1f}%[/{loss_color}]")
        console.print(f"  Packets:   {udp.packets_received}/{udp.packets_sent} received")

    if result.mtu_detected:
        console.print(f"\n[bold]Path MTU[/bold]   {result.mtu_detected} bytes")


def print_diagnostic(report: DiagnosticReport) -> None:
    _status_color = {"ok": "green", "warning": "yellow", "error": "red", "skipped": "dim"}
    _status_icon = {"ok": "✓", "warning": "!", "error": "✗", "skipped": "-"}

    console.print(Panel.fit(
        f"[bold]Diagnostic Report: {report.target}[/bold]",
        border_style="blue",
    ))

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Icon", width=3)
    table.add_column("Check", style="bold", min_width=25)
    table.add_column("Status", min_width=10)
    table.add_column("Message")

    for check in report.checks:
        color = _status_color.get(check.status, "white")
        icon = _status_icon.get(check.status, "?")
        table.add_row(
            f"[{color}]{icon}[/{color}]",
            check.name,
            f"[{color}]{check.status.upper()}[/{color}]",
            check.message,
        )

    console.print(table)

    ok_c = "green" if report.summary_ok > 0 else "dim"
    warn_c = "yellow" if report.summary_warning > 0 else "dim"
    err_c = "red" if report.summary_error > 0 else "dim"
    console.print(
        f"\n[{ok_c}]✓ {report.summary_ok} OK[/{ok_c}]  "
        f"[{warn_c}]! {report.summary_warning} warnings[/{warn_c}]  "
        f"[{err_c}]✗ {report.summary_error} errors[/{err_c}]"
    )


_CHANGE_COLOR = {
    "new_device": "green",
    "device_gone": "red",
    "port_opened": "yellow",
    "port_closed": "dim",
    "hostname_changed": "yellow",
    "os_guess_changed": "yellow",
    "ip_changed": "yellow",
    "mac_changed": "red",
    "vendor_changed": "dim",
    "service_added": "green",
    "service_removed": "dim",
    "firmware_changed": "yellow",
}


def print_changes(changes: list[dict]) -> None:
    """changes: list of dicts with keys device_ip, device_hostname,
    change_type, field, old_value, new_value, detected_at (already
    resolved/joined by the caller, since ChangeEvent rows only carry a
    device_id FK)."""
    if not changes:
        console.print("[green]No changes detected.[/green]")
        return

    table = Table(
        title=f"NetScanX Change Report ({len(changes)} changes)", box=box.ROUNDED
    )
    table.add_column("Device", style="cyan", min_width=15)
    table.add_column("Change", min_width=16)
    table.add_column("Field", style="dim", max_width=15)
    table.add_column("Old → New")
    table.add_column("Detected", style="dim")

    for c in changes:
        color = _CHANGE_COLOR.get(c["change_type"], "white")
        device = c.get("device_hostname") or c.get("device_ip") or f"device #{c.get('device_id')}"
        old_new = ""
        if c.get("old_value") or c.get("new_value"):
            old_new = f"{c.get('old_value') or 'N/A'} → {c.get('new_value') or 'N/A'}"
        table.add_row(
            device,
            f"[{color}]{c['change_type']}[/{color}]",
            c.get("field") or "N/A",
            old_new or "N/A",
            str(c.get("detected_at") or ""),
        )

    console.print(table)


def print_health(report: HealthReport) -> None:
    _status_color = {"ok": "green", "warning": "yellow", "error": "red", "skipped": "dim"}
    _status_icon = {"ok": "✓", "warning": "!", "error": "✗", "skipped": "-"}

    score_color = "green" if report.score >= 80 else "yellow" if report.score >= 50 else "red"
    console.print(Panel.fit(
        f"[bold]Health Report: {report.target}[/bold]\n"
        f"Health Score: [{score_color}]{report.score}/100[/{score_color}]",
        border_style="blue",
    ))

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Icon", width=3)
    table.add_column("Check", style="bold", min_width=20)
    table.add_column("Status", min_width=10)
    table.add_column("Message")

    for check in report.checks:
        color = _status_color.get(check.status, "white")
        icon = _status_icon.get(check.status, "?")
        table.add_row(
            f"[{color}]{icon}[/{color}]",
            check.name,
            f"[{color}]{check.status.upper()}[/{color}]",
            check.message,
        )

    console.print(table)

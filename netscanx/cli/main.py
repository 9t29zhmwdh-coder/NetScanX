import click
from rich.console import Console

console = Console()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option("1.1.0", prog_name="netscanx")
def cli() -> None:
    """NetScanX — cross-platform network discovery and diagnostic toolkit.

    \b
    Commands:
      discover   Discover hosts via ARP / ICMP / port scan
      services   Discover network services (mDNS, SSDP, NetBIOS, SNMP)
      speedtest  Measure TCP/UDP throughput, latency and jitter
      diagnose   Auto-diagnose DNS, routing, DHCP, packet loss
      dashboard  Launch optional web dashboard
    """


from netscanx.cli.discover import discover
from netscanx.cli.diagnose import diagnose
from netscanx.cli.services import services
from netscanx.cli.speedtest import speedtest
from netscanx.cli.dashboard import dashboard

cli.add_command(discover)
cli.add_command(services)
cli.add_command(speedtest)
cli.add_command(diagnose)
cli.add_command(dashboard)

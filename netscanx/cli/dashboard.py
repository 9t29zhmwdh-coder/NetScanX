"""netscanx dashboard — optional web dashboard."""
from __future__ import annotations

import asyncio

import click
from rich.console import Console

console = Console(stderr=True)


@click.command()
@click.option("--host", default="0.0.0.0", metavar="HOST",
              help="Bind host [default: 0.0.0.0]")
@click.option("--port", default=8080, type=int, metavar="PORT",
              help="Bind port [default: 8080]")
@click.option("--open-browser/--no-open-browser", default=True,
              help="Open browser automatically")
def dashboard(host: str, port: int, open_browser: bool) -> None:
    """Launch the optional web dashboard for scan results.

    \b
    Example:
      netscanx dashboard
      netscanx dashboard --port 9090 --no-open-browser
    """
    asyncio.run(_run(host=host, port=port, open_browser=open_browser))


async def _run(host: str, port: int, open_browser: bool) -> None:
    import uvicorn
    from netscanx.dashboard.server import app

    url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}"
    console.print(f"[bold green]NetScanX Dashboard[/bold green]  {url}")

    if open_browser:
        import webbrowser
        await asyncio.sleep(0.5)
        webbrowser.open(url)

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

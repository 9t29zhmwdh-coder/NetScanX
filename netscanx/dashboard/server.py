"""FastAPI dashboard server for NetScanX."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from netscanx.models import DiscoverResult, DiagnosticReport, ServicesResult
from netscanx.scanner.layer2 import get_arp_cache
from netscanx.diagnostics.checks import DiagnosticsRunner

app = FastAPI(title="NetScanX Dashboard", version="1.0.0")

_STATIC = Path(__file__).parent / "static"


class BroadcastRegistry:
    def __init__(self):
        self._clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, data: dict) -> None:
        dead = set()
        for ws in self._clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self._clients -= dead


_registry = BroadcastRegistry()
_scan_cache: dict[str, Any] = {}


@app.get("/", response_class=HTMLResponse)
async def root():
    index = _STATIC / "index.html"
    return HTMLResponse(content=index.read_text())


@app.get("/api/hosts")
async def api_hosts():
    return _scan_cache.get("hosts", [])


@app.get("/api/services")
async def api_services():
    return _scan_cache.get("services", [])


@app.get("/api/diagnostics")
async def api_diagnostics():
    return _scan_cache.get("diagnostics", {})


@app.get("/api/scan")
async def api_trigger_scan():
    asyncio.create_task(_background_scan())
    return {"status": "scan_started"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await _registry.connect(ws)
    try:
        await ws.send_json({"type": "connected", "ts": _ts()})
        if _scan_cache:
            await ws.send_json({"type": "cache", "data": _scan_cache, "ts": _ts()})
        while True:
            await asyncio.sleep(30)
            await ws.send_json({"type": "ping", "ts": _ts()})
    except WebSocketDisconnect:
        _registry.disconnect(ws)
    except Exception:
        _registry.disconnect(ws)


@app.on_event("startup")
async def startup():
    asyncio.create_task(_background_scan())


async def _background_scan():
    await _registry.broadcast({"type": "scan_start", "ts": _ts()})

    try:
        arp_hosts = await get_arp_cache()
        hosts_data = [json.loads(h.model_dump_json()) for h in arp_hosts]
        _scan_cache["hosts"] = hosts_data
        await _registry.broadcast({"type": "hosts", "data": hosts_data, "ts": _ts()})
    except Exception:
        pass

    try:
        runner = DiagnosticsRunner()
        report = await runner.run_all()
        diag_data = json.loads(report.model_dump_json())
        _scan_cache["diagnostics"] = diag_data
        await _registry.broadcast({"type": "diagnostics", "data": diag_data, "ts": _ts()})
    except Exception:
        pass

    await _registry.broadcast({"type": "scan_done", "ts": _ts()})


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


app.mount("/", StaticFiles(directory=str(_STATIC), html=True), name="static")

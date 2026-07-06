"""FastAPI dashboard server for NetScanX."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from netscanx.cli.discover import _auto_detect_network, run_discover_scan
from netscanx.cli.services import run_services_scan
from netscanx.diagnostics.checks import DiagnosticsRunner
from netscanx.scanner.layer3 import ping_stats

app = FastAPI(title="NetScanX Dashboard", version="1.1.0")

_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,62}\.?)+$")


class SpeedtestRequest(BaseModel):
    host: str
    count: int = 15

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        v = v.strip()
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            pass
        if len(v) <= 253 and _HOSTNAME_RE.match(v):
            return v
        raise ValueError("invalid host, must be an IP address or hostname")

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        return max(1, min(v, 50))

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


@app.get("/api/speedtest")
async def api_speedtest_last():
    return _scan_cache.get("speedtest", {})


@app.post("/api/speedtest")
async def api_speedtest_run(req: SpeedtestRequest):
    try:
        stats = await ping_stats(req.host, count=req.count, interval=0.1)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"speedtest failed: {e}")

    data = json.loads(stats.model_dump_json())
    _scan_cache["speedtest"] = data
    await _registry.broadcast({"type": "speedtest", "data": data, "ts": _ts()})
    return data


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
    target = _auto_detect_network()

    try:
        discover_result = await run_discover_scan(
            target=target,
            do_arp=True,
            do_ping=True,
            do_vendor=True,
            do_hostname=True,
            timeout=1.5,
            include_cache=True,
        )
        hosts_data = json.loads(discover_result.model_dump_json())["hosts"]
        _scan_cache["hosts"] = hosts_data
        await _registry.broadcast({"type": "hosts", "data": hosts_data, "ts": _ts()})
    except Exception:
        pass

    try:
        services_result = await run_services_scan(
            target=target,
            do_mdns=True,
            do_ssdp=True,
            do_netbios=False,
            do_snmp=False,
            mdns_timeout=4.0,
            ssdp_timeout=3.0,
        )
        services_data = json.loads(services_result.model_dump_json())["services"]
        _scan_cache["services"] = services_data
        await _registry.broadcast({"type": "services", "data": services_data, "ts": _ts()})
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

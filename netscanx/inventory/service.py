from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from netscanx.enrichment.passive import enrich_host_passive
from netscanx.inventory.diff import ChangeRecord, SnapshotFields, diff_devices
from netscanx.inventory.identity import is_mac_randomized
from netscanx.models import DiscoverResult, Host, ServiceInfo, ServicesResult
from netscanx.storage.db import get_engine, get_session, init_db
from netscanx.storage.repository import InventoryRepository
from netscanx.storage.schema import ChangeEvent, Device, DeviceSnapshot, ScanRun

_IDENTITY_GRACE_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot_to_fields(snap: DeviceSnapshot) -> SnapshotFields:
    return SnapshotFields(
        ip=snap.ip,
        mac=snap.mac,
        hostname=snap.hostname,
        vendor=snap.vendor,
        os_guess=snap.os_guess,
        device_type=snap.device_type,
        open_ports=frozenset(tuple(p) for p in json.loads(snap.open_ports_json)),
        services=frozenset(tuple(s) for s in json.loads(snap.services_json)),
        snmp_sysdescr=snap.snmp_sysdescr,
    )


class InventoryService:
    """Orchestrates existing scanners + persistence + drift detection.
    Does not modify scanner internals -- calls run_discover_scan() /
    run_services_scan() as-is (imported lazily to avoid a circular import,
    since cli/discover.py's dashboard-facing helper is also imported by
    dashboard/server.py)."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path

    async def _get_ready_engine(self):
        engine = get_engine(self._db_path)
        await init_db(engine)
        return engine

    async def run_and_persist(
        self,
        target: str,
        discover_kwargs: dict | None = None,
        services_kwargs: dict | None = None,
        do_services: bool = True,
    ) -> tuple[ScanRun, list[ChangeRecord]]:
        """Convenience wrapper: runs a fresh discover (+ optionally
        services) scan, then persists + diffs. Used by the CLI."""
        from netscanx.cli.discover import run_discover_scan
        from netscanx.cli.services import run_services_scan

        discover_result = await run_discover_scan(target=target, **(discover_kwargs or {}))
        services_result: ServicesResult | None = None
        if do_services:
            services_result = await run_services_scan(target=target, **(services_kwargs or {}))

        return await self.persist_results(discover_result, services_result)

    async def persist_results(
        self,
        discover_result: DiscoverResult,
        services_result: ServicesResult | None = None,
    ) -> tuple[ScanRun, list[ChangeRecord]]:
        """Persists already-scanned results (avoids a duplicate scan when
        the caller -- e.g. the dashboard's background scan -- already has
        them) as a new ScanRun + per-device snapshots, resolves device
        identity, diffs against the previous state, and persists the
        resulting ChangeEvents."""
        services_by_ip = _group_services_by_ip(services_result.services if services_result else [])

        engine = await self._get_ready_engine()
        async with get_session(engine) as session:
            repo = InventoryRepository(session)
            now = _now()
            scan_types = ["discover"] + (["services"] if services_result else [])
            run = await repo.create_scan_run(discover_result.target, scan_types, now)

            current: dict[int, SnapshotFields] = {}

            for host in discover_result.hosts:
                host_services = services_by_ip.get(host.ip, [])
                enriched = await enrich_host_passive(host, host_services)
                device = await self._resolve_device(repo, enriched, now)

                port_tuples = sorted({(p.port, p.protocol.value) for p in enriched.open_ports})
                service_tuples = sorted({(s.name, s.type) for s in host_services})
                snmp_sysdescr = _extract_snmp_sysdescr(host_services)

                await repo.add_snapshot(
                    device=device,
                    scan_run=run,
                    ip=enriched.ip,
                    mac=enriched.mac,
                    hostname=enriched.hostname,
                    vendor=enriched.vendor,
                    ttl=enriched.ttl,
                    os_guess=enriched.os_guess,
                    device_type=enriched.device_type,
                    open_ports_json=json.dumps(port_tuples),
                    services_json=json.dumps(service_tuples),
                    snmp_sysdescr=snmp_sysdescr,
                    discovered_via=",".join(enriched.discovered_via),
                    enriched_via="network-inferred",
                    health_score=None,
                    created_at=now,
                )

                current[device.id] = SnapshotFields(
                    ip=enriched.ip,
                    mac=enriched.mac,
                    hostname=enriched.hostname,
                    vendor=enriched.vendor,
                    os_guess=enriched.os_guess,
                    device_type=enriched.device_type,
                    open_ports=frozenset(port_tuples),
                    services=frozenset(service_tuples),
                    snmp_sysdescr=snmp_sysdescr,
                )

            await repo.finish_scan_run(run, _now(), len(discover_result.hosts))

            previous_snapshots = await repo.get_latest_snapshot_per_device(exclude_run_id=run.id)
            previous: dict[int, SnapshotFields] = {
                snap.device_id: _snapshot_to_fields(snap) for snap in previous_snapshots
            }

            change_records = diff_devices(previous, current)
            for device_id, change in change_records:
                await repo.add_change(
                    scan_run=run,
                    device_id=device_id,
                    change_type=change.change_type,
                    field=change.field,
                    old_value=change.old_value,
                    new_value=change.new_value,
                    detected_at=now,
                )

            await session.commit()
            return run, [change for _, change in change_records]

    async def _resolve_device(
        self, repo: InventoryRepository, host: Host, now: datetime
    ) -> Device:
        """Layered device-identity resolution: primary key is a
        non-randomized MAC; fallback is IP+hostname within a grace window.
        A MAC change on a previously-known IP is treated as a change EVENT
        on the existing device rather than a new device (see diff.py's
        mac_changed handling), so this lookup order matters: IP-based
        matching must run for hosts with a randomized/absent MAC, but a
        genuinely new MAC on a known IP still resolves to that IP's
        existing device here -- the mac_changed detection happens later,
        in diff_snapshots(), not in identity resolution."""
        randomized = bool(host.mac) and is_mac_randomized(host.mac)

        if host.mac and not randomized:
            device = await repo.find_device_by_mac(host.mac)
            if device is not None:
                return device

        device = await repo.find_device_by_ip_recent(host.ip, host.hostname, _IDENTITY_GRACE_DAYS)
        if device is not None:
            return device

        return await repo.create_device(
            mac=host.mac if not randomized else None,
            is_mac_randomized=randomized,
            now=now,
        )

    async def pin_baseline(self, run_id: int | None = None) -> ScanRun:
        engine = await self._get_ready_engine()
        async with get_session(engine) as session:
            repo = InventoryRepository(session)
            target_run_id = run_id
            if target_run_id is None:
                latest = await repo.get_latest_scan_run()
                if latest is None:
                    raise ValueError("no scan runs exist yet -- run a scan first")
                target_run_id = latest.id
            await repo.mark_baseline(target_run_id)
            await session.commit()
            return await repo.get_scan_run(target_run_id)

    async def get_changes(self, since_baseline: bool = False) -> list[ChangeEvent]:
        engine = await self._get_ready_engine()
        async with get_session(engine) as session:
            repo = InventoryRepository(session)
            if since_baseline:
                return await repo.get_changes(since_baseline=True)
            latest = await repo.get_latest_scan_run()
            if latest is None:
                return []
            return await repo.get_changes(since_run_id=latest.id)

    async def list_assets(self) -> list[Device]:
        engine = await self._get_ready_engine()
        async with get_session(engine) as session:
            repo = InventoryRepository(session)
            return await repo.list_devices()


def _group_services_by_ip(services: list[ServiceInfo]) -> dict[str, list[ServiceInfo]]:
    grouped: dict[str, list[ServiceInfo]] = {}
    for service in services:
        key = service.ip or service.host
        grouped.setdefault(key, []).append(service)
    return grouped


def _extract_snmp_sysdescr(services: list[ServiceInfo]) -> str | None:
    for service in services:
        if service.source == "snmp":
            sysdescr = service.properties.get("sysDescr")
            if sysdescr:
                return sysdescr
    return None

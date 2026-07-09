from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from netscanx.storage.schema import ChangeEvent, Device, DeviceSnapshot, ScanRun


class InventoryRepository:
    """Plain CRUD layer over the SQLAlchemy schema. Deliberately kept free
    of any dependency on the Pydantic domain models (Host, ServiceInfo) --
    that translation happens one layer up, in inventory/service.py."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # -- devices ----------------------------------------------------------

    async def find_device_by_mac(self, mac: str) -> Device | None:
        result = await self._session.execute(select(Device).where(Device.primary_mac == mac))
        return result.scalar_one_or_none()

    async def find_device_by_ip_recent(
        self, ip: str, hostname: str | None, grace_days: int
    ) -> Device | None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=grace_days)
        result = await self._session.execute(
            select(Device).where(Device.last_ip == ip, Device.last_seen >= cutoff)
        )
        for candidate in result.scalars().all():
            if hostname is None or candidate.last_hostname is None or candidate.last_hostname == hostname:
                return candidate
        return None

    async def create_device(self, mac: str | None, is_mac_randomized: bool, now: datetime) -> Device:
        device = Device(
            primary_mac=mac, is_mac_randomized=is_mac_randomized, first_seen=now, last_seen=now
        )
        self._session.add(device)
        await self._session.flush()
        return device

    async def list_devices(self) -> list[Device]:
        result = await self._session.execute(select(Device).order_by(Device.last_seen.desc()))
        return list(result.scalars().all())

    # -- scan runs ----------------------------------------------------------

    async def create_scan_run(self, target: str, scan_types: list[str], started_at: datetime) -> ScanRun:
        run = ScanRun(
            target=target,
            started_at=started_at,
            finished_at=started_at,
            scan_types=",".join(scan_types),
            host_count=0,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def finish_scan_run(self, run: ScanRun, finished_at: datetime, host_count: int) -> None:
        run.finished_at = finished_at
        run.host_count = host_count
        await self._session.flush()

    async def get_scan_run(self, run_id: int) -> ScanRun | None:
        result = await self._session.execute(select(ScanRun).where(ScanRun.id == run_id))
        return result.scalar_one_or_none()

    async def get_latest_scan_run(self, exclude_run_id: int | None = None) -> ScanRun | None:
        stmt = select(ScanRun).order_by(ScanRun.id.desc()).limit(1)
        if exclude_run_id is not None:
            stmt = select(ScanRun).where(ScanRun.id != exclude_run_id).order_by(ScanRun.id.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_baseline(self, run_id: int) -> None:
        await self._session.execute(update(ScanRun).values(is_baseline=False))
        run = await self.get_scan_run(run_id)
        if run is None:
            raise ValueError(f"scan run {run_id} not found")
        run.is_baseline = True
        await self._session.flush()

    async def get_baseline_scan_run(self) -> ScanRun | None:
        result = await self._session.execute(select(ScanRun).where(ScanRun.is_baseline.is_(True)))
        return result.scalar_one_or_none()

    # -- snapshots ----------------------------------------------------------

    async def add_snapshot(
        self,
        *,
        device: Device,
        scan_run: ScanRun,
        ip: str | None,
        mac: str | None,
        hostname: str | None,
        vendor: str | None,
        ttl: int | None,
        os_guess: str | None,
        device_type: str | None,
        open_ports_json: str,
        services_json: str,
        snmp_sysdescr: str | None,
        discovered_via: str,
        enriched_via: str,
        health_score: int | None,
        created_at: datetime,
    ) -> DeviceSnapshot:
        snapshot = DeviceSnapshot(
            scan_run_id=scan_run.id,
            device_id=device.id,
            ip=ip,
            mac=mac,
            hostname=hostname,
            vendor=vendor,
            ttl=ttl,
            os_guess=os_guess,
            device_type=device_type,
            open_ports_json=open_ports_json,
            services_json=services_json,
            snmp_sysdescr=snmp_sysdescr,
            discovered_via=discovered_via,
            enriched_via=enriched_via,
            health_score=health_score,
            created_at=created_at,
        )
        self._session.add(snapshot)
        await self._session.flush()

        # Keep the Device's denormalized "last known" fields in sync so
        # dashboard reads of Device rows don't need a join.
        device.last_ip = ip
        device.last_hostname = hostname
        device.last_vendor = vendor
        device.last_os_guess = os_guess
        device.last_device_type = device_type
        device.last_seen = created_at

        return snapshot

    async def get_latest_snapshot_per_device(
        self, exclude_run_id: int | None = None
    ) -> list[DeviceSnapshot]:
        """Most recent snapshot for each device, optionally excluding a
        given scan_run_id (used to fetch the 'previous' state while diffing
        the run currently being persisted)."""
        base_stmt = select(DeviceSnapshot)
        if exclude_run_id is not None:
            base_stmt = base_stmt.where(DeviceSnapshot.scan_run_id != exclude_run_id)
        subq = base_stmt.subquery()

        max_id_subq = (
            select(subq.c.device_id, func.max(subq.c.id).label("max_id"))
            .group_by(subq.c.device_id)
            .subquery()
        )

        result = await self._session.execute(
            select(DeviceSnapshot).join(max_id_subq, DeviceSnapshot.id == max_id_subq.c.max_id)
        )
        return list(result.scalars().all())

    async def get_baseline_snapshot_per_device(self) -> list[DeviceSnapshot]:
        baseline_run = await self.get_baseline_scan_run()
        if baseline_run is None:
            return []
        result = await self._session.execute(
            select(DeviceSnapshot).where(DeviceSnapshot.scan_run_id == baseline_run.id)
        )
        return list(result.scalars().all())

    # -- changes ----------------------------------------------------------

    async def add_change(
        self,
        *,
        scan_run: ScanRun,
        device_id: int,
        change_type: str,
        field: str | None,
        old_value: str | None,
        new_value: str | None,
        detected_at: datetime,
    ) -> ChangeEvent:
        change = ChangeEvent(
            scan_run_id=scan_run.id,
            device_id=device_id,
            change_type=change_type,
            field=field,
            old_value=old_value,
            new_value=new_value,
            detected_at=detected_at,
        )
        self._session.add(change)
        await self._session.flush()
        return change

    async def get_changes(
        self, since_run_id: int | None = None, since_baseline: bool = False
    ) -> list[ChangeEvent]:
        stmt = select(ChangeEvent).order_by(ChangeEvent.detected_at.desc())

        if since_baseline:
            baseline_run = await self.get_baseline_scan_run()
            if baseline_run is None:
                return []
            stmt = stmt.where(ChangeEvent.scan_run_id >= baseline_run.id)
        elif since_run_id is not None:
            stmt = stmt.where(ChangeEvent.scan_run_id == since_run_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

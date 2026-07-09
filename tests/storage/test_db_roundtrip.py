from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from netscanx.storage.db import get_engine, get_session, init_db
from netscanx.storage.schema import ChangeEvent, Device, DeviceSnapshot, ScanRun


def _now():
    return datetime.now(timezone.utc)


@pytest.fixture
async def engine(tmp_path):
    db_path = tmp_path / "test.db"
    eng = get_engine(db_path)
    await init_db(eng)
    yield eng
    await eng.dispose()


async def test_create_and_read_device(engine):
    now = _now()
    async with get_session(engine) as session:
        device = Device(
            primary_mac="AA:BB:CC:DD:EE:FF",
            is_mac_randomized=False,
            first_seen=now,
            last_seen=now,
            last_ip="10.0.0.5",
        )
        session.add(device)
        await session.commit()
        await session.refresh(device)
        device_id = device.id

    async with get_session(engine) as session:
        result = await session.execute(select(Device).where(Device.id == device_id))
        fetched = result.scalar_one()
        assert fetched.primary_mac == "AA:BB:CC:DD:EE:FF"
        assert fetched.last_ip == "10.0.0.5"


async def test_scan_run_and_snapshot_roundtrip(engine):
    now = _now()
    async with get_session(engine) as session:
        device = Device(first_seen=now, last_seen=now, primary_mac="11:22:33:44:55:66")
        session.add(device)
        await session.flush()

        run = ScanRun(
            target="192.168.1.0/24",
            started_at=now,
            finished_at=now,
            scan_types="discover",
            host_count=1,
        )
        session.add(run)
        await session.flush()

        snapshot = DeviceSnapshot(
            scan_run_id=run.id,
            device_id=device.id,
            ip="192.168.1.10",
            mac="11:22:33:44:55:66",
            hostname="pc-123",
            open_ports_json="[]",
            services_json="[]",
            discovered_via="arp",
            created_at=now,
        )
        session.add(snapshot)
        await session.commit()
        run_id, device_id = run.id, device.id

    async with get_session(engine) as session:
        result = await session.execute(
            select(DeviceSnapshot).where(DeviceSnapshot.scan_run_id == run_id)
        )
        fetched = result.scalar_one()
        assert fetched.device_id == device_id
        assert fetched.hostname == "pc-123"


async def test_change_event_cascade_delete_on_device(engine):
    now = _now()
    async with get_session(engine) as session:
        device = Device(first_seen=now, last_seen=now)
        session.add(device)
        await session.flush()
        run = ScanRun(
            target="x", started_at=now, finished_at=now, scan_types="discover", host_count=1
        )
        session.add(run)
        await session.flush()
        change = ChangeEvent(
            scan_run_id=run.id,
            device_id=device.id,
            change_type="new_device",
            detected_at=now,
        )
        session.add(change)
        await session.commit()
        device_id = device.id

        await session.delete(device)
        await session.commit()

    async with get_session(engine) as session:
        result = await session.execute(
            select(ChangeEvent).where(ChangeEvent.device_id == device_id)
        )
        assert result.scalar_one_or_none() is None

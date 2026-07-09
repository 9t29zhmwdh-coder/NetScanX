from __future__ import annotations

from netscanx.inventory.service import InventoryService
from netscanx.models import DiscoverResult, Host, Port


async def test_first_scan_produces_new_device_events(tmp_path):
    service = InventoryService(db_path=tmp_path / "e2e.db")
    result = DiscoverResult(
        target="10.0.0.0/24",
        hosts=[
            Host(
                ip="10.0.0.5",
                mac="AA:BB:CC:DD:EE:FF",
                hostname="pc1",
                open_ports=[Port(port=22)],
                discovered_via=["arp"],
                ttl=64,
            )
        ],
    )

    run, changes = await service.persist_results(result)

    assert run.host_count == 1
    assert [c.change_type for c in changes] == ["new_device"]


async def test_second_scan_detects_port_opened_and_new_device(tmp_path):
    db_path = tmp_path / "e2e.db"
    service = InventoryService(db_path=db_path)

    first = DiscoverResult(
        target="10.0.0.0/24",
        hosts=[
            Host(
                ip="10.0.0.5",
                mac="AA:BB:CC:DD:EE:FF",
                hostname="pc1",
                open_ports=[Port(port=22)],
                discovered_via=["arp"],
            )
        ],
    )
    await service.persist_results(first)

    second = DiscoverResult(
        target="10.0.0.0/24",
        hosts=[
            Host(
                ip="10.0.0.5",
                mac="AA:BB:CC:DD:EE:FF",
                hostname="pc1",
                open_ports=[Port(port=22), Port(port=3389)],
                discovered_via=["arp"],
            ),
            Host(
                ip="10.0.0.9",
                mac="11:22:33:44:55:66",
                hostname="printer1",
                discovered_via=["arp"],
            ),
        ],
    )
    run, changes = await service.persist_results(second)

    change_types = {c.change_type for c in changes}
    assert "port_opened" in change_types
    assert "new_device" in change_types
    port_opened = next(c for c in changes if c.change_type == "port_opened")
    assert port_opened.new_value == "3389/tcp"


async def test_device_gone_when_missing_from_next_scan(tmp_path):
    db_path = tmp_path / "e2e.db"
    service = InventoryService(db_path=db_path)

    first = DiscoverResult(
        target="10.0.0.0/24",
        hosts=[Host(ip="10.0.0.5", mac="AA:BB:CC:DD:EE:FF", discovered_via=["arp"])],
    )
    await service.persist_results(first)

    second = DiscoverResult(target="10.0.0.0/24", hosts=[])
    run, changes = await service.persist_results(second)

    assert [c.change_type for c in changes] == ["device_gone"]


async def test_unchanged_rescan_produces_no_changes(tmp_path):
    db_path = tmp_path / "e2e.db"
    service = InventoryService(db_path=db_path)

    scan = DiscoverResult(
        target="10.0.0.0/24",
        hosts=[
            Host(
                ip="10.0.0.5",
                mac="AA:BB:CC:DD:EE:FF",
                hostname="pc1",
                open_ports=[Port(port=22)],
                discovered_via=["arp"],
            )
        ],
    )
    await service.persist_results(scan)
    _, changes = await service.persist_results(scan.model_copy(deep=True))

    assert changes == []


async def test_baseline_pin_and_changes_since_baseline(tmp_path):
    db_path = tmp_path / "e2e.db"
    service = InventoryService(db_path=db_path)

    host = Host(ip="10.0.0.5", mac="AA:BB:CC:DD:EE:FF", discovered_via=["arp"])
    baseline_run, _ = await service.persist_results(
        DiscoverResult(target="10.0.0.0/24", hosts=[host])
    )
    await service.pin_baseline(baseline_run.id)

    changed_host = Host(
        ip="10.0.0.5", mac="AA:BB:CC:DD:EE:FF", open_ports=[Port(port=443)], discovered_via=["arp"]
    )
    await service.persist_results(DiscoverResult(target="10.0.0.0/24", hosts=[changed_host]))

    since_baseline = await service.get_changes(since_baseline=True)
    assert any(c.change_type == "port_opened" for c in since_baseline)


async def test_list_assets_returns_persisted_devices(tmp_path):
    db_path = tmp_path / "e2e.db"
    service = InventoryService(db_path=db_path)
    await service.persist_results(
        DiscoverResult(
            target="10.0.0.0/24",
            hosts=[Host(ip="10.0.0.5", mac="AA:BB:CC:DD:EE:FF", discovered_via=["arp"])],
        )
    )

    assets = await service.list_assets()

    assert len(assets) == 1
    assert assets[0].last_ip == "10.0.0.5"

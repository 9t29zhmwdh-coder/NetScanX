"""Reverse DNS hostname resolution for discovered hosts."""
from __future__ import annotations

import asyncio
import socket


async def resolve_hostname(ip: str, timeout: float = 1.5) -> str | None:
    try:
        name, _, _ = await asyncio.wait_for(
            asyncio.to_thread(socket.gethostbyaddr, ip), timeout=timeout
        )
        return name
    except Exception:
        return None


async def resolve_hostnames_batch(
    ips: list[str], concurrency: int = 32, timeout: float = 1.5
) -> dict[str, str | None]:
    sem = asyncio.Semaphore(concurrency)

    async def _one(ip: str) -> tuple[str, str | None]:
        async with sem:
            return ip, await resolve_hostname(ip, timeout=timeout)

    results = await asyncio.gather(*[_one(ip) for ip in ips])
    return dict(results)

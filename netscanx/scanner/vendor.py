from __future__ import annotations

import asyncio
import re

_cache: dict[str, str] = {}


def _normalise_mac(mac: str) -> str:
    digits = re.sub(r"[^0-9a-fA-F]", "", mac)
    return ":".join(digits[i : i + 2] for i in range(0, 12, 2)).upper()


async def lookup_vendor(mac: str) -> str | None:
    if not mac:
        return None
    norm = _normalise_mac(mac)
    if norm in _cache:
        return _cache[norm]

    try:
        import aiohttp

        oui = norm.replace(":", "")[:6]
        url = f"https://api.macvendors.com/{oui}"
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=2)
        ) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    vendor = (await resp.text()).strip()
                    _cache[norm] = vendor
                    return vendor
    except Exception:
        pass
    return None


async def lookup_vendors_batch(
    macs: list[str], rate_delay: float = 1.1
) -> dict[str, str | None]:
    results: dict[str, str | None] = {}
    for mac in macs:
        results[mac] = await lookup_vendor(mac)
        await asyncio.sleep(rate_delay)
    return results

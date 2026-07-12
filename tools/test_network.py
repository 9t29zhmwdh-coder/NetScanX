"""
NetScanX network probe simulator: cross-platform (Linux, Windows, macOS).

Simulates common network services by opening TCP listeners on configurable ports.
Useful for testing netscanx discover and netscanx services without a real network.

Usage:
    python tools/test_network.py
    python tools/test_network.py --ports 22,80,443,8080 --host 127.0.0.1
    python tools/test_network.py --duration 60

Requires: no extra dependencies (stdlib only)
"""
import argparse
import asyncio
import sys


BANNERS: dict[int, bytes] = {
    22: b"SSH-2.0-OpenSSH_9.0p1 NetScanX-Sim\r\n",
    21: b"220 NetScanX FTP Simulator ready\r\n",
    25: b"220 netscanx.local ESMTP NetScanX-Sim\r\n",
    80: b"HTTP/1.1 200 OK\r\nServer: NetScanX-Sim/1.0\r\nContent-Length: 0\r\n\r\n",
    443: b"HTTP/1.1 200 OK\r\nServer: NetScanX-Sim/1.0 (TLS)\r\nContent-Length: 0\r\n\r\n",
    8080: b"HTTP/1.1 200 OK\r\nServer: NetScanX-Sim/1.0 alt\r\nContent-Length: 0\r\n\r\n",
    3306: b"\x4a\x00\x00\x00\x0a5.7.99-NetScanX-Sim\x00",
    5432: b"R\x00\x00\x00\x08\x00\x00\x00\x00",  # PostgreSQL auth request
}


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    port: int,
) -> None:
    try:
        banner = BANNERS.get(port, f"NetScanX-Sim port {port}\r\n".encode())
        writer.write(banner)
        await writer.drain()
        await asyncio.wait_for(reader.read(256), timeout=2.0)
    except Exception:
        pass
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
        except Exception:
            pass


async def start_servers(host: str, ports: list[int]) -> list[asyncio.Server]:
    servers = []
    for port in ports:
        try:
            srv = await asyncio.start_server(
                lambda r, w, p=port: handle_client(r, w, p),
                host,
                port,
            )
            print(f"  Listening on {host}:{port}")
            servers.append(srv)
        except OSError as e:
            print(f"  Cannot bind {port}: {e}", file=sys.stderr)
    return servers


async def main(host: str, ports: list[int], duration: float) -> None:
    print(f"NetScanX probe simulator: {host}")
    print(f"Ports: {', '.join(str(p) for p in ports)}")
    print(f"Duration: {duration}s (Ctrl+C to stop early)\n")

    servers = await start_servers(host, ports)
    if not servers:
        print("No ports could be bound.", file=sys.stderr)
        return

    print(f"\nAll servers running. Test with:")
    print(f"  netscanx discover {host} --ping --ports {','.join(str(p) for p in ports)}")
    print()

    try:
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        pass

    for srv in servers:
        srv.close()
        await srv.wait_closed()
    print("Stopped.")


def parse_ports(spec: str) -> list[int]:
    ports = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            ports.extend(range(int(lo), int(hi) + 1))
        elif part:
            ports.append(int(part))
    return sorted(set(ports))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetScanX probe simulator")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host [default: 127.0.0.1]")
    parser.add_argument(
        "--ports", default="22,21,25,80,443,8080,3306,5432",
        help="Ports to simulate [default: 22,21,25,80,443,8080,3306,5432]"
    )
    parser.add_argument("--duration", type=float, default=300.0,
                        help="How long to run in seconds [default: 300]")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.host, parse_ports(args.ports), args.duration))
    except KeyboardInterrupt:
        print("\nInterrupted.")

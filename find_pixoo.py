#!/usr/bin/env python3
"""
Scan the local network for Divoom Pixoo64 devices.

Probes each host on the local /24 subnet at port 80 using the Pixoo
HTTP API (POST /post with Device/SetBrightness). A valid Pixoo64
responds with {"error_code": 0}.

Usage:
    python find_pixoo.py                 # auto-detect subnet
    python find_pixoo.py 192.168.2.0/24  # explicit CIDR
"""

import asyncio
import argparse
import ipaddress
import socket
import sys

import aiohttp


def get_local_subnet() -> ipaddress.IPv4Network:
    """Determine the local /24 subnet from the primary network interface."""
    # Connect to a public address (no traffic is actually sent) to find
    # which local interface would be used.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    return ipaddress.ip_network(f"{local_ip}/24", strict=False)


async def probe_host(ip: str, timeout: float = 1.5) -> bool:
    """Return True if the host responds like a Pixoo device."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{ip}:80/get", timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                return response.status == 200
    except Exception:
        return False


async def scan_subnet(network: ipaddress.IPv4Network) -> list[str]:
    """Probe all usable hosts in the subnet concurrently, return Pixoo IPs."""
    hosts = [str(ip) for ip in network.hosts()]
    print(f"Scanning {len(hosts)} hosts on {network} ...")

    # Limit concurrency to avoid flooding the network / local sockets
    semaphore = asyncio.Semaphore(128)

    async def bounded_probe(ip: str) -> str | None:
        async with semaphore:
            return ip if await probe_host(ip) else None

    results = await asyncio.gather(*(bounded_probe(h) for h in hosts))
    return sorted(r for r in results if r)


async def main():
    parser = argparse.ArgumentParser(
        description="Scan the local network for Divoom Pixoo64 devices"
    )
    parser.add_argument(
        "subnet",
        nargs="?",
        help="Subnet to scan in CIDR notation (default: auto-detect local /24)",
    )
    args = parser.parse_args()

    if args.subnet:
        try:
            network = ipaddress.ip_network(args.subnet, strict=False)
        except ValueError as e:
            print(f"Invalid subnet: {e}")
            sys.exit(1)
    else:
        try:
            network = get_local_subnet()
        except OSError:
            print("Could not determine local subnet. Pass one explicitly, e.g.:")
            print("  python find_pixoo.py 192.168.1.0/24")
            sys.exit(1)

    found = await scan_subnet(network)

    if found:
        print("\nFound Pixoo device(s):")
        for ip in found:
            print(f"  http://{ip}")
        print(f"\nSet pixoo_host = \"{found[0]}\" in your Config.")
    else:
        print("\nNo Pixoo devices found. Make sure the device is powered on")
        print("and connected to the same network, then try again.")


if __name__ == "__main__":
    asyncio.run(main())

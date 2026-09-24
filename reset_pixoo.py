#!/usr/bin/env python3
"""
Reset the Pixoo64 to its original state.

The album art service switches the display to the custom channel (index 3)
and pushes an HTTP "GIF" to it. This script stops that stream and switches
back to the default clock channel (index 0), which shows the time/weather
face selected in the Divoom app.

Usage:
    python reset_pixoo.py                    # uses pixoo_host from Config
    python reset_pixoo.py --ip 192.168.2.206
"""

import argparse
import asyncio

import aiohttp

from lms_pixoo_service import Config


async def reset_pixoo(host: str, port: int = 80) -> bool:
    """Restore the default clock channel and clear the HTTP gif stream."""
    base_url = f"http://{host}:{port}"
    steps = [
        # Stop any HTTP gif stream the service may have started
        {"Command": "Draw/ResetHttpGifId"},
        # Switch back to the clock channel (0 = time/weather faces)
        {"Command": "Channel/SetIndex", "SelectIndex": 0},
    ]
    try:
        async with aiohttp.ClientSession() as session:
            for payload in steps:
                async with session.post(
                    f"{base_url}/post",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status != 200:
                        print(f"Pixoo64 returned status {response.status} for {payload['Command']}")
                        return False
                    # Device responds with JSON but a text/html content-type
                    data = await response.json(content_type=None)
                    if data.get("error_code") != 0:
                        print(f"Pixoo64 rejected {payload['Command']}: {data}")
                        return False
        print(f"Pixoo64 at {host} reset to time/weather display.")
        return True
    except Exception as e:
        print(f"Cannot reach Pixoo64 at {base_url}: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="Reset the Pixoo64 to its default time/weather display"
    )
    parser.add_argument(
        "--ip",
        default=Config().pixoo_host,
        help="Pixoo64 IP address (default: pixoo_host from Config in lms_pixoo_service.py)",
    )
    args = parser.parse_args()

    ok = await reset_pixoo(args.ip)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

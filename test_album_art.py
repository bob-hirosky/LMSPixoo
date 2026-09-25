#!/usr/bin/env python3
"""
Test sending a sample album art image to Pixoo64
"""

import argparse
import asyncio
import logging

from lms_pixoo_service import Config
from patterns import create_album_art_image
from pixoo import PixooClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Album art display test")
    parser.add_argument("--ip", default=Config().pixoo_host,
                        help="Pixoo64 IP address (default: from Config)")
    args = parser.parse_args()

    print("=" * 60)
    print("Testing Album Art Display")
    print("=" * 60)

    client = PixooClient(args.ip)

    # Create test image
    logger.info("Creating test album art image...")
    test_img = create_album_art_image()

    # Send to Pixoo64
    logger.info("Sending to Pixoo64...")
    success = await client.send_image(test_img)

    if success:
        print("\n✓ Test image sent successfully!")
        print("Check your Pixoo64 - you should see a colorful radial gradient")
    else:
        print("\n✗ Failed to send test image")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

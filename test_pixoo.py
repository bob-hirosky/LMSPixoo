#!/usr/bin/env python3
"""
Test script to verify Pixoo64 connection and display test images
"""

import argparse
import asyncio
import logging

from lms_pixoo_service import Config
from patterns import create_gradient_image, create_text_image
from pixoo import PixooClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_pixoo_connection(pixoo_ip: str):
    """Test the Pixoo64 connection with various test images"""
    client = PixooClient(pixoo_ip)

    logger.info("Testing connection to Pixoo64 at %s...", pixoo_ip)

    # Test 1: Basic connection
    if not await client.test_connection():
        logger.error("Failed to connect to Pixoo64!")
        logger.error("Please check:")
        logger.error("  1. The IP address is correct")
        logger.error("  2. The Pixoo64 is powered on")
        logger.error("  3. Both devices are on the same network")
        return

    logger.info("✓ Connection successful!")

    # Test 2: Send simple colored test image
    logger.info("Test 2: Sending red test pattern...")
    await client.send_image(create_text_image("TEST", color=(255, 0, 0)))
    await asyncio.sleep(2)

    # Test 3: Send gradient image
    logger.info("Test 3: Sending gradient pattern...")
    await client.send_image(create_gradient_image())
    await asyncio.sleep(2)

    # Test 4: Send green success image
    logger.info("Test 4: Sending green success pattern...")
    await client.send_image(create_text_image("OK!", color=(0, 255, 0)))

    logger.info("✓ All tests completed successfully!")
    logger.info("Your Pixoo64 is ready to display album art.")


async def main():
    parser = argparse.ArgumentParser(description="Pixoo64 connection test")
    parser.add_argument("--ip", default=Config().pixoo_host,
                        help="Pixoo64 IP address (default: from Config)")
    args = parser.parse_args()

    print("=" * 60)
    print("Pixoo64 Connection Test")
    print("=" * 60)
    print(f"\nPixoo64 IP: {args.ip}\n")

    await test_pixoo_connection(args.ip)


if __name__ == "__main__":
    asyncio.run(main())

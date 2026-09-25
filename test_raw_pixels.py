#!/usr/bin/env python3
"""
Test sending image using raw pixel data instead of GIF
"""

import argparse
import asyncio
import base64
import logging

import aiohttp
from PIL import Image

from lms_pixoo_service import Config
from patterns import create_quadrants_image
from pixoo import post_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_image_raw_pixels(host: str, image: Image.Image) -> bool:
    """Send image using raw pixel data format"""
    image = image.convert('RGB')

    # Method 1: PicData as an array of packed RGB integers
    pixels = []
    for y in range(64):
        for x in range(64):
            r, g, b = image.getpixel((x, y))
            pixels.append((r << 16) | (g << 8) | b)

    async with aiohttp.ClientSession() as session:
        # Switch to custom channel first
        await post_command(session, host, "Channel/SetIndex", SelectIndex=3)

        result = await post_command(
            session, host, "Draw/SendHttpItemList",
            ItemList=[{
                "type": 0, "x": 0, "y": 0, "dir": 0,
                "width": 64, "height": 64, "PicData": pixels,
            }])
        logger.info("Method 1 (pixel array) - %s", "OK" if result is not None else "FAILED")
        return result is not None


async def send_image_base64_rgb(host: str, image: Image.Image) -> bool:
    """Send image using base64-encoded RGB bytes"""
    rgb_bytes = image.convert('RGB').tobytes()

    async with aiohttp.ClientSession() as session:
        result = await post_command(
            session, host, "Draw/CommandList",
            CommandList=[{
                "Command": "Draw/SendRemote",
                "PicWidth": 64,
                "PicData": base64.b64encode(rgb_bytes).decode('utf-8'),
            }])
        logger.info("Method 2 (base64 RGB) - %s", "OK" if result is not None else "FAILED")
        return result is not None


async def main():
    parser = argparse.ArgumentParser(description="Raw pixel format test")
    parser.add_argument("--ip", default=Config().pixoo_host,
                        help="Pixoo64 IP address (default: from Config)")
    args = parser.parse_args()

    print("=" * 70)
    print("Testing RAW PIXEL methods")
    print("=" * 70)

    test_img = create_quadrants_image()
    test_img.save("test_pattern.png")
    logger.info("Created test pattern: 4 colored squares")

    print("\nTrying Method 1: Pixel array...")
    await send_image_raw_pixels(args.ip, test_img)
    await asyncio.sleep(3)

    print("\nTrying Method 2: Base64 RGB...")
    await send_image_base64_rgb(args.ip, test_img)

    print("\n" + "=" * 70)
    print("Check your Pixoo64 display!")
    print("You should see 4 colored squares (red, green, blue, yellow)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

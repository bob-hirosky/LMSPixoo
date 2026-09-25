#!/usr/bin/env python3
"""
Diagnostic script to test different Pixoo64 API methods
"""

import argparse
import asyncio
import base64
import logging
from io import BytesIO

import aiohttp

from lms_pixoo_service import Config
from patterns import create_diagnostic_image
from pixoo import PIXOO_SIZE, post_command, to_pixel_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_method_1(host: str, image):
    """Method 1: Device/SetStaticImage"""
    logger.info("\n=== Testing Method 1: Device/SetStaticImage ===")

    async with aiohttp.ClientSession() as session:
        return await post_command(
            session, host, "Device/SetStaticImage",
            StaticImageData={
                "PicNum": 1, "PicWidth": PIXOO_SIZE, "PicOffset": 0,
                "PicID": 0, "PicSpeed": 1000,
                "PicData": base64.b64encode(to_pixel_data(image)).decode('utf-8'),
            }) is not None


async def test_method_2(host: str, image):
    """Method 2: Draw/SendHttpGif with an actual GIF"""
    logger.info("\n=== Testing Method 2: Draw/SendHttpGif (GIF file) ===")

    gif_buffer = BytesIO()
    image.save(gif_buffer, format='GIF')

    async with aiohttp.ClientSession() as session:
        return await post_command(
            session, host, "Draw/SendHttpGif",
            PicNum=1, PicWidth=PIXOO_SIZE, PicOffset=0, PicID=1, PicSpeed=1000,
            PicData=base64.b64encode(gif_buffer.getvalue()).decode('utf-8')) is not None


async def test_method_4(host: str):
    """Method 4: Switch to custom page/channel"""
    logger.info("\n=== Testing Method 4: Switch to Custom Channel ===")

    async with aiohttp.ClientSession() as session:
        return await post_command(session, host, "Channel/SetIndex",
                                  SelectIndex=3) is not None


async def get_device_info(host: str):
    """Get current device settings"""
    logger.info("\n=== Getting Device Info ===")

    commands = [
        ("Channel/GetIndex", "Current channel"),
        ("Device/GetDeviceTime", "Device time"),
        ("Channel/GetAllConf", "All channel config"),
    ]

    async with aiohttp.ClientSession() as session:
        for command, description in commands:
            data = await post_command(session, host, command)
            logger.info("%s (%s): %s", description, command, data)


async def test_method_5(host: str, image):
    """Method 5: Reset animation, send GIF, play"""
    logger.info("\n=== Testing Method 5: Reset animation first ===")

    gif_buffer = BytesIO()
    image.save(gif_buffer, format='GIF')

    async with aiohttp.ClientSession() as session:
        await post_command(session, host, "Draw/ResetHttpGifId")
        await asyncio.sleep(0.5)

        ok = await post_command(
            session, host, "Draw/SendHttpGif",
            PicNum=1, PicWidth=PIXOO_SIZE, PicOffset=0, PicID=0, PicSpeed=1000,
            PicData=base64.b64encode(gif_buffer.getvalue()).decode('utf-8')) is not None

        await asyncio.sleep(0.5)
        await post_command(session, host, "Draw/SendHttpItemList", ItemList=[])
        return ok


async def main():
    parser = argparse.ArgumentParser(description="Pixoo64 API diagnostic tool")
    parser.add_argument("--ip", default=Config().pixoo_host,
                        help="Pixoo64 IP address (default: from Config)")
    args = parser.parse_args()

    print("=" * 70)
    print("PIXOO64 API DIAGNOSTIC TOOL")
    print("=" * 70)
    print(f"\nTesting Pixoo64 at: {args.ip}")
    print("\nThis will try different API methods to find what works")
    print("with your Pixoo64's firmware version.\n")

    # Create test image
    test_image = create_diagnostic_image()

    # Get device info first
    await get_device_info(args.ip)

    print("\n" + "=" * 70)
    print("TRYING DIFFERENT DISPLAY METHODS")
    print("=" * 70)

    # Try switching to custom channel first
    await test_method_4(args.ip)
    await asyncio.sleep(1)

    # Try each method
    await test_method_1(args.ip, test_image)
    await asyncio.sleep(3)

    await test_method_2(args.ip, test_image)
    await asyncio.sleep(3)

    await test_method_5(args.ip, test_image)
    await asyncio.sleep(3)

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)
    print("\nCheck your Pixoo64 display to see if any method worked.")
    print("If you saw a red square with white border and X, note which method worked!")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Systematically test different pixel formats to find what works
"""

import argparse
import asyncio
import base64
import logging
from io import BytesIO

import aiohttp
from PIL import Image

from lms_pixoo_service import Config
from patterns import create_orientation_image
from pixoo import post_command, to_pixel_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_format(host: str, format_name: str, pixel_data: bytes, extra_delay: int = 2):
    """Test a specific pixel format"""
    logger.info("\n%s", "=" * 60)
    logger.info("Testing: %s", format_name)
    logger.info("%s", "=" * 60)

    async with aiohttp.ClientSession() as session:
        # Switch to channel 3, reset, send data, display
        await post_command(session, host, "Channel/SetIndex", SelectIndex=3)
        await post_command(session, host, "Draw/ResetHttpGifId")
        result = await post_command(
            session, host, "Draw/SendHttpGif",
            PicNum=1, PicWidth=64, PicOffset=0, PicID=0, PicSpeed=1000,
            PicData=base64.b64encode(pixel_data).decode('utf-8'))
        if result is None:
            logger.error("Send failed")
            return
        await post_command(session, host, "Draw/SendHttpItemList", ItemList=[])

    logger.info("✓ Sent - Check display now!")
    logger.info("You should see: RED top half, GREEN bottom half, BLUE center square")

    # Wait for user to observe
    await asyncio.sleep(extra_delay)


async def main():
    parser = argparse.ArgumentParser(description="Pixel format finder")
    parser.add_argument("--ip", default=Config().pixoo_host,
                        help="Pixoo64 IP address (default: from Config)")
    args = parser.parse_args()

    print("=" * 70)
    print("PIXEL FORMAT FINDER")
    print("=" * 70)
    print("\nCreating test image...")
    print("Expected result: RED top, GREEN bottom, BLUE square in center")
    print("\nWill try different formats with 5 second delay between each")
    print("=" * 70)

    test_img = create_orientation_image()
    test_img.save("format_test.png")

    # Wait before starting
    await asyncio.sleep(2)

    # Format 1: Save as GIF normally
    logger.info("\n\n*** FORMAT 1: Standard PIL GIF ***")
    gif_buf = BytesIO()
    test_img.save(gif_buf, format='GIF')
    await test_format(args.ip, "Standard GIF", gif_buf.getvalue(), 5)

    # Format 2: GIF with palette conversion
    logger.info("\n\n*** FORMAT 2: GIF with Palette Mode ***")
    gif_buf2 = BytesIO()
    test_img.convert('P', palette=Image.Palette.ADAPTIVE).save(gif_buf2, format='GIF', optimize=False)
    await test_format(args.ip, "GIF Palette Mode", gif_buf2.getvalue(), 5)

    # Format 3: Save as PNG
    logger.info("\n\n*** FORMAT 3: PNG converted to bytes ***")
    png_buf = BytesIO()
    test_img.save(png_buf, format='PNG')
    await test_format(args.ip, "PNG Format", png_buf.getvalue(), 5)

    # Format 4: Raw RGB bytes (row-major, RGB order)
    logger.info("\n\n*** FORMAT 4: Raw RGB row-major ***")
    await test_format(args.ip, "Raw RGB Row-Major", to_pixel_data(test_img), 5)

    # Format 5: Raw BGR bytes (row-major, BGR order)
    logger.info("\n\n*** FORMAT 5: Raw BGR row-major ***")
    bgr_bytes = bytearray()
    for y in range(64):
        for x in range(64):
            r, g, b = test_img.getpixel((x, y))
            bgr_bytes.extend([b, g, r])
    await test_format(args.ip, "Raw BGR Row-Major", bytes(bgr_bytes), 5)

    # Format 6: Raw RGB bytes (column-major)
    logger.info("\n\n*** FORMAT 6: Raw RGB column-major ***")
    rgb_col_bytes = bytearray()
    for x in range(64):
        for y in range(64):
            r, g, b = test_img.getpixel((x, y))
            rgb_col_bytes.extend([r, g, b])
    await test_format(args.ip, "Raw RGB Column-Major", bytes(rgb_col_bytes), 5)

    print("\n" + "=" * 70)
    print("TESTING COMPLETE")
    print("=" * 70)
    print("\nWhich format displayed correctly?")
    print("1. Standard GIF")
    print("2. GIF Palette Mode")
    print("3. PNG Format")
    print("4. Raw RGB Row-Major")
    print("5. Raw BGR Row-Major")
    print("6. Raw RGB Column-Major")
    print("\nLet me know which one worked!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

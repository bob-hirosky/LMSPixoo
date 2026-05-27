#!/usr/bin/env python3
"""
Systematically test different pixel formats to find what works
"""

import asyncio
import aiohttp
import base64
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_distinct_test_image() -> Image.Image:
    """Create image with very distinct regions for testing"""
    img = Image.new('RGB', (64, 64), (0, 0, 0))
    
    # Top half: RED
    for y in range(32):
        for x in range(64):
            img.putpixel((x, y), (255, 0, 0))
    
    # Bottom half: GREEN
    for y in range(32, 64):
        for x in range(64):
            img.putpixel((x, y), (0, 255, 0))
    
    # Small BLUE square in center for orientation
    for y in range(28, 36):
        for x in range(28, 36):
            img.putpixel((x, y), (0, 0, 255))
    
    return img


async def test_format(host: str, image: Image.Image, format_name: str, pixel_data: bytes, extra_delay: int = 2):
    """Test a specific pixel format"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing: {format_name}")
    logger.info(f"{'='*60}")
    
    payload = {
        "Command": "Draw/SendHttpGif",
        "PicNum": 1,
        "PicWidth": 64,
        "PicOffset": 0,
        "PicID": 0,
        "PicSpeed": 1000,
        "PicData": base64.b64encode(pixel_data).decode('utf-8')
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Switch to channel 3
            await session.post(f"http://{host}/post", json={
                "Command": "Channel/SetIndex",
                "SelectIndex": 3
            })
            
            # Reset
            await session.post(f"http://{host}/post", json={
                "Command": "Draw/ResetHttpGifId"
            })
            
            # Send data
            async with session.post(f"http://{host}/post", json=payload) as response:
                status = response.status
                logger.info(f"Response status: {status}")
            
            # Display
            await session.post(f"http://{host}/post", json={
                "Command": "Draw/SendHttpItemList",
                "ItemList": []
            })
        
        logger.info(f"✓ Sent - Check display now!")
        logger.info(f"You should see: RED top half, GREEN bottom half, BLUE center square")
        
        # Wait for user to observe
        await asyncio.sleep(extra_delay)
        
    except Exception as e:
        logger.error(f"Error: {e}")


async def main():
    PIXOO_IP = "192.168.2.206"
    
    print("=" * 70)
    print("PIXEL FORMAT FINDER")
    print("=" * 70)
    print("\nCreating test image...")
    print("Expected result: RED top, GREEN bottom, BLUE square in center")
    print("\nWill try different formats with 5 second delay between each")
    print("=" * 70)
    
    test_img = create_distinct_test_image()
    test_img.save("format_test.png")
    
    # Wait before starting
    await asyncio.sleep(2)
    
    # Format 1: Save as GIF normally
    logger.info("\n\n*** FORMAT 1: Standard PIL GIF ***")
    from io import BytesIO
    gif_buf = BytesIO()
    test_img.save(gif_buf, format='GIF')
    await test_format(PIXOO_IP, test_img, "Standard GIF", gif_buf.getvalue(), 5)
    
    # Format 2: GIF with palette conversion
    logger.info("\n\n*** FORMAT 2: GIF with Palette Mode ***")
    gif_buf2 = BytesIO()
    test_img.convert('P', palette=Image.Palette.ADAPTIVE).save(gif_buf2, format='GIF', optimize=False)
    await test_format(PIXOO_IP, test_img, "GIF Palette Mode", gif_buf2.getvalue(), 5)
    
    # Format 3: Save as PNG then convert
    logger.info("\n\n*** FORMAT 3: PNG converted to bytes ***")
    png_buf = BytesIO()
    test_img.save(png_buf, format='PNG')
    await test_format(PIXOO_IP, test_img, "PNG Format", png_buf.getvalue(), 5)
    
    # Format 4: Raw RGB bytes (row-major, RGB order)
    logger.info("\n\n*** FORMAT 4: Raw RGB row-major ***")
    rgb_bytes = bytearray()
    for y in range(64):
        for x in range(64):
            r, g, b = test_img.getpixel((x, y))
            rgb_bytes.extend([r, g, b])
    await test_format(PIXOO_IP, test_img, "Raw RGB Row-Major", bytes(rgb_bytes), 5)
    
    # Format 5: Raw BGR bytes (row-major, BGR order)
    logger.info("\n\n*** FORMAT 5: Raw BGR row-major ***")
    bgr_bytes = bytearray()
    for y in range(64):
        for x in range(64):
            r, g, b = test_img.getpixel((x, y))
            bgr_bytes.extend([b, g, r])
    await test_format(PIXOO_IP, test_img, "Raw BGR Row-Major", bytes(bgr_bytes), 5)
    
    # Format 6: Raw RGB bytes (column-major)
    logger.info("\n\n*** FORMAT 6: Raw RGB column-major ***")
    rgb_col_bytes = bytearray()
    for x in range(64):
        for y in range(64):
            r, g, b = test_img.getpixel((x, y))
            rgb_col_bytes.extend([r, g, b])
    await test_format(PIXOO_IP, test_img, "Raw RGB Column-Major", bytes(rgb_col_bytes), 5)
    
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

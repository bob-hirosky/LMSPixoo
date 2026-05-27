#!/usr/bin/env python3
"""
Test sending image using raw pixel data instead of GIF
"""

import asyncio
import aiohttp
import base64
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_simple_test_image() -> Image.Image:
    """Create a simple test pattern"""
    img = Image.new('RGB', (64, 64))
    
    # Create quarters with different colors
    for y in range(64):
        for x in range(64):
            if x < 32 and y < 32:
                color = (255, 0, 0)  # Red
            elif x >= 32 and y < 32:
                color = (0, 255, 0)  # Green
            elif x < 32 and y >= 32:
                color = (0, 0, 255)  # Blue
            else:
                color = (255, 255, 0)  # Yellow
            img.putpixel((x, y), color)
    
    return img


async def send_image_raw_pixels(host: str, image: Image.Image) -> bool:
    """Send image using raw pixel data format"""
    try:
        image = image.convert('RGB')
        
        # Method 1: Try with PicData as array of RGB values
        pixels = []
        for y in range(64):
            for x in range(64):
                r, g, b = image.getpixel((x, y))
                # Pack as RGB integer
                pixels.append((r << 16) | (g << 8) | b)
        
        payload = {
            "Command": "Draw/SendHttpItemList",
            "ItemList": [
                {
                    "type": 0,
                    "x": 0,
                    "y": 0,
                    "dir": 0,
                    "width": 64,
                    "height": 64,
                    "PicData": pixels
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            # Switch to custom channel first
            await session.post(f"http://{host}/post", json={
                "Command": "Channel/SetIndex",
                "SelectIndex": 3
            })
            
            async with session.post(
                f"http://{host}/post",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                logger.info(f"Method 1 (pixel array) - Status: {response.status}")
                text = await response.text()
                logger.info(f"Response: {text[:200]}")
                return response.status == 200
                
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


async def send_image_base64_rgb(host: str, image: Image.Image) -> bool:
    """Send image using base64-encoded RGB bytes"""
    try:
        image = image.convert('RGB')
        
        # Create raw RGB byte array
        rgb_bytes = []
        for y in range(64):
            for x in range(64):
                r, g, b = image.getpixel((x, y))
                rgb_bytes.extend([r, g, b])
        
        payload = {
            "Command": "Draw/CommandList",
            "CommandList": [
                {
                    "Command": "Draw/SendRemote",
                    "PicWidth": 64,
                    "PicData": base64.b64encode(bytes(rgb_bytes)).decode('utf-8')
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{host}/post",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                logger.info(f"Method 2 (base64 RGB) - Status: {response.status}")
                text = await response.text()
                logger.info(f"Response: {text[:200]}")
                return response.status == 200
                
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


async def main():
    PIXOO_IP = "192.168.2.206"
    
    print("=" * 70)
    print("Testing RAW PIXEL methods")
    print("=" * 70)
    
    test_img = create_simple_test_image()
    test_img.save("test_pattern.png")
    logger.info("Created test pattern: 4 colored squares")
    
    print("\nTrying Method 1: Pixel array...")
    await send_image_raw_pixels(PIXOO_IP, test_img)
    await asyncio.sleep(3)
    
    print("\nTrying Method 2: Base64 RGB...")
    await send_image_base64_rgb(PIXOO_IP, test_img)
    
    print("\n" + "=" * 70)
    print("Check your Pixoo64 display!")
    print("You should see 4 colored squares (red, green, blue, yellow)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
    

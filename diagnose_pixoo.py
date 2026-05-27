#!/usr/bin/env python3
"""
Diagnostic script to test different Pixoo64 API methods
"""

import asyncio
import aiohttp
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_simple_test_image() -> Image.Image:
    """Create a simple red square test image"""
    img = Image.new('RGB', (64, 64), color=(255, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw white border
    draw.rectangle([0, 0, 63, 63], outline=(255, 255, 255), width=3)
    # Draw X in the middle
    draw.line([20, 20, 44, 44], fill=(255, 255, 255), width=2)
    draw.line([20, 44, 44, 20], fill=(255, 255, 255), width=2)
    return img


async def test_method_1(host: str, image: Image.Image):
    """Method 1: Device/SetStaticImage (current implementation)"""
    logger.info("\n=== Testing Method 1: Device/SetStaticImage ===")
    
    image = image.convert('RGB')
    pixels = []
    for y in range(64):
        for x in range(64):
            r, g, b = image.getpixel((x, y))
            pixels.append(r)
            pixels.append(g)
            pixels.append(b)
    
    payload = {
        "Command": "Device/SetStaticImage",
        "StaticImageData": {
            "PicNum": 1,
            "PicWidth": 64,
            "PicOffset": 0,
            "PicID": 0,
            "PicSpeed": 1000,
            "PicData": base64.b64encode(bytes(pixels)).decode('utf-8')
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://{host}/post", json=payload) as response:
            text = await response.text()
            logger.info(f"Status: {response.status}")
            logger.info(f"Response: {text}")
            return response.status == 200


async def test_method_2(host: str, image: Image.Image):
    """Method 2: Draw/SendHttpGif"""
    logger.info("\n=== Testing Method 2: Draw/SendHttpGif ===")
    
    # Save image as GIF
    from io import BytesIO
    gif_buffer = BytesIO()
    image.save(gif_buffer, format='GIF')
    gif_data = gif_buffer.getvalue()
    
    payload = {
        "Command": "Draw/SendHttpGif",
        "PicNum": 1,
        "PicWidth": 64,
        "PicOffset": 0,
        "PicID": 1,
        "PicSpeed": 1000,
        "PicData": base64.b64encode(gif_data).decode('utf-8')
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://{host}/post", json=payload) as response:
            text = await response.text()
            logger.info(f"Status: {response.status}")
            logger.info(f"Response: {text}")
            return response.status == 200


async def test_method_3(host: str, image: Image.Image):
    """Method 3: Direct pixel push with simpler format"""
    logger.info("\n=== Testing Method 3: Simpler pixel format ===")
    
    image = image.convert('RGB')
    pixel_data = []
    for y in range(64):
        for x in range(64):
            r, g, b = image.getpixel((x, y))
            # Pack RGB into single integer
            pixel_data.append((r << 16) | (g << 8) | b)
    
    payload = {
        "Command": "Draw/SendHttpItemList",
        "ItemList": [
            {
                "TextId": 1,
                "type": 22,
                "x": 0,
                "y": 0,
                "dir": 0,
                "font": 0,
                "TextWidth": 64,
                "Textheight": 64,
                "speed": 0,
                "color": "#FFFFFF",
                "align": 1
            }
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://{host}/post", json=payload) as response:
            text = await response.text()
            logger.info(f"Status: {response.status}")
            logger.info(f"Response: {text}")
            return response.status == 200


async def test_method_4(host: str):
    """Method 4: Switch to custom page/channel first"""
    logger.info("\n=== Testing Method 4: Switch to Custom Channel ===")
    
    # Try switching to custom page (channel 3 is usually custom)
    payload = {
        "Command": "Channel/SetIndex",
        "SelectIndex": 3
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://{host}/post", json=payload) as response:
            text = await response.text()
            logger.info(f"Status: {response.status}")
            logger.info(f"Response: {text}")
            return response.status == 200


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
            payload = {"Command": command}
            try:
                async with session.post(f"http://{host}/post", json=payload, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    text = await response.text()
                    logger.info(f"\n{description} ({command}):")
                    logger.info(f"  Status: {response.status}")
                    logger.info(f"  Response: {text}")
            except Exception as e:
                logger.info(f"  Error: {e}")


async def test_method_5(host: str, image: Image.Image):
    """Method 5: Reset animation and send image"""
    logger.info("\n=== Testing Method 5: Reset animation first ===")
    
    async with aiohttp.ClientSession() as session:
        # First, reset/clear animation
        reset_payload = {
            "Command": "Draw/ResetHttpGifId"
        }
        async with session.post(f"http://{host}/post", json=reset_payload) as response:
            logger.info(f"Reset status: {response.status}")
        
        await asyncio.sleep(0.5)
        
        # Now send GIF
        from io import BytesIO
        gif_buffer = BytesIO()
        image.save(gif_buffer, format='GIF')
        gif_data = gif_buffer.getvalue()
        
        payload = {
            "Command": "Draw/SendHttpGif",
            "PicNum": 1,
            "PicWidth": 64,
            "PicOffset": 0,
            "PicID": 0,
            "PicSpeed": 1000,
            "PicData": base64.b64encode(gif_data).decode('utf-8')
        }
        
        async with session.post(f"http://{host}/post", json=payload) as response:
            text = await response.text()
            logger.info(f"Send GIF status: {response.status}")
            logger.info(f"Response: {text}")
            
        await asyncio.sleep(0.5)
        
        # Finally, play the animation
        play_payload = {
            "Command": "Draw/SendHttpItemList",
            "ItemList": []
        }
        async with session.post(f"http://{host}/post", json=play_payload) as response:
            logger.info(f"Play status: {response.status}")


async def main():
    PIXOO_IP = "192.168.2.206"  # Your Pixoo IP
    
    print("=" * 70)
    print("PIXOO64 API DIAGNOSTIC TOOL")
    print("=" * 70)
    print(f"\nTesting Pixoo64 at: {PIXOO_IP}")
    print("\nThis will try different API methods to find what works")
    print("with your Pixoo64's firmware version.\n")
    
    # Create test image
    test_image = create_simple_test_image()
    
    # Get device info first
    await get_device_info(PIXOO_IP)
    
    print("\n" + "=" * 70)
    print("TRYING DIFFERENT DISPLAY METHODS")
    print("=" * 70)
    
    # Try switching to custom channel first
    await test_method_4(PIXOO_IP)
    await asyncio.sleep(1)
    
    # Try each method
    await test_method_1(PIXOO_IP, test_image)
    await asyncio.sleep(3)
    
    await test_method_2(PIXOO_IP, test_image)
    await asyncio.sleep(3)
    
    await test_method_5(PIXOO_IP, test_image)
    await asyncio.sleep(3)
    
    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)
    print("\nCheck your Pixoo64 display to see if any method worked.")
    print("If you saw a red square with white border and X, note which method worked!")


if __name__ == "__main__":
    asyncio.run(main())

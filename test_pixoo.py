#!/usr/bin/env python3
"""
Test script to verify Pixoo64 connection and display test images
"""

import asyncio
from PIL import Image, ImageDraw, ImageFont
from lms_pixoo_service import PixooClient
import logging

logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_image(text: str, color: tuple = (255, 0, 0)) -> Image.Image:
    """Create a simple test image with text"""
    img = Image.new('RGB', (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a colored border
    draw.rectangle([0, 0, 63, 63], outline=color, width=2)
    
    # Add text in center
    try:
        # Try to use a default font, fallback to basic if not available
        font = ImageFont.load_default()
    except:
        font = None
    
    # Calculate text position (center)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((64 - text_width) // 2, (64 - text_height) // 2)
    
    draw.text(position, text, fill=color, font=font)
    
    return img


def create_gradient_image() -> Image.Image:
    """Create a colorful gradient test image"""
    img = Image.new('RGB', (64, 64))
    for y in range(64):
        for x in range(64):
            r = int(255 * x / 64)
            g = int(255 * y / 64)
            b = int(255 * (1 - x / 64))
            img.putpixel((x, y), (r, g, b))
    return img


async def test_pixoo_connection(pixoo_ip: str):
    """Test the Pixoo64 connection with various test images"""
    client = PixooClient(pixoo_ip)
    
    logger.info(f"Testing connection to Pixoo64 at {pixoo_ip}...")
    
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
    logger.info("\nTest 2: Sending red test pattern...")
    test_img = create_test_image("TEST", color=(255, 0, 0))
    await client.send_image(test_img)
    await asyncio.sleep(2)
    
    # Test 3: Send gradient image
    logger.info("Test 3: Sending gradient pattern...")
    gradient_img = create_gradient_image()
    await client.send_image(gradient_img)
    await asyncio.sleep(2)
    
    # Test 4: Send green success image
    logger.info("Test 4: Sending green success pattern...")
    success_img = create_test_image("OK!", color=(0, 255, 0))
    await client.send_image(success_img)
    
    logger.info("\n✓ All tests completed successfully!")
    logger.info("Your Pixoo64 is ready to display album art.")


async def main():
    # UPDATE THIS with your Pixoo64's IP address
    PIXOO_IP = "192.168.2.206"
    
    print("=" * 60)
    print("Pixoo64 Connection Test")
    print("=" * 60)
    print(f"\nPixoo64 IP: {PIXOO_IP}")
    print("\nMake sure to update PIXOO_IP in this script")
    print("with your actual Pixoo64 IP address!\n")
    
    await test_pixoo_connection(PIXOO_IP)


if __name__ == "__main__":
    asyncio.run(main())

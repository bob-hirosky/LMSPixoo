#!/usr/bin/env python3
"""
Test sending a sample album art image to Pixoo64
"""

import asyncio
import sys
from PIL import Image
sys.path.insert(0, 'mnt')
from lms_pixoo_service import PixooClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_album_art() -> Image.Image:
    """Create a colorful test image that looks like album art"""
    img = Image.new('RGB', (64, 64))
    
    # Create a gradient background
    for y in range(64):
        for x in range(64):
            # Create a radial gradient
            dx = (x - 32) / 32
            dy = (y - 32) / 32
            distance = (dx*dx + dy*dy) ** 0.5
            
            if distance < 0.8:
                # Inner circle - colorful
                r = int(128 + 127 * (x / 64))
                g = int(128 + 127 * (y / 64))
                b = int(200 - 100 * distance)
            else:
                # Outer ring - darker
                r = int(50 + 50 * (x / 64))
                g = int(50 + 50 * (y / 64))
                b = 100
            
            img.putpixel((x, y), (r, g, b))
    
    return img


async def main():
    PIXOO_IP = "192.168.2.206"
    
    print("=" * 60)
    print("Testing Album Art Display")
    print("=" * 60)
    
    client = PixooClient(PIXOO_IP)
    
    # Create test image
    logger.info("Creating test album art image...")
    test_img = create_test_album_art()
    
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

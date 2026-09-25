#!/usr/bin/env python3
"""
64x64 test pattern generators for the Pixoo64.

Shared by the test/diagnostic scripts so each pattern is defined once.
"""

from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

from pixoo import PIXOO_SIZE

Color = Tuple[int, int, int]


def create_text_image(text: str, color: Color = (255, 0, 0)) -> Image.Image:
    """Create an image with a colored border and centered text."""
    img = Image.new('RGB', (PIXOO_SIZE, PIXOO_SIZE), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, PIXOO_SIZE - 1, PIXOO_SIZE - 1], outline=color, width=2)

    font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((PIXOO_SIZE - text_width) // 2, (PIXOO_SIZE - text_height) // 2)
    draw.text(position, text, fill=color, font=font)

    return img


def create_gradient_image() -> Image.Image:
    """Create a colorful gradient test image."""
    img = Image.new('RGB', (PIXOO_SIZE, PIXOO_SIZE))
    for y in range(PIXOO_SIZE):
        for x in range(PIXOO_SIZE):
            r = int(255 * x / PIXOO_SIZE)
            g = int(255 * y / PIXOO_SIZE)
            b = int(255 * (1 - x / PIXOO_SIZE))
            img.putpixel((x, y), (r, g, b))
    return img


def create_quadrants_image() -> Image.Image:
    """Create four colored quadrants: red, green, blue, yellow."""
    img = Image.new('RGB', (PIXOO_SIZE, PIXOO_SIZE))
    half = PIXOO_SIZE // 2
    for y in range(PIXOO_SIZE):
        for x in range(PIXOO_SIZE):
            if x < half and y < half:
                color = (255, 0, 0)      # red
            elif x >= half and y < half:
                color = (0, 255, 0)      # green
            elif x < half and y >= half:
                color = (0, 0, 255)      # blue
            else:
                color = (255, 255, 0)    # yellow
            img.putpixel((x, y), color)
    return img


def create_orientation_image() -> Image.Image:
    """Create a pattern with distinct regions for orientation testing.

    Red top half, green bottom half, blue square in the center.
    """
    img = Image.new('RGB', (PIXOO_SIZE, PIXOO_SIZE), (0, 0, 0))
    half = PIXOO_SIZE // 2
    lo, hi = half - 4, half + 4
    for y in range(PIXOO_SIZE):
        for x in range(PIXOO_SIZE):
            if lo <= x < hi and lo <= y < hi:
                img.putpixel((x, y), (0, 0, 255))    # blue center square
            elif y < half:
                img.putpixel((x, y), (255, 0, 0))    # red top
            else:
                img.putpixel((x, y), (0, 255, 0))    # green bottom
    return img


def create_album_art_image() -> Image.Image:
    """Create a colorful radial-gradient image that looks like album art."""
    img = Image.new('RGB', (PIXOO_SIZE, PIXOO_SIZE))
    center = PIXOO_SIZE // 2
    for y in range(PIXOO_SIZE):
        for x in range(PIXOO_SIZE):
            dx = (x - center) / center
            dy = (y - center) / center
            distance = (dx * dx + dy * dy) ** 0.5

            if distance < 0.8:
                r = int(128 + 127 * (x / PIXOO_SIZE))
                g = int(128 + 127 * (y / PIXOO_SIZE))
                b = int(200 - 100 * distance)
            else:
                r = int(50 + 50 * (x / PIXOO_SIZE))
                g = int(50 + 50 * (y / PIXOO_SIZE))
                b = 100

            img.putpixel((x, y), (r, g, b))
    return img


def create_diagnostic_image() -> Image.Image:
    """Create a red square with a white border and an X in the middle."""
    img = Image.new('RGB', (PIXOO_SIZE, PIXOO_SIZE), color=(255, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, PIXOO_SIZE - 1, PIXOO_SIZE - 1],
                   outline=(255, 255, 255), width=3)
    draw.line([20, 20, 44, 44], fill=(255, 255, 255), width=2)
    draw.line([20, 44, 44, 20], fill=(255, 255, 255), width=2)
    return img

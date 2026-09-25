#!/usr/bin/env python3
"""
Divoom Pixoo64 client and protocol helpers.

Shared by the album art service, reset_pixoo.py and the test/diagnostic
scripts so that the 4-step upload sequence and other protocol details
live in exactly one place.
"""

import base64
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

PIXOO_SIZE = 64

# Default timeouts used for the fire-and-forget HTTP API
POST_TIMEOUT = aiohttp.ClientTimeout(total=5)


async def post_command(session: aiohttp.ClientSession, host: str, command: str,
                       port: int = 80, check_error: bool = False,
                       **fields) -> Optional[Dict[str, Any]]:
    """POST one command to the Pixoo HTTP API.

    `command` is e.g. "Channel/SetIndex"; extra payload fields are passed
    as keyword arguments. Returns the decoded JSON body, or None on
    connection/HTTP errors. The device replies with JSON but a text/html
    content-type, so decoding uses content_type=None.

    With check_error=True the device's error_code is also validated and
    non-zero responses return None.
    """
    url = f"http://{host}:{port}/post"
    payload = {"Command": command, **fields}
    try:
        async with session.post(url, json=payload, timeout=POST_TIMEOUT) as response:
            if response.status != 200:
                logger.error("Pixoo %s -> HTTP %s", command, response.status)
                return None
            data = await response.json(content_type=None)
            if check_error and data.get("error_code") != 0:
                logger.error("Pixoo %s rejected: %s", command, data)
                return None
            return data
    except Exception as e:
        logger.error("Pixoo %s failed: %s", command, e)
        return None


async def reset_pixoo(host: str, port: int = 80) -> bool:
    """Restore the default time/weather display (clock channel)."""
    try:
        async with aiohttp.ClientSession() as session:
            # Stop any HTTP gif stream, then switch back to clock channel 0
            if await post_command(session, host, "Draw/ResetHttpGifId", port,
                                  check_error=True) is None:
                return False
            if await post_command(session, host, "Channel/SetIndex", port,
                                  check_error=True, SelectIndex=0) is None:
                return False
        logger.info("Pixoo64 at %s reset to time/weather display", host)
        return True
    except Exception as e:
        logger.error("Cannot reach Pixoo64 at %s: %s", host, e)
        return False


def to_pixel_data(image: Image.Image) -> bytes:
    """Convert an image to raw 64x64 RGB bytes (row-major order)."""
    if image.size != (PIXOO_SIZE, PIXOO_SIZE):
        image = image.resize((PIXOO_SIZE, PIXOO_SIZE), Image.Resampling.LANCZOS)
    return image.convert('RGB').tobytes()


TITLE_BAR_HEIGHT = 10


def _draw_title_frame(art: Image.Image, title: str, x_offset: int,
                      font, bbox) -> Image.Image:
    """Render one frame: album art with the title bar drawn at x_offset."""
    frame = art.copy()
    draw = ImageDraw.Draw(frame)
    bar_top = PIXOO_SIZE - TITLE_BAR_HEIGHT
    draw.rectangle([0, bar_top, PIXOO_SIZE - 1, PIXOO_SIZE - 1], fill=(0, 0, 0))
    # Vertically center the glyph box in the bar, compensating for the
    # font's own y offset so descenders aren't clipped at the bottom edge.
    text_height = bbox[3] - bbox[1]
    y = bar_top + (TITLE_BAR_HEIGHT - text_height) // 2 - bbox[1]
    draw.text((x_offset, y), title, fill=(255, 255, 255), font=font)
    return frame


def make_title_frames(image: Image.Image, title: str,
                      hold_frames: int = 4, gap: int = 32,
                      step: int = 2) -> List[Image.Image]:
    """Build the animation frames for the title overlay.

    Short titles that fit the display width are centered and held still.
    Longer titles scroll leftwards as a looping marquee, pausing at the
    start, with blank space between repetitions. `step` is the scroll
    distance in pixels per frame (larger = faster, fewer frames).
    """
    font = ImageFont.load_default()
    art = image.copy().convert('RGB').resize(
        (PIXOO_SIZE, PIXOO_SIZE), Image.Resampling.LANCZOS)

    bbox = font.getbbox(title)
    text_width = bbox[2] - bbox[0]

    if text_width <= PIXOO_SIZE:
        # Fits: single static frame, centered
        x = (PIXOO_SIZE - text_width) // 2 - bbox[0]
        return [_draw_title_frame(art, title, x, font, bbox)]

    # Scrolling marquee: start with the text fully on-screen (x=0),
    # then shift left until the tail end has cleared, plus a blank gap.
    scroll_range = text_width + gap
    frames = [
        _draw_title_frame(art, title, -bbox[0] - x, font, bbox)
        for x in range(0, scroll_range + 1, step)
    ]
    # Hold the first frame a little so the start of the title lingers
    return frames[:1] * hold_frames + frames


class PixooClient:
    """Client for the Divoom Pixoo64 LED display."""

    def __init__(self, host: str, port: int = 80):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._last_frames: Optional[List[bytes]] = None

    async def _push_pixel_data(self, frames: List[bytes], session: aiohttp.ClientSession,
                               frame_ms: int = 200) -> bool:
        """Push raw 64x64 RGB frame(s) to the display using the 4-step sequence.

        With multiple frames the device plays them as a looping animation,
        each frame shown for frame_ms milliseconds.
        """
        # Step 1: switch to custom channel (3)
        if await post_command(session, self.host, "Channel/SetIndex",
                              self.port, SelectIndex=3) is None:
            return False
        # Step 2: reset animation
        if await post_command(session, self.host, "Draw/ResetHttpGifId",
                              self.port) is None:
            return False
        # Step 3: send raw RGB pixel data, one chunk per frame
        # (Despite the name "SendHttpGif", the payload is raw RGB bytes)
        for offset, pixel_data in enumerate(frames):
            if await post_command(
                    session, self.host, "Draw/SendHttpGif", self.port,
                    PicNum=len(frames), PicWidth=PIXOO_SIZE, PicOffset=offset,
                    PicID=0, PicSpeed=frame_ms,
                    PicData=base64.b64encode(pixel_data).decode('utf-8')) is None:
                return False
        # Step 4: play/display the image
        return await post_command(session, self.host, "Draw/SendHttpItemList",
                                  self.port, ItemList=[]) is not None

    async def send_image(self, image: Image.Image, title: str = "") -> bool:
        """Send an image to the display.

        If title is given, it is drawn in a bar at the bottom; titles too
        wide for the display scroll as a looping marquee.

        Skips the update if the image is identical to the one currently shown.
        """
        try:
            if title:
                frames = [to_pixel_data(f) for f in make_title_frames(image, title)]
            else:
                frames = [to_pixel_data(image)]

            # Nothing to do if the display already shows this exact image
            if frames == self._last_frames:
                logger.info("Image unchanged; skipping update")
                return True

            async with aiohttp.ClientSession() as session:
                if not await self._push_pixel_data(frames, session):
                    return False

            self._last_frames = frames
            logger.info("Successfully sent image to Pixoo64 (%d frame(s))", len(frames))
            return True

        except Exception as e:
            logger.error("Error sending image to Pixoo64: %s", e)
            return False

    async def reset(self) -> bool:
        """Restore the default time/weather display (clock channel)."""
        return await reset_pixoo(self.host, self.port)

    async def test_connection(self) -> bool:
        """Test connection to the Pixoo64."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/get", timeout=POST_TIMEOUT
                ) as response:
                    if response.status == 200:
                        logger.info("Pixoo64 connection successful")
                        return True
                    return False
        except Exception as e:
            logger.error("Cannot connect to Pixoo64: %s", e)
            return False

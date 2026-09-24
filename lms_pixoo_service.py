#!/usr/bin/env python3
"""
LMS to Pixoo64 Album Art Display Service
Monitors Lyrion Media Server for song changes and displays album art on Divoom Pixoo64
"""

import asyncio
import argparse
import sys
import aiohttp
import json
import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Service configuration"""
    lms_host: str = "192.168.2.78"
    lms_port: int = 9000
    lms_player_id: str = "aa:aa:cd:8f:38:b0"  # MAC address of player, empty = first player
    pixoo_host: str = "192.168.2.206"  # Update with your Pixoo64 IP
    pixoo_port: int = 80
    poll_interval: float = 1.0  # seconds
    image_size: int = 64
    show_title: bool = False  # overlay scrolling song title at the bottom


class PixooClient:
    """Client for Divoom Pixoo64 LED display"""

    def __init__(self, host: str, port: int = 80):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._last_frames: Optional[List[bytes]] = None

    @staticmethod
    def _to_pixel_data(image: Image.Image) -> bytes:
        """Convert image to raw 64x64 RGB bytes (row-major order)."""
        # Ensure image is 64x64 RGB
        if image.size != (64, 64):
            image = image.resize((64, 64), Image.Resampling.LANCZOS)

        # Convert to RGB
        image = image.convert('RGB')

        # Create raw RGB byte array (row-major order)
        rgb_bytes = bytearray()
        for y in range(64):
            for x in range(64):
                r, g, b = image.getpixel((x, y))
                rgb_bytes.extend([r, g, b])

        return bytes(rgb_bytes)

    async def _push_pixel_data(self, frames: List[bytes], session: aiohttp.ClientSession,
                               frame_ms: int = 200) -> bool:
        """Push raw 64x64 RGB frame(s) to the display using the 4-step sequence.

        With multiple frames the device plays them as a looping animation,
        each frame shown for frame_ms milliseconds.
        """
        # Step 1: Switch to custom channel (channel 3)
        channel_payload = {
            "Command": "Channel/SetIndex",
            "SelectIndex": 3
        }
        await session.post(
            f"{self.base_url}/post",
            json=channel_payload,
            timeout=aiohttp.ClientTimeout(total=5)
        )

        # Step 2: Reset animation
        reset_payload = {
            "Command": "Draw/ResetHttpGifId"
        }
        await session.post(
            f"{self.base_url}/post",
            json=reset_payload,
            timeout=aiohttp.ClientTimeout(total=5)
        )

        # Step 3: Send raw RGB pixel data, one chunk per frame
        # (Note: Despite command name "SendHttpGif", we send raw RGB bytes)
        for offset, pixel_data in enumerate(frames):
            pixel_payload = {
                "Command": "Draw/SendHttpGif",
                "PicNum": len(frames),
                "PicWidth": 64,
                "PicOffset": offset,
                "PicID": 0,
                "PicSpeed": frame_ms,
                "PicData": base64.b64encode(pixel_data).decode('utf-8')
            }

            async with session.post(
                f"{self.base_url}/post",
                json=pixel_payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status != 200:
                    logger.error(f"Pixoo64 returned status {response.status}")
                    return False

        # Step 4: Play/display the image
        play_payload = {
            "Command": "Draw/SendHttpItemList",
            "ItemList": []
        }
        async with session.post(
            f"{self.base_url}/post",
            json=play_payload,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            if response.status != 200:
                logger.error(f"Failed to display image: status {response.status}")
                return False

        return True

    async def send_image(self, image: Image.Image, title: str = "") -> bool:
        """
        Send image to Pixoo64 display
        Image should already be 64x64 pixels

        If title is given, it is drawn in a bar at the bottom; titles too
        wide for the display scroll as a looping marquee.

        Skips the update if the image is identical to the one currently shown.
        """
        try:
            if title:
                frames = [self._to_pixel_data(f) for f in make_title_frames(image, title)]
            else:
                frames = [self._to_pixel_data(image)]

            # Nothing to do if the display already shows this exact image
            if frames == self._last_frames:
                logger.info("Image unchanged; skipping update")
                return True

            async with aiohttp.ClientSession() as session:
                if not await self._push_pixel_data(frames, session):
                    return False

            self._last_frames = frames
            logger.info(f"Successfully sent image to Pixoo64 ({len(frames)} frame(s))")
            return True

        except Exception as e:
            logger.error(f"Error sending image to Pixoo64: {e}")
            return False

    async def reset(self) -> bool:
        """Restore the default time/weather display (clock channel)."""
        steps = [
            # Stop any HTTP gif stream we may have started
            {"Command": "Draw/ResetHttpGifId"},
            # Switch back to the clock channel (0 = time/weather faces)
            {"Command": "Channel/SetIndex", "SelectIndex": 0},
        ]
        try:
            async with aiohttp.ClientSession() as session:
                for payload in steps:
                    await session.post(
                        f"{self.base_url}/post",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=5),
                    )
            logger.info("Pixoo64 reset to time/weather display")
            return True
        except Exception as e:
            logger.error(f"Error resetting Pixoo64: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test connection to Pixoo64"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/get",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.info("Pixoo64 connection successful")
                        return True
                    return False
        except Exception as e:
            logger.error(f"Cannot connect to Pixoo64: {e}")
            return False


class LMSMonitor:
    """Monitor Lyrion Media Server for song changes"""

    def __init__(self, host: str, port: int, player_id: str = ""):
        self.host = host
        self.port = port
        self.player_id = player_id
        self.current_track_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _send_command(self, command: str, params: list = None) -> Optional[Dict[str, Any]]:
        """Send JSON-RPC command to LMS"""
        if params is None:
            params = []

        payload = {
            "id": 1,
            "method": "slim.request",
            "params": [self.player_id, [command] + params]
        }

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.post(
                f"http://{self.host}:{self.port}/jsonrpc.js",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result', {})
                else:
                    logger.error(f"LMS returned status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error communicating with LMS: {e}")
            return None

    async def get_player_id(self) -> Optional[str]:
        """Get first available player if not specified"""
        result = await self._send_command("players", ["0", "1"])
        if result and "players_loop" in result and len(result["players_loop"]) > 0:
            player = result["players_loop"][0]
            player_id = player.get("playerid")
            logger.info(f"Found player: {player.get('name')} ({player_id})")
            return player_id
        return None

    async def initialize(self) -> bool:
        """Initialize connection to LMS"""
        if not self.player_id:
            self.player_id = await self.get_player_id()
            if not self.player_id:
                logger.error("No LMS player found")
                return False
        return True


    async def select_player_interactive(self) -> Optional[str]:
        """Prompt user to select from available players"""
        result = await self._send_command("players", ["0", "100"])

        if not result or "players_loop" not in result:
            logger.error("No players found")
            return None

        players = result["players_loop"]

        if not players:
            logger.error("No players available")
            return None

        print("\nAvailable LMS Players:")
        for idx, player in enumerate(players, 1):
            print(f"{idx}. {player.get('name')} ({player.get('playerid')})")

        while True:
            try:
                choice = input("Select player number: ").strip()
                selection = int(choice)

                if 1 <= selection <= len(players):
                    selected = players[selection - 1]
                    player_id = selected.get("playerid")
                    logger.info(f"Selected player: {selected.get('name')} ({player_id})")
                    return player_id
                else:
                    print("Invalid selection. Try again.")
            except (ValueError, KeyboardInterrupt):
                print("Invalid input. Enter a number.")

    async def _send_command_global(self, command: str, params: list = None) -> Optional[Dict[str, Any]]:
        """Send server-level JSON-RPC command (no player context)"""
        if params is None:
            params = []

        payload = {
            "id": 1,
            "method": "slim.request",
            "params": ["", [command] + params]  # empty player_id
        }

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.post(
                    f"http://{self.host}:{self.port}/jsonrpc.js",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", {})
                else:
                    logger.error(f"LMS returned status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error communicating with LMS: {e}")
            return None
    
    async def select_player_interactive2(self) -> Optional[str]:
        """Prompt user to select from available players"""
        result = await self._send_command_global("players", ["0", "100"])

        if not result or "players_loop" not in result:
            logger.error("No players found")
            return None

        players = result["players_loop"]

        if not players:
            logger.error("No players available")
            return None

        print("\nAvailable LMS Players:")
        for idx, player in enumerate(players, 1):
            print(f"{idx}. {player.get('name')} ({player.get('playerid')})")

            while True:
                try:
                    choice = input("Select player number (Ctrl-C to cancel): ").strip()
                    selection = int(choice)

                    if 1 <= selection <= len(players):
                        selected = players[selection - 1]
                        player_id = selected.get("playerid")
                        logger.info(f"Selected player: {selected.get('name')} ({player_id})")
                        return player_id
                    else:
                        print("Invalid selection. Try again.")

                except ValueError:
                    print("Invalid input. Enter a number.")

                except KeyboardInterrupt:
                    print("\nSelection cancelled.")
                    raise  # <-- let it propagate properly
                
    async def get_current_track_info(self) -> Optional[Dict[str, Any]]:
        """Get information about currently playing track"""
        result = await self._send_command("status", ["-", "1", "tags:alcu"])
        if result and "playlist_loop" in result and len(result["playlist_loop"]) > 0:
            return result["playlist_loop"][0]
        return None

    async def get_album_art_url(self, track_info: Dict[str, Any]) -> Optional[str]:
        """Extract album art URL from track info"""
        # LMS provides cover art via a special URL
        if "artwork_url" in track_info:
            return f"http://{self.host}:{self.port}/{track_info['artwork_url']}"
        elif "coverid" in track_info:
            return f"http://{self.host}:{self.port}/music/{track_info['coverid']}/cover.jpg"
        return None

    async def download_album_art(self, url: str) -> Optional[Image.Image]:
        """Download and return album art as PIL Image"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    image_data = await response.read()
                    image = Image.open(BytesIO(image_data))
                    
                    # Normalize problematic image modes
                    if image.mode == "P":
                        image = image.convert("RGBA")

                    if image.mode in ("RGBA", "LA"):
                        # Remove transparency by compositing onto black background
                        background = Image.new("RGB", image.size, (0, 0, 0))
                        background.paste(image, mask=image.split()[-1])
                        image = background
                    else:
                        image = image.convert("RGB")

                    logger.info(f"Downloaded album art: {image.size} ({image.mode})")
                    return image
                else:
                    logger.error(f"Failed to download album art: status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error downloading album art: {e}")
            return None

    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()

    

TITLE_BAR_HEIGHT = 10


def _draw_title_frame(art: Image.Image, title: str, text_width: int,
                      x_offset: int, font, bbox) -> Image.Image:
    """Render one frame: album art with the title bar drawn at x_offset."""
    frame = art.copy()
    draw = ImageDraw.Draw(frame)
    bar_top = 64 - TITLE_BAR_HEIGHT
    draw.rectangle([0, bar_top, 63, 63], fill=(0, 0, 0))
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

    Short titles that fit the 64px width are centered and held still.
    Longer titles scroll leftwards as a looping marquee, pausing at the
    start, with blank space between repetitions. `step` is the scroll
    distance in pixels per frame (larger = faster, fewer frames).
    """
    font = ImageFont.load_default()
    art = image.copy().convert('RGB').resize((64, 64), Image.Resampling.LANCZOS)

    bbox = font.getbbox(title)
    text_width = bbox[2] - bbox[0]

    if text_width <= 64:
        # Fits: single static frame, centered
        x = (64 - text_width) // 2 - bbox[0]
        return [_draw_title_frame(art, title, text_width, x, font, bbox)]

    # Scrolling marquee: start with the text fully on-screen (x=0),
    # then shift left until the tail end has cleared, plus a blank gap.
    scroll_range = text_width + gap
    frames = [
        _draw_title_frame(art, title, text_width, -bbox[0] - x, font, bbox)
        for x in range(0, scroll_range + 1, step)
    ]
    # Hold the first frame a little so the start of the title lingers
    return frames[:1] * hold_frames + frames


class AlbumArtService:
    """Main service to monitor LMS and update Pixoo64"""

    def __init__(self, config: Config):
        self.config = config
        self.lms = LMSMonitor(config.lms_host, config.lms_port, config.lms_player_id)
        self.pixoo = PixooClient(config.pixoo_host, config.pixoo_port)
        self.current_track_id: Optional[str] = None
        self.running = False

    async def process_new_track(self, track_info: Dict[str, Any]):
        """Process a new track - get album art and send to Pixoo64"""
        logger.info(f"New track: {track_info.get('artist', 'Unknown')} - {track_info.get('title', 'Unknown')}")

        # Get album art URL
        art_url = await self.lms.get_album_art_url(track_info)
        if not art_url:
            logger.warning("No album art URL available")
            return

        # Download album art
        image = await self.lms.download_album_art(art_url)
        if not image:
            logger.warning("Failed to download album art")
            return

        # Send to Pixoo64, optionally with the song title overlaid at the bottom
        title = track_info.get("title", "") if self.config.show_title else ""
        await self.pixoo.send_image(image, title=title)

    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting monitoring loop...")

        while self.running:
            try:
                # Get current track info
                track_info = await self.lms.get_current_track_info()

                if track_info:
                    # Check if track has changed
                    track_id = track_info.get("id")
                    if track_id and track_id != self.current_track_id:
                        self.current_track_id = track_id
                        await self.process_new_track(track_info)

                # Wait before next poll
                await asyncio.sleep(self.config.poll_interval)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except KeyboardInterrupt:
                logger.info("Monitoring loop interrupted")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.poll_interval)

    async def start(self):
        """Start the service"""
        logger.info("Starting LMS to Pixoo64 service...")

        # Test Pixoo64 connection
        if not await self.pixoo.test_connection():
            logger.error("Cannot connect to Pixoo64. Check IP address and network.")
            return

        # Initialize LMS connection
        if not await self.lms.initialize():
            logger.error("Cannot connect to LMS. Check host and port.")
            return

        # Start monitoring
        self.running = True
        try:
            await self.monitor_loop()
        except asyncio.CancelledError:
            logger.info("Received shutdown signal")
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.running = False
            await self.lms.close()
            # Restore the Pixoo64's default time/weather display
            await self.pixoo.reset()

    def stop(self):
        """Stop the service"""
        logger.info("Stopping service...")
        self.running = False

async def main():
    """Main entry point with CLI support"""

    parser = argparse.ArgumentParser(
        description="LMS to Pixoo64 Album Art Display Service"
    )

    parser.add_argument(
        "--host",
        help="LMS server hostname or IP address"
    )

    parser.add_argument(
        "--pixoo-ip",
        help="Pixoo64 IP address"
    )

    parser.add_argument(
        "--player-id",
        help="LMS player MAC address"
    )

    parser.add_argument(
        "-s",
        action="store_true",
        help="Select LMS player interactively"
    )

    parser.add_argument(
        "--list-players",
        action="store_true",
        help="List available LMS players and exit"
    )

    parser.add_argument(
        "--show-title",
        action="store_true",
        help="Overlay the song title in a scrolling bar at the bottom"
    )

    args = parser.parse_args()

    # Start with default config
    config = Config()

    # Override config from CLI if provided
    if args.host:
        config.lms_host = args.host

    if args.pixoo_ip:
        config.pixoo_host = args.pixoo_ip

    if args.player_id:
        config.lms_player_id = args.player_id

    if args.show_title:
        config.show_title = True

    # Temporary LMS monitor for selection / listing
    temp_lms = LMSMonitor(config.lms_host, config.lms_port, "")

    try:
        # --list-players mode
        if args.list_players:
            result = await temp_lms._send_command("players", ["0", "100"])

            if not result or "players_loop" not in result:
                print("No players found.")
                return

            players = result["players_loop"]

            if not players:
                print("No players available.")
                return

            print("\nAvailable LMS Players:")
            for player in players:
                print(f"- {player.get('name')} ({player.get('playerid')})")

            return

        # -s interactive selection
        if args.s:
            selected_player = await temp_lms.select_player_interactive()

            if not selected_player:
                logger.error("No player selected. Exiting.")
                return

            config.lms_player_id = selected_player

        await temp_lms.close()

        # Create service with final config
        service = AlbumArtService(config)

        await service.start()

    except asyncio.CancelledError:
        logger.info("Received shutdown signal")
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await temp_lms.close()


if __name__ == "__main__":
    asyncio.run(main())
    

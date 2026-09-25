#!/usr/bin/env python3
"""
Lyrion Media Server (LMS) JSON-RPC client.

Shared by the album art service and test_lms.py. Handles the
slim.request wire protocol, player discovery/selection, track status
polling and album art download.
"""

import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

import aiohttp
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=5)


class LMSMonitor:
    """Client/monitor for a Lyrion Media Server."""

    def __init__(self, host: str, port: int = 9000, player_id: str = ""):
        self.host = host
        self.port = port
        self.player_id = player_id
        self.current_track_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def send_command(self, command: str, params: Optional[list] = None,
                           player_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC command to LMS.

        player_id defaults to this monitor's configured player; pass ""
        explicitly for server-level commands (e.g. "players", "serverstatus").
        """
        if params is None:
            params = []
        if player_id is None:
            player_id = self.player_id

        payload = {
            "id": 1,
            "method": "slim.request",
            "params": [player_id, [command] + params],
        }

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.post(
                f"http://{self.host}:{self.port}/jsonrpc.js",
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", {})
                logger.error("LMS returned status %s", response.status)
                return None
        except aiohttp.ClientConnectorError:
            logger.error("Cannot connect to LMS at %s:%s", self.host, self.port)
            return None
        except Exception as e:
            logger.error("Error communicating with LMS: %s", e)
            return None

    async def get_players(self, count: int = 100) -> List[Dict[str, Any]]:
        """Return the list of connected players."""
        result = await self.send_command("players", ["0", str(count)], player_id="")
        if result and "players_loop" in result:
            return result["players_loop"]
        return []

    async def get_player_id(self) -> Optional[str]:
        """Get first available player if not specified."""
        players = await self.get_players(count=1)
        if players:
            player = players[0]
            player_id = player.get("playerid")
            logger.info("Found player: %s (%s)", player.get("name"), player_id)
            return player_id
        return None

    async def initialize(self) -> bool:
        """Initialize connection to LMS."""
        if not self.player_id:
            self.player_id = await self.get_player_id()
            if not self.player_id:
                logger.error("No LMS player found")
                return False
        return True

    async def select_player_interactive(self) -> Optional[str]:
        """Prompt the user to select from available players."""
        players = await self.get_players()

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
                    logger.info("Selected player: %s (%s)",
                                selected.get("name"), player_id)
                    return player_id
                print("Invalid selection. Try again.")
            except ValueError:
                print("Invalid input. Enter a number.")
            except KeyboardInterrupt:
                print("\nSelection cancelled.")
                raise

    async def get_current_track_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently playing track."""
        result = await self.send_command("status", ["-", "1", "tags:alcu"])
        if result and "playlist_loop" in result and len(result["playlist_loop"]) > 0:
            return result["playlist_loop"][0]
        return None

    async def get_album_art_url(self, track_info: Dict[str, Any]) -> Optional[str]:
        """Extract the album art URL from track info."""
        if "artwork_url" in track_info:
            return f"http://{self.host}:{self.port}/{track_info['artwork_url']}"
        if "coverid" in track_info:
            return f"http://{self.host}:{self.port}/music/{track_info['coverid']}/cover.jpg"
        return None

    async def download_album_art(self, url: str) -> Optional[Image.Image]:
        """Download and return album art as a PIL Image (RGB, no alpha)."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.error("Failed to download album art: status %s", response.status)
                    return None

                image = Image.open(BytesIO(await response.read()))

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

                logger.info("Downloaded album art: %s (%s)", image.size, image.mode)
                return image
        except Exception as e:
            logger.error("Error downloading album art: %s", e)
            return None

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

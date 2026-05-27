#!/usr/bin/env python3
"""
Test script to verify LMS connectivity and monitor track changes
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LMSTestClient:
    """Simple LMS test client"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _send_command(self, player_id: str, command: str, params: list = None) -> Optional[Dict[str, Any]]:
        """Send JSON-RPC command to LMS"""
        if params is None:
            params = []

        payload = {
            "id": 1,
            "method": "slim.request",
            "params": [player_id, [command] + params]
        }

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.post(
                f"{self.base_url}/jsonrpc.js",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result', {})
                else:
                    logger.error(f"LMS returned status {response.status}")
                    return None
        except aiohttp.ClientConnectorError:
            logger.error(f"Cannot connect to LMS at {self.base_url}")
            logger.error("Please check that LMS is running and the host/port are correct")
            return None
        except Exception as e:
            logger.error(f"Error communicating with LMS: {e}")
            return None

    async def test_connection(self) -> bool:
        """Test basic connection to LMS"""
        result = await self._send_command("", "serverstatus", ["0", "0"])
        return result is not None

    async def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get LMS server information"""
        return await self._send_command("", "serverstatus", ["0", "0"])

    async def get_players(self) -> List[Dict[str, Any]]:
        """Get list of all connected players"""
        result = await self._send_command("", "players", ["0", "999"])
        if result and "players_loop" in result:
            return result["players_loop"]
        return []

    async def get_player_status(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a specific player"""
        return await self._send_command(player_id, "status", ["-", "1", "tags:aAlbumArtistcdDgiIjJKlLmMnNoOpPqrRsStTuUvwxXyY"])

    async def get_current_track(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get current track information"""
        status = await self.get_player_status(player_id)
        if status and "playlist_loop" in status and len(status["playlist_loop"]) > 0:
            track = status["playlist_loop"][0]
            # Add playback state info
            track["mode"] = status.get("mode", "stop")
            track["time"] = status.get("time", 0)
            track["duration"] = status.get("duration", 0)
            return track
        return None

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def display_server_info(info: Dict[str, Any]):
    """Display LMS server information"""
    print("\n" + "=" * 70)
    print("LMS SERVER INFORMATION")
    print("=" * 70)
    print(f"Version:        {info.get('version', 'Unknown')}")
    print(f"Players:        {info.get('player count', 0)} connected")
    print(f"Total albums:   {info.get('info total albums', 'Unknown')}")
    print(f"Total artists:  {info.get('info total artists', 'Unknown')}")
    print(f"Total songs:    {info.get('info total songs', 'Unknown')}")
    print("=" * 70)


def display_players(players: List[Dict[str, Any]]):
    """Display available players"""
    print("\n" + "=" * 70)
    print("AVAILABLE PLAYERS")
    print("=" * 70)
    if not players:
        print("No players found!")
    else:
        for i, player in enumerate(players, 1):
            print(f"\n{i}. {player.get('name', 'Unknown')}")
            print(f"   Player ID:  {player.get('playerid', 'Unknown')}")
            print(f"   Model:      {player.get('model', 'Unknown')}")
            print(f"   Connected:  {player.get('connected', 0) == 1}")
            print(f"   Power:      {'ON' if player.get('power', 0) == 1 else 'OFF'}")
    print("=" * 70)


def display_track_info(track: Dict[str, Any], is_update: bool = False):
    """Display current track information"""
    if not is_update:
        print("\n" + "=" * 70)
        print("NOW PLAYING")
        print("=" * 70)
    else:
        print("\n" + "─" * 70)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] TRACK CHANGED")
        print("─" * 70)

    # Playback state
    mode = track.get('mode', 'stop')
    mode_str = {
        'play': '▶ PLAYING',
        'pause': '⏸ PAUSED',
        'stop': '⏹ STOPPED'
    }.get(mode, mode.upper())

    print(f"\nStatus:         {mode_str}")

    # Track info
    title = track.get('title', 'Unknown')
    artist = track.get('artist', 'Unknown Artist')
    album = track.get('album', 'Unknown Album')

    print(f"Title:          {title}")
    print(f"Artist:         {artist}")
    print(f"Album:          {album}")

    # Additional metadata
    if 'year' in track:
        print(f"Year:           {track['year']}")
    if 'genre' in track:
        print(f"Genre:          {track['genre']}")
    if 'tracknum' in track:
        print(f"Track #:        {track['tracknum']}")

    # Duration
    duration = track.get('duration', 0)
    current_time = track.get('time', 0)
    if duration > 0:
        print(f"Duration:       {format_time(current_time)} / {format_time(duration)}")

    # Album art availability
    has_artwork = 'artwork_url' in track or 'coverid' in track
    print(f"Album art:      {'✓ Available' if has_artwork else '✗ Not available'}")

    if has_artwork and 'coverid' in track:
        print(f"Cover ID:       {track['coverid']}")

    print("=" * 70)


async def monitor_playback(client: LMSTestClient, player_id: str, interval: float = 1.0):
    """Monitor playback and display track changes"""
    print("\n" + "=" * 70)
    print("MONITORING PLAYBACK")
    print("=" * 70)
    print(f"Checking for changes every {interval} second(s)")
    print("Press Ctrl+C to stop")
    print("=" * 70)

    current_track_id = None
    last_mode = None

    while True:
        try:
            track = await client.get_current_track(player_id)

            if track:
                track_id = track.get('id')
                mode = track.get('mode', 'stop')

                # Check if track changed or playback state changed
                if track_id != current_track_id:
                    current_track_id = track_id
                    display_track_info(track, is_update=(last_mode is not None))
                elif mode != last_mode and last_mode is not None:
                    # Playback state changed (play/pause/stop)
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Playback state: {mode.upper()}")

                last_mode = mode
            else:
                if current_track_id is not None:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] No track playing")
                    current_track_id = None
                    last_mode = None

            await asyncio.sleep(interval)

        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"Error during monitoring: {e}")
            await asyncio.sleep(interval)


async def interactive_player_selection(players: List[Dict[str, Any]]) -> Optional[str]:
    """Let user select a player"""
    if not players:
        return None

    if len(players) == 1:
        player = players[0]
        print(f"\nAuto-selecting the only available player: {player.get('name')}")
        return player.get('playerid')

    print("\nSelect a player to monitor:")
    for i, player in enumerate(players, 1):
        print(f"  {i}. {player.get('name')} ({player.get('model')})")

    while True:
        try:
            choice = input(f"\nEnter player number (1-{len(players)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(players):
                return players[idx].get('playerid')
            else:
                print(f"Please enter a number between 1 and {len(players)}")
        except ValueError:
            print("Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            return None


async def main():
    """Main test routine"""
    # Configuration - UPDATE THESE
    LMS_HOST = "192.168.2.78"
    LMS_PORT = 9000

    print("=" * 70)
    print("LMS CONNECTIVITY TEST")
    print("=" * 70)
    print(f"\nLMS Host: {LMS_HOST}")
    print(f"LMS Port: {LMS_PORT}")

    client = LMSTestClient(LMS_HOST, LMS_PORT)

    try:
        # Test 1: Basic connectivity
        print("\n[1/4] Testing LMS connection...")
        if not await client.test_connection():
            print("\n✗ FAILED: Cannot connect to LMS")
            print("\nTroubleshooting:")
            print("  1. Is LMS running?")
            print("  2. Is the host/port correct?")
            print(f"  3. Can you access http://{LMS_HOST}:{LMS_PORT} in a browser?")
            return

        print("✓ Connection successful!")

        # Test 2: Get server info
        print("\n[2/4] Retrieving server information...")
        server_info = await client.get_server_info()
        if server_info:
            display_server_info(server_info)
            print("✓ Server info retrieved!")
        else:
            print("✗ Could not retrieve server info")

        # Test 3: Get players
        print("\n[3/4] Discovering players...")
        players = await client.get_players()
        display_players(players)

        if not players:
            print("\n✗ No players found!")
            print("\nPlease ensure at least one player is connected to LMS")
            return

        print("✓ Players discovered!")

        # Test 4: Monitor playback
        print("\n[4/4] Setting up playback monitoring...")

        # Select player
        player_id = await interactive_player_selection(players)
        if not player_id:
            print("\nMonitoring cancelled")
            return

        # Start monitoring
        await monitor_playback(client, player_id, interval=1.0)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        await client.close()
        print("\n✓ Test completed")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
LMS to Pixoo64 Album Art Display Service
Monitors Lyrion Media Server for song changes and displays album art on Divoom Pixoo64
"""

import asyncio
import argparse
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass

from lms import LMSMonitor
from pixoo import PixooClient

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
        logger.info("New track: %s - %s",
                    track_info.get('artist', 'Unknown'),
                    track_info.get('title', 'Unknown'))

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
                logger.error("Error in monitoring loop: %s", e, exc_info=True)
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
        "-p",
        "--player-id",
        default=Config().lms_player_id,
        help=f"LMS player MAC address (default: {Config().lms_player_id})"
    )

    parser.add_argument(
        "-s",
        action="store_true",
        help="Select LMS player interactively"
    )

    parser.add_argument(
        "-l",
        "--list-players",
        action="store_true",
        help="List available LMS players and exit"
    )

    parser.add_argument(
        "-t",
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
            players = await temp_lms.get_players()

            if not players:
                print("No players found.")
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

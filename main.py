#!/usr/bin/env python3
"""
NASA Solar Image Downloader
Main entry point for the application.
"""

import sys
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from models import PlaybackState


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('nasa_downloader.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("NASA Solar Image Downloader starting...")
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    logger.info(f"Data directory: {data_dir.absolute()}")
    logger.info("Application setup complete")
    
    # TODO: Initialize and start components
    print("NASA Solar Image Downloader")
    print("Ready to download solar images from NASA SDO")
    print("Press Ctrl+C to exit")
    
    try:
        # Keep the application running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Application shutting down...")
        print("\nShutting down...")


if __name__ == "__main__":
    main()
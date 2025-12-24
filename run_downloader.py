#!/usr/bin/env python3
"""
NASA Solar Image Downloader - Full Application Runner
"""

import sys
import logging
import signal
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.downloader.url_generator import URLGenerator
from src.storage.storage_organizer import StorageOrganizer
from src.downloader.image_fetcher import ImageFetcher, DownloadManager
from src.scheduler.monitoring_loop import MonitoringLoop, TaskCoordinator, StatusReporter


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


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n🛑 Shutting down NASA Solar Image Downloader...")
    sys.exit(0)


def main():
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 NASA Solar Image Downloader")
    print("=" * 50)
    
    try:
        # Initialize components
        print("🔧 Initializing components...")
        url_generator = URLGenerator()
        storage = StorageOrganizer("data")
        fetcher = ImageFetcher(rate_limit_delay=1.0)  # Be respectful to NASA servers
        download_manager = DownloadManager(fetcher, storage)
        
        # Create monitoring loop (default 1 day, check every 5 minutes)
        monitoring = MonitoringLoop(
            url_generator, 
            download_manager, 
            storage,
            check_interval_minutes=5,
            monitoring_range_days=1  # Default 1 day
        )
        
        # Set up coordinator and reporter
        coordinator = TaskCoordinator(monitoring)
        reporter = StatusReporter(monitoring)
        
        print("✅ Components initialized successfully")
        
        # Show initial status
        print("\n📊 Initial Status:")
        reporter.print_status()
        
        # Ask user for configuration
        print("\n⚙️  Configuration Options:")
        print("1. Keep default (1 day monitoring)")
        print("2. Set custom monitoring range")
        
        try:
            choice = input("\nEnter choice (1-2, or press Enter for default): ").strip()
            
            if choice == "2":
                days = input("Enter number of days to monitor (1-30): ").strip()
                try:
                    days = int(days)
                    if 1 <= days <= 30:
                        monitoring.set_monitoring_range(days)
                        print(f"✅ Set monitoring range to {days} days")
                    else:
                        print("⚠️  Invalid range, using default (1 day)")
                except ValueError:
                    print("⚠️  Invalid input, using default (1 day)")
        except (EOFError, KeyboardInterrupt):
            print("\n🛑 Cancelled by user")
            return
        
        # Show final configuration
        print(f"\n🎯 Final Configuration:")
        status = monitoring.get_status()
        print(f"   • Monitoring range: {status['monitoring_range_days']} days")
        print(f"   • Check interval: {status['check_interval_minutes']} minutes")
        print(f"   • Data directory: {Path('data').absolute()}")
        
        # Start monitoring
        print(f"\n🚀 Starting monitoring loop...")
        print(f"   • Will check for new images every {status['check_interval_minutes']} minutes")
        print(f"   • Press Ctrl+C to stop")
        
        monitoring.start_monitoring()
        
        # Keep running and show periodic status
        import time
        last_status_time = time.time()
        
        while True:
            time.sleep(10)  # Check every 10 seconds
            
            # Show status every 2 minutes
            if time.time() - last_status_time > 120:
                print(f"\n📊 Status Update ({datetime.now().strftime('%H:%M:%S')}):")
                current_status = monitoring.get_status()
                print(f"   • Total checks: {current_status['total_checks']}")
                print(f"   • New images found: {current_status['new_images_found']}")
                print(f"   • Total downloads: {current_status['total_downloads']}")
                if current_status['failed_downloads'] > 0:
                    print(f"   • Failed downloads: {current_status['failed_downloads']}")
                last_status_time = time.time()
    
    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down...")
        if 'monitoring' in locals():
            monitoring.stop_monitoring()
        print("👋 Goodbye!")
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
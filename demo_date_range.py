#!/usr/bin/env python3
"""
Demo script showing the configurable date range functionality.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.downloader.url_generator import URLGenerator
from src.scheduler.monitoring_loop import MonitoringLoop
from src.storage.storage_organizer import StorageOrganizer
from src.downloader.image_fetcher import ImageFetcher, DownloadManager


def demo_date_range_configuration():
    """Demonstrate the configurable date range functionality."""
    print("🚀 NASA Solar Image Downloader - Date Range Configuration Demo")
    print("=" * 60)
    
    # Initialize components
    url_gen = URLGenerator()
    storage = StorageOrganizer("demo_data")
    fetcher = ImageFetcher(rate_limit_delay=1.0)
    manager = DownloadManager(fetcher, storage)
    
    print("✅ Components initialized")
    
    # Test different date ranges
    end_date = datetime.now()
    
    print(f"\n📅 Testing different date ranges (end date: {end_date.strftime('%Y-%m-%d')})")
    print("-" * 60)
    
    # Test 1 day (new default)
    urls_1_day = url_gen.generate_default_urls(end_date)
    print(f"📊 Default (1 day):  {len(urls_1_day):4d} URLs")
    
    # Test custom ranges
    for days in [1, 3, 7, 14, 30]:
        urls = url_gen.generate_date_range_urls(days, end_date)
        print(f"📊 {days:2d} day{'s' if days > 1 else ' '}:       {len(urls):4d} URLs")
    
    # Test monitoring loop configuration
    print(f"\n🔄 Monitoring Loop Configuration")
    print("-" * 60)
    
    # Create monitoring loop with default 1 day
    monitoring = MonitoringLoop(url_gen, manager, storage, 
                               check_interval_minutes=5, 
                               monitoring_range_days=1)  # Default 1 day
    
    print(f"📊 Initial monitoring range: {monitoring.get_monitoring_range()} day(s)")
    
    # Test changing the range
    for days in [1, 3, 7, 30]:
        monitoring.set_monitoring_range(days)
        status = monitoring.get_status()
        print(f"📊 Set to {days:2d} day{'s' if days > 1 else ' '}:           {status['monitoring_range_days']} day(s)")
    
    # Show status report
    print(f"\n📋 Status Report")
    print("-" * 60)
    
    from src.scheduler.monitoring_loop import StatusReporter
    reporter = StatusReporter(monitoring)
    reporter.print_status()
    
    print(f"\n💡 Key Changes:")
    print(f"   • Default date range changed from 30 days to 1 day")
    print(f"   • Date range is now user-configurable via set_monitoring_range()")
    print(f"   • URL generation supports custom date ranges")
    print(f"   • Status reports show current monitoring range")
    
    print(f"\n🎯 Usage Examples:")
    print(f"   • monitoring.set_monitoring_range(1)   # Check last 1 day")
    print(f"   • monitoring.set_monitoring_range(7)   # Check last 7 days")
    print(f"   • monitoring.set_monitoring_range(30)  # Check last 30 days")
    
    print(f"\n✨ This makes the system more efficient by default (1 day)")
    print(f"   while still allowing users to configure longer ranges as needed!")


if __name__ == "__main__":
    try:
        demo_date_range_configuration()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
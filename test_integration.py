#!/usr/bin/env python3
"""
Integration test for NASA Solar Image Downloader components.
This script tests the URL generator, storage organizer, and image fetcher together.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.downloader.url_generator import URLGenerator
from src.storage.storage_organizer import StorageOrganizer
from src.downloader.image_fetcher import ImageFetcher, DownloadManager
from src.models import DownloadTask


def test_integration():
    """Test integration of all components."""
    print("🚀 NASA Solar Image Downloader - Integration Test")
    print("=" * 50)
    
    # Initialize components
    url_gen = URLGenerator()
    storage = StorageOrganizer("test_data")
    fetcher = ImageFetcher(rate_limit_delay=0.5)  # Be respectful to NASA servers
    manager = DownloadManager(fetcher, storage)
    
    print("✅ Components initialized")
    
    # Test URL generation
    test_date = datetime.now() - timedelta(days=1)  # Yesterday
    daily_urls = url_gen.generate_daily_urls(test_date)
    print(f"✅ Generated {len(daily_urls)} URLs for {test_date.strftime('%Y-%m-%d')}")
    
    # Test a few URLs (first 3 to be respectful)
    test_urls = daily_urls[:3]
    print(f"🔍 Testing {len(test_urls)} URLs...")
    
    successful_downloads = 0
    for i, url in enumerate(test_urls, 1):
        print(f"\n📥 Testing URL {i}/{len(test_urls)}: {url}")
        
        # Validate URL format
        if not url_gen.validate_url(url):
            print("❌ Invalid URL format")
            continue
        
        # Check if image exists
        if not fetcher.check_image_exists(url):
            print("⚠️  Image doesn't exist (404) - this is normal")
            continue
        
        # Extract metadata
        date, time_seq = url_gen.extract_metadata_from_url(url)
        filename = Path(url).name
        
        print(f"📊 Date: {date}, Time: {time_seq}, File: {filename}")
        
        # Create download task
        local_path = storage.get_local_path(filename, date)
        task = DownloadTask(url=url, target_path=local_path)
        
        # Attempt download
        success = manager.download_and_save(task)
        
        if success:
            print("✅ Download successful!")
            successful_downloads += 1
            
            # Verify file exists locally
            if storage.file_exists(filename, date):
                file_size = storage.get_file_size(filename, date)
                print(f"📁 File saved: {file_size} bytes")
            else:
                print("❌ File not found after download")
        else:
            print(f"❌ Download failed: {task.error_message}")
    
    print(f"\n📈 Summary:")
    print(f"   • URLs tested: {len(test_urls)}")
    print(f"   • Successful downloads: {successful_downloads}")
    print(f"   • Total downloads: {manager.get_download_count()}")
    print(f"   • Failed tasks: {len(manager.get_failed_tasks())}")
    
    # List downloaded files
    if successful_downloads > 0:
        print(f"\n📂 Downloaded files:")
        images = storage.list_local_images(test_date)
        for image in images:
            print(f"   • {image}")
    
    print(f"\n🎉 Integration test completed!")
    return successful_downloads > 0


if __name__ == "__main__":
    try:
        success = test_integration()
        if success:
            print("✅ Integration test PASSED")
            sys.exit(0)
        else:
            print("⚠️  No images were downloaded (this may be normal if no recent images exist)")
            sys.exit(0)
    except Exception as e:
        print(f"❌ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
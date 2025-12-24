#!/usr/bin/env python3
"""
NASA Solar Image Downloader - One-time Download Script
Downloads images from today only (no continuous monitoring)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.downloader.url_generator import URLGenerator
from src.storage.storage_organizer import StorageOrganizer
from src.downloader.image_fetcher import ImageFetcher, DownloadManager
from src.models import DownloadTask


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def main():
    """Download images from today only."""
    setup_logging()
    
    print("📥 NASA Solar Image Downloader - Today's Images")
    print("=" * 50)
    
    try:
        # Initialize components
        print("🔧 Initializing components...")
        url_generator = URLGenerator()
        storage = StorageOrganizer("data")
        fetcher = ImageFetcher(rate_limit_delay=1.0)
        download_manager = DownloadManager(fetcher, storage)
        
        print("✅ Components initialized")
        
        # Generate URLs for today
        print("🔗 Generating URLs for today...")
        today_urls = url_generator.generate_default_urls()  # Default 1 day
        print(f"📊 Generated {len(today_urls)} URLs to check")
        
        # Filter to only new images
        print("🔍 Checking which images are new...")
        new_urls = []
        
        for url in today_urls:
            # Extract metadata
            date, time_seq = url_generator.extract_metadata_from_url(url)
            if not date or not time_seq:
                continue
            
            filename = url.split('/')[-1]
            
            # Check if already exists
            if not storage.file_exists(filename, date):
                # Quick check if image exists on NASA server
                if fetcher.check_image_exists(url):
                    new_urls.append(url)
        
        print(f"📊 Found {len(new_urls)} new images to download")
        
        if not new_urls:
            print("✅ No new images found. All up to date!")
            return
        
        # Download new images
        print(f"📥 Downloading {len(new_urls)} images...")
        successful = 0
        failed = 0
        
        for i, url in enumerate(new_urls, 1):
            print(f"📥 [{i}/{len(new_urls)}] Downloading: {url.split('/')[-1]}")
            
            # Extract metadata
            date, time_seq = url_generator.extract_metadata_from_url(url)
            filename = url.split('/')[-1]
            local_path = storage.get_local_path(filename, date)
            
            # Create download task
            task = DownloadTask(url=url, target_path=local_path)
            
            # Download
            success = download_manager.download_and_save(task)
            
            if success:
                successful += 1
                print(f"   ✅ Success")
            else:
                failed += 1
                print(f"   ❌ Failed: {task.error_message}")
        
        # Summary
        print(f"\n📊 Download Summary:")
        print(f"   • Total attempted: {len(new_urls)}")
        print(f"   • Successful: {successful}")
        print(f"   • Failed: {failed}")
        print(f"   • Success rate: {successful/len(new_urls)*100:.1f}%")
        
        if successful > 0:
            print(f"\n📁 Images saved to: {Path('data').absolute()}")
            
            # Show some downloaded files
            today = datetime.now()
            images = storage.list_local_images(today)
            if images:
                print(f"📋 Downloaded files:")
                for image in images[:5]:  # Show first 5
                    print(f"   • {image}")
                if len(images) > 5:
                    print(f"   ... and {len(images) - 5} more")
    
    except KeyboardInterrupt:
        print(f"\n🛑 Cancelled by user")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
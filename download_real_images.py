#!/usr/bin/env python3
"""
NASA Solar Image Downloader - Real Images from Directory Scraping
This script scrapes NASA directory pages to find actual available images.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.downloader.directory_scraper import DirectoryScraper
from src.storage.storage_organizer import StorageOrganizer
from src.downloader.image_fetcher import ImageFetcher, DownloadManager


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
    """Download real images by scraping NASA directories."""
    setup_logging()
    
    print("🔍 NASA Solar Image Downloader - Real Images")
    print("=" * 50)
    print("This script scrapes NASA directory pages to find actual available images")
    print()
    
    try:
        # Initialize components
        print("🔧 Initializing components...")
        scraper = DirectoryScraper(rate_limit_delay=1.0)
        storage = StorageOrganizer("data")
        fetcher = ImageFetcher(rate_limit_delay=1.0)
        download_manager = DownloadManager(fetcher, storage)
        
        print("✅ Components initialized")
        
        # Ask user for date range
        print("\n📅 Date Range Selection:")
        print("1. Today only")
        print("2. Last 3 days")
        print("3. Last 7 days")
        print("4. Custom date")
        
        choice = input("\nEnter choice (1-4, or press Enter for today): ").strip()
        
        today = datetime.now()
        
        if choice == "2":
            start_date = today - timedelta(days=2)
            end_date = today
            print(f"📊 Selected: Last 3 days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        elif choice == "3":
            start_date = today - timedelta(days=6)
            end_date = today
            print(f"📊 Selected: Last 7 days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        elif choice == "4":
            try:
                date_str = input("Enter date (YYYY-MM-DD): ").strip()
                custom_date = datetime.strptime(date_str, "%Y-%m-%d")
                start_date = end_date = custom_date
                print(f"📊 Selected: {custom_date.strftime('%Y-%m-%d')}")
            except ValueError:
                print("⚠️  Invalid date format, using today")
                start_date = end_date = today
        else:
            start_date = end_date = today
            print(f"📊 Selected: Today ({today.strftime('%Y-%m-%d')})")
        
        # Scrape directories to find available images
        print(f"\n🔍 Scraping NASA directories...")
        available_images = scraper.get_available_images_for_date_range(start_date, end_date)
        
        print(f"📊 Found {len(available_images)} total images available")
        
        if not available_images:
            print("❌ No images found for the selected date range")
            print("💡 This could mean:")
            print("   • No images were taken on these dates")
            print("   • The directory doesn't exist yet")
            print("   • Network issues accessing NASA servers")
            return
        
        # Show some examples
        print(f"\n📋 Sample available images:")
        for date, filename in available_images[:5]:
            print(f"   • {date.strftime('%Y-%m-%d')}: {filename}")
        if len(available_images) > 5:
            print(f"   ... and {len(available_images) - 5} more")
        
        # Filter to new images only
        print(f"\n🔍 Checking which images are new...")
        new_images = scraper.filter_new_images(available_images, storage)
        
        if not new_images:
            print("✅ All images are already downloaded! Nothing to do.")
            return
        
        print(f"📊 Found {len(new_images)} new images to download")
        
        # Ask for confirmation
        proceed = input(f"\n❓ Download {len(new_images)} images? (y/N): ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("🛑 Download cancelled")
            return
        
        # Create download tasks
        print(f"\n📥 Creating download tasks...")
        tasks = scraper.create_download_tasks(new_images, storage)
        
        # Download images
        print(f"📥 Downloading {len(tasks)} images...")
        successful = 0
        failed = 0
        
        for i, task in enumerate(tasks, 1):
            filename = task.target_path.name
            print(f"📥 [{i}/{len(tasks)}] {filename}")
            
            success = download_manager.download_and_save(task)
            
            if success:
                successful += 1
                print(f"   ✅ Success")
            else:
                failed += 1
                print(f"   ❌ Failed: {task.error_message}")
        
        # Summary
        print(f"\n📊 Download Summary:")
        print(f"   • Total available: {len(available_images)}")
        print(f"   • New images: {len(new_images)}")
        print(f"   • Successfully downloaded: {successful}")
        print(f"   • Failed: {failed}")
        if len(new_images) > 0:
            print(f"   • Success rate: {successful/len(new_images)*100:.1f}%")
        
        if successful > 0:
            print(f"\n📁 Images saved to: {Path('data').absolute()}")
            
            # Show directory structure
            print(f"📂 Directory structure:")
            current_date = start_date
            while current_date <= end_date:
                images = storage.list_local_images(current_date)
                if images:
                    print(f"   📅 {current_date.strftime('%Y-%m-%d')}: {len(images)} images")
                current_date += timedelta(days=1)
    
    except KeyboardInterrupt:
        print(f"\n🛑 Cancelled by user")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
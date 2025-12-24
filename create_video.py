#!/usr/bin/env python3
"""
NASA Solar Image Video Creator
Creates MP4 videos from downloaded NASA solar images using ffmpeg.
"""

import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.storage.storage_organizer import StorageOrganizer


def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_available_dates(storage: StorageOrganizer) -> list:
    """Get list of dates that have downloaded images."""
    data_dir = storage.base_data_dir
    available_dates = []
    
    if not data_dir.exists():
        return available_dates
    
    # Look for year/month/day structure
    for year_dir in data_dir.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            
            for day_dir in month_dir.iterdir():
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue
                
                # Check if this directory has images
                images = list(day_dir.glob("*_4096_0211.jpg"))
                if images:
                    try:
                        date = datetime(int(year_dir.name), int(month_dir.name), int(day_dir.name))
                        available_dates.append((date, len(images)))
                    except ValueError:
                        continue
    
    return sorted(available_dates)


def create_video_for_date(storage: StorageOrganizer, date: datetime, 
                         output_path: Path, fps: int = 10) -> bool:
    """
    Create MP4 video for a specific date.
    
    Args:
        storage: StorageOrganizer instance
        date: Date to create video for
        output_path: Output MP4 file path
        fps: Frames per second for the video
        
    Returns:
        True if successful, False otherwise
    """
    # Get images for this date
    images = storage.list_local_images(date)
    
    if not images:
        print(f"❌ No images found for {date.strftime('%Y-%m-%d')}")
        return False
    
    print(f"📊 Found {len(images)} images for {date.strftime('%Y-%m-%d')}")
    
    # Get the directory path
    date_dir = storage.get_date_path(date)
    
    # Create temporary symlinks with sequential names for ffmpeg
    temp_dir = Path("temp_video_frames")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        print("🔗 Creating temporary frame links...")
        
        # Sort images by filename (which includes timestamp)
        sorted_images = sorted(images)
        
        # Create symlinks with sequential names
        for i, image in enumerate(sorted_images):
            src_path = date_dir / image
            temp_path = temp_dir / f"frame_{i:06d}.jpg"
            
            # Remove existing symlink if it exists
            if temp_path.exists():
                temp_path.unlink()
            
            # Create symlink (or copy on Windows if symlink fails)
            try:
                temp_path.symlink_to(src_path.absolute())
            except OSError:
                # Fallback to copy on Windows
                shutil.copy2(src_path, temp_path)
        
        print(f"✅ Created {len(sorted_images)} frame links")
        
        # Build ffmpeg command
        input_pattern = str(temp_dir / "frame_%06d.jpg")
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-framerate', str(fps),
            '-i', input_pattern,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-crf', '18',  # High quality
            str(output_path)
        ]
        
        print(f"🎬 Creating video: {output_path}")
        print(f"   • Input: {len(sorted_images)} frames")
        print(f"   • FPS: {fps}")
        print(f"   • Duration: ~{len(sorted_images)/fps:.1f} seconds")
        
        # Run ffmpeg
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Video created successfully!")
            
            # Get video file size
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"📁 File size: {size_mb:.1f} MB")
            
            return True
        else:
            print(f"❌ FFmpeg error:")
            print(result.stderr)
            return False
    
    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def main():
    """Main video creation interface."""
    print("🎬 NASA Solar Image Video Creator")
    print("=" * 50)
    
    # Check if ffmpeg is available
    if not check_ffmpeg():
        print("❌ FFmpeg not found!")
        print("💡 Please install FFmpeg:")
        print("   • Windows: Download from https://ffmpeg.org/download.html")
        print("   • Or use: winget install FFmpeg")
        print("   • Or use: choco install ffmpeg")
        return
    
    print("✅ FFmpeg found")
    
    # Initialize storage
    storage = StorageOrganizer("data")
    
    # Get available dates
    print("\n📅 Scanning for downloaded images...")
    available_dates = get_available_dates(storage)
    
    if not available_dates:
        print("❌ No downloaded images found!")
        print("💡 Run 'python download_real_images.py' first to download some images")
        return
    
    print(f"📊 Found images for {len(available_dates)} dates:")
    for i, (date, count) in enumerate(available_dates, 1):
        print(f"   {i}. {date.strftime('%Y-%m-%d')}: {count} images")
    
    # Let user choose date
    print(f"\n🎯 Video Creation Options:")
    print(f"1. Create video for specific date")
    print(f"2. Create video for date range")
    print(f"3. Create video for all dates")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        # Single date
        try:
            date_choice = int(input(f"Enter date number (1-{len(available_dates)}): "))
            if 1 <= date_choice <= len(available_dates):
                selected_date, image_count = available_dates[date_choice - 1]
                
                # Get FPS
                fps = input("Enter FPS (default 10): ").strip()
                fps = int(fps) if fps.isdigit() else 10
                
                # Create output filename
                output_file = f"nasa_solar_{selected_date.strftime('%Y%m%d')}.mp4"
                output_path = Path(output_file)
                
                success = create_video_for_date(storage, selected_date, output_path, fps)
                
                if success:
                    print(f"\n🎉 Video created: {output_path.absolute()}")
            else:
                print("❌ Invalid date number")
        except ValueError:
            print("❌ Invalid input")
    
    elif choice == "2":
        print("📅 Date range videos not implemented yet")
        print("💡 For now, create individual videos and combine them manually")
    
    elif choice == "3":
        # All dates
        fps = input("Enter FPS (default 10): ").strip()
        fps = int(fps) if fps.isdigit() else 10
        
        print(f"\n🎬 Creating videos for all {len(available_dates)} dates...")
        
        successful = 0
        for date, image_count in available_dates:
            output_file = f"nasa_solar_{date.strftime('%Y%m%d')}.mp4"
            output_path = Path(output_file)
            
            print(f"\n📅 Processing {date.strftime('%Y-%m-%d')}...")
            
            if create_video_for_date(storage, date, output_path, fps):
                successful += 1
        
        print(f"\n📊 Summary: {successful}/{len(available_dates)} videos created successfully")
    
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n🛑 Cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
"""Local storage and file organization for NASA solar images."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

from ..models import ImageMetadata


class StorageOrganizer:
    """Manages local storage and organization of NASA solar images."""
    
    def __init__(self, base_data_dir: str = "data", resolution: str = "1024", solar_filter: str = "0211"):
        """
        Initialize storage organizer.
        
        Args:
            base_data_dir: Base directory for storing images
            resolution: Image resolution (1024, 2048, or 4096)
            solar_filter: Solar filter number (0193, 0304, 0171, 0211, 0131, 0335, 0094, 1600, 1700)
        """
        self.base_data_dir = Path(base_data_dir)
        self.resolution = resolution
        self.solar_filter = solar_filter
        self.logger = logging.getLogger(__name__)
        
        # Create base directory if it doesn't exist
        self.base_data_dir.mkdir(exist_ok=True)
    
    def update_file_pattern(self, resolution: str, solar_filter: str):
        """
        Update the resolution and solar filter settings.
        
        Args:
            resolution: Image resolution (1024, 2048, or 4096)
            solar_filter: Solar filter number (0193, 0304, 0171, 0211, 0131, 0335, 0094, 1600, 1700)
        """
        self.resolution = resolution
        self.solar_filter = solar_filter
    
    def get_date_path(self, date: datetime) -> Path:
        """
        Get the date-based folder path for a given date.
        
        Args:
            date: Date to get path for
            
        Returns:
            Path following data/YYYY/MM/DD/ structure
        """
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        
        return self.base_data_dir / year / month / day
    
    def create_date_structure(self, date: datetime) -> Path:
        """
        Create the date-based folder structure if it doesn't exist.
        
        Args:
            date: Date to create structure for
            
        Returns:
            Path to the created directory
        """
        date_path = self.get_date_path(date)
        date_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(f"Created directory structure: {date_path}")
        return date_path
    
    def get_local_path(self, filename: str, date: datetime) -> Path:
        """
        Get the complete local path for a file.
        
        Args:
            filename: Original NASA filename
            date: Date of the image
            
        Returns:
            Complete local path for the file
        """
        date_path = self.get_date_path(date)
        return date_path / filename
    
    def file_exists(self, filename: str, date: datetime) -> bool:
        """
        Check if a file already exists locally.
        
        Args:
            filename: Original NASA filename
            date: Date of the image
            
        Returns:
            True if file exists, False otherwise
        """
        local_path = self.get_local_path(filename, date)
        return local_path.exists()
    
    def get_file_size(self, filename: str, date: datetime) -> Optional[int]:
        """
        Get the size of a local file.
        
        Args:
            filename: Original NASA filename
            date: Date of the image
            
        Returns:
            File size in bytes, or None if file doesn't exist
        """
        local_path = self.get_local_path(filename, date)
        
        if local_path.exists():
            return local_path.stat().st_size
        return None
    
    def save_image(self, image_data: bytes, filename: str, date: datetime) -> Path:
        """
        Save image data to the appropriate local path.
        
        Args:
            image_data: Raw image data
            filename: Original NASA filename (preserved)
            date: Date of the image
            
        Returns:
            Path where the file was saved
        """
        # Create directory structure
        date_path = self.create_date_structure(date)
        local_path = date_path / filename
        
        # Write image data
        with open(local_path, 'wb') as f:
            f.write(image_data)
        
        self.logger.info(f"Saved image: {local_path}")
        return local_path
    
    def validate_file_integrity(self, filename: str, date: datetime, expected_size: int) -> bool:
        """
        Validate that a downloaded file has the expected size.
        
        Args:
            filename: Original NASA filename
            date: Date of the image
            expected_size: Expected file size in bytes
            
        Returns:
            True if file size matches expected size, False otherwise
        """
        actual_size = self.get_file_size(filename, date)
        
        if actual_size is None:
            self.logger.warning(f"File not found for integrity check: {filename}")
            return False
        
        if actual_size != expected_size:
            self.logger.warning(
                f"File size mismatch for {filename}: "
                f"expected {expected_size}, got {actual_size}"
            )
            return False
        
        return True
    
    def get_available_space(self) -> int:
        """
        Get available disk space in the data directory.
        
        Returns:
            Available space in bytes
        """
        stat = shutil.disk_usage(self.base_data_dir)
        return stat.free
    
    def check_sufficient_space(self, required_bytes: int) -> bool:
        """
        Check if there's sufficient disk space for downloads.
        
        Args:
            required_bytes: Required space in bytes
            
        Returns:
            True if sufficient space available, False otherwise
        """
        available = self.get_available_space()
        return available >= required_bytes
    
    def list_local_images(self, date: datetime) -> List[str]:
        """
        List all images stored locally for a given date.
        
        Args:
            date: Date to list images for
            
        Returns:
            List of filenames for the given date
        """
        date_path = self.get_date_path(date)
        
        if not date_path.exists():
            return []
        
        # Find all .jpg files with the NASA pattern using current filter settings
        images = []
        pattern = f"*_{self.resolution}_{self.solar_filter}.jpg"
        for file_path in date_path.glob(pattern):
            images.append(file_path.name)
        
        return sorted(images)
    
    def get_image_metadata(self, filename: str, date: datetime, url: str) -> Optional[ImageMetadata]:
        """
        Create ImageMetadata for a local file.
        
        Args:
            filename: Original NASA filename
            date: Date of the image
            url: Original URL
            
        Returns:
            ImageMetadata object or None if file doesn't exist
        """
        local_path = self.get_local_path(filename, date)
        
        if not local_path.exists():
            return None
        
        # Extract time sequence from filename
        # Format: YYYYMMDD_HHMMSS_4096_0211.jpg
        parts = filename.split('_')
        if len(parts) >= 2:
            time_sequence = parts[1]
        else:
            time_sequence = "000000"
        
        file_size = local_path.stat().st_size
        download_timestamp = datetime.fromtimestamp(local_path.stat().st_mtime)
        
        return ImageMetadata(
            date=date,
            time_sequence=time_sequence,
            filename=filename,
            local_path=local_path,
            file_size=file_size,
            download_timestamp=download_timestamp,
            url=url
        )
    
    def cleanup_corrupted_files(self, date: datetime) -> int:
        """
        Remove corrupted or zero-size files for a given date.
        
        Args:
            date: Date to clean up files for
            
        Returns:
            Number of files removed
        """
        date_path = self.get_date_path(date)
        
        if not date_path.exists():
            return 0
        
        removed_count = 0
        pattern = f"*_{self.resolution}_{self.solar_filter}.jpg"
        for file_path in date_path.glob(pattern):
            if file_path.stat().st_size == 0:
                file_path.unlink()
                removed_count += 1
                self.logger.info(f"Removed corrupted file: {file_path}")
        
        return removed_count
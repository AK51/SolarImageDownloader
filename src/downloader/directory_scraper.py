"""NASA SDO directory scraper to find actual available images."""

import re
import logging
from typing import List, Set
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

from ..models import DownloadTask


class DirectoryScraper:
    """Scrapes NASA SDO directory pages to find available images."""
    
    def __init__(self, rate_limit_delay: float = 1.0, resolution: str = "1024", solar_filter: str = "0211"):
        """
        Initialize directory scraper.
        
        Args:
            rate_limit_delay: Minimum delay between requests in seconds
            resolution: Image resolution (1024, 2048, or 4096)
            solar_filter: Solar filter number (0193, 0304, 0171, 0211, 0131, 0335, 0094, 1600, 1700)
        """
        self.rate_limit_delay = rate_limit_delay
        self.resolution = resolution
        self.solar_filter = solar_filter
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NASA-Solar-Image-Downloader/1.0'
        })
        
        # Pattern to match our target files with configurable resolution and filter
        self.file_pattern = re.compile(rf'(\d{{8}}_\d{{6}}_{resolution}_{solar_filter}\.jpg)')
    
    def update_filters(self, resolution: str, solar_filter: str):
        """
        Update the resolution and solar filter settings.
        
        Args:
            resolution: Image resolution (1024, 2048, or 4096)
            solar_filter: Solar filter number (0193, 0304, 0171, 0211, 0131, 0335, 0094, 1600, 1700)
        """
        self.resolution = resolution
        self.solar_filter = solar_filter
        self.file_pattern = re.compile(rf'(\d{{8}}_\d{{6}}_{resolution}_{solar_filter}\.jpg)')
    
    def get_directory_url(self, date: datetime) -> str:
        """
        Get the NASA directory URL for a specific date.
        
        Args:
            date: Date to get directory for
            
        Returns:
            NASA directory URL
        """
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        
        return f"https://sdo.gsfc.nasa.gov/assets/img/browse/{year}/{month}/{day}/"
    
    def scrape_directory(self, date: datetime) -> List[str]:
        """
        Scrape a NASA directory page to find available images.
        
        Args:
            date: Date to scrape directory for
            
        Returns:
            List of image filenames matching our pattern
        """
        directory_url = self.get_directory_url(date)
        
        try:
            self.logger.info(f"Scraping directory: {directory_url}")
            
            response = self.session.get(directory_url, timeout=30)
            
            if response.status_code == 404:
                self.logger.debug(f"Directory not found (404): {directory_url}")
                return []
            
            if response.status_code != 200:
                self.logger.warning(f"HTTP {response.status_code} for directory: {directory_url}")
                return []
            
            # Parse HTML to find image files
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links that match our pattern
            image_files = []
            
            # Look for links in the page
            for link in soup.find_all('a', href=True):
                href = link['href']
                match = self.file_pattern.search(href)
                if match:
                    filename = match.group(1)
                    image_files.append(filename)
            
            # Also check for direct text matches (some servers list files differently)
            page_text = response.text
            matches = self.file_pattern.findall(page_text)
            for match in matches:
                if match not in image_files:
                    image_files.append(match)
            
            self.logger.info(f"Found {len(image_files)} images in directory for {date.strftime('%Y-%m-%d')}")
            
            return sorted(image_files)  # Sort by filename (which includes timestamp)
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error scraping directory {directory_url}: {e}")
            return []
        
        except Exception as e:
            self.logger.error(f"Unexpected error scraping directory {directory_url}: {e}")
            return []
    
    def get_available_images_for_date_range(self, start_date: datetime, end_date: datetime) -> List[tuple]:
        """
        Get all available images for a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of tuples (date, filename) for all available images
        """
        all_images = []
        current_date = start_date
        
        while current_date <= end_date:
            filenames = self.scrape_directory(current_date)
            
            for filename in filenames:
                all_images.append((current_date, filename))
            
            current_date += timedelta(days=1)
            
            # Rate limiting between directory requests
            if current_date <= end_date:
                import time
                time.sleep(self.rate_limit_delay)
        
        return all_images
    
    def get_image_url(self, date: datetime, filename: str) -> str:
        """
        Construct the full URL for an image.
        
        Args:
            date: Date of the image
            filename: Image filename
            
        Returns:
            Complete image URL
        """
        directory_url = self.get_directory_url(date)
        return directory_url + filename
    
    def filter_new_images(self, available_images: List[tuple], storage_organizer) -> List[tuple]:
        """
        Filter available images to only include ones not already downloaded.
        
        Args:
            available_images: List of (date, filename) tuples
            storage_organizer: StorageOrganizer instance to check existing files
            
        Returns:
            List of (date, filename) tuples for images not yet downloaded
        """
        new_images = []
        
        for date, filename in available_images:
            if not storage_organizer.file_exists(filename, date):
                new_images.append((date, filename))
        
        self.logger.info(f"Filtered to {len(new_images)} new images out of {len(available_images)} available")
        
        return new_images
    
    def create_download_tasks(self, new_images: List[tuple], storage_organizer) -> List[DownloadTask]:
        """
        Create download tasks for new images.
        
        Args:
            new_images: List of (date, filename) tuples
            storage_organizer: StorageOrganizer instance
            
        Returns:
            List of DownloadTask objects
        """
        tasks = []
        
        for date, filename in new_images:
            url = self.get_image_url(date, filename)
            local_path = storage_organizer.get_local_path(filename, date)
            
            task = DownloadTask(url=url, target_path=local_path)
            tasks.append(task)
        
        return tasks
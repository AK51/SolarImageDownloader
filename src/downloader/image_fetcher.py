"""HTTP downloader for NASA solar images with error handling."""

import time
import logging
from typing import Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models import DownloadTask, TaskStatus


class ImageFetcher:
    """Downloads NASA solar images with robust error handling."""
    
    def __init__(self, rate_limit_delay: float = 1.0, max_retries: int = 5):
        """
        Initialize image fetcher.
        
        Args:
            rate_limit_delay: Minimum delay between requests in seconds
            max_retries: Maximum number of retry attempts
        """
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.last_request_time = 0.0
        
        # Configure session with retry strategy
        self.session = requests.Session()
        
        # Set up retry strategy for connection issues
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # Will be overridden by exponential backoff
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set user agent to be respectful
        self.session.headers.update({
            'User-Agent': 'NASA-Solar-Image-Downloader/1.0'
        })
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _exponential_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        return min(2 ** attempt, 60)  # Cap at 60 seconds
    
    def download_image(self, url: str) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Download an image from the given URL with retry logic.
        
        Args:
            url: URL to download from
            
        Returns:
            Tuple of (success, image_data, error_message)
        """
        self._enforce_rate_limit()
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Downloading {url} (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    self.logger.info(f"Successfully downloaded: {url}")
                    return True, response.content, None
                
                elif response.status_code == 404:
                    # Image doesn't exist - not an error to retry
                    self.logger.debug(f"Image not found (404): {url}")
                    return False, None, f"Image not found (404): {url}"
                
                else:
                    # Other HTTP errors - log and potentially retry
                    error_msg = f"HTTP {response.status_code}: {url}"
                    self.logger.warning(error_msg)
                    
                    if attempt < self.max_retries - 1:
                        delay = self._exponential_backoff(attempt)
                        self.logger.info(f"Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    
                    return False, None, error_msg
            
            except requests.exceptions.Timeout:
                error_msg = f"Timeout downloading: {url}"
                self.logger.warning(error_msg)
                
                if attempt < self.max_retries - 1:
                    delay = self._exponential_backoff(attempt)
                    self.logger.info(f"Retrying after timeout in {delay}s...")
                    time.sleep(delay)
                    continue
                
                return False, None, error_msg
            
            except requests.exceptions.ConnectionError:
                error_msg = f"Connection error downloading: {url}"
                self.logger.warning(error_msg)
                
                if attempt < self.max_retries - 1:
                    delay = self._exponential_backoff(attempt)
                    self.logger.info(f"Retrying after connection error in {delay}s...")
                    time.sleep(delay)
                    continue
                
                return False, None, error_msg
            
            except Exception as e:
                error_msg = f"Unexpected error downloading {url}: {str(e)}"
                self.logger.error(error_msg)
                return False, None, error_msg
        
        return False, None, f"Max retries exceeded for: {url}"
    
    def check_image_exists(self, url: str) -> bool:
        """
        Check if an image exists without downloading it.
        
        Args:
            url: URL to check
            
        Returns:
            True if image exists, False otherwise
        """
        self._enforce_rate_limit()
        
        try:
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.debug(f"Error checking image existence {url}: {e}")
            return False
    
    def get_image_size(self, url: str) -> Optional[int]:
        """
        Get the size of an image without downloading it.
        
        Args:
            url: URL to check
            
        Returns:
            Image size in bytes, or None if unavailable
        """
        self._enforce_rate_limit()
        
        try:
            response = self.session.head(url, timeout=10)
            if response.status_code == 200:
                content_length = response.headers.get('content-length')
                if content_length:
                    return int(content_length)
        except Exception as e:
            self.logger.debug(f"Error getting image size {url}: {e}")
        
        return None


class DownloadManager:
    """Manages download tasks and coordinates with storage."""
    
    def __init__(self, fetcher: ImageFetcher, storage_organizer):
        """
        Initialize download manager.
        
        Args:
            fetcher: ImageFetcher instance
            storage_organizer: StorageOrganizer instance
        """
        self.fetcher = fetcher
        self.storage = storage_organizer
        self.logger = logging.getLogger(__name__)
        self.download_count = 0
        self.failed_tasks = []
    
    def download_and_save(self, task: DownloadTask) -> bool:
        """
        Download an image and save it to local storage.
        
        Args:
            task: DownloadTask to execute
            
        Returns:
            True if successful, False otherwise
        """
        task.status = TaskStatus.DOWNLOADING
        
        # Extract filename and date from target path
        filename = task.target_path.name
        date = task.target_path.parent.name  # This needs to be converted to datetime
        
        # For now, extract date from filename (YYYYMMDD format)
        try:
            from datetime import datetime
            date_str = filename.split('_')[0]  # Get YYYYMMDD part
            date = datetime.strptime(date_str, '%Y%m%d')
        except (ValueError, IndexError):
            task.status = TaskStatus.FAILED
            task.error_message = f"Could not parse date from filename: {filename}"
            self.logger.error(task.error_message)
            return False
        
        # Check if file already exists (duplicate detection)
        if self.storage.file_exists(filename, date):
            self.logger.info(f"File already exists, skipping: {filename}")
            task.status = TaskStatus.COMPLETED
            return True
        
        # Download the image
        success, image_data, error_msg = self.fetcher.download_image(task.url)
        
        if success and image_data:
            try:
                # Save to storage
                saved_path = self.storage.save_image(image_data, filename, date)
                
                # Verify file integrity
                expected_size = len(image_data)
                if self.storage.validate_file_integrity(filename, date, expected_size):
                    task.status = TaskStatus.COMPLETED
                    self.download_count += 1
                    self.logger.info(f"Successfully downloaded and saved: {filename}")
                    return True
                else:
                    task.status = TaskStatus.FAILED
                    task.error_message = "File integrity check failed"
                    self.logger.error(f"Integrity check failed for: {filename}")
                    return False
                    
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error_message = f"Error saving file: {str(e)}"
                self.logger.error(task.error_message)
                return False
        else:
            task.status = TaskStatus.FAILED
            task.error_message = error_msg or "Download failed"
            self.failed_tasks.append(task)
            self.logger.error(f"Download failed: {task.error_message}")
            return False
    
    def get_download_count(self) -> int:
        """Get the number of successfully downloaded images."""
        return self.download_count
    
    def get_failed_tasks(self) -> list:
        """Get list of failed download tasks."""
        return self.failed_tasks.copy()
    
    def reset_counters(self):
        """Reset download counters."""
        self.download_count = 0
        self.failed_tasks.clear()
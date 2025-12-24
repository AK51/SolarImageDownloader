"""Monitoring scheduler for NASA solar image downloads."""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable, List
import schedule

from ..downloader.url_generator import URLGenerator
from ..downloader.image_fetcher import DownloadManager
from ..storage.storage_organizer import StorageOrganizer
from ..models import DownloadTask


class MonitoringLoop:
    """Manages 5-minute monitoring cycles for new NASA images."""
    
    def __init__(self, url_generator: URLGenerator, download_manager: DownloadManager, 
                 storage_organizer: StorageOrganizer, check_interval_minutes: int = 5,
                 monitoring_range_days: int = 1):
        """
        Initialize monitoring loop.
        
        Args:
            url_generator: URLGenerator instance
            download_manager: DownloadManager instance
            storage_organizer: StorageOrganizer instance
            check_interval_minutes: Minutes between checks (default 5)
            monitoring_range_days: Days to look back for new images (default 1)
        """
        self.url_generator = url_generator
        self.download_manager = download_manager
        self.storage = storage_organizer
        self.check_interval = check_interval_minutes
        self.monitoring_range_days = monitoring_range_days
        self.logger = logging.getLogger(__name__)
        
        self.is_running = False
        self.monitoring_thread = None
        self.last_check_time = None
        self.total_checks = 0
        self.new_images_found = 0
        
        # Callbacks for status updates
        self.on_check_start: Optional[Callable] = None
        self.on_check_complete: Optional[Callable] = None
        self.on_new_images_found: Optional[Callable] = None
    
    def start_monitoring(self):
        """Start the monitoring loop in a background thread."""
        if self.is_running:
            self.logger.warning("Monitoring loop is already running")
            return
        
        self.is_running = True
        self.logger.info(f"Starting monitoring loop with {self.check_interval}-minute intervals")
        
        # Schedule the monitoring job
        schedule.every(self.check_interval).minutes.do(self._check_for_new_images)
        
        # Start the scheduler thread
        self.monitoring_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.monitoring_thread.start()
        
        # Run initial check immediately
        self._check_for_new_images()
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        if not self.is_running:
            self.logger.warning("Monitoring loop is not running")
            return
        
        self.is_running = False
        schedule.clear()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("Monitoring loop stopped")
    
    def _run_scheduler(self):
        """Run the scheduler in a background thread."""
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)  # Check every second
    
    def _check_for_new_images(self):
        """Check for new images and download them."""
        check_start_time = datetime.now()
        self.total_checks += 1
        
        self.logger.info(f"Starting monitoring check #{self.total_checks} at {check_start_time}")
        
        if self.on_check_start:
            self.on_check_start(check_start_time, self.total_checks)
        
        try:
            # Get URLs for recent images (configurable range)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.monitoring_range_days)
            
            recent_urls = []
            current_date = start_date
            while current_date <= end_date:
                daily_urls = self.url_generator.generate_daily_urls(current_date)
                recent_urls.extend(daily_urls)
                current_date += timedelta(days=1)
            
            self.logger.debug(f"Generated {len(recent_urls)} URLs to check (last {self.monitoring_range_days} days)")
            
            # Filter to only new images (not already downloaded)
            new_urls = self._filter_new_images(recent_urls)
            
            if new_urls:
                self.logger.info(f"Found {len(new_urls)} new images to download")
                self.new_images_found += len(new_urls)
                
                if self.on_new_images_found:
                    self.on_new_images_found(new_urls)
                
                # Download new images
                self._download_new_images(new_urls)
            else:
                self.logger.info("No new images found")
            
            self.last_check_time = check_start_time
            check_duration = (datetime.now() - check_start_time).total_seconds()
            
            self.logger.info(f"Monitoring check completed in {check_duration:.1f}s")
            
            if self.on_check_complete:
                self.on_check_complete(check_start_time, len(new_urls), check_duration)
        
        except Exception as e:
            self.logger.error(f"Error during monitoring check: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    def _filter_new_images(self, urls: List[str]) -> List[str]:
        """
        Filter URLs to only include images not already downloaded.
        
        Args:
            urls: List of URLs to check
            
        Returns:
            List of URLs for images not yet downloaded
        """
        new_urls = []
        
        for url in urls:
            # Extract metadata from URL
            date, time_seq = self.url_generator.extract_metadata_from_url(url)
            if not date or not time_seq:
                continue
            
            # Get filename
            filename = url.split('/')[-1]
            
            # Check if already exists locally
            if not self.storage.file_exists(filename, date):
                new_urls.append(url)
        
        return new_urls
    
    def _download_new_images(self, urls: List[str]):
        """
        Download a list of new images.
        
        Args:
            urls: List of URLs to download
        """
        successful_downloads = 0
        
        for url in urls:
            try:
                # Extract metadata
                date, time_seq = self.url_generator.extract_metadata_from_url(url)
                if not date or not time_seq:
                    self.logger.warning(f"Could not extract metadata from URL: {url}")
                    continue
                
                filename = url.split('/')[-1]
                local_path = self.storage.get_local_path(filename, date)
                
                # Create download task
                task = DownloadTask(url=url, target_path=local_path)
                
                # Attempt download
                success = self.download_manager.download_and_save(task)
                
                if success:
                    successful_downloads += 1
                    self.logger.info(f"Downloaded: {filename}")
                else:
                    self.logger.warning(f"Failed to download: {filename} - {task.error_message}")
            
            except Exception as e:
                self.logger.error(f"Error downloading {url}: {e}")
        
        self.logger.info(f"Downloaded {successful_downloads}/{len(urls)} new images")
    
    def get_status(self) -> dict:
        """
        Get current monitoring status.
        
        Returns:
            Dictionary with monitoring statistics
        """
        return {
            'is_running': self.is_running,
            'check_interval_minutes': self.check_interval,
            'monitoring_range_days': self.monitoring_range_days,
            'total_checks': self.total_checks,
            'last_check_time': self.last_check_time,
            'new_images_found': self.new_images_found,
            'total_downloads': self.download_manager.get_download_count(),
            'failed_downloads': len(self.download_manager.get_failed_tasks())
        }
    
    def force_check(self):
        """Force an immediate check for new images."""
        if not self.is_running:
            self.logger.warning("Cannot force check - monitoring loop is not running")
            return
        
        self.logger.info("Forcing immediate check for new images")
        self._check_for_new_images()
    
    def set_monitoring_range(self, days: int):
        """
        Set the monitoring range in days.
        
        Args:
            days: Number of days to look back for new images
        """
        if days < 1:
            raise ValueError("Monitoring range must be at least 1 day")
        
        old_range = self.monitoring_range_days
        self.monitoring_range_days = days
        self.logger.info(f"Changed monitoring range from {old_range} to {days} days")
    
    def get_monitoring_range(self) -> int:
        """
        Get the current monitoring range in days.
        
        Returns:
            Number of days being monitored
        """
        return self.monitoring_range_days
    
    def set_monitoring_range(self, days: int):
        """
        Set the monitoring range in days.
        
        Args:
            days: Number of days to look back for new images
        """
        if days < 1:
            raise ValueError("Monitoring range must be at least 1 day")
        
        old_range = self.monitoring_range_days
        self.monitoring_range_days = days
        self.logger.info(f"Monitoring range changed from {old_range} to {days} days")
    
    def get_monitoring_range(self) -> int:
        """
        Get the current monitoring range in days.
        
        Returns:
            Number of days being monitored
        """
        return self.monitoring_range_days


class TaskCoordinator:
    """Coordinates download tasks and UI updates."""
    
    def __init__(self, monitoring_loop: MonitoringLoop):
        """
        Initialize task coordinator.
        
        Args:
            monitoring_loop: MonitoringLoop instance to coordinate
        """
        self.monitoring_loop = monitoring_loop
        self.logger = logging.getLogger(__name__)
        
        # Set up callbacks
        self.monitoring_loop.on_check_start = self._on_check_start
        self.monitoring_loop.on_check_complete = self._on_check_complete
        self.monitoring_loop.on_new_images_found = self._on_new_images_found
    
    def _on_check_start(self, check_time: datetime, check_number: int):
        """Handle monitoring check start."""
        self.logger.info(f"Check #{check_number} started at {check_time.strftime('%H:%M:%S')}")
    
    def _on_check_complete(self, check_time: datetime, new_images: int, duration: float):
        """Handle monitoring check completion."""
        self.logger.info(f"Check completed: {new_images} new images, {duration:.1f}s duration")
    
    def _on_new_images_found(self, urls: List[str]):
        """Handle new images found."""
        self.logger.info(f"New images found: {len(urls)}")
        for url in urls[:5]:  # Log first 5 URLs
            filename = url.split('/')[-1]
            self.logger.debug(f"  - {filename}")
        if len(urls) > 5:
            self.logger.debug(f"  ... and {len(urls) - 5} more")


class StatusReporter:
    """Reports monitoring activity and download results."""
    
    def __init__(self, monitoring_loop: MonitoringLoop):
        """
        Initialize status reporter.
        
        Args:
            monitoring_loop: MonitoringLoop instance to report on
        """
        self.monitoring_loop = monitoring_loop
        self.logger = logging.getLogger(__name__)
    
    def print_status(self):
        """Print current monitoring status."""
        status = self.monitoring_loop.get_status()
        
        print("\n" + "="*50)
        print("NASA Solar Image Downloader - Status Report")
        print("="*50)
        print(f"Monitoring: {'Running' if status['is_running'] else 'Stopped'}")
        print(f"Check interval: {status['check_interval_minutes']} minutes")
        print(f"Monitoring range: {status['monitoring_range_days']} days")
        print(f"Total checks: {status['total_checks']}")
        
        if status['last_check_time']:
            last_check = status['last_check_time'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"Last check: {last_check}")
        
        print(f"New images found: {status['new_images_found']}")
        print(f"Total downloads: {status['total_downloads']}")
        print(f"Failed downloads: {status['failed_downloads']}")
        print("="*50)
    
    def log_periodic_status(self, interval_minutes: int = 30):
        """
        Log status periodically.
        
        Args:
            interval_minutes: Minutes between status logs
        """
        def log_status():
            status = self.monitoring_loop.get_status()
            self.logger.info(
                f"Status: {status['total_checks']} checks, "
                f"{status['new_images_found']} new images, "
                f"{status['total_downloads']} downloads"
            )
        
        schedule.every(interval_minutes).minutes.do(log_status)
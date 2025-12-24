"""NASA SDO URL generation and validation."""

import re
from datetime import datetime, timedelta
from typing import List, Tuple
from urllib.parse import urlparse


class URLGenerator:
    """Generates NASA SDO image URLs based on date and time patterns."""
    
    BASE_URL = "https://sdo.gsfc.nasa.gov/assets/img/browse"
    RESOLUTION = "4096"
    INSTRUMENT_CODE = "0211"
    
    def __init__(self):
        """Initialize URL generator."""
        self.url_pattern = re.compile(
            r"https://sdo\.gsfc\.nasa\.gov/assets/img/browse/"
            r"(\d{4})/(\d{2})/(\d{2})/"
            r"(\d{8})_(\d{6})_4096_0211\.jpg"
        )
    
    def generate_default_urls(self, end_date: datetime = None) -> List[str]:
        """
        Generate URLs for all potential images from the default range (1 day).
        
        Args:
            end_date: End date for the range (defaults to now)
            
        Returns:
            List of NASA SDO URLs for the default date range
        """
        return self.generate_date_range_urls(1, end_date)
    
    def generate_last_month_urls(self, end_date: datetime = None) -> List[str]:
        """
        Generate URLs for all potential images from the last 30 days.
        Kept for backward compatibility.
        
        Args:
            end_date: End date for the range (defaults to now)
            
        Returns:
            List of NASA SDO URLs for the last 30 days
        """
        return self.generate_date_range_urls(30, end_date)
    
    def generate_date_range_urls(self, days: int, end_date: datetime = None) -> List[str]:
        """
        Generate URLs for all potential images from the specified number of days.
        
        Args:
            days: Number of days to generate URLs for (1 means just the end_date)
            end_date: End date for the range (defaults to now)
            
        Returns:
            List of NASA SDO URLs for the specified date range
        """
        if end_date is None:
            end_date = datetime.now()
        
        # For days=1, we want just the end_date
        # For days=2, we want end_date and the day before, etc.
        start_date = end_date - timedelta(days=days-1)
        urls = []
        
        current_date = start_date
        while current_date <= end_date:
            daily_urls = self.generate_daily_urls(current_date)
            urls.extend(daily_urls)
            current_date += timedelta(days=1)
        
        return urls
    
    def generate_daily_urls(self, date: datetime) -> List[str]:
        """
        Generate URLs for potential images in a single day.
        
        NASA SDO images are taken at irregular intervals. We'll generate
        URLs for common time patterns based on observed data.
        
        Args:
            date: The date to generate URLs for
            
        Returns:
            List of URLs for the given date
        """
        urls = []
        
        # Generate URLs for various time intervals throughout the day
        # Based on NASA SDO patterns, images appear roughly every 12-15 minutes
        # but with irregular timing like 001959, 003959, etc.
        
        time_patterns = []
        
        # Generate times every ~12 minutes with some variation
        for hour in range(24):
            # Common minute patterns observed in NASA data
            minutes = [0, 12, 24, 36, 48]  # Every 12 minutes
            for minute in minutes:
                # Add some second variations (00, 30, 59 are common)
                for second in [0, 30, 59]:
                    time_sequence = f"{hour:02d}{minute:02d}{second:02d}"
                    time_patterns.append(time_sequence)
        
        # Create URLs for all time patterns
        for time_sequence in time_patterns:
            url = self.construct_url(date, time_sequence)
            urls.append(url)
        
        return urls
    
    def construct_url(self, date: datetime, time_sequence: str) -> str:
        """
        Construct a NASA SDO URL for a specific date and time.
        
        Args:
            date: The date of the image
            time_sequence: Time in HHMMSS format
            
        Returns:
            Complete NASA SDO URL
        """
        date_str = date.strftime("%Y%m%d")
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        
        filename = f"{date_str}_{time_sequence}_{self.RESOLUTION}_{self.INSTRUMENT_CODE}.jpg"
        
        url = f"{self.BASE_URL}/{year}/{month}/{day}/{filename}"
        return url
    
    def validate_url(self, url: str) -> bool:
        """
        Validate that a URL matches the expected NASA SDO format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid NASA SDO format, False otherwise
        """
        if not url:
            return False
        
        # Check if URL matches the expected pattern
        match = self.url_pattern.match(url)
        if not match:
            return False
        
        # Extract components and validate
        year, month, day, date_part, time_part = match.groups()
        
        # Validate date components
        try:
            # Check if date is valid
            datetime(int(year), int(month), int(day))
            
            # Check if date_part matches YYYYMMDD format
            expected_date = f"{year}{month}{day}"
            if date_part != expected_date:
                return False
            
            # Validate time format (HHMMSS)
            if len(time_part) != 6:
                return False
            
            hour = int(time_part[:2])
            minute = int(time_part[2:4])
            second = int(time_part[4:6])
            
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def extract_metadata_from_url(self, url: str) -> Tuple[datetime, str]:
        """
        Extract date and time sequence from a NASA SDO URL.
        
        Args:
            url: NASA SDO URL
            
        Returns:
            Tuple of (datetime, time_sequence) or (None, None) if invalid
        """
        match = self.url_pattern.match(url)
        if not match:
            return None, None
        
        year, month, day, date_part, time_part = match.groups()
        
        try:
            date = datetime(int(year), int(month), int(day))
            return date, time_part
        except (ValueError, TypeError):
            return None, None
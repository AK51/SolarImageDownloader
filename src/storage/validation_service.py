"""File integrity and validation service for NASA solar images."""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io

from ..models import ImageMetadata


class ValidationService:
    """Validates downloaded images for integrity and format."""
    
    def __init__(self):
        """Initialize validation service."""
        self.logger = logging.getLogger(__name__)
    
    def validate_image_format(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file is a valid JPEG image.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with Image.open(file_path) as img:
                # Check if it's a JPEG
                if img.format != 'JPEG':
                    return False, f"Expected JPEG format, got {img.format}"
                
                # Verify image can be loaded completely
                img.verify()
                
                self.logger.debug(f"Image format validation passed: {file_path}")
                return True, None
                
        except Exception as e:
            error_msg = f"Image format validation failed: {str(e)}"
            self.logger.warning(f"{error_msg} for {file_path}")
            return False, error_msg
    
    def calculate_file_hash(self, file_path: Path, algorithm: str = 'md5') -> Optional[str]:
        """
        Calculate hash of a file for integrity checking.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm ('md5', 'sha256', etc.)
            
        Returns:
            Hex digest of the hash, or None if error
        """
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def validate_file_size(self, file_path: Path, expected_size: int, tolerance: int = 0) -> Tuple[bool, Optional[str]]:
        """
        Validate file size matches expected size.
        
        Args:
            file_path: Path to the file
            expected_size: Expected file size in bytes
            tolerance: Allowed difference in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            actual_size = file_path.stat().st_size
            size_diff = abs(actual_size - expected_size)
            
            if size_diff <= tolerance:
                self.logger.debug(f"File size validation passed: {file_path} ({actual_size} bytes)")
                return True, None
            else:
                error_msg = f"Size mismatch: expected {expected_size}, got {actual_size} (diff: {size_diff})"
                self.logger.warning(f"File size validation failed: {error_msg} for {file_path}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error checking file size: {str(e)}"
            self.logger.error(f"{error_msg} for {file_path}")
            return False, error_msg
    
    def validate_image_content(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate image content and extract basic properties.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with Image.open(file_path) as img:
                # Check image dimensions (NASA SDO images should be reasonable size)
                width, height = img.size
                
                if width < 100 or height < 100:
                    return False, f"Image too small: {width}x{height}"
                
                if width > 10000 or height > 10000:
                    return False, f"Image too large: {width}x{height}"
                
                # Check if image has reasonable color depth
                if img.mode not in ['RGB', 'L', 'RGBA']:
                    return False, f"Unexpected color mode: {img.mode}"
                
                self.logger.debug(f"Image content validation passed: {file_path} ({width}x{height}, {img.mode})")
                return True, None
                
        except Exception as e:
            error_msg = f"Image content validation failed: {str(e)}"
            self.logger.warning(f"{error_msg} for {file_path}")
            return False, error_msg
    
    def comprehensive_validation(self, file_path: Path, expected_size: Optional[int] = None) -> Tuple[bool, list]:
        """
        Perform comprehensive validation of an image file.
        
        Args:
            file_path: Path to the image file
            expected_size: Expected file size in bytes (optional)
            
        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        errors = []
        
        # Check if file exists
        if not file_path.exists():
            errors.append(f"File does not exist: {file_path}")
            return False, errors
        
        # Check if file is not empty
        if file_path.stat().st_size == 0:
            errors.append(f"File is empty: {file_path}")
            return False, errors
        
        # Validate file size if expected size provided
        if expected_size is not None:
            size_valid, size_error = self.validate_file_size(file_path, expected_size)
            if not size_valid:
                errors.append(size_error)
        
        # Validate image format
        format_valid, format_error = self.validate_image_format(file_path)
        if not format_valid:
            errors.append(format_error)
        
        # Validate image content
        content_valid, content_error = self.validate_image_content(file_path)
        if not content_valid:
            errors.append(content_error)
        
        all_valid = len(errors) == 0
        
        if all_valid:
            self.logger.info(f"Comprehensive validation passed: {file_path}")
        else:
            self.logger.warning(f"Comprehensive validation failed for {file_path}: {errors}")
        
        return all_valid, errors
    
    def repair_corrupted_image(self, file_path: Path) -> bool:
        """
        Attempt to repair a corrupted image file.
        
        Args:
            file_path: Path to the corrupted image
            
        Returns:
            True if repair was successful, False otherwise
        """
        try:
            # Try to open and re-save the image
            with Image.open(file_path) as img:
                # Create a backup
                backup_path = file_path.with_suffix('.backup')
                file_path.rename(backup_path)
                
                # Save the image again (this can fix minor corruption)
                img.save(file_path, 'JPEG', quality=95)
                
                # Validate the repaired image
                is_valid, _ = self.validate_image_format(file_path)
                
                if is_valid:
                    # Remove backup if repair successful
                    backup_path.unlink()
                    self.logger.info(f"Successfully repaired image: {file_path}")
                    return True
                else:
                    # Restore backup if repair failed
                    file_path.unlink()
                    backup_path.rename(file_path)
                    self.logger.warning(f"Failed to repair image: {file_path}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error attempting to repair {file_path}: {e}")
            return False
    
    def get_image_info(self, file_path: Path) -> Optional[dict]:
        """
        Extract detailed information about an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary with image information, or None if error
        """
        try:
            with Image.open(file_path) as img:
                info = {
                    'filename': file_path.name,
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.size[0],
                    'height': img.size[1],
                    'file_size': file_path.stat().st_size,
                    'has_transparency': img.mode in ['RGBA', 'LA'] or 'transparency' in img.info
                }
                
                # Add EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    info['has_exif'] = True
                else:
                    info['has_exif'] = False
                
                return info
                
        except Exception as e:
            self.logger.error(f"Error getting image info for {file_path}: {e}")
            return None
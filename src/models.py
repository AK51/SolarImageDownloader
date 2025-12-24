"""Core data models for NASA Solar Image Downloader."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum


class TaskStatus(Enum):
    """Status of download tasks."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ImageMetadata:
    """Metadata for a NASA solar image."""
    date: datetime
    time_sequence: str  # HHMMSS format
    filename: str
    local_path: Path
    file_size: int
    download_timestamp: datetime
    url: str


@dataclass
class DownloadTask:
    """Represents a download task for an image."""
    url: str
    target_path: Path
    retry_count: int = 0
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None


@dataclass
class PlaybackState:
    """Current state of video playback interface."""
    current_frame: int = 0
    total_frames: int = 0
    is_playing: bool = False
    playback_speed: float = 1.0  # frames per second
    selected_date_range: Optional[Tuple[datetime, datetime]] = None
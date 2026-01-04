"""
Cross-platform file locking utilities.
"""
import os
import logging
from pathlib import Path
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)


class ChannelLock:
    """
    Cross-platform file lock for preventing concurrent updates to the same channel.
    Uses filelock library which works on Windows, Linux, and Mac.
    """
    
    def __init__(self, channel_id: str, lock_dir: str = "data/locks", timeout: int = 0):
        """
        Initialize channel lock.
        
        Args:
            channel_id: Channel ID to lock
            lock_dir: Directory for lock files
            timeout: Timeout in seconds (0 = non-blocking, -1 = wait forever)
        """
        self.channel_id = channel_id
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        
        lockfile_path = self.lock_dir / f"{channel_id}.lock"
        self.lock = FileLock(str(lockfile_path), timeout=timeout)
    
    def __enter__(self):
        """Acquire lock."""
        try:
            self.lock.acquire()
            logger.debug(f"Acquired lock for channel {self.channel_id}")
            return self
        except Timeout:
            raise Exception(f"Channel {self.channel_id} is already being updated by another process")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock."""
        self.lock.release()
        logger.debug(f"Released lock for channel {self.channel_id}")
        return False


def cleanup_old_locks(lock_dir: str = "data/locks", max_age_hours: int = 24):
    """
    Clean up stale lock files.
    
    Args:
        lock_dir: Directory containing lock files
        max_age_hours: Maximum age in hours before considering a lock stale
    """
    import time
    
    lock_path = Path(lock_dir)
    if not lock_path.exists():
        return
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    for lockfile in lock_path.glob("*.lock"):
        try:
            file_age = current_time - os.path.getmtime(lockfile)
            if file_age > max_age_seconds:
                lockfile.unlink()
                logger.info(f"Removed stale lock file: {lockfile.name}")
        except Exception as e:
            logger.warning(f"Error cleaning lock file {lockfile}: {e}")

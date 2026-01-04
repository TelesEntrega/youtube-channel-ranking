#!/usr/bin/env python
"""
Video Snapshots Collector Script

Run this script daily (manually or via scheduler) to collect view count snapshots
for all videos in the database. This enables delta-based ranking calculations.

Usage:
    python scripts/collect_snapshots.py

Scheduling:
    Windows Task Scheduler: Run daily at 2 AM
    Linux cron: 0 2 * * * /path/to/python /path/to/scripts/collect_snapshots.py
"""
import sys
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import Database
from app.youtube_client import YouTubeClient
from app.collector import Collector
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/snapshot_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main snapshot collection function."""
    logger.info("=" * 80)
    logger.info(f"Starting video snapshot collection - {datetime.now()}")
    logger.info("=" * 80)
    
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv('YT_API_KEY')
    if not api_key:
        logger.error("YT_API_KEY not found in environment variables!")
        return 1
    
    db_path = os.getenv('DB_PATH', 'data/rankings.db')
    
    # Initialize components
    logger.info(f"Initializing database: {db_path}")
    db = Database(db_path)
    
    logger.info("Initializing YouTube API client")
    youtube = YouTubeClient(api_key)
    
    logger.info("Initializing collector")
    collector = Collector(youtube, db)
    
    # Collect snapshots
    try:
        result = collector.collect_snapshots_for_all_channels()
        
        logger.info("=" * 80)
        logger.info("SNAPSHOT COLLECTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Status: {result['status']}")
        logger.info(f"Date: {result['snapshot_date']}")
        logger.info(f"Videos snapshotted: {result['videos_snapshotted']:,}")
        logger.info(f"Channels processed: {result['channels_processed']}")
        logger.info(f"Channels skipped: {result['channels_skipped']}")
        logger.info(f"Errors: {result['errors']}")
        logger.info("=" * 80)
        
        if result['status'] == 'success':
            logger.info("✅ Snapshot collection successful!")
            return 0
        else:
            logger.warning("⚠️ Snapshot collection completed with errors")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Fatal error during snapshot collection: {e}", exc_info=True)
        return 1
    finally:
        db.close()


def perform_weekly_backup():
    """Perform automatic backup to cloud storage (runs only on Sundays)."""
    import shutil
    from pathlib import Path
    
    # Check if today is Sunday (weekday 6)
    if datetime.now().weekday() != 6:
        logger.info("Skipping backup (not Sunday)")
        return
    
    logger.info("=" * 80)
    logger.info("PERFORMING WEEKLY BACKUP")
    logger.info("=" * 80)
    
    # Detect cloud storage
    cloud_paths = [
        Path.home() / "Google Drive" / "Meu Drive",
        Path.home() / "Google Drive" / "My Drive",
        Path.home() / "Google Drive",
        Path.home() / "GoogleDrive",
        Path("G:/Meu Drive"),
        Path("G:/My Drive"),
        Path.home() / "OneDrive"
    ]
    
    cloud_path = None
    cloud_type = ""
    
    for path in cloud_paths:
        if path.exists():
            cloud_path = path
            if "Google" in str(path) or str(path).startswith("G:"):
                cloud_type = "Google Drive"
            else:
                cloud_type = "OneDrive"
            break
    
    if not cloud_path:
        logger.warning("No cloud storage found, skipping backup")
        return
    
    # Create backup directory
    backup_dir = cloud_path / "Backup Ranking Gorgonoid"
    backup_dir.mkdir(exist_ok=True)
    
    # Backup file name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup_file = backup_dir / f"rankings_backup_{timestamp}.db"
    
    # Copy database
    db_path = Path("data/rankings.db")
    if db_path.exists():
        shutil.copy2(db_path, backup_file)
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Backup created: {backup_file}")
        logger.info(f"   Size: {size_mb:.2f} MB")
        logger.info(f"   Destination: {cloud_type}")
        
        # Clean old backups (keep last 5)
        backups = sorted(backup_dir.glob("rankings_backup_*.db"), key=lambda x: x.stat().st_mtime, reverse=True)
        for old_backup in backups[5:]:
            old_backup.unlink()
            logger.info(f"   Removed old backup: {old_backup.name}")
    else:
        logger.error("Database file not found!")
    
    logger.info("=" * 80)


if __name__ == "__main__":
    exit_code = main()
    
    # Perform weekly backup after snapshots (Sundays only)
    try:
        perform_weekly_backup()
    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
    
    sys.exit(exit_code)

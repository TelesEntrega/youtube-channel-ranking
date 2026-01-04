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


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

"""
Daily update script for YouTube channel ranking system.
Can be run manually or scheduled via cron/Task Scheduler.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from db import Database
from youtube_client import YouTubeClient
from collector import Collector

# Load environment variables
load_dotenv()

# Configure logging
log_path = os.getenv('LOG_PATH', 'logs/collector.log')
Path(log_path).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Run daily update for all channels."""
    logger.info("=" * 80)
    logger.info(f"Starting daily update at {datetime.now()}")
    logger.info("=" * 80)
    
    try:
        # Initialize components
        db_path = os.getenv('DB_PATH', 'data/rankings.db')
        api_key = os.getenv('YT_API_KEY')
        
        if not api_key:
            logger.error("YouTube API key not found in environment variables")
            return 2
        
        db = Database(db_path)
        youtube = YouTubeClient(api_key)
        collector = Collector(youtube, db)
        
        # Get list of all channels
        cursor = db.conn.cursor()
        cursor.execute("SELECT channel_id, title FROM channels ORDER BY updated_at ASC")
        channels = cursor.fetchall()
        
        if not channels:
            logger.warning("No channels found in database")
            return 0
        
        logger.info(f"Found {len(channels)} channels to update")
        
        # Update mode
        mode = os.getenv('UPDATE_MODE', 'incremental')
        logger.info(f"Update mode: {mode}")
        
        # Collect data
        successful = 0
        failed = 0
        
        for i, (channel_id, title) in enumerate(channels, 1):
            logger.info(f"[{i}/{len(channels)}] Updating: {title} ({channel_id})")
            
            try:
                result = collector.collect_channel(channel_id, mode=mode)
                
                if result['status'] == 'success':
                    successful += 1
                    logger.info(
                        f"✓ Success: {result.get('title', 'Unknown')} - "
                        f"{result.get('videos_collected', 0)} videos collected"
                    )
                else:
                    failed += 1
                    logger.error(f"✗ Failed: {result.get('message', 'Unknown error')}")
            
            except Exception as e:
                failed += 1
                logger.exception(f"✗ Exception while updating {channel_id}: {e}")
        
        # Summary
        logger.info("=" * 80)
        logger.info(f"Update complete at {datetime.now()}")
        logger.info(f"Successful: {successful}/{len(channels)}")
        logger.info(f"Failed: {failed}/{len(channels)}")
        logger.info("=" * 80)
        
        # Close database
        db.close()
        
        # Return exit code
        if failed == 0:
            return 0  # All successful
        elif successful > 0:
            return 1  # Partial success
        else:
            return 2  # All failed
    
    except Exception as e:
        logger.exception(f"Critical error in daily update: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

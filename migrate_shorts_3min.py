import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import Database
from app.youtube_client import YouTubeClient
from app.config import Config
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def migrate_shorts():
    """
    Migrate existing videos to new Shorts definition (<= 180s).
    Since DB doesn't store duration, we must re-fetch details from API.
    """
    db = Database()
    
    # Initialize API client
    api_key = Config.YOUTUBE_API_KEY
    if not api_key:
        logger.error("No API Key found.")
        return
        
    client = YouTubeClient(api_key)
    
    # 1. Get all videos currently marked as LONG (is_short = 0)
    cursor = db.conn.cursor()
    cursor.execute("SELECT video_id FROM videos WHERE is_short = 0")
    rows = cursor.fetchall()
    
    video_ids = [row['video_id'] for row in rows]
    total_videos = len(video_ids)
    
    logger.info(f"Found {total_videos} videos currently marked as Long. Checking for Extended Shorts (60s-180s)...")
    
    if not video_ids:
        logger.info("No videos to migrate.")
        return

    updated_count = 0
    BATCH_SIZE = 50
    
    # 2. Process in batches
    for i in range(0, total_videos, BATCH_SIZE):
        batch = video_ids[i:i+BATCH_SIZE]
        
        try:
            # Fetch details (this returns parsed 'duration_seconds' and new 'is_short')
            # The client code is already updated to use 180s threshold!
            video_details = client.get_videos_details(batch)
            
            videos_to_update = []
            for vid in video_details:
                # We need to ensure channel_id is present because upsert_videos requires it.
                # If get_videos_details didn't return it (it should in snippet), we might fail.
                # However, our DB schema enforces it.
                # For this specific migration, we are fetching by ID.
                # The prompt implies we just need to save.
                
                # If client says it's a short (now <= 180s), but we thought it was long
                # We save ALL videos fetched to be safe/consistent, or filter?
                # Let's save all fetched since we have fresh data.
                if vid.get('is_short') == 1:
                     # Check if channel_id is missing, if so, we might need to fetch it or skip?
                     # get_videos_details usually includes snippet which has channelId.
                     pass 
                
                videos_to_update.append(vid)

            if videos_to_update:
                db.upsert_videos(videos_to_update)
                updated_count += len([v for v in videos_to_update if v['is_short'] == 1])
                logger.info(f"Processed {i + len(batch)}/{total_videos} videos... (Saved: {len(videos_to_update)})")
            
        except Exception as e:
            logger.error(f"Error processing batch {i}: {e}")
            
    logger.info("-" * 30)
    logger.info(f"MIGRATION COMPLETE.")
    logger.info(f"Total converted to Shorts: {updated_count}")
    logger.info("-" * 30)

if __name__ == "__main__":
    migrate_shorts()

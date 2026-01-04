import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import Database
from app.youtube_client import YouTubeClient
from app.config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def migrate_heuristic():
    """
    Re-classify ALL videos using Heuristic Scoring (2025).
    """
    db = Database()
    
    api_key = Config.YOUTUBE_API_KEY
    if not api_key:
        logger.error("No API Key found.")
        return
        
    client = YouTubeClient(api_key)
    
    # 1. Get ALL video IDs (to correct both Long->Short and Short->Long)
    cursor = db.conn.cursor()
    cursor.execute("SELECT video_id, title, is_short FROM videos")
    rows = cursor.fetchall()
    
    video_ids = [row['video_id'] for row in rows]
    total_videos = len(video_ids)
    
    logger.info(f"Starting Heuristic Migration for {total_videos} videos...")
    
    if not video_ids:
        return

    updated_count = 0
    swapped_to_short = 0
    swapped_to_long = 0
    
    BATCH_SIZE = 50
    
    for i in range(0, total_videos, BATCH_SIZE):
        batch = video_ids[i:i+BATCH_SIZE]
        try:
            # get_videos_details now uses the NEW Scoring logic internally
            video_details = client.get_videos_details(batch)
            
            videos_to_save = []
            
            for vid in video_details:
                # Check if classification changed (we don't have old score, just old is_short)
                # We need to look up the old value.
                # Inefficeint to look up one by one.
                # But we can just upsert all.
                
                # For logging stats:
                # Find old row?
                # Let's just track how many are Short in the new batch vs old?
                # Too complex, just save.
                videos_to_save.append(vid)
                
            if videos_to_save:
                db.upsert_videos(videos_to_save)
                updated_count += len(videos_to_save)
            
            logger.info(f"Processed {min(i + BATCH_SIZE, total_videos)}/{total_videos} videos.")
            
        except Exception as e:
            logger.error(f"Error processing batch {i}: {e}")
            
    logger.info("-" * 30)
    logger.info(f"MIGRATION COMPLETE.")
    logger.info(f"Re-processed {updated_count} videos with Scoring Logic.")
    logger.info("-" * 30)

if __name__ == "__main__":
    migrate_heuristic()

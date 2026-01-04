#!/usr/bin/env python
"""
Reclassify all videos using DURATION ONLY criterion.

This script updates the is_short field for all videos in the database
using the new simplified rule: Duration <= 60 seconds = Short

Run this after changing the classification logic to update existing data.
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reclassify_videos():
    """Reclassify all videos using duration-only criterion."""
    logger.info("=" * 70)
    logger.info(" Reclassificação de Vídeos: APENAS DURAÇÃO")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Critério: Duração <= 180 segundos (3 min) = Short")
    logger.info("")
    
    db = Database('data/rankings.db')
    cursor = db.conn.cursor()
    
    # Get all videos
    cursor.execute("SELECT video_id, duration_seconds, is_short FROM videos")
    videos = cursor.fetchall()
    
    logger.info(f"Total de vídeos no banco: {len(videos)}")
    logger.info("")
    
    # Reclassify
    changed_to_short = 0
    changed_to_long = 0
    unchanged = 0
    
    for video in videos:
        video_id = video['video_id']
        duration = video['duration_seconds']
        old_is_short = video['is_short']
        
        # New classification: ONLY duration (≤180s = Short)
        new_is_short = 1 if (0 < duration <= 180) else 0
        
        if old_is_short != new_is_short:
            cursor.execute("UPDATE videos SET is_short = ? WHERE video_id = ?", 
                          (new_is_short, video_id))
            
            if new_is_short == 1:
                changed_to_short += 1
            else:
                changed_to_long += 1
        else:
            unchanged += 1
    
    db.conn.commit()
    
    logger.info("=" * 70)
    logger.info(" RESULTADO DA RECLASSIFICAÇÃO")
    logger.info("=" * 70)
    logger.info(f"📹 Total de vídeos:        {len(videos):,}")
    logger.info(f"✅ Sem mudança:            {unchanged:,}")
    logger.info(f"🔄 Mudados para Short:     {changed_to_short:,}")
    logger.info(f"🔄 Mudados para Longo:     {changed_to_long:,}")
    logger.info("")
    
    # Show new statistics
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN is_short = 1 THEN 1 ELSE 0 END) as shorts,
            SUM(CASE WHEN is_short = 0 THEN 1 ELSE 0 END) as longs
        FROM videos
    """)
    stats = cursor.fetchone()
    
    logger.info("=" * 70)
    logger.info(" ESTATÍSTICAS FINAIS")
    logger.info("=" * 70)
    logger.info(f"🎬 Shorts (≤180s):  {stats['shorts']:,}")
    logger.info(f"📹 Longos (>180s):  {stats['longs']:,}")
    logger.info("=" * 70)
    logger.info("")
    logger.info("✅ Reclassificação concluída!")
    logger.info("")
    
    db.close()

if __name__ == "__main__":
    reclassify_videos()

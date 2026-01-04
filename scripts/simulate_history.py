import sys
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from db import Database

def simulate_history():
    print("Simulando histórico de dados...")
    db = Database()
    cursor = db.conn.cursor()
    
    # Get all channels
    cursor.execute("SELECT channel_id, title FROM channels")
    channels = cursor.fetchall()
    
    # Get current stats as baseline
    for channel in channels:
        cid = channel['channel_id']
        title = channel['title']
        print(f"Gerando dados para: {title}")
        
        # Get current stats
        current = db.get_channel_stats(cid)
        curr_views = current['total_views']
        curr_videos = current['total_videos'] - 5  # Assume last 5 videos are recent
        
        # Simula 60 dias para trás
        for days_ago in range(1, 61):
            date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            # Remove some views/videos to simulate past state
            # Crescimento diário aleatório entre 0.05% e 0.2%
            reduction_factor = 1 - (random.uniform(0.0005, 0.002) * days_ago)
            
            past_views = int(curr_views * reduction_factor)
            past_videos = max(1, int(curr_videos * (1 - (0.001 * days_ago))))
            
            # Insert snapshot
            try:
                cursor.execute("""
                    INSERT INTO channel_snapshots (
                        channel_id, snapshot_date, total_views, shorts_views, long_views,
                        total_videos, shorts_videos, long_videos
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(channel_id, snapshot_date) DO NOTHING
                """, (
                    cid, date, 
                    past_views, 
                    int(past_views * 0.3), # Est. shorts ratio
                    int(past_views * 0.7), 
                    past_videos,
                    int(past_videos * 0.2),
                    int(past_videos * 0.8)
                ))
            except Exception as e:
                print(f"Erro: {e}")
                
    db.conn.commit()
    print("Histórico simulado com sucesso!")
    db.close()

if __name__ == "__main__":
    simulate_history()

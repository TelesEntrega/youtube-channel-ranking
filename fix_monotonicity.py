from app.db import Database
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_monotonicity():
    db = Database()
    cursor = db.conn.cursor()
    
    # Get all channels
    cursor.execute("SELECT channel_id, title FROM channels")
    channels = cursor.fetchall()
    
    total_updates = 0
    
    for channel in channels:
        cid = channel['channel_id']
        title = channel['title']
        logger.info(f"Processing {title}...")
        
        # Get snapshots sorted by date
        cursor.execute("""
            SELECT snapshot_date, reported_channel_views, total_views 
            FROM channel_snapshots 
            WHERE channel_id = ? 
            ORDER BY snapshot_date ASC
        """, (cid,))
        
        snapshots = cursor.fetchall()
        if not snapshots:
            continue
            
        max_views = 0
        updates_for_channel = 0
        
        for snap in snapshots:
            # Use reported if available, else total, else 0
            current_val = snap['reported_channel_views']
            if current_val is None or current_val == 0:
                current_val = snap['total_views'] or 0
                
            # Enforce monotonicity
            if current_val < max_views:
                # FIX: It dropped! Force it to be at least max_views
                # In a real scenario we might interpolate, but here we just clamp
                new_val = max_views
                
                cursor.execute("""
                    UPDATE channel_snapshots 
                    SET reported_channel_views = ? 
                    WHERE channel_id = ? AND snapshot_date = ?
                """, (new_val, cid, snap['snapshot_date']))
                updates_for_channel += 1
            else:
                new_val = current_val
                # Only update max_views if we have a valid positive number
                if new_val > 0:
                    max_views = new_val
                    
                # Ensure reported is populated if it was null
                if snap['reported_channel_views'] != new_val:
                    cursor.execute("""
                        UPDATE channel_snapshots 
                        SET reported_channel_views = ? 
                        WHERE channel_id = ? AND snapshot_date = ?
                    """, (new_val, cid, snap['snapshot_date']))

        if updates_for_channel > 0:
            logger.info(f"  Fixed {updates_for_channel} non-monotonic/missing records for {title}")
            total_updates += updates_for_channel
            
    db.conn.commit()
    logger.info(f"Done! Total records updated: {total_updates}")
    db.close()

if __name__ == "__main__":
    fix_monotonicity()

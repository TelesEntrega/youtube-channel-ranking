from app.db import Database
from app.ranking import RankingEngine
import logging

logging.basicConfig(level=logging.ERROR)

def validate():
    db = Database()
    ranking = RankingEngine(db)
    
    # 1. Get a date range that definitely has published videos
    cursor = db.conn.cursor()
    cursor.execute("SELECT MIN(published_at), MAX(published_at) FROM videos")
    dates = cursor.fetchone()
    if not dates or not dates[0]:
        print("No videos found to validate.")
        return
        
    # Python slices off the time for the function argument, but the function adds it back.
    # We just need YYYY-MM-DD
    s_date = dates[0][:10]
    e_date = dates[1][:10]
    print(f"Validating Range: {s_date} -> {e_date}")

    # 2. Get active channels in this range
    cursor.execute("""
        SELECT DISTINCT channel_id FROM videos 
        WHERE published_at >= ? AND published_at <= ?
        LIMIT 1
    """, (dates[0], dates[1]))
    row = cursor.fetchone()
    
    if not row:
        print("No active channels in range.")
        return
        
    cid = row['channel_id']
    print(f"Testing Channel: {cid}")
    
    # 3. Run Ranking Logic
    data = ranking.get_comparison_data([cid], s_date, e_date)
    
    if not data:
        print("Result: EMPTY LIST (Unexpected!)")
        return

    item = data[0]
    shorts = item['shorts_views']
    longs = item['long_views']
    total = item['views_period']
    
    print("-" * 30)
    print(f"Shorts Views: {shorts}")
    print(f"Long Views:   {longs}")
    print(f"Total Period: {total}")
    print("-" * 30)
    
    # 4. Verify Math
    if (shorts + longs) == total:
        print("Math Check: PASS ✅")
    else:
        print(f"Math Check: FAIL ❌ ({shorts} + {longs} != {total})")

if __name__ == "__main__":
    validate()

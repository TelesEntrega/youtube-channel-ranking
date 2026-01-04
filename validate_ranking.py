from app.db import Database
from app.ranking import RankingEngine
import logging

logging.basicConfig(level=logging.ERROR)

def validate():
    db = Database()
    ranking = RankingEngine(db)
    cursor = db.conn.cursor()

    # Find a channel with > 1 snapshot
    cursor.execute("""
        SELECT channel_id, COUNT(*) as c 
        FROM channel_snapshots 
        GROUP BY channel_id 
        HAVING c > 1 
        LIMIT 1
    """)
    row = cursor.fetchone()
    
    if not row:
        print("No channel with > 1 snapshot found.")
        return

    cid = row['channel_id']
    print(f"Testing Channel: {cid}")

    # Get Date Range
    cursor.execute("SELECT MIN(snapshot_date), MAX(snapshot_date) FROM channel_snapshots WHERE channel_id = ?", (cid,))
    dates = cursor.fetchone()
    s_date, e_date = dates[0], dates[1]
    print(f"Date Range: {s_date} -> {e_date}")

    # Run Ranking Logic
    data = ranking.get_comparison_data([cid], s_date, e_date)
    
    if not data:
        print("Result: EMPTY LIST (Unexpected!)")
    else:
        item = data[0]
        print(f"Rank: 1")
        print(f"Channel ID: {item['channel_id']}")
        print(f"Views Start: {item['views_start']} ({item['start_date']})")
        print(f"Views End:   {item['views_end']}   ({item['end_date']})")
        print(f"Views Period: {item['views_period']}")
        
        # Verify Math
        calc = item['views_end'] - item['views_start']
        if calc == item['views_period']:
            print("Mathematical Check: PASS ✅")
        else:
            print(f"Mathematical Check: FAIL ❌ ({calc} != {item['views_period']})")

if __name__ == "__main__":
    validate()

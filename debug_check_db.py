from app.db import Database

def check_db():
    db = Database()
    cursor = db.conn.cursor()
    
    # Check for Renato Cariani or similar
    # First get the ID
    cursor.execute("SELECT channel_id, title FROM channels WHERE title LIKE '%Cariani%' LIMIT 1")
    chan = cursor.fetchone()
    if not chan:
        print("Channel not found")
        return

    cid = chan['channel_id']
    print(f"Checking for {chan['title']} ({cid})")

    cursor.execute("""
        SELECT snapshot_date, reported_channel_views, total_views 
        FROM channel_snapshots 
        WHERE channel_id = ? 
        ORDER BY snapshot_date
    """, (cid,))
    
    rows = cursor.fetchall()
    print(f"{'Date':<12} | {'Reported':<15} | {'Total (Sum)':<15}")
    print("-" * 50)
    for r in rows:
        rep = r['reported_channel_views']
        tot = r['total_views']
        print(f"{r['snapshot_date']} | {str(rep):<15} | {str(tot):<15}")
        
    db.close()

if __name__ == "__main__":
    check_db()

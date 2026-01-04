"""Quick debug script to check Cariani video data."""
from app.db import Database

db = Database('data/rankings.db')
cursor = db.conn.cursor()

# Get Cariani channel ID
cursor.execute("SELECT channel_id, title FROM channels WHERE title LIKE '%Cariani%'")
row = cursor.fetchone()
if row:
    channel_id, title = row['channel_id'], row['title']
    print(f"\n=== {title} ({channel_id}) ===\n")
    
    # Total videos
    cursor.execute("SELECT COUNT(*) FROM videos WHERE channel_id = ?", (channel_id,))
    total = cursor.fetchone()[0]
    print(f"Total videos in DB: {total}")
    
    # By type
    cursor.execute("""
        SELECT is_short, COUNT(*), SUM(last_view_count)
        FROM videos WHERE channel_id = ?
        GROUP BY is_short
    """, (channel_id,))
    for row in cursor.fetchall():
        print(f"  is_short={row[0]}: {row[1]} videos, {row[2]:,} views")
    
    # In December 2025
    cursor.execute("""
        SELECT is_short, COUNT(*), SUM(last_view_count)
        FROM videos
        WHERE channel_id = ?
        AND published_at >= '2025-12-01T00:00:00Z'
        AND published_at <= '2025-12-31T23:59:59Z'
        GROUP BY is_short
    """, (channel_id,))
    print(f"\nVideos published in December 2025:")
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"  is_short={row[0]}: {row[1]} videos, {row[2]:,} views")
    else:
        print("  NO VIDEOS FOUND IN THIS PERIOD!")
    
    # Show some recent videos
    cursor.execute("""
        SELECT video_id, title, published_at, is_short, last_view_count
        FROM videos
        WHERE channel_id = ?
        ORDER BY published_at DESC
        LIMIT 10
    """, (channel_id,))
    print(f"\n10 most recent videos:")
    for row in cursor.fetchall():
        print(f"  {row['published_at'][:10]} - Short={row['is_short']} - {row['last_view_count']:,} views - {row['title'][:50]}")

db.close()

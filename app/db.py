"""
Database operations for YouTube ranking system.
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "data/rankings.db"):
        """Initialize database connection."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._connect()
        self.init_db()
    
    def _connect(self):
        """Create database connection."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Enable foreign keys for CASCADE operations
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_path}")
    
    def init_db(self):
        """Create database schema."""
        cursor = self.conn.cursor()
        
        
        # Tabela de canais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                handle TEXT,
                custom_url TEXT,
                country TEXT,
                uploads_playlist_id TEXT,
                brand TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Migration: Add brand column if not exists (for existing dbs)
        try:
            cursor.execute("SELECT brand FROM channels LIMIT 1")
        except:
            logger.info("Migrating schema: Adding 'brand' column to channels table")
            try:
                cursor.execute("ALTER TABLE channels ADD COLUMN brand TEXT")
            except Exception as e:
                logger.error(f"Migration failed: {e}")
        
        # Tabela de vídeos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                title TEXT NOT NULL,
                published_at TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                is_short INTEGER NOT NULL DEFAULT 0,
                is_live INTEGER NOT NULL DEFAULT 0,
                last_view_count INTEGER NOT NULL DEFAULT 0,
                last_fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
            )
        """)
        
        # Índices
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_is_short ON videos(is_short)
        """)
        
        # Tabela de snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                total_views INTEGER NOT NULL DEFAULT 0,
                shorts_views INTEGER NOT NULL DEFAULT 0,
                long_views INTEGER NOT NULL DEFAULT 0,
                total_videos INTEGER NOT NULL DEFAULT 0,
                shorts_videos INTEGER NOT NULL DEFAULT 0,
                long_videos INTEGER NOT NULL DEFAULT 0,
                reported_channel_views INTEGER,
                diff_percent REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE,
                UNIQUE(channel_id, snapshot_date)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_channel_date 
            ON channel_snapshots(channel_id, snapshot_date)
        """)
        
        # Video snapshots table (for delta-based ranking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_snapshots (
                video_id TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                view_count INTEGER NOT NULL,
                like_count INTEGER,
                comment_count INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (video_id, snapshot_date),
                FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_snapshots_date 
            ON video_snapshots(snapshot_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_snapshots_video_date 
            ON video_snapshots(video_id, snapshot_date)
        """)
        
        self.conn.commit()
        logger.info("Database schema initialized")
    
    def upsert_channel(self, channel_id: str, title: str, handle: str = None, 
                      custom_url: str = None, country: str = None, uploads_playlist_id: str = None):
        """Insert or update channel."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO channels (channel_id, title, handle, custom_url, country, uploads_playlist_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(channel_id) DO UPDATE SET
                title = excluded.title,
                handle = excluded.handle,
                custom_url = excluded.custom_url,
                country = excluded.country,
                uploads_playlist_id = excluded.uploads_playlist_id,
                updated_at = datetime('now')
        """, (channel_id, title, handle, custom_url, country, uploads_playlist_id))
        self.conn.commit()

    def update_channel_brand(self, channel_title: str, brand: str):
        """Update brand for a channel by title."""
        cursor = self.conn.cursor()
        # Clean inputs
        brand = brand.strip() if brand and brand.strip() not in ['?', '-'] else None
        
        cursor.execute("UPDATE channels SET brand = ? WHERE title = ?", (brand, channel_title))
        if cursor.rowcount > 0:
            logger.info(f"Updated brand for '{channel_title}' to '{brand}'")
            self.conn.commit()
        else:
            logger.warning(f"Channel not found for brand update: {channel_title}")
        logger.debug(f"Upserted channel: {channel_id} - {title}")
    
    def upsert_videos(self, videos: List[Dict]):
        """Batch insert or update videos."""
        cursor = self.conn.cursor()
        
        for video in videos:
            cursor.execute("""
                INSERT INTO videos (
                    video_id, channel_id, title, published_at, duration_seconds,
                    is_short, is_live, last_view_count, last_fetched_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(video_id) DO UPDATE SET
                    title = excluded.title,
                    duration_seconds = excluded.duration_seconds,
                    is_short = excluded.is_short,
                    is_live = excluded.is_live,
                    last_view_count = excluded.last_view_count,
                    last_fetched_at = excluded.last_fetched_at
            """, (
                video['video_id'],
                video['channel_id'],
                video['title'],
                video['published_at'],
                video['duration_seconds'],
                video['is_short'],
                video['is_live'],
                video['last_view_count']
            ))
        
        self.conn.commit()
        logger.info(f"Upserted {len(videos)} videos")
    
    def get_existing_video_ids(self, channel_id: str) -> set:
        """Get all video IDs for a channel."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT video_id FROM videos WHERE channel_id = ?", (channel_id,))
        return {row['video_id'] for row in cursor.fetchall()}
    
    def get_channel_stats(self, channel_id: str) -> Dict:
        """Get aggregated stats for a channel."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(last_view_count) as total_views,
                SUM(CASE WHEN is_short = 1 THEN last_view_count ELSE 0 END) as shorts_views,
                SUM(CASE WHEN is_short = 0 THEN last_view_count ELSE 0 END) as long_views,
                COUNT(*) as total_videos,
                SUM(is_short) as shorts_videos,
                SUM(CASE WHEN is_short = 0 THEN 1 ELSE 0 END) as long_videos
            FROM videos
            WHERE channel_id = ?
        """, (channel_id,))
        
        row = cursor.fetchone()
        return {
            'total_views': row['total_views'] or 0,
            'shorts_views': row['shorts_views'] or 0,
            'long_views': row['long_views'] or 0,
            'total_videos': row['total_videos'] or 0,
            'shorts_videos': row['shorts_videos'] or 0,
            'long_videos': row['long_videos'] or 0
        }
    
    def create_snapshot(self, channel_id: str, snapshot_date: str = None, 
                       reported_channel_views: int = None):
        """Create daily snapshot for a channel."""
        if snapshot_date is None:
            snapshot_date = datetime.now().strftime('%Y-%m-%d')
        
        stats = self.get_channel_stats(channel_id)
        
        # Calculate divergence if reported views available
        diff_percent = None
        if reported_channel_views is not None and reported_channel_views > 0:
            calculated = stats['total_views']
            diff_percent = abs(calculated - reported_channel_views) / reported_channel_views * 100
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO channel_snapshots (
                channel_id, snapshot_date, total_views, shorts_views, long_views,
                total_videos, shorts_videos, long_videos, reported_channel_views, diff_percent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel_id, snapshot_date) DO UPDATE SET
                total_views = excluded.total_views,
                shorts_views = excluded.shorts_views,
                long_views = excluded.long_views,
                total_videos = excluded.total_videos,
                shorts_videos = excluded.shorts_videos,
                long_videos = excluded.long_videos,
                reported_channel_views = excluded.reported_channel_views,
                diff_percent = excluded.diff_percent,
                created_at = datetime('now')
        """, (
            channel_id, snapshot_date,
            stats['total_views'], stats['shorts_views'], stats['long_views'],
            stats['total_videos'], stats['shorts_videos'], stats['long_videos'],
            reported_channel_views, diff_percent
        ))
        
        self.conn.commit()
        logger.info(f"Created snapshot for channel {channel_id} on {snapshot_date}")
    
    def save_video_snapshot(self, video_id: str, view_count: int, 
                           snapshot_date: str = None, like_count: int = None, 
                           comment_count: int = None):
        """
        Save or update video snapshot for a specific date.
        
        Args:
            video_id: Video ID
            view_count: Current view count
            snapshot_date: Date for snapshot (default: today)
            like_count: Optional like count
            comment_count: Optional comment count
        """
        if snapshot_date is None:
            snapshot_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO video_snapshots 
            (video_id, snapshot_date, view_count, like_count, comment_count)
            VALUES (?, ?, ?, ?, ?)
        """, (video_id, snapshot_date, view_count, like_count, comment_count))
        self.conn.commit()
        logger.debug(f"Saved snapshot for video {video_id} on {snapshot_date}: {view_count:,} views")
    
    def get_video_snapshot(self, video_id: str, snapshot_date: str) -> Optional[int]:
        """
        Get view count for a video on a specific date.
        
        Args:
            video_id: Video ID
            snapshot_date: Date to query (YYYY-MM-DD)
        
        Returns:
            View count or None if no snapshot exists
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT view_count FROM video_snapshots
            WHERE video_id = ? AND snapshot_date = ?
        """, (video_id, snapshot_date))
        row = cursor.fetchone()
        return row['view_count'] if row else None
    
    def get_latest_snapshot_date(self) -> Optional[str]:
        """
        Get the most recent snapshot date in the database.
        
        Returns:
            Latest snapshot date (YYYY-MM-DD) or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(snapshot_date) as latest FROM video_snapshots")
        row = cursor.fetchone()
        return row['latest'] if row and row['latest'] else None
    
    def get_snapshot_stats(self) -> Dict:
        """Get statistics about snapshot coverage."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_snapshots")
        total_snapshots = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT video_id) FROM video_snapshots")
        videos_with_snapshots = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT snapshot_date) FROM video_snapshots")
        unique_dates = cursor.fetchone()[0]
        
        return {
            'total_snapshots': total_snapshots,
            'videos_tracked': videos_with_snapshots,
            'unique_dates': unique_dates,
            'latest_date': self.get_latest_snapshot_date()
        }
    
    def save_channel_snapshot(self, channel_id: str, snapshot_date: str, 
                             view_count: int, subscriber_count: int = None, video_count: int = None):
        """
        Save channel statistics snapshot (for Delta Canal - Gorgonoid Planilha).
        Uses reported_channel_views field to store official YouTube channel viewCount.
        """
        cursor = self.conn.cursor()
        try:
            # For now, store in reported_channel_views field
            # In future migrations, consider adding dedicated columns
            cursor.execute("""
                INSERT INTO channel_snapshots (
                    channel_id, snapshot_date, 
                    reported_channel_views,
                    total_views, shorts_views, long_views,
                    total_videos, shorts_videos, long_videos
                )
                VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0)
                ON CONFLICT(channel_id, snapshot_date) DO UPDATE SET
                    reported_channel_views = excluded.reported_channel_views
            """, (channel_id, snapshot_date, view_count))
            self.conn.commit()
            logger.debug(f"Saved channel snapshot for {channel_id} on {snapshot_date}: {view_count:,} views")
        except Exception as e:
            logger.error(f"Error saving channel snapshot for {channel_id}: {e}")
            raise
    
    def get_channel_snapshot(self, channel_id: str, snapshot_date: str) -> Optional[int]:
        """Get channel viewCount for a specific date."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT reported_channel_views FROM channel_snapshots
            WHERE channel_id = ? AND snapshot_date = ?
        """, (channel_id, snapshot_date))
        row = cursor.fetchone()
        return row['reported_channel_views'] if row else None
    
    def delete_channel(self, channel_id: str):
        """Delete channel and all associated data."""
        cursor = self.conn.cursor()
        # Due to ON DELETE CASCADE, videos and snapshots will be deleted automatically
        cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        self.conn.commit()
        logger.info(f"Deleted channel {channel_id}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


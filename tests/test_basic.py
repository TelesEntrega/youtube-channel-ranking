"""
Basic tests for YouTube ranking system.
Run with: pytest tests/test_basic.py -v
"""
import pytest
import sys
from pathlib import Path
import isodate

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from youtube_client import YouTubeClient


class TestDurationParsing:
    """Test ISO 8601 duration parsing."""
    
    def test_parse_short_durations(self):
        """Test parsing of short video durations."""
        assert self._parse_duration('PT15S') == 15
        assert self._parse_duration('PT59S') == 59
        assert self._parse_duration('PT60S') == 60
        assert self._parse_duration('PT61S') == 61
    
    def test_parse_minute_durations(self):
        """Test parsing of minute-based durations."""
        assert self._parse_duration('PT1M') == 60
        assert self._parse_duration('PT1M30S') == 90
        assert self._parse_duration('PT10M45S') == 645
    
    def test_parse_hour_durations(self):
        """Test parsing of hour-based durations."""
        assert self._parse_duration('PT1H') == 3600
        assert self._parse_duration('PT1H2M10S') == 3730
    
    def test_parse_zero_duration(self):
        """Test parsing of zero/empty duration."""
        assert self._parse_duration('PT0S') == 0
    
    @staticmethod
    def _parse_duration(duration_str):
        """Helper to parse duration."""
        try:
            duration = isodate.parse_duration(duration_str)
            return int(duration.total_seconds())
        except:
            return 0


class TestShortsDetection:
    """Test Shorts identification logic."""
    
    def test_normal_short(self):
        """Test normal Short (<=60s, not live)."""
        assert YouTubeClient._is_video_short(59, 'none') == True
        assert YouTubeClient._is_video_short(60, 'none') == True
    
    def test_not_short(self):
        """Test videos that are not Shorts."""
        assert YouTubeClient._is_video_short(61, 'none') == False
        assert YouTubeClient._is_video_short(120, 'none') == False
    
    def test_live_not_short(self):
        """Test that live videos are not Shorts even if short duration."""
        assert YouTubeClient._is_video_short(30, 'live') == False
        assert YouTubeClient._is_video_short(45, 'upcoming') == False
    
    def test_none_live_status(self):
        """Test handling of None liveBroadcastContent."""
        assert YouTubeClient._is_video_short(50, None) == True
        assert YouTubeClient._is_video_short(70, None) == False


class TestQuotaEstimation:
    """Test quota cost estimation."""
    
    def test_quota_estimation_ceil(self):
        """Test that quota uses ceiling division."""
        # 1 channel, 51 videos = ceil(51/50) * 1 = 2 requests per operation
        # Total: 1 (channel) + 2 (playlist) + 2 (videos) = 5
        cost = YouTubeClient.estimate_quota_cost(1, 51)
        assert cost == 5
    
    def test_quota_estimation_exact(self):
        """Test quota with exact multiples."""
        # 1 channel, 50 videos = ceil(50/50) * 1 = 1 request per operation
        # Total: 1 + 1 + 1 = 3
        cost = YouTubeClient.estimate_quota_cost(1, 50)
        assert cost == 3
    
    def test_quota_estimation_large(self):
        """Test quota with large channel."""
        # 1 channel, 1000 videos
        # ceil(1000/50) = 20 requests per operation
        # Total: 1 + 20 + 20 = 41
        cost = YouTubeClient.estimate_quota_cost(1, 1000)
        assert cost == 41
    
    def test_quota_estimation_multiple_channels(self):
        """Test quota with multiple channels."""
        # 10 channels, 100 videos each
        # channels: 10
        # playlists: ceil(100/50) * 10 = 20
        # videos: ceil(100/50) * 10 = 20
        # Total: 50
        cost = YouTubeClient.estimate_quota_cost(10, 100)
        assert cost == 50


class TestDatabaseIntegrity:
    """Test database constraints and integrity."""
    
    def test_foreign_keys_enabled(self):
        """Test that foreign keys are enabled."""
        import sqlite3
        from db import Database
        
        db = Database(':memory:')
        cursor = db.conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        
        assert result[0] == 1, "Foreign keys should be enabled"
        
        db.close()
    
    def test_unique_snapshot_constraint(self):
        """Test that channel_id + snapshot_date is unique."""
        from db import Database
        
        db = Database(':memory:')
        
        # Create a test channel first
        db.upsert_channel('test_channel', 'Test Channel')
        
        # Insert first snapshot
        db.create_snapshot('test_channel', '2026-01-01')
        
        # Try to insert duplicate - should update, not error
        try:
            db.create_snapshot('test_channel', '2026-01-01')
            # Should succeed (ON CONFLICT UPDATE)
        except Exception as e:
            pytest.fail(f"Duplicate snapshot should update, not fail: {e}")
        
        # Verify only one snapshot exists
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM channel_snapshots 
            WHERE channel_id = 'test_channel' AND snapshot_date = '2026-01-01'
        """)
        count = cursor.fetchone()[0]
        
        assert count == 1, "Should only have one snapshot per channel per date"
        
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, '-v'])


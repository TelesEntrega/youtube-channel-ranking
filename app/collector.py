"""
Data collection pipeline for YouTube channels.
"""
import logging
from typing import List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Collector:
    """Channel data collector."""
    
    def __init__(self, youtube_client, database):
        """Initialize collector with YouTube client and database."""
        self.youtube = youtube_client
        self.db = database
    
    def collect_channel(self, channel_input: str, mode: str = 'incremental') -> Dict:
        """
        Collect data for a single channel.
        
        Args:
            channel_input: Channel ID, handle, or URL
            mode: 'incremental' (only new videos) or 'full' (all videos)
        
        Returns:
            Dict with collection statistics
        """
        logger.info(f"Starting collection for: {channel_input} (mode: {mode})")
        
        # Step 1: Resolve channel ID
        channel_id = self.youtube.resolve_channel_id(channel_input)
        if not channel_id:
            logger.error(f"Could not resolve channel ID for: {channel_input}")
            return {'status': 'error', 'message': 'Invalid channel input'}
        
        # Step 2: Get channel metadata
        metadata = self.youtube.get_channel_metadata(channel_id)
        if not metadata:
            logger.error(f"Could not get metadata for channel: {channel_id}")
            return {'status': 'error', 'message': 'Channel not found'}
        
        # Save channel info with uploads_playlist_id for caching
        self.db.upsert_channel(
            channel_id=metadata['channel_id'],
            title=metadata['title'],
            handle=metadata['handle'],
            country=metadata['country'],
            uploads_playlist_id=metadata['uploads_playlist_id']
        )
        
        # Step 3: Get all video IDs from uploads playlist
        logger.info(f"Fetching video IDs for: {metadata['title']}")
        video_ids = self.youtube.get_all_video_ids(metadata['uploads_playlist_id'])
        
        if not video_ids:
            logger.warning(f"No videos found for channel: {metadata['title']}")
            return {
                'status': 'success',
                'channel_id': channel_id,
                'title': metadata['title'],
                'videos_collected': 0,
                'new_videos': 0
            }
        
        # Step 4: Determine which videos to fetch details for
        existing_video_ids = self.db.get_existing_video_ids(channel_id)
        new_video_ids = [vid for vid in video_ids if vid not in existing_video_ids]
        
        logger.info(f"Found {len(video_ids)} total videos, {len(new_video_ids)} new, {len(existing_video_ids)} existing")
        
        # Step 5: Fetch video details with improved incremental strategy
        videos_to_fetch = []
        
        if mode == 'incremental':
            # Fetch new videos
            videos_to_fetch = new_video_ids
            
            # Also refresh some existing videos:
            # - Recent videos (published in last 90 days) - views still growing
            # - 10% rotation of older videos to keep ranking accurate
            cursor = self.db.conn.cursor()
            
            # Get recent videos (last 90 days)
            cursor.execute("""
                SELECT video_id FROM videos
                WHERE channel_id = ? 
                  AND published_at >= date('now', '-90 days')
                ORDER BY published_at DESC
            """, (channel_id,))
            recent_videos = [row[0] for row in cursor.fetchall()]
            
            # Get 10% of older videos for rotation (random sample)
            cursor.execute("""
                SELECT video_id FROM videos
                WHERE channel_id = ?
                  AND published_at < date('now', '-90 days')
                ORDER BY RANDOM()
                LIMIT (SELECT MAX(1, COUNT(*) / 10) FROM videos 
                       WHERE channel_id = ? 
                       AND published_at < date('now', '-90 days'))
            """, (channel_id, channel_id))
            rotation_videos = [row[0] for row in cursor.fetchall()]
            
            # Combine
            videos_to_fetch.extend(recent_videos)
            videos_to_fetch.extend(rotation_videos)
            videos_to_fetch = list(set(videos_to_fetch))  # Remove duplicates
            
            logger.info(f"Incremental mode: {len(new_video_ids)} new + {len(recent_videos)} recent + {len(rotation_videos)} rotation = {len(videos_to_fetch)} to fetch")
        else:  # full mode
            videos_to_fetch = video_ids
        
        if not videos_to_fetch:
            logger.info("No videos to fetch")
            # Still create snapshot with reported channel views
            self.db.create_snapshot(
                channel_id, 
                reported_channel_views=metadata.get('view_count')
            )
            return {
                'status': 'success',
                'channel_id': channel_id,
                'title': metadata['title'],
                'videos_collected': 0,
                'new_videos': 0
            }
        
        logger.info(f"Fetching details for {len(videos_to_fetch)} videos")
        video_details = self.youtube.get_videos_details(videos_to_fetch)
        
        # Add channel_id to each video
        for video in video_details:
            video['channel_id'] = channel_id
        
        # Step 6: Save videos to database
        if video_details:
            self.db.upsert_videos(video_details)
            logger.info(f"Saved {len(video_details)}/{len(videos_to_fetch)} videos (some may have been skipped due to missing data)")
        
        # Step 7: Create snapshot with reported channel views
        self.db.create_snapshot(
            channel_id,
            reported_channel_views=metadata.get('view_count')
        )
        
        stats = self.db.get_channel_stats(channel_id)
        
        logger.info(f"Collection complete for {metadata['title']}: {stats['total_videos']} videos, {stats['total_views']:,} total views")
        
        return {
            'status': 'success',
            'channel_id': channel_id,
            'title': metadata['title'],
            'videos_collected': len(video_details),
            'new_videos': len([v for v in new_video_ids if v in [vd['video_id'] for vd in video_details]]),
            'total_views': stats['total_views'],
            'shorts_views': stats['shorts_views'],
            'total_videos': stats['total_videos']
        }
    
    def collect_channels(self, channel_inputs: List[str], mode: str = 'incremental') -> List[Dict]:
        """
        Collect data for multiple channels.
        
        Args:
            channel_inputs: List of channel IDs, handles, or URLs
            mode: 'incremental' or 'full'
        
        Returns:
            List of collection results
        """
        results = []
        
        logger.info(f"Starting collection for {len(channel_inputs)} channels")
        
        for i, channel_input in enumerate(channel_inputs, 1):
            logger.info(f"Processing channel {i}/{len(channel_inputs)}: {channel_input}")
            
            try:
                result = self.collect_channel(channel_input, mode=mode)
                results.append(result)
            except Exception as e:
                logger.error(f"Error collecting channel {channel_input}: {e}")
                results.append({
                    'status': 'error',
                    'channel_input': channel_input,
                    'message': str(e)
                })
        
        success_count = len([r for r in results if r['status'] == 'success'])
        logger.info(f"Collection complete: {success_count}/{len(channel_inputs)} channels successful")
        
        return results
    
    def collect_snapshots_for_all_channels(self, snapshot_date: str = None) -> Dict:
        """
        Collect current view counts for all videos and save as snapshots.
        This should be run daily (manually or via scheduler) to enable delta-based rankings.
        
        Args:
            snapshot_date: Date for snapshot (default: today, YYYY-MM-DD format)
        
        Returns:
            Dict with collection statistics
        """
        if snapshot_date is None:
            snapshot_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"🔵 Starting video snapshot collection for {snapshot_date}")
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT DISTINCT channel_id, title FROM channels")
        channels = cursor.fetchall()
        
        total_videos = 0
        total_channels = len(channels)
        errors = 0
        skipped_channels = 0
        
        for i, row in enumerate(channels, 1):
            channel_id = row['channel_id']
            channel_title = row['title']
            logger.info(f"📹 Processing channel {i}/{total_channels}: {channel_title}")
            
            try:
                # Get all video IDs for this channel
                cursor.execute("SELECT video_id FROM videos WHERE channel_id = ?", (channel_id,))
                video_ids = [r['video_id'] for r in cursor.fetchall()]
                
                if not video_ids:
                    logger.warning(f"No videos found for channel {channel_title}, skipping")
                    skipped_channels += 1
                    continue
                
                # Fetch current stats from YouTube API (in batches of 50)
                video_details = self.youtube.get_videos_details(video_ids)
                
                # Save snapshots
                saved_count = 0
                for video in video_details:
                    self.db.save_video_snapshot(
                        video_id=video['video_id'],
                        view_count=video['last_view_count'],
                        snapshot_date=snapshot_date
                    )
                    saved_count += 1
                    total_videos += 1
                
                logger.info(f"✅ Saved {saved_count}/{len(video_ids)} snapshots for {channel_title}")
                
            except Exception as e:
                logger.error(f"❌ Error collecting snapshots for {channel_title}: {e}")
                errors += 1
                continue
        
        logger.info(f"🎯 Snapshot collection complete: {total_videos} videos, {total_channels} channels, {errors} errors, {skipped_channels} skipped")
        
        return {
            'status': 'success' if errors < total_channels else 'partial',
            'snapshot_date': snapshot_date,
            'videos_snapshotted': total_videos,
            'channels_processed': total_channels - skipped_channels,
            'channels_skipped': skipped_channels,
            'errors': errors
        }


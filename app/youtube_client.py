"""
YouTube Data API v3 client wrapper.
"""
import time
import random
import math
import logging
import isodate
import re
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to avoid hitting YouTube API rate limits."""
    
    def __init__(self, max_per_second: int = 50):
        self.max_per_second = max_per_second
        self.last_request = 0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        now = time.time()
        time_since_last = now - self.last_request
        min_interval = 1.0 / self.max_per_second
        
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        
        self.last_request = time.time()


class YouTubeClient:
    """YouTube Data API v3 client."""
    
    def __init__(self, api_key: str, rate_limit: int = 50):
        """Initialize YouTube API client."""
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.rate_limiter = RateLimiter(max_per_second=rate_limit)
        logger.info("YouTube API client initialized")
    
    def _api_request_with_retry(self, request_func, max_retries: int = 5):
        """Execute API request with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                self.rate_limiter.wait_if_needed()
                return request_func.execute()
            except HttpError as e:
                if e.resp.status in [429, 503]:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Rate limit hit. Waiting {wait_time:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                elif e.resp.status == 403 and 'quotaExceeded' in str(e):
                    logger.error("Daily quota exceeded. Aborting.")
                    raise
                else:
                    logger.error(f"API error: {e}")
                    raise
        
        raise Exception(f"Max retries ({max_retries}) reached")
    
    def resolve_channel_id(self, input_str: str) -> Optional[str]:
        """
        Resolve channel ID from various input formats:
        - Direct channel ID (UC...)
        - Handle (@username)
        - URL (youtube.com/@handle or youtube.com/channel/ID)
        """
        input_str = input_str.strip()
        
        # Direct channel ID
        if input_str.startswith('UC') and len(input_str) == 24:
            return input_str
        
        # Handle (@username)
        if input_str.startswith('@'):
            handle = input_str[1:]
            try:
                request = self.youtube.channels().list(
                    part='id',
                    forHandle=handle
                )
                response = self._api_request_with_retry(request)
                
                if response.get('items'):
                    channel_id = response['items'][0]['id']
                    logger.info(f"Resolved @{handle} -> {channel_id}")
                    return channel_id
            except TypeError:
                # Fallback for libraries that don't support forHandle yet
                logger.warning(f"forHandle not supported by client, falling back to search for @{handle}")
                try:
                    request = self.youtube.search().list(
                        part='snippet',
                        q=f"@{handle}",
                        type='channel',
                        maxResults=1
                    )
                    response = self._api_request_with_retry(request)
                    if response.get('items'):
                        channel_id = response['items'][0]['snippet']['channelId']
                        logger.info(f"Resolved via search @{handle} -> {channel_id}")
                        return channel_id
                except Exception as e:
                    logger.error(f"Error searching for handle @{handle}: {e}")
            except Exception as e:
                logger.error(f"Error resolving handle @{handle}: {e}")
                return None
            
            logger.warning(f"Handle @{handle} not found")
            return None
        
        # URL parsing
        if 'youtube.com' in input_str or 'youtu.be' in input_str:
            # Extract channel ID or handle from URL
            if '/channel/' in input_str:
                channel_id = input_str.split('/channel/')[1].split('/')[0].split('?')[0]
                return channel_id
            elif '/@' in input_str:
                handle = input_str.split('/@')[1].split('/')[0].split('?')[0]
                return self.resolve_channel_id(f'@{handle}')
        
        logger.error(f"Could not resolve channel ID from: {input_str}")
        return None
    
    def get_channel_metadata(self, channel_id: str) -> Optional[Dict]:
        """Get channel metadata and uploads playlist ID."""
        try:
            request = self.youtube.channels().list(
                part='snippet,contentDetails,statistics',
                id=channel_id
            )
            response = self._api_request_with_retry(request)
            
            if not response.get('items'):
                logger.warning(f"Channel {channel_id} not found")
                return None
            
            item = response['items'][0]
            snippet = item['snippet']
            content_details = item['contentDetails']
            statistics = item.get('statistics', {})
            
            metadata = {
                'channel_id': channel_id,
                'title': snippet['title'],
                'handle': snippet.get('customUrl', None),
                'country': snippet.get('country', None),
                'uploads_playlist_id': content_details['relatedPlaylists']['uploads'],
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0))
            }
            
            logger.info(f"Got metadata for channel: {metadata['title']} ({metadata['video_count']} videos)")
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting channel metadata for {channel_id}: {e}")
            return None
    
    def get_all_video_ids(self, uploads_playlist_id: str) -> List[str]:
        """Get all video IDs from uploads playlist with pagination."""
        video_ids = []
        next_page_token = None
        page_count = 0
        
        while True:
            try:
                request = self.youtube.playlistItems().list(
                    part='contentDetails',
                    playlistId=uploads_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = self._api_request_with_retry(request)
                
                page_count += 1
                items = response.get('items', [])
                
                for item in items:
                    video_id = item['contentDetails']['videoId']
                    video_ids.append(video_id)
                
                logger.debug(f"Page {page_count}: collected {len(items)} videos (total: {len(video_ids)})")
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
            except Exception as e:
                logger.error(f"Error getting video IDs (page {page_count}): {e}")
                break
        
        logger.info(f"Collected {len(video_ids)} video IDs from playlist {uploads_playlist_id}")
        return video_ids
    
    def get_videos_details(self, video_ids: List[str]) -> List[Dict]:
        """Get video details in batches of 50."""
        all_videos = []
        
        # Split into batches of 50
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            
            try:
                request = self.youtube.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=','.join(batch)
                )
                response = self._api_request_with_retry(request)
                
                for item in response.get('items', []):
                    video_data = self._parse_video_item(item)
                    if video_data:
                        all_videos.append(video_data)
                
                logger.debug(f"Processed batch {i//50 + 1}: {len(batch)} videos")
                
            except Exception as e:
                logger.error(f"Error getting video details for batch starting at {i}: {e}")
        
        logger.info(f"Collected details for {len(all_videos)}/{len(video_ids)} videos")
        return all_videos
    
    def _parse_video_item(self, item: Dict) -> Optional[Dict]:
        """Parse video item from API response."""
        try:
            video_id = item['id']
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            statistics = item.get('statistics', {})
            
            # Skip if no statistics available
            if not statistics or 'viewCount' not in statistics:
                logger.warning(f"Video {video_id} has no statistics available")
                return None
            
            # Parse duration
            duration_str = content_details.get('duration', 'PT0S')
            try:
                duration = isodate.parse_duration(duration_str)
                duration_seconds = int(duration.total_seconds())
            except Exception as e:
                logger.error(f"Error parsing duration '{duration_str}' for video {video_id}: {e}")
                duration_seconds = 0
            
            # Determine if Short using Heuristic Score
            is_short, score, reasons = self._classify_video_score(duration_seconds, snippet)
            is_live = 1 if snippet.get('liveBroadcastContent', 'none') in ['live', 'upcoming'] else 0
            
            return {
                'video_id': video_id,
                'channel_id': snippet.get('channelId'),
                'title': snippet.get('title', 'Unknown'),
                'published_at': snippet.get('publishedAt', ''),
                'duration_seconds': duration_seconds,
                'is_short': 1 if is_short else 0,
                'score': score, # Optional: save score for debugging if needed (DB doesn't have col yet)

                'is_live': is_live,
                'last_view_count': int(statistics.get('viewCount', 0))
            }
            
        except Exception as e:
            logger.error(f"Error parsing video item {item.get('id', 'unknown')}: {e}")
            return None
    
    @staticmethod
    def _classify_video_score(duration: int, snippet: Dict) -> tuple:
        """
        Classify video as Short or Long using Surgical Heuristic Scoring (2025).
        Returns: (is_short: bool, score: int, reasons: list)
        
        Methodology:
        Positive:
        +2: Duration <= 180s
        +2: Hashtag #shorts in title/desc/tags
        +2: Short Description (<= 300 chars)
        +1: Short Title (<= 70 chars)
        
        Negative:
        -3: Live/Upcoming
        -3: Timestamps (Chapters)
        
        Threshold: Score >= 3 -> SHORT
        """
        score = 0
        reasons = []
        
        # 1. Duration (+2) - Updated weight
        if 0 < duration <= 180:
            score += 2
            reasons.append("+2 Duration")
            
        # 2. Hashtags (+2)
        title = snippet.get('title', '').replace('\n', ' ').strip()
        desc = snippet.get('description', '').replace('\n', ' ').strip()
        tags = [t.lower() for t in snippet.get('tags', [])]
        
        # Check text fields
        title_lower = title.lower()
        desc_lower = desc.lower()
        
        has_hash = '#shorts' in title_lower or '#shorts' in desc_lower or 'shorts' in tags
        if has_hash:
            score += 2
            reasons.append("+2 Hashtag")
            
        # 3. Short Description (+2) - New signal
        if len(desc) <= 300:
            score += 2
            reasons.append("+2 Short Desc")
            
        # 4. Short Title (+1) - New signal
        if len(title) <= 70:
            score += 1
            reasons.append("+1 Short Title")
            
        # 5. Live (-3)
        live = snippet.get('liveBroadcastContent', 'none')
        if live in ['live', 'upcoming', 'completed']:
            score -= 3
            reasons.append("-3 Live")
            
        # 6. Timestamps (-3) - Updated weight
        # Regex for "00:00" or "0:00" pattern
        if re.search(r'\b\d{1,2}:\d{2}\b', desc) and len(desc) > 100:
             # Only penalize if desc is long enough to actually BE a chapter list? 
             # Or just strictly if present. User said "-3 possui capítulos".
             # Usually short descriptions don't have chapters. 
             # If desc <= 300 (+2) AND has timestamps (-3) -> net -1. Good.
            score -= 3
            reasons.append("-3 Timestamps")
            
        is_short = score >= 3
        return is_short, score, reasons
    
    @staticmethod
    def estimate_quota_cost(num_channels: int, avg_videos_per_channel: int) -> int:
        """
        Estimate quota cost for collecting channels.
        
        Returns:
            Estimated quota units needed
        """
        # channels.list for metadata: 1 unit per channel
        channels_requests = num_channels
        
        # playlistItems.list: 1 unit per request (50 items/page)
        playlist_requests = math.ceil(avg_videos_per_channel / 50) * num_channels
        
        # videos.list: 1 unit per request (50 videos/batch)
        videos_requests = math.ceil(avg_videos_per_channel / 50) * num_channels
        
        total_cost = channels_requests + playlist_requests + videos_requests
        return total_cost

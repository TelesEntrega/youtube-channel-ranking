"""
Ranking calculations and queries.
"""
import logging
from typing import List, Dict, Optional
import sqlite3

logger = logging.getLogger(__name__)


class RankingEngine:
    """Ranking calculation engine."""
    
    def __init__(self, database):
        """Initialize with database connection."""
        self.db = database
    
    def get_global_ranking(self, limit: int = 100, offset: int = 0, 
                          search_query: str = None) -> List[Dict]:
        """
        Get global ranking of channels by total views.
        
        Args:
            limit: Number of results to return
            offset: Offset for pagination
            search_query: Optional search term for channel title
        
        Returns:
            List of ranked channels with statistics
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT 
                c.channel_id,
                c.title,
                c.handle,
                c.brand,
                SUM(v.last_view_count) as total_views,
                SUM(CASE WHEN v.is_short = 1 THEN v.last_view_count ELSE 0 END) as shorts_views,
                SUM(CASE WHEN v.is_short = 0 THEN v.last_view_count ELSE 0 END) as long_views,
                COUNT(*) as total_videos,
                SUM(v.is_short) as shorts_count,
                SUM(CASE WHEN v.is_short = 0 THEN 1 ELSE 0 END) as long_count,
                MAX(v.last_fetched_at) as last_update
            FROM channels c
            INNER JOIN videos v ON c.channel_id = v.channel_id
        """
        
        params = []
        
        if search_query:
            query += " WHERE c.title LIKE ?"
            params.append(f"%{search_query}%")
        
        query += """
            GROUP BY c.channel_id, c.title, c.handle, c.brand
            ORDER BY total_views DESC
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        ranking = []
        for i, row in enumerate(rows, start=offset + 1):
            ranking.append({
                'rank': i,
                'channel_id': row['channel_id'],
                'title': row['title'],
                'handle': row['handle'],
                'brand': row['brand'],
                'total_views': row['total_views'] or 0,
                'shorts_views': row['shorts_views'] or 0,
                'long_views': row['long_views'] or 0,
                'total_videos': row['total_videos'] or 0,
                'shorts_count': row['shorts_count'] or 0,
                'long_count': row['long_count'] or 0,
                'last_update': row['last_update']
            })
        
        logger.debug(f"Retrieved {len(ranking)} channels for ranking")
        return ranking
    
    def get_channel_details(self, channel_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific channel.
        
        Args:
            channel_id: Channel ID
        
        Returns:
            Channel details with top videos
        """
        cursor = self.db.conn.cursor()
        
        # Get channel info
        cursor.execute("""
            SELECT channel_id, title, handle, country, brand
            FROM channels
            WHERE channel_id = ?
        """, (channel_id,))
        
        channel_row = cursor.fetchone()
        if not channel_row:
            logger.warning(f"Channel {channel_id} not found")
            return None
        
        # Get aggregated stats
        stats = self.db.get_channel_stats(channel_id)
        
        # Get top video overall
        cursor.execute("""
            SELECT video_id, title, last_view_count, is_short, published_at
            FROM videos
            WHERE channel_id = ?
            ORDER BY last_view_count DESC
            LIMIT 1
        """, (channel_id,))
        top_video = cursor.fetchone()
        
        # Get top Short
        cursor.execute("""
            SELECT video_id, title, last_view_count, published_at
            FROM videos
            WHERE channel_id = ? AND is_short = 1
            ORDER BY last_view_count DESC
            LIMIT 1
        """, (channel_id,))
        top_short = cursor.fetchone()
        
        # Get top 10 videos
        cursor.execute("""
            SELECT video_id, title, last_view_count, is_short, published_at
            FROM videos
            WHERE channel_id = ?
            ORDER BY last_view_count DESC
            LIMIT 10
        """, (channel_id,))
        top_10_videos = cursor.fetchall()
        
        return {
            'channel_id': channel_row['channel_id'],
            'title': channel_row['title'],
            'handle': channel_row['handle'],
            'country': channel_row['country'],
            'brand': channel_row['brand'],
            'stats': stats,
            'top_video': dict(top_video) if top_video else None,
            'top_short': dict(top_short) if top_short else None,
            'top_10_videos': [dict(row) for row in top_10_videos]
        }
    
    def get_channel_history(self, channel_id: str, days: int = 30) -> List[Dict]:
        """
        Get historical snapshots for a channel.
        
        Args:
            channel_id: Channel ID
            days: Number of days of history to retrieve
        
        Returns:
            List of historical snapshots
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT 
                snapshot_date,
                total_views,
                shorts_views,
                long_views,
                total_videos,
                shorts_videos,
                long_videos
            FROM channel_snapshots
            WHERE channel_id = ?
              AND snapshot_date >= date('now', '-' || ? || ' days')
            ORDER BY snapshot_date ASC
        """, (channel_id, days))
        
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_total_channels_count(self, search_query: str = None) -> int:
        """Get total number of channels in database."""
        cursor = self.db.conn.cursor()
        
        query = "SELECT COUNT(DISTINCT c.channel_id) FROM channels c INNER JOIN videos v ON c.channel_id = v.channel_id"
        params = []
        
        if search_query:
            query += " WHERE c.title LIKE ?"
            params.append(f"%{search_query}%")
        
        cursor.execute(query, params)
        return cursor.fetchone()[0]

    def get_comparison_data(self, channel_ids: List[str], start_date: str, end_date: str) -> List[Dict]:
        """
        Get ranking by summing TOTAL VIEWS of videos PUBLISHED within the date range.
        
        This is the "Published Content Analysis" methodology:
        - Filters videos by published_at date
        - Sums accumulated views (last_view_count) since publication
        - Measures volume of content output
        
        For growth-based ranking, use get_comparison_data_delta() instead.
        
        Args:
            channel_ids: List of channel IDs
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of dicts with:
                - channel_id
                - shorts_views (Sum of views from Shorts published in period)
                - long_views (Sum of views from Long videos published in period)
                - total_views_period (shorts_views + long_views)
                - views_reais (Internal: long_views * 1.0 + shorts_views * 0.25)
                - media_por_conteudo (Efficiency: views_period / total_videos)
                - media_shorts (Average views per Short)
                - media_longos (Average views per Long video)
                - below_cutoff (Editorial flag: views_period < 1M)
                - start_date
                - end_date
        """
        if not channel_ids:
            return []

        cursor = self.db.conn.cursor()
        results = []

        # Convert to datetime strings for SQL comparison if needed, 
        # generally YYYY-MM-DD works fine with ISO8601 published_at strings 
        # provided we handle the time part. 
        # published_at format: YYYY-MM-DDTHH:MM:SSZ
        # We start at start_date 00:00:00 and end at end_date 23:59:59
        
        start_ts = f"{start_date}T00:00:00Z"
        end_ts = f"{end_date}T23:59:59Z"

        for channel_id in channel_ids:
            # query: Sum views and COUNT videos for videos published in range, split by type
            # We use COALESCE to ensure 0 instead of NULL
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN is_short = 1 THEN last_view_count ELSE 0 END) as shorts_views,
                    SUM(CASE WHEN is_short = 0 THEN last_view_count ELSE 0 END) as long_views,
                    SUM(CASE WHEN is_short = 1 THEN 1 ELSE 0 END) as shorts_count,
                    SUM(CASE WHEN is_short = 0 THEN 1 ELSE 0 END) as long_count
                FROM videos
                WHERE channel_id = ?
                  AND published_at >= ?
                  AND published_at <= ?
            """, (channel_id, start_ts, end_ts))
            
            row = cursor.fetchone()
            
            shorts_views = row['shorts_views'] if row and row['shorts_views'] else 0
            long_views = row['long_views'] if row and row['long_views'] else 0
            shorts_count = row['shorts_count'] if row and row['shorts_count'] else 0
            long_count = row['long_count'] if row and row['long_count'] else 0
            
            total_views_period = shorts_views + long_views
            total_videos_period = shorts_count + long_count
            
            # ========== INTERNAL METRICS (GORGONOID ENHANCEMENTS) ==========
            
            # 1. Views Reais: Weighted views (longos * 1.0 + shorts * 0.25)
            views_reais = (long_views * 1.0) + (shorts_views * 0.25)
            
            # 2. Efficiency Metrics
            media_por_conteudo = total_views_period / total_videos_period if total_videos_period > 0 else 0
            media_shorts = shorts_views / shorts_count if shorts_count > 0 else 0
            media_longos = long_views / long_count if long_count > 0 else 0
            
            # 3. Editorial Cut-off Flag (< 1M views)
            below_cutoff = total_views_period < 1_000_000
            
            # ===============================================================
            
            # Get channel title and brand
            cursor.execute("SELECT title, brand FROM channels WHERE channel_id = ?", (channel_id,))
            ch_row = cursor.fetchone()
            title = ch_row['title'] if ch_row else channel_id
            brand = ch_row['brand'] if ch_row else None
            
            results.append({
                "channel_id": channel_id,
                "title": title,
                "brand": brand,
                "shorts_views": shorts_views,
                "long_views": long_views,
                "views_period": total_views_period,
                "shorts_count": shorts_count,
                "long_count": long_count,
                "total_videos": total_videos_period,
                "start_date": start_date,
                "end_date": end_date,
                # Internal metrics (not displayed as columns)
                "views_reais": views_reais,
                "media_por_conteudo": media_por_conteudo,
                "media_shorts": media_shorts,
                "media_longos": media_longos,
                "below_cutoff": below_cutoff
            })

        # Sort by total views in period descending
        results.sort(key=lambda x: x['views_period'], reverse=True)
        
        return results
    
    def get_comparison_data_delta(self, channel_ids: List[str], start_date: str, end_date: str) -> List[Dict]:
        """
        Get ranking by calculating VIEW DELTA (growth) for each channel in period.
        This is the CORRECT Gorgonoid methodology.
        
        Calculates: views_end - views_start for ALL videos (regardless of publish date).
        Videos published before, during, or after the period are included if they have snapshots.
        
        Args:
            channel_ids: List of channel IDs
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of dicts with delta-based metrics:
                - channel_id
                - shorts_views (delta for shorts)
                - long_views (delta for long videos)
                - views_period (total delta)
                - shorts_count (shorts with data)
                - long_count (long videos with data)
                - total_videos (total with data)
                - videos_with_data (for diagnostics)
                - Internal metrics (views_reais, efficiency, etc.)
        """
        if not channel_ids:
            return []
        
        cursor = self.db.conn.cursor()
        results = []
        
        for channel_id in channel_ids:
            # OPTIMIZED: Single query with JOIN to get both snapshots at once
            cursor.execute("""
                SELECT 
                    v.video_id,
                    v.is_short,
                    vs_start.view_count as views_start,
                    vs_end.view_count as views_end
                FROM videos v
                LEFT JOIN video_snapshots vs_start ON v.video_id = vs_start.video_id AND vs_start.snapshot_date = ?
                LEFT JOIN video_snapshots vs_end ON v.video_id = vs_end.video_id AND vs_end.snapshot_date = ?
                WHERE v.channel_id = ?
            """, (start_date, end_date, channel_id))
            
            videos = cursor.fetchall()
            
            shorts_delta = 0
            long_delta = 0
            shorts_count = 0
            long_count = 0
            videos_with_data = 0
            videos_skipped = 0
            
            for video in videos:
                views_start = video['views_start']
                views_end = video['views_end']
                is_short = video['is_short']
                
                # Skip if we don't have both snapshots
                if views_start is None or views_end is None:
                    videos_skipped += 1
                    continue
                
                # Calculate delta (clamp to 0 if negative - rare but possible)
                delta = max(0, views_end - views_start)
                
                if is_short:
                    shorts_delta += delta
                    shorts_count += 1
                else:
                    long_delta += delta
                    long_count += 1
                
                videos_with_data += 1
            
            total_delta = shorts_delta + long_delta
            total_videos = shorts_count + long_count
            
            # ========== INTERNAL METRICS (SAME AS BEFORE) ==========
            
            # 1. Views Reais: Weighted views (longos * 1.0 + shorts * 0.25)
            views_reais = (long_delta * 1.0) + (shorts_delta * 0.25)
            
            # 2. Efficiency Metrics
            media_por_conteudo = total_delta / total_videos if total_videos > 0 else 0
            media_shorts = shorts_delta / shorts_count if shorts_count > 0 else 0
            media_longos = long_delta / long_count if long_count > 0 else 0
            
            # 3. Editorial Cut-off Flag (< 1M views)
            below_cutoff = total_delta < 1_000_000
            
            # ===========================================================
            
            # Get channel title and brand
            cursor.execute("SELECT title, brand FROM channels WHERE channel_id = ?", (channel_id,))
            ch_row = cursor.fetchone()
            title = ch_row['title'] if ch_row else channel_id
            brand = ch_row['brand'] if ch_row else None
            
            results.append({
                "channel_id": channel_id,
                "title": title,
                "brand": brand,
                "shorts_views": shorts_delta,
                "long_views": long_delta,
                "views_period": total_delta,
                "shorts_count": shorts_count,
                "long_count": long_count,
                "total_videos": total_videos,
                "videos_with_data": videos_with_data,  # Diagnostic
                "videos_skipped": videos_skipped,       # Diagnostic
                "start_date": start_date,
                "end_date": end_date,
                # Internal metrics
                "views_reais": views_reais,
                "media_por_conteudo": media_por_conteudo,
                "media_shorts": media_shorts,
                "media_longos": media_longos,
                "below_cutoff": below_cutoff
            })
        
        # Sort by total delta descending
        results.sort(key=lambda x: x['views_period'], reverse=True)
        
        logger.info(f"Delta ranking calculated for {len(results)} channels between {start_date} and {end_date}")
        
        return results
    
    def get_comparison_data_delta_channel(self, channel_ids: List[str], start_date: str, end_date: str) -> List[Dict]:
        """
        Get ranking by CHANNEL DELTA (Ant / Atual / Reais / %) - Métrica Gorgonoid Planilha.
        
        This is the "Delta Canal" methodology - uses reported_channel_views from API:
        - Ant = channel viewCount at start_date
        - Atual = channel viewCount at end_date
        - Reais = Atual - Ant
        - % = (Reais / Ant) * 100
        
        For granular analysis (Shorts/Longos breakdown), use get_comparison_data_delta() instead.
        
        Args:
            channel_ids: List of channel IDs to compare
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            List of rankings with Ant/Atual/Reais/% metrics, sorted by Reais descending
        """
        if not channel_ids:
            return []
        
        cursor = self.db.conn.cursor()
        results = []
        
        for channel_id in channel_ids:
            # Get channel title and brand
            cursor.execute("SELECT title, brand FROM channels WHERE channel_id = ?", (channel_id,))
            ch_row = cursor.fetchone()
            title = ch_row['title'] if ch_row else channel_id
            brand = ch_row['brand'] if ch_row else None
            
            # Get channel snapshots for start and end dates
            views_ant = self.db.get_channel_snapshot(channel_id, start_date)
            views_atual = self.db.get_channel_snapshot(channel_id, end_date)
            
            # Skip if we don't have both snapshots
            if views_ant is None or views_atual is None:
                logger.warning(f"Channel {channel_id} missing snapshots (Ant: {views_ant}, Atual: {views_atual})")
                # Add with zeros for diagnostic
                results.append({
                    "channel_id": channel_id,
                    "title": title,
                    "brand": brand,
                    "ant": 0,
                    "atual": 0,
                    "reais": 0,
                    "percent": 0.0,
                    "missing_snapshots": True,
                    "start_date": start_date,
                    "end_date": end_date
                })
                continue
            
            # Calculate Delta Canal metrics
            reais = max(0, views_atual - views_ant)  # Clamp to 0 if negative
            percent = (reais / views_ant * 100.0) if views_ant > 0 else 0.0
            
            results.append({
                "channel_id": channel_id,
                "title": title,
                "brand": brand,
                "ant": views_ant,
                "atual": views_atual,
                "reais": reais,
                "percent": percent,
                "missing_snapshots": False,
                "start_date": start_date,
                "end_date": end_date
            })
        
        # Sort by Reais descending
        results.sort(key=lambda x: x['reais'], reverse=True)
        
        logger.info(f"Delta Canal ranking calculated for {len(results)} channels between {start_date} and {end_date}")
        return results

from odoo import models, api
import requests
import logging
import os

_logger = logging.getLogger(__name__)

class TrendService(models.AbstractModel):
    _name = "jj.trend.service"
    _description = "Trend Data Service (Supabase)"

    @api.model
    def _get_supabase_config(self):
        # Try environment variables first (from .env file)
        url = os.getenv("SUPABASE_URL")
        # Support both naming conventions for the API key
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        # Fallback to System Parameters if env vars not set
        if not url or not key:
            IrConfig = self.env["ir.config_parameter"].sudo()
            url = url or IrConfig.get_param("jj_trend.supabase_url")
            key = key or IrConfig.get_param("jj_trend.supabase_key")
        
        return url, key

    @api.model
    def _get_table_name(self, platform):
        """Map platform name to Supabase table name"""
        platform_map = {
            'facebook': 'facebook',
            'instagram': 'instagram',
            'linkedin': 'linkedin',
            'linkdin': 'linkedin',  # Typo handling
            'tiktok': 'tiktok',
            'twitter': 'twitter',
            'x': 'twitter',
            'youtube': 'youtube',
            'yt': 'youtube',       # Shorthand
        }
        # Default to 'tiktok' if platform is unknown or empty
        return platform_map.get(platform.lower() if platform else None, 'tiktok')

    @api.model
    def _get_column_mapping(self, table_name):
        """Standardize column names based on the table name"""
        mapping = {
            'trends': ('timestamp', 'title'),
            'tiktok': ('scraped_at', 'topic'),
            'youtube': ('scraped_at', 'topic_hashtag'),
            'facebook': ('scraped_at', 'topic_hashtag'),
            'instagram': ('scraped_at', 'topic_hashtag'),
            'linkedin': ('scraped_at', 'topic_hashtag'),
            'twitter': ('scraped_at', 'topic_hashtag'),
        }
        return mapping.get(table_name, ('scraped_at', 'topic_hashtag'))

    @api.model
    def fetch_top_per_platform(self, top_n=1, platform=None, date_from=None, date_to=None,
                               min_engagement=None, hashtag=None):
        """
        Fetch the top N hashtags from EACH platform separately with filtering.
        """
        url, key = self._get_supabase_config()
        if not url or not key:
            _logger.warning("Supabase URL or Key not set.")
            return []

        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
        }

        # Query and filter platform tables
        platforms = ['facebook', 'instagram', 'linkedin', 'tiktok', 'twitter', 'youtube']
        
        if platform:
            mapped_platform = self._get_table_name(platform)
            if mapped_platform in platforms:
                platforms = [mapped_platform]
            else:
                _logger.warning(f"Requested platform '{platform}' (mapped to '{mapped_platform}') not in supported list.")
                return []

        all_results = []

        for table_name in platforms:
            date_col, text_col = self._get_column_mapping(table_name)
            
            params = {
                "select": "*",
                "limit": top_n,
                "order": f"{date_col}.desc,engagement_score.desc",
            }

            # Build list of AND conditions for complex filtering
            and_conditions = []

            # Date Range
            if date_from and date_to:
                and_conditions.append(f"{date_col}.gte.{date_from}")
                and_conditions.append(f"{date_col}.lte.{date_to}")
            elif date_from:
                params[date_col] = f"gte.{date_from}"
            elif date_to:
                params[date_col] = f"lte.{date_to}"
            
            # Min Engagement
            if min_engagement:
                params["engagement_score"] = f"gte.{min_engagement}"
                
            # Text Search
            if hashtag:
                params[text_col] = f"ilike.%{hashtag}%"

            # If we have multiple AND conditions, combine them
            if and_conditions:
                params["and"] = f"({','.join(and_conditions)})"

            try:
                _logger.info(f"Fetching top {top_n} from {table_name}")
                resp = requests.get(f"{url}/rest/v1/{table_name}", headers=headers, params=params, timeout=10)
                
                if resp.status_code != 200:
                    _logger.warning(f"Supabase Table '{table_name}' Error {resp.status_code}: {resp.text}")
                    continue
                    
                raw_data = resp.json()
                
                for item in raw_data:
                    # Normalize Title (Topic/Hashtag)
                    title = item.get(text_col) or item.get('topic') or item.get('topic_hashtag') or item.get('title') or item.get('text') or "No Title"
                    
                    # Normalize Timestamp
                    timestamp = item.get(date_col) or item.get('timestamp') or item.get('scraped_at') or item.get('created_at') or ""
                    
                    # Extract URL
                    post_url = item.get('url')
                    if not post_url and item.get('metadata'):
                        try:
                            meta = item.get('metadata')
                            if isinstance(meta, str):
                                import json
                                meta = json.loads(meta)
                            post_url = meta.get('url') or meta.get('link')
                        except Exception:
                            pass

                    # Normalize Score (handle NULLs)
                    score = item.get('engagement_score')
                    try:
                        score = float(score) if score is not None else 0.0
                    except:
                        score = 0.0

                    # Use table name as primary platform identification to avoid cross-contamination
                    platform_label = table_name.capitalize()
                    if table_name == 'trends' and item.get('platform'):
                        platform_label = item.get('platform').capitalize()

                    all_results.append({
                        'id': item.get('id'),
                        'platform': platform_label,
                        'engagement_score': score,
                        'url': post_url or "#",
                        'title': title,
                        'timestamp': timestamp,
                    })

            except Exception as e:
                _logger.error(f"Error fetching from {table_name}: {e}")

        _logger.info(f"Fetched {len(all_results)} total results ({top_n} per platform)")
        return all_results


    @api.model
    def fetch_trends(self, platform=None, date_from=None, date_to=None,
                     min_engagement=None, hashtag=None, limit=200):
        url, key = self._get_supabase_config()
        if not url or not key:
            _logger.warning("Supabase URL or Key not set.")
            return []

        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
        }

        # List of tables to query
        tables_to_query = []
        if platform:
            tables_to_query.append(self._get_table_name(platform))
        else:
            # Unified view: Query all available platform tables
            tables_to_query = ['facebook', 'instagram', 'linkedin', 'tiktok', 'twitter', 'youtube']

        all_results = []
        
        # For global top-N, we need to fetch more from each table to ensure we get the true top results
        # If requesting top 3 globally, we should get at least top 10-20 from each platform
        if platform:
            # Single platform: use the requested limit
            per_table_limit = limit
        else:
            # Multi-platform: fetch enough from each to find global top N
            # For small limits (like top 3), get at least 50 from each table
            # For larger limits, get proportionally more
            per_table_limit = max(50, limit * 3)

        for table_name in tables_to_query:
            date_col, text_col = self._get_column_mapping(table_name)
            
            params = {
                "select": "*",
                "limit": per_table_limit,
                "order": f"{date_col}.desc,engagement_score.desc",
            }

            # Build list of AND conditions for complex filtering
            and_conditions = []

            # Date Range - Build proper conditions
            if date_from and date_to:
                # For date range, we need both conditions
                and_conditions.append(f"{date_col}.gte.{date_from}")
                and_conditions.append(f"{date_col}.lte.{date_to}")
            elif date_from:
                params[date_col] = f"gte.{date_from}"
            elif date_to:
                params[date_col] = f"lte.{date_to}"
            
            # Min Engagement
            if min_engagement:
                params["engagement_score"] = f"gte.{min_engagement}"
                
            # Text Search
            if hashtag:
                params[text_col] = f"ilike.%{hashtag}%"

            # If we have multiple AND conditions, combine them
            if and_conditions:
                params["and"] = f"({','.join(and_conditions)})"


            try:
                _logger.info(f"Supabase Query Table={table_name}: {params}")
                resp = requests.get(f"{url}/rest/v1/{table_name}", headers=headers, params=params, timeout=10)
                
                if resp.status_code != 200:
                    _logger.warning(f"Supabase Table '{table_name}' Error {resp.status_code}: {resp.text}")
                    continue
                    
                raw_data = resp.json()
                
                for item in raw_data:
                    # Normalize Title (Topic/Hashtag)
                    title = item.get(text_col) or item.get('topic') or item.get('topic_hashtag') or item.get('title') or item.get('text') or "No Title"
                    
                    # Normalize Timestamp
                    timestamp = item.get(date_col) or item.get('timestamp') or item.get('scraped_at') or item.get('created_at') or ""
                    
                    # Extract URL
                    post_url = item.get('url')
                    if not post_url and item.get('metadata'):
                        try:
                            meta = item.get('metadata')
                            if isinstance(meta, str):
                                import json
                                meta = json.loads(meta)
                            post_url = meta.get('url') or meta.get('link')
                        except Exception: pass

                    # Normalize Score (handle NULLs)
                    score = item.get('engagement_score')
                    try:
                        score = float(score) if score is not None else 0.0
                    except:
                        score = 0.0

                    # Use table name as primary platform identification to avoid cross-contamination
                    platform_label = table_name.capitalize()
                    if table_name == 'trends' and item.get('platform'):
                        platform_label = item.get('platform').capitalize()

                    all_results.append({
                        'id': item.get('id'),
                        'platform': platform_label,
                        'engagement_score': score,
                        'url': post_url or "#",
                        'title': title,
                        'timestamp': timestamp,
                    })

            except Exception as e:
                _logger.error(f"Error fetching from {table_name}: {e}")

        # 5. Global Sort & Limit
        # Sort by timestamp descending to match Supabase "Latest First" view
        all_results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Log platform distribution for debugging
        if all_results:
            platform_counts = {}
            for r in all_results[:limit]:
                platform_counts[r['platform']] = platform_counts.get(r['platform'], 0) + 1
            _logger.info(f"Top {limit} results by platform: {platform_counts}")
            if all_results:
                _logger.info(f"Top result: {all_results[0]['platform']} - {all_results[0]['title']} - Score: {all_results[0]['engagement_score']}")
        
        return all_results[:limit]

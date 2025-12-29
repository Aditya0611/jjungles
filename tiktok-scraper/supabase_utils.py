
import os
import re
import math
import uuid
import logging
import random
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from supabase import create_client, Client
from functools import wraps

logger = logging.getLogger(__name__)

# ============================================================================
# ASYNC RETRY WRAPPER FOR DATABASE OPERATIONS
# ============================================================================

def async_retry_wrapper(max_retries: int = 3, base_delay: float = 1.0, exponential: bool = True):
    """
    Decorator for async retry with exponential backoff and job queue fallback.
    
    This decorator wraps async database operations to automatically retry on failure
    with exponential backoff. If all retries fail and a job_queue is available in kwargs,
    the failed operation is queued for async retry.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds between retries (default: 1.0)
        exponential: Use exponential backoff if True, linear if False (default: True)
    
    Usage:
        @async_retry_wrapper(max_retries=3, base_delay=1.0)
        async def upload_data(supabase, data, **kwargs):
            # Database operation here
            pass
    
    Returns:
        Decorated async function with retry logic
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            job_queue = kwargs.get('job_queue')  # Extract job_queue if provided
            
            for attempt in range(1, max_retries + 1):
                try:
                    # Call the original function
                    result = await func(*args, **kwargs)
                    
                    # Success - log if this was a retry
                    if attempt > 1:
                        logger.info(f"✅ {func.__name__} succeeded on attempt {attempt}/{max_retries}")
                    
                    return result
                    
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"❌ {func.__name__} failed on attempt {attempt}/{max_retries}: {str(e)[:200]}"
                    )
                    
                    # If not the last attempt, wait before retrying
                    if attempt < max_retries:
                        if exponential:
                            # Exponential backoff with jitter
                            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                        else:
                            # Linear backoff with jitter
                            delay = base_delay * attempt + random.uniform(0, 0.5)
                        
                        logger.info(f"⏳ Retrying in {delay:.2f}s...")
                        await asyncio.sleep(delay)
            
            # All retries exhausted - try to queue for async retry if job_queue available
            if job_queue:
                try:
                    # Extract function name and arguments for job queue
                    payload = {
                        "function": func.__name__,
                        "args_repr": str(args)[:500],  # Truncate for storage
                        "kwargs_keys": list(kwargs.keys()),
                        "error": str(last_error)[:500]
                    }
                    
                    job_id = job_queue.add_job(
                        job_type="database_operation",
                        payload=payload,
                        max_attempts=3
                    )
                    
                    if job_id:
                        logger.warning(
                            f"⚠️ {func.__name__} failed after {max_retries} attempts. "
                            f"Queued for async retry (job_id: {job_id})"
                        )
                    else:
                        logger.error(
                            f"❌ {func.__name__} failed and could not be queued for retry"
                        )
                        
                except Exception as queue_error:
                    logger.error(f"Failed to queue job for retry: {queue_error}")
            else:
                logger.error(
                    f"❌ {func.__name__} failed after {max_retries} attempts "
                    f"and no job_queue available for async retry"
                )
            
            # Re-raise the last error
            raise last_error
        
        return wrapper
    return decorator


# ============================================================================
# STANDARDIZED DATA MODEL - Reusable Schema
# ============================================================================

@dataclass
class SocialMediaRecord:
    """
    Standardized data model for social media trending content.
    Reusable across platforms with consistent schema.
    """
    # Core identification (required fields first)
    platform: str
    timestamp: datetime
    topic: str  # Primary hashtag/topic
    
    # Optional fields with defaults
    version_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)  # Additional tags
    
    # Scoring
    score: float = 0.0  # Engagement score (0.0-10.0)
    
    # Sentiment
    sentiment: Dict[str, Any] = field(default_factory=lambda: {
        'polarity': 0.0,  # -1.0 to 1.0
        'label': 'Neutral'  # Positive, Neutral, Negative
    })
    
    # Metrics
    metrics: Dict[str, Any] = field(default_factory=lambda: {
        'posts': None,  # Number of posts
        'views': None,  # Total views
        'likes': None,  # Number of likes
        'comments': None,  # Number of comments
        'reactions': None,  # Number of reactions (shares, hearts, etc.)
        'rank': None,  # Ranking position
    })
    
    # Content
    content: Dict[str, Any] = field(default_factory=lambda: {
        'caption': None,
        'title': None,
        'format': 'video',  # video, image, carousel, live (default: video for TikTok)
        'sound': None  # Sound information dict (critical for TikTok virality)
    })
    
    # Classification
    category: str = "General"
    language: Optional[str] = None  # Detected language code (e.g., 'en', 'es', 'fr')
    language_confidence: Optional[float] = None  # Detection confidence (0.0-1.0)
    
    # Trend Lifecycle Tracking
    trend_lifecycle: Dict[str, Any] = field(default_factory=lambda: {
        'first_seen': None,  # When trend first appeared (ISO timestamp)
        'peak_time': None,  # When trend reached peak engagement (ISO timestamp)
        'peak_score': None,  # Highest engagement score achieved
        'is_decaying': False,  # Whether trend is declining
        'decay_rate': None,  # Rate of decline (score change per hour)
        'trend_status': 'unknown'  # 'emerging', 'rising', 'peak', 'decaying', 'stale'
    })
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        # Convert datetime to ISO string
        data['timestamp'] = self.timestamp.isoformat()
        # Flatten sentiment for database compatibility
        data['sentiment_polarity'] = data['sentiment']['polarity']
        data['sentiment_label'] = data['sentiment']['label']
        # Flatten metrics
        data['posts'] = data['metrics']['posts']
        data['views'] = data['metrics']['views']
        data['likes'] = data['metrics']['likes']
        data['comments'] = data['metrics']['comments']
        data['reactions'] = data['metrics']['reactions']
        # Flatten content to metadata for database
        data['metadata'].update({
            'rank': data['metrics']['rank'],
            'category': data['category'],
            'language': data.get('language'),
            'language_confidence': data.get('language_confidence'),
            'caption': data['content']['caption'],
            'title': data['content']['title'],
            'post_format': data['content']['format'],  # Critical for TikTok virality analysis
            'sound': data['content']['sound'],  # Critical for content suggestion
            'tags': data['tags'],
            'trend_lifecycle': data['trend_lifecycle'],
            'source_url': data['metadata'].get('source_url', 
                'https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en')
        })
        return data
    
    @classmethod
    def from_scraped_data(cls, scraped_item: Dict[str, Any], 
                         platform: str = "TikTok",
                         version_id: Optional[str] = None) -> 'SocialMediaRecord':
        """Create record from scraped hashtag data."""
        timestamp = datetime.now(timezone.utc)
        
        # Extract topic/tags
        topic = scraped_item.get('hashtag', '')
        tags = [topic] if topic else []
        
        # Extract score
        score = float(scraped_item.get('engagement_score', 0.0))
        
        # Extract sentiment
        sentiment = {
            'polarity': float(scraped_item.get('sentiment_polarity', 0.0)),
            'label': scraped_item.get('sentiment_label', 'Neutral')
        }
        
        # Extract metrics
        metrics = {
            'posts': convert_to_numeric(scraped_item.get('posts', 'N/A')),
            'views': convert_to_numeric(scraped_item.get('views', 'N/A')),
            'likes': convert_to_numeric(scraped_item.get('likes', 'N/A')),
            'comments': convert_to_numeric(scraped_item.get('comments', 'N/A')),
            'reactions': convert_to_numeric(scraped_item.get('reactions', 'N/A')),
            'rank': scraped_item.get('rank', None)
        }
        
        # Extract content (post format and sound info are critical for TikTok virality)
        sound_info = {
            'name': scraped_item.get('sound_name'),
            'artist': scraped_item.get('sound_artist'),
            'sound_id': scraped_item.get('sound_id'),
            'original_sound': scraped_item.get('original_sound', False)
        } if scraped_item.get('sound_name') or scraped_item.get('sound_artist') else None
        
        content = {
            'caption': scraped_item.get('caption'),
            'title': scraped_item.get('title', topic),
            'format': scraped_item.get('post_format', 'video'),  # Default to video for TikTok
            'sound': sound_info
        }
        
        # Extract category
        category = scraped_item.get('category', 'General')
        
        # Extract language (if already detected)
        language = scraped_item.get('language')
        language_confidence = scraped_item.get('language_confidence')
        
        # Build metadata
        metadata = {
            'source_url': 'https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en'
        }
        
        # Trend lifecycle will be populated by analyze_trend_lifecycle
        trend_lifecycle = {
            'first_seen': None,
            'peak_time': None,
            'peak_score': None,
            'is_decaying': False,
            'decay_rate': None,
            'trend_status': 'unknown'
        }
        
        return cls(
            platform=platform,
            timestamp=timestamp,
            version_id=version_id,
            topic=topic,
            tags=tags,
            score=score,
            sentiment=sentiment,
            metrics=metrics,
            content=content,
            category=category,
            language=language,
            language_confidence=language_confidence,
            trend_lifecycle=trend_lifecycle,
            metadata=metadata
        )
    
    def to_database_format(self, include_collected_at_hour: bool = True, include_language: bool = True, 
                          snapshot_date: Optional[str] = None, snapshot_version: Optional[int] = None,
                          include_comments: bool = True, include_likes: bool = True,
                          include_views: bool = True, include_posts: bool = True,
                          include_reactions: bool = True) -> Dict[str, Any]:
        """Convert to database-compatible format matching schema."""
        data = self.to_dict()
        
        # Return in database schema format
        db_format = {
            'platform': self.platform,
            'topic': self.topic,
            'engagement_score': self.score,
            'sentiment_polarity': self.sentiment['polarity'],
            'sentiment_label': self.sentiment['label'],
            # Metrics handled conditionally below
            # 'posts': self.metrics['posts'],
            # 'views': self.metrics['views'],
            # 'likes': self.metrics['likes'],
            # 'comments': self.metrics['comments'],
            # 'reactions': self.metrics['reactions'],
            'metadata': data['metadata'],
            'scraped_at': self.timestamp.isoformat(),
            'version_id': self.version_id,
        }
        
        if include_posts:
            db_format['posts'] = self.metrics['posts']
        if include_views:
            db_format['views'] = self.metrics['views']
        if include_likes:
            db_format['likes'] = self.metrics['likes']
        if include_reactions:
            db_format['reactions'] = self.metrics['reactions']
        
        if include_comments:
            db_format['comments'] = self.metrics['comments']
        
        if include_language:
            db_format['language'] = self.language
            db_format['language_confidence'] = self.language_confidence
        
        if include_collected_at_hour:
            db_format['collected_at_hour'] = self.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        
        if snapshot_date:
            db_format['snapshot_date'] = snapshot_date
        if snapshot_version:
            db_format['snapshot_version'] = snapshot_version
        
        return db_format


def validate_social_media_record(record: SocialMediaRecord) -> tuple[bool, Optional[str]]:
    """
    Validate SocialMediaRecord before database insert/upsert.
    """
    # Topic required
    if not record.topic or not isinstance(record.topic, str):
        return False, "Missing or invalid topic"

    # Score sanity check
    try:
        score = float(record.score)
    except (TypeError, ValueError):
        return False, "Invalid engagement_score"
    if math.isnan(score) or math.isinf(score):
        return False, "Non-finite engagement_score"

    # Posts / views must be numeric or None
    for field_name in ("posts", "views"):
        value = record.metrics.get(field_name)
        if value is not None:
            try:
                int(value)
            except (TypeError, ValueError):
                return False, f"Invalid {field_name} value: {value}"

    # Language confidence sanity check
    if record.language_confidence is not None:
        try:
            lc = float(record.language_confidence)
        except (TypeError, ValueError):
            return False, "Invalid language_confidence"
        if lc < 0.0 or lc > 1.0:
            return False, "language_confidence out of range 0.0-1.0"

    return True, None

def init_supabase(url: str, key: str) -> Optional[Client]:
    """Initialize Supabase client"""
    try:
        if not url or not key:
            logger.warning("SUPABASE_URL or SUPABASE_KEY environment variables not set")
            return None
        
        supabase: Client = create_client(url, key)
        logger.info("Supabase client initialized successfully")
        return supabase
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

def convert_to_numeric(value: str) -> Optional[int]:
    """Convert string values like '1.2K', '5.3M', '2.1B' to numeric integers."""
    if not value or value == "N/A":
        return None
    
    try:
        clean_value = str(value).strip()
        clean_value = re.sub(r'[^0-9.KMBkmb-]', '', clean_value)
        clean_value = clean_value.upper()
        
        if not clean_value:
            return None
        
        multiplier = 1
        if 'B' in clean_value:
            multiplier = 1_000_000_000
            clean_value = clean_value.replace('B', '')
        elif 'M' in clean_value:
            multiplier = 1_000_000
            clean_value = clean_value.replace('M', '')
        elif 'K' in clean_value:
            multiplier = 1_000
            clean_value = clean_value.replace('K', '')
        
        number = float(clean_value)
        return int(number * multiplier)
        
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(f"Failed to convert '{value}' to numeric: {e}")
        return None

def get_next_snapshot_version(supabase, table_name: str, snapshot_date: str) -> int:
    """Get the next snapshot version number for a given date."""
    try:
        result = supabase.table(table_name).select("snapshot_version").eq("snapshot_date", snapshot_date).order("snapshot_version", desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            max_version = result.data[0].get("snapshot_version", 0)
            return max_version + 1
        else:
            return 1  # First snapshot of the day
    except Exception as e:
        logger.warning(f"Failed to get snapshot version for {snapshot_date}: {e}, defaulting to 1")
        return 1

def get_historical_trend_data(supabase: Client, topic: str, table_name: str = "tiktok", 
                              lookback_hours: int = 168, local_cache=None) -> List[Dict[str, Any]]:
    """Query historical data for a specific topic to analyze trend lifecycle."""
    if local_cache:
        cached_data = local_cache.get_trend_data(topic, platform="TikTok")
        if cached_data:
            logger.debug(f"Cache hit for {topic}")
            return cached_data

    try:
        if not supabase:
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        
        response = supabase.table(table_name)\
            .select("*")\
            .eq("topic", topic)\
            .gte("scraped_at", cutoff_time.isoformat())\
            .order("scraped_at", desc=False)\
            .execute()
        
        if response.data:
            logger.debug(f"Found {len(response.data)} historical records for {topic}")
            if local_cache:
                local_cache.set_trend_data(topic, response.data, platform="TikTok")
            return response.data
        else:
            return []
    except Exception as e:
        logger.warning(f"Failed to query historical data for {topic}: {e}")
        return []

def analyze_trend_lifecycle(current_record: SocialMediaRecord, 
                           historical_data: List[Dict[str, Any]]) -> SocialMediaRecord:
    """Analyze trend lifecycle: first seen, peak, and decay detection."""
    if not historical_data:
        current_record.trend_lifecycle = {
            'first_seen': current_record.timestamp.isoformat(),
            'peak_time': current_record.timestamp.isoformat(),
            'peak_score': current_record.score,
            'is_decaying': False,
            'decay_rate': None,
            'trend_status': 'emerging'
        }
        return current_record
    
    first_record = min(historical_data, key=lambda x: x.get('scraped_at', ''))
    first_seen = first_record.get('scraped_at')
    
    all_records = historical_data + [{
        'scraped_at': current_record.timestamp.isoformat(),
        'engagement_score': current_record.score
    }]
    
    peak_record = max(all_records, key=lambda x: float(x.get('engagement_score', 0) or 0))
    peak_time = peak_record.get('scraped_at')
    peak_score = float(peak_record.get('engagement_score', 0) or 0)
    
    is_decaying = False
    decay_rate = None
    trend_status = 'unknown'
    
    if len(historical_data) >= 2:
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
        recent_records = [
            r for r in historical_data 
            if datetime.fromisoformat(r.get('scraped_at', '').replace('Z', '+00:00')) >= recent_cutoff
        ]
        
        if recent_records:
            recent_scores = [float(r.get('engagement_score', 0) or 0) for r in recent_records]
            avg_recent_score = sum(recent_scores) / len(recent_scores) if recent_scores else current_record.score
            
            score_drop = avg_recent_score - current_record.score
            if score_drop > 0.5:
                is_decaying = True
                if len(recent_records) > 1:
                    time_span_hours = (
                        datetime.fromisoformat(recent_records[-1].get('scraped_at', '').replace('Z', '+00:00')) -
                        datetime.fromisoformat(recent_records[0].get('scraped_at', '').replace('Z', '+00:00'))
                    ).total_seconds() / 3600
                    if time_span_hours > 0:
                        decay_rate = score_drop / time_span_hours
    
    if not first_seen or first_seen == current_record.timestamp.isoformat():
        trend_status = 'emerging'
    elif current_record.score >= peak_score * 0.95:
        trend_status = 'peak'
    elif is_decaying:
        trend_status = 'decaying'
    elif current_record.score > float(historical_data[-1].get('engagement_score', 0) or 0):
        trend_status = 'rising'
    else:
        trend_status = 'stale'
    
    current_record.trend_lifecycle = {
        'first_seen': first_seen or current_record.timestamp.isoformat(),
        'peak_time': peak_time or current_record.timestamp.isoformat(),
        'peak_score': peak_score,
        'is_decaying': is_decaying,
        'decay_rate': round(decay_rate, 3) if decay_rate else None,
        'trend_status': trend_status
    }
    
    return current_record

def verify_trend_lifecycle_mapping(record: SocialMediaRecord) -> tuple[bool, List[str]]:
    """
    Verify that all required trend lifecycle fields are properly mapped.
    
    Args:
        record: SocialMediaRecord to validate
    
    Returns:
        Tuple of (is_valid: bool, missing_fields: List[str])
    """
    required_fields = [
        'first_seen', 
        'peak_time', 
        'peak_score', 
        'is_decaying', 
        'decay_rate', 
        'trend_status'
    ]
    
    missing_fields = []
    
    if not record.trend_lifecycle:
        logger.warning(f"Missing trend_lifecycle dict for topic: {record.topic}")
        return False, required_fields
    
    for field in required_fields:
        if field not in record.trend_lifecycle:
            missing_fields.append(field)
    
    if missing_fields:
        logger.warning(
            f"Topic '{record.topic}' missing trend_lifecycle fields: {', '.join(missing_fields)}"
        )
        return False, missing_fields
    
    # Validate field types
    if record.trend_lifecycle.get('is_decaying') is not None:
        if not isinstance(record.trend_lifecycle['is_decaying'], bool):
            logger.warning(f"Topic '{record.topic}': is_decaying should be bool, got {type(record.trend_lifecycle['is_decaying'])}")
    
    if record.trend_lifecycle.get('peak_score') is not None:
        try:
            float(record.trend_lifecycle['peak_score'])
        except (TypeError, ValueError):
            logger.warning(f"Topic '{record.topic}': peak_score should be numeric, got {record.trend_lifecycle['peak_score']}")
    
    logger.debug(f"✅ Trend lifecycle validation passed for topic: {record.topic}")
    return True, []

def upload_to_supabase(
    supabase,
    hashtag_data,
    table_name: str = "tiktok",
    version_id: Optional[str] = None,
    top_n: int = 10,
    use_data_model: bool = True,
    validate: bool = True,
    upsert: bool = True,
    enable_daily_snapshots: bool = True,
    local_cache = None,
    job_queue = None,  # NEW: Job queue for async retries
    chunk_size: int = 100,
    max_batch_size: int = 1000,
    batch_retry_attempts: int = 3,
    batch_retry_delay: float = 1.0
):
    """Upload top N hashtags to Supabase with validation and upserts.
    
    Args:
        supabase: Supabase client instance
        hashtag_data: List of hashtag data to upload
        table_name: Target table name (default: "tiktok")
        version_id: Version ID for grouping records
        top_n: Number of top records to upload (default: 10)
        use_data_model: Use SocialMediaRecord data model (default: True)
        validate: Validate records before upload (default: True)
        upsert: Use upsert instead of insert (default: True)
        enable_daily_snapshots: Enable daily snapshot versioning (default: True)
        local_cache: Local cache instance for offline queue
        job_queue: Job queue instance for async retries (NEW)
        chunk_size: Batch size for uploads (default: 100)
        max_batch_size: Maximum batch size (default: 1000)
        batch_retry_attempts: Number of retry attempts (default: 3)
        batch_retry_delay: Delay between retries in seconds (default: 1.0)
    
    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        if not version_id:
            version_id = str(uuid.uuid4())
        
        snapshot_date = None
        snapshot_version = None
        if enable_daily_snapshots and supabase:
            try:
                snapshot_date = datetime.now(timezone.utc).date().isoformat()
                snapshot_version = get_next_snapshot_version(supabase, table_name, snapshot_date)
                logger.info(f"Daily snapshot: date={snapshot_date}, version={snapshot_version}")
            except Exception as e:
                logger.warning(f"Failed to set snapshot versioning: {e}")
                enable_daily_snapshots = False
        
        if use_data_model:
            records: List[SocialMediaRecord] = []
            invalid_count = 0
            lifecycle_validation_failures = 0
            
            for idx, item in enumerate(hashtag_data):
                if isinstance(item, SocialMediaRecord):
                    record = item
                else:
                    record = SocialMediaRecord.from_scraped_data(item, version_id=version_id)

                if validate:
                    is_valid, error_msg = validate_social_media_record(record)
                    if not is_valid:
                        logger.warning(
                            f"Skipping invalid record at index {idx}: {error_msg} "
                            f"(topic={getattr(record, 'topic', None)})"
                        )
                        invalid_count += 1
                        continue
                
                # NEW: Verify trend lifecycle mapping
                lifecycle_valid, missing_fields = verify_trend_lifecycle_mapping(record)
                if not lifecycle_valid:
                    logger.warning(
                        f"Trend lifecycle validation failed for '{record.topic}': "
                        f"missing fields: {', '.join(missing_fields)}"
                    )
                    lifecycle_validation_failures += 1
                    # Continue anyway - lifecycle data is optional but recommended

                records.append(record)

            if validate and invalid_count:
                logger.info(f"Validation filtered out {invalid_count} invalid records")
            
            if lifecycle_validation_failures:
                logger.warning(
                    f"⚠️ {lifecycle_validation_failures} records have incomplete trend lifecycle data"
                )
            
            sorted_records = sorted(records, key=lambda x: x.score, reverse=True)
            top_records = sorted_records[:top_n]
            
            logger.info(f"Uploading top {len(top_records)} hashtags (from {len(records)} total) to Supabase using standardized data model")
            
            if supabase:
                logger.info("Analyzing trend lifecycle (first seen, peak, decay)...")
                for record in top_records:
                    try:
                        historical_data = get_historical_trend_data(supabase, record.topic, table_name, local_cache=local_cache)
                        record = analyze_trend_lifecycle(record, historical_data)
                        record = analyze_trend_lifecycle(record, historical_data)
                    except Exception as e:
                        logger.error(f"Failed to analyze trend lifecycle for {record.topic}: {e}")
                        # Don't increment metrics here, but ensure visibility
            
            has_collected_at_hour_column = False
            has_language_columns = False
            has_snapshot_columns = False
            
            # Metric columns availability
            has_cols = {
                'comments': False,
                'likes': False,
                'views': False,
                'posts': False,
                'reactions': False
            }
            
            if supabase:
                try:
                    supabase.table(table_name).select("collected_at_hour").limit(0).execute()
                    has_collected_at_hour_column = True
                except Exception:
                    pass
                
                try:
                    supabase.table(table_name).select("language,language_confidence").limit(0).execute()
                    has_language_columns = True
                except Exception:
                    pass
                
                try:
                    supabase.table(table_name).select("snapshot_date,snapshot_version").limit(0).execute()
                    has_snapshot_columns = True
                except Exception:
                    pass

                # Check all metric columns
                for col in has_cols.keys():
                    try:
                        supabase.table(table_name).select(col).limit(0).execute()
                        has_cols[col] = True
                    except Exception:
                        pass
            
            snapshot_date_to_use = snapshot_date if (enable_daily_snapshots and has_snapshot_columns) else None
            snapshot_version_to_use = snapshot_version if (enable_daily_snapshots and has_snapshot_columns) else None
            
            upload_data = [
                record.to_database_format(
                    include_collected_at_hour=has_collected_at_hour_column,
                    include_language=has_language_columns,
                    snapshot_date=snapshot_date_to_use,
                    snapshot_version=snapshot_version_to_use,
                    include_comments=has_cols['comments'],
                    include_likes=has_cols['likes'],
                    include_views=has_cols['views'],
                    include_posts=has_cols['posts'],
                    include_reactions=has_cols['reactions']
                ) 
                for record in top_records
            ]
        else:
            sorted_data = sorted(hashtag_data, key=lambda x: x.get('engagement_score', 0), reverse=True)
            top_hashtags = sorted_data[:top_n]
            
            logger.info(f"Uploading top {len(top_hashtags)} hashtags (from {len(hashtag_data)} total) to Supabase (legacy mode)")
            
            current_time = datetime.now(timezone.utc)
            upload_data = []
            for item in top_hashtags:
                posts_numeric = convert_to_numeric(item.get("posts", "N/A"))
                views_numeric = convert_to_numeric(item.get("views", "N/A"))
                
                sentiment_polarity = item.get("sentiment_polarity", 0.0)
                if isinstance(sentiment_polarity, str):
                    sentiment_polarity = float(sentiment_polarity)
                
                sentiment_label = item.get("sentiment_label", "Neutral")
                engagement_score = item.get("engagement_score", 5.0)
                if isinstance(engagement_score, str):
                    engagement_score = float(engagement_score)
                
                caption = item.get("caption")
                title = item.get("title", item["hashtag"])
                post_format = item.get("post_format", "video")
                sound_name = item.get("sound_name")
                sound_artist = item.get("sound_artist")
                sound_id = item.get("sound_id")
                original_sound = item.get("original_sound", False)
                language = item.get("language")
                language_confidence = item.get("language_confidence")
                
                metadata = {
                    "rank": item.get("rank", "N/A"),
                    "category": item.get("category", "General"),
                    "source_url": "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en",
                    "caption": caption if caption else None,
                    "title": title,
                    "post_format": post_format,
                    "sound": {
                        "name": sound_name,
                        "artist": sound_artist,
                        "sound_id": sound_id,
                        "original_sound": original_sound
                    } if sound_name or sound_artist or sound_id else None
                }
                
                upload_item = {
                    "platform": "TikTok",
                    "topic": item["hashtag"],
                    "engagement_score": engagement_score,
                    "sentiment_polarity": sentiment_polarity,
                    "sentiment_label": sentiment_label,
                    "posts": posts_numeric,
                    "views": views_numeric,
                    "metadata": metadata,
                    "scraped_at": current_time.isoformat(),
                    "version_id": version_id
                }
                
                if language is not None or language_confidence is not None:
                    upload_item["language"] = language
                    upload_item["language_confidence"] = language_confidence
                
                upload_data.append(upload_item)
        
        effective_chunk_size = min(chunk_size, max_batch_size)
        if effective_chunk_size > 100:
            logger.info(f"Using batch size: {effective_chunk_size} records per chunk")
        
        has_language_columns_cached = None
        has_collected_at_hour_cached = None
        if supabase:
            try:
                supabase.table(table_name).select("language,language_confidence").limit(0).execute()
                has_language_columns_cached = True
            except Exception:
                has_language_columns_cached = False
            
            try:
                supabase.table(table_name).select("collected_at_hour").limit(0).execute()
                has_collected_at_hour_cached = True
            except Exception:
                has_collected_at_hour_cached = False
        
        cleaned_upload_data = []
        for item in upload_data:
            cleaned_item = dict(item)
            if not has_language_columns_cached:
                cleaned_item.pop("language", None)
                cleaned_item.pop("language_confidence", None)
            if not has_collected_at_hour_cached:
                cleaned_item.pop("collected_at_hour", None)
            cleaned_upload_data.append(cleaned_item)
        
        can_use_upsert = upsert and has_collected_at_hour_cached
        
        total_uploaded = 0
        total_chunks = (len(cleaned_upload_data) + effective_chunk_size - 1) // effective_chunk_size
        
        for i in range(0, len(cleaned_upload_data), effective_chunk_size):
            chunk = cleaned_upload_data[i:i + effective_chunk_size]
            chunk_num = i // effective_chunk_size + 1
            
            logger.info(f"Inserting chunk {chunk_num}/{total_chunks} ({len(chunk)} records)")
            
            chunk_success = False
            last_error = None
            
            for retry_attempt in range(batch_retry_attempts):
                try:
                    if can_use_upsert:
                        result = (
                            supabase
                            .table(table_name)
                            .upsert(chunk, on_conflict="topic,collected_at_hour")
                            .execute()
                        )
                    else:
                        result = supabase.table(table_name).insert(chunk).execute()
                    
                    if result.data:
                        total_uploaded += len(result.data)
                        chunk_success = True
                        break
                    
                except Exception as chunk_error:
                    last_error = chunk_error
                    logger.warning(f"Chunk {chunk_num} attempt {retry_attempt + 1} failed: {chunk_error}")
                    if retry_attempt < batch_retry_attempts - 1:
                        import time
                        wait_time = batch_retry_delay * (2 ** retry_attempt)
                        time.sleep(wait_time)
            
            if not chunk_success:
                logger.error(f"Chunk {chunk_num} failed permanently after {batch_retry_attempts} attempts. Error: {last_error}")
                if local_cache:
                    logger.info(f"Queuing chunk {chunk_num} to local cache for later retry")
                    local_cache.queue_offline_upload(table_name, chunk)
                else:
                    logger.warning(f"Local cache not available. Chunk {chunk_num} data lost.")
                continue
        
        logger.info(f"Successfully uploaded {total_uploaded} records total")
        return total_uploaded > 0
            
    except Exception as e:
        logger.error(f"Fatal error in upload_to_supabase: {e}", exc_info=True)
        
        if local_cache and 'cleaned_upload_data' in locals() and cleaned_upload_data:
            # If we haven't uploaded anything yet, queue the whole thing
            if total_uploaded == 0:
                logger.info("Fatal error before any chunks uploaded. Queueing all data for offline upload...")
                local_cache.queue_offline_upload(table_name, cleaned_upload_data)
                return True
            
        return False

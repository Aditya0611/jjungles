import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Tuple, List
from supabase import create_client, Client
from twitter_scraper_app.utils import logger
from twitter_scraper_app.config import SCRAPE_VERSION_ID
from twitter_scraper_app.queue_manager import retry_queue
import twitter_scraper_app.config as config

# --- Supabase Initialization ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Optional[Client] = None

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase credentials not found. Running in TEST MODE.")
    config.TEST_MODE = True
else:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not initialize Supabase client: {e}. Running in TEST MODE.")
        config.TEST_MODE = True

# Convenience reference
TEST_MODE = config.TEST_MODE

@dataclass
class TrendRecord:
    """
    Structured data model for trending hashtag records across all platforms.
    
    Attributes:
        platform: Name of the social media platform (e.g., 'Twitter', 'Facebook').
        topic_hashtag: The trending topic or hashtag.
        engagement_score: Calculated engagement metric (0.0 to 10.0).
        sentiment_score: Numerical sentiment polarity (-1.0 to 1.0).
        sentiment_label: Human-readable sentiment (Positive, Negative, Neutral).
        language: Detected language code (ISO 639-1).
        posts: Approximate number of posts/mentions.
        views: Approximate number of views.
        retweets: Number of shares or retweets.
        likes: Number of likes/favorites.
        comments: Number of comments (unified metric).
        reactions: Number of reactions (unified metric).
        metadata: Additional platform-specific data.
        version_id: Unique identifier for the scraping run.
        scraped_at: Timestamp of data extraction.
        first_seen: Timestamp when the topic was first detected.
        last_seen: Timestamp of most recent detection.
    """
    platform: str = "Twitter"
    topic_hashtag: str = ""
    engagement_score: float = 0.0
    sentiment_score: float = 0.0
    sentiment_label: str = "Neutral"
    language: str = "unknown"
    posts: int = 0
    views: int = 0
    retweets: int = 0
    likes: int = 0
    comments: int = 0
    reactions: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    version_id: str = field(default_factory=lambda: SCRAPE_VERSION_ID)
    scraped_at: Optional[datetime] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def to_dict(self, include_timestamps: bool = True) -> Dict[str, Any]:
        """Converts the record to a dictionary suitable for Supabase insertion."""
        now = datetime.now(timezone.utc).isoformat()
        result = {
            "platform": self.platform,
            "topic_hashtag": self.topic_hashtag,
            "engagement_score": float(self.engagement_score),
            "sentiment_polarity": float(self.sentiment_score),
            "sentiment_label": self.sentiment_label,
            "language": self.language,
            "posts": int(self.posts),
            "views": int(self.views),
            "retweets": int(self.retweets),
            "likes": int(self.likes),
            "comments": int(self.comments),
            "reactions": int(self.reactions),
            "metadata": self.metadata,
            "version_id": self.version_id,
            "scraped_at": now
        }
        
        if include_timestamps:
            if self.first_seen:
                result["first_seen"] = self.first_seen.isoformat() if isinstance(self.first_seen, datetime) else self.first_seen
            else:
                result["first_seen"] = now
            
            if self.last_seen:
                result["last_seen"] = self.last_seen.isoformat() if isinstance(self.last_seen, datetime) else self.last_seen
            else:
                result["last_seen"] = now
        return result

    def validate(self) -> bool:
        """Validates the data integrity of the record before DB insertion."""
        if not self.topic_hashtag: return False
        if not (-1.0 <= self.sentiment_score <= 1.0): return False
        if not (0.0 <= self.engagement_score <= 10.0): return False
        if self.sentiment_label not in ["Positive", "Negative", "Neutral"]: return False
        return True

    @classmethod
    def from_db_record(cls, db_record: Dict[str, Any]) -> 'TrendRecord':
        """Reconstructs a TrendRecord object from a database row dictionary."""
        first_seen = None
        last_seen = None
        
        # Helper to parse varying timestamp formats from Supabase
        def parse_ts(ts):
            if not ts: return None
            try:
                if isinstance(ts, datetime): return ts
                if isinstance(ts, str):
                    s = ts.replace('Z', '+00:00')
                    if '.' in s: s = s.split('.')[0] + "+00:00"
                    return datetime.fromisoformat(s)
            except: return None
            return None

        first_seen = parse_ts(db_record.get("first_seen"))
        last_seen = parse_ts(db_record.get("last_seen"))

        return cls(
            platform=db_record.get("platform", "Twitter"),
            topic_hashtag=db_record.get("topic_hashtag", ""),
            engagement_score=float(db_record.get("engagement_score", 0.0)),
            sentiment_score=float(db_record.get("sentiment_score") or db_record.get("sentiment_polarity") or 0.0),
            sentiment_label=db_record.get("sentiment_label", "Neutral"),
            language=db_record.get("language", "unknown"),
            posts=int(db_record.get("posts", 0)),
            views=int(db_record.get("views", 0)),
            retweets=int(db_record.get("retweets", 0)),
            likes=int(db_record.get("likes", 0)),
            comments=int(db_record.get("comments", 0)),
            reactions=int(db_record.get("reactions", 0)),
            metadata=db_record.get("metadata", {}),
            version_id=db_record.get("version_id", SCRAPE_VERSION_ID),
            first_seen=first_seen,
            last_seen=last_seen
        )

    @classmethod
    def from_raw_topic(cls, topic_data: Dict[str, Any], **enrichments) -> 'TrendRecord':
        """Creates a TrendRecord from raw scraped data and enrichment results."""
        now = datetime.now(timezone.utc)
        
        # Merge enrichment fields with defaults
        return cls(
            platform=enrichments.get("platform", "Twitter"),
            topic_hashtag=topic_data.get("topic", ""),
            engagement_score=float(enrichments.get("engagement_score", 1.0)),
            sentiment_score=float(enrichments.get("sentiment_score", 0.0)),
            sentiment_label=str(enrichments.get("sentiment_label", "Neutral")),
            language=str(enrichments.get("language", "unknown")),
            posts=int(enrichments.get("posts", 0)),
            views=int(enrichments.get("views", 0)),
            retweets=int(topic_data.get("retweets") or enrichments.get("retweets", 0)),
            likes=int(topic_data.get("likes") or enrichments.get("likes", 0)),
            comments=int(topic_data.get("comments") or enrichments.get("comments", 0)),
            reactions=int(topic_data.get("reactions") or enrichments.get("reactions", 0)),
            metadata={
                "source": enrichments.get("source", "trends24.in"),
                "twitter_link": enrichments.get("twitter_link", ""),
                "post_content": enrichments.get("post_content", "")
            },
            version_id=SCRAPE_VERSION_ID,
            scraped_at=now,
            first_seen=enrichments.get("first_seen") or now,
            last_seen=enrichments.get("last_seen") or now
        )

def get_existing_trend(topic_hashtag: str, platform: str = "Twitter") -> Optional[TrendRecord]:
    """Fetches the most recent existing trend record for first_seen preservation."""
    if TEST_MODE or not supabase: return None
    try:
        result = supabase.table('twitter').select('*').eq('platform', platform).eq('topic_hashtag', topic_hashtag).order('last_seen', desc=True).limit(1).execute()
        if result.data:
            return TrendRecord.from_db_record(result.data[0])
    except Exception as e:
        logger.warning(f"Error checking existing trend for {topic_hashtag}: {e}")
    return None

def log_scrape_start(scraper_name: str) -> Optional[str]:
    """Logs the start of a scraping run to Supabase and structured logs."""
    if TEST_MODE or not supabase: return None
    try:
        data = {
            "scraper_name": scraper_name,
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        result = supabase.table('scraping_logs').insert(data).execute()
        logger.info(f"{scraper_name}_scrape_start", extra={"event": f"{scraper_name}_scrape_start", "data": data})
        if result.data: return result.data[0]['id']
    except Exception as e:
        logger.warning(f"Failed to log scrape start: {e}")
    return None

def log_scrape_end(log_id: str, status: str, items_scraped: int, error_message: str = None):
    """Logs the completion (success or failure) of a scraping run."""
    if TEST_MODE or not supabase or not log_id: return
    try:
        update_data = {
            "end_time": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "items_scraped": items_scraped
        }
        if error_message:
            update_data["error_message"] = error_message
        
        supabase.table('scraping_logs').update(update_data).eq('id', log_id).execute()
        
        event_name = f"scrape_{status}"
        log_func = logger.info if status == "success" else logger.error
        log_func(event_name, extra={"event": event_name, "data": update_data})
    except Exception as e:
        logger.warning(f"Failed to log scrape end: {e}")

async def process_retry_queue():
    """Attempts to upload records from the local SQLite queue to Supabase."""
    if TEST_MODE or not supabase: return
    
    records = retry_queue.get_all()
    if not records: return

    logger.info(f"Processing local retry queue ({len(records)} items)...")
    success_count = 0
    
    for item in records:
        try:
            supabase.table('twitter').insert(item['data']).execute()
            retry_queue.remove(item['id'])
            success_count += 1
        except Exception:
            continue
            
    if success_count > 0:
        logger.info(f"Successfully uploaded {success_count} items from local retry queue.")

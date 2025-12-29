"""
Supabase storage for hashtag data with sentiment analysis and unified schema.
"""
import json
import uuid
from typing import Dict, List, Optional, Tuple
from supabase import create_client, Client

from .config import get_config
from .logger import logger


def get_supabase_client() -> Client:
	"""Get Supabase client."""
	cfg = get_config()
	if not cfg.supabase_url or not cfg.supabase_anon_key:
		raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
	
	return create_client(cfg.supabase_url, cfg.supabase_anon_key)


def init_database() -> None:
	"""
	Initialize the database table if it doesn't exist.
	"""
	try:
		client = get_supabase_client()
		# Test connection by trying to query the table
		result = client.table("youtube").select("id").limit(1).execute()
		logger.info("Database connection verified (table: youtube)")
	except Exception as e:
		error_msg = str(e)
		if "relation" in error_msg.lower() or "does not exist" in error_msg.lower():
			logger.warning("Table 'youtube' does not exist in Supabase.")
			logger.info("Please create it using the SQL provided in DATABASE_SETUP.md")
		else:
			logger.error(f"Database connection issue: {e}")
			raise


def store_hashtag_data(
	platform: str,
	topic_hashtag: str,
	engagement_score: Optional[float] = None,
	sentiment_polarity: Optional[float] = None,
	sentiment_label: Optional[str] = None,
	posts: Optional[int] = None,
	views: Optional[int] = None,
	likes: Optional[int] = None,
	comments: Optional[int] = None,
	language: Optional[str] = None,
	metadata: Optional[Dict] = None,
	version_id: Optional[str] = None
) -> int:
	"""
	Store a single hashtag record in the database.
	"""
	if version_id is None:
		version_id = str(uuid.uuid4())
	
	client = get_supabase_client()
	
	data = {
		"platform": platform,
		"topic_hashtag": topic_hashtag,
		"engagement_score": engagement_score,
		"sentiment_polarity": sentiment_polarity,
		"sentiment_label": sentiment_label,
		"posts": posts,
		"views": views,
		"likes": likes,
		"comments": comments,
		"language": language,
		"metadata": metadata,
		"version_id": version_id
	}
	
	# Remove None values
	data = {k: v for k, v in data.items() if v is not None}
	
	result = client.table("youtube").insert(data).execute()
	
	if result.data and len(result.data) > 0:
		return result.data[0]["id"]
	else:
		raise Exception("Failed to insert record")


from tenacity import retry, stop_after_attempt, wait_exponential
from .logger import logger

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def store_hashtags_batch(
	records: List[Tuple[str, str, Optional[float], Optional[float], Optional[str], Optional[int], Optional[int], Optional[int], Optional[int], Optional[Dict], Optional[str]]]
) -> None:
	"""
	Store multiple hashtag records in batch.
	"""
	if not records:
		return
	
	version_id = str(uuid.uuid4())
	client = get_supabase_client()
	
	# Prepare data
	data_list = []
	for platform, hashtag, engagement_score, sentiment_polarity, sentiment_label, posts, views, likes, comments, metadata, _ in records:
		record = {
			"platform": platform,
			"topic_hashtag": hashtag,
			"engagement_score": engagement_score,
			"sentiment_polarity": sentiment_polarity,
			"sentiment_label": sentiment_label,
			"posts": posts,
			"views": views,
			"likes": likes,
			"comments": comments,
			"language": metadata.get("language") if isinstance(metadata, dict) else None,
			"metadata": metadata,
			"version_id": version_id
		}
		# Remove None values
		record = {k: v for k, v in record.items() if v is not None}
		data_list.append(record)

	
	# Insert in batches
	batch_size = 100
	total_inserted = 0
	for i in range(0, len(data_list), batch_size):
		batch = data_list[i:i + batch_size]
		try:
			result = client.table("youtube").insert(batch).execute()
			if result.data:
				total_inserted += len(result.data)
			else:
				if hasattr(result, 'error') and result.error:
					raise Exception(f"Supabase error: {result.error}")
				logger.warning(f"Batch {i//batch_size + 1}: Insert completed but no data returned (possible RLS issue)")
		except Exception as e:
			logger.error(f"Failed to insert batch: {e}")
			raise
	
	if total_inserted > 0:
		logger.info(f"Stored {total_inserted} records in Supabase (version_id: {version_id})")
	else:
		logger.warning("Insert completed but no records confirmed. Check RLS policies.")


def get_hashtag_stats(platform: Optional[str] = None, limit: int = 100) -> List[Dict]:
	client = get_supabase_client()
	
	query = client.table("youtube").select("*").order("scraped_at", desc=True).limit(limit)
	
	if platform:
		query = query.eq("platform", platform)
	
	result = query.execute()
	return result.data if result.data else []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def store_scraping_log(
    platform: str,
    status: str,
    items_collected: int,
    error_message: Optional[str] = None,
    duration_seconds: float = 0.0,
    metadata: Optional[Dict] = None
) -> None:
    """Store scraping execution log."""
    try:
        client = get_supabase_client()
        data = {
            "platform": platform,
            "status": status,
            "items_collected": items_collected,
            "error_message": error_message,
            "duration_seconds": duration_seconds,
            "metadata": metadata
        }
        client.table("scraping_logs").insert(data).execute()
        logger.info(f"Scraping log stored: status={status}")
    except Exception as e:
        # Gracefully handle missing scraping_logs table
        error_msg = str(e)
        if "scraping_logs" in error_msg and ("does not exist" in error_msg or "schema cache" in error_msg):
            logger.warning(f"Scraping logs table not found - skipping log storage")
        else:
            logger.error(f"Failed to store scraping log: {e}")


def fetch_trends(limit: int = 1000, platform: str = "All", min_score: float = 0) -> List[Dict]:
    """
    Fetch trending hashtags from the database for the dashboard.
    """
    client = get_supabase_client()
    query = client.table("youtube").select("*").order("scraped_at", desc=True).limit(limit)
    
    if platform != "All":
        query = query.eq("platform", platform)
    
    if min_score > 0:
        query = query.gte("engagement_score", min_score)
        
    result = query.execute()
    return result.data if result.data else []


def fetch_scraping_logs(limit: int = 100) -> List[Dict]:
    """
    Fetch scraping logs from the database.
    """
    client = get_supabase_client()
    query = client.table("scraping_logs").select("*").order("scraped_at", desc=True).limit(limit)
    result = query.execute()
    return result.data if result.data else []

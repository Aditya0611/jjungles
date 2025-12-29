import logging
from typing import List, Dict, Any
from supabase import Client

# Local imports
from models import Config, TrendRecord, ErrorCode
from observability import metrics
from etl_pipeline import ETLPipeline

# Logger instance
logger = logging.getLogger(__name__)

def save_to_supabase(supabase: Client, trend_record: TrendRecord) -> bool:
    """
    Save a single trend record to Supabase using the UNIFIED trends table.
    Ensures compliance with the TrendRecord shape.
    """
    try:
        # Targeting 'trends' table (Unified Schema Requirement)
        table = supabase.table('trends')
        
        # Check if trend exists for this platform/hashtag
        existing = table.select('id').eq('platform', trend_record.platform).eq('topic_hashtag', trend_record.hashtags[0]).execute()
        
        payload = trend_record.to_dict()
        # Map fields to 'trends' schema if necessary (TrendRecord already follows this)
        
        if existing.data:
            logger.info(f"Updating existing trend: {trend_record.hashtags[0]}")
            result = table.update(payload).eq('id', existing.data[0]['id']).execute()
        else:
            logger.info(f"Creating new trend: {trend_record.hashtags[0]}")
            result = table.insert(payload).execute()
            
        if result.data:
            metrics.increment('db_save_success_total')
            return True
        return False
        
    except Exception as e:
        logger.error(f"[{ErrorCode.DB_SAVE_FAILED}] Database error: {e}")
        metrics.increment('db_save_failures_total')
        return False

def save_trends_to_database(supabase: Client, trend_records: List[TrendRecord]) -> Dict[str, int]:
    """
    Process and save multiple trends using the ETL Pipeline for normalization.
    """
    logger.info(f"Processing {len(trend_records)} trends through ETL Pipeline")
    
    etl = ETLPipeline(supabase)
    results = {"success": 0, "failed": 0}
    
    # Unified path: All platforms write to the same structure
    for record in trend_records:
        if save_to_supabase(supabase, record):
            results["success"] += 1
        else:
            results["failed"] += 1
            
    # Also trigger ETL Pipeline for secondary normalization/archiving if needed
    try:
        etl.process_batch(trend_records)
    except Exception as e:
        logger.warning(f"ETL batch process error: {e}")
        
    return results

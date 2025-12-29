import logging
import sys
import json
import asyncio
import functools
import re
import urllib.parse
from datetime import datetime, timezone
import httpx

# JSON Formatter for structured logging
class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs records in a structured JSON format.
    Ensures logs are machine-readable for cloud logging services.
    """
    def format(self, record):
        log_object = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", "log"),
            "message": record.getMessage()
        }
        if hasattr(record, "data") and isinstance(record.data, dict):
            log_object.update(record.data)
        return json.dumps(log_object, ensure_ascii=False)

def setup_logging(logger_name: str = "twitter_scraper") -> logging.Logger:
    """
    Configures a logger with JSON formatting and stdout delivery.
    
    Args:
        logger_name: The internal name for the logger instance.
        
    Returns:
        A configured logging.Logger object.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers if setup multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    
    # Silence verbose network libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logger

# Global logger instance
logger = setup_logging()

def detect_language(text: str) -> str:
    """
    Simple language detection based on text heuristics. 
    It checks for Indian script characters and falls back to English.
    
    Args:
        text: Input string to analyze.
        
    Returns:
        String language code (e.g., 'en', 'hi', 'unknown').
    """
    try:
        clean_text = text.replace('#', '').replace('_', ' ').strip()
        if not clean_text or len(clean_text) < 2:
            return "unknown"
        
        # Check for Indian scripts
        indian_scripts_pattern = re.compile(r'[\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]')
        if indian_scripts_pattern.search(clean_text):
            return "hi" # Hindi/General Indian script
            
        return "en" # Fallback to English for standard hashtags
    except Exception:
        return "unknown"

def parse_post_count(count_str: str) -> int:
    """
    Parses human-readable number strings like '25K', '2.1M' into integers.
    
    Args:
        count_str: The string representation of the count.
        
    Returns:
        The parsed integer value.
    """
    if not count_str or count_str == "N/A":
        return 0
    try:
        clean = count_str.replace(',', '').strip().upper()
        if 'M' in clean:
            return int(float(clean.replace('M', '')) * 1000000)
        if 'K' in clean:
            return int(float(clean.replace('K', '')) * 1000)
        return int(''.join(filter(str.isdigit, clean)))
    except:
        return 0

def generate_twitter_search_link(topic: str) -> str:
    """
    Generates a Twitter search link for a given topic or hashtag.
    
    Args:
        topic: The search query (e.g., "python", "#AI").
        
    Returns:
        A URL string for the Twitter search.
    """
    encoded = urllib.parse.quote(topic)
    return f"https://twitter.com/search?q={encoded}"

def retry_with_backoff(retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """
    Async decorator for exponential backoff retry.
    Catches exceptions and retries the decorated function with increasing delays.
    
    Args:
        retries: The maximum number of times to retry the function.
        initial_delay: The delay in seconds before the first retry.
        backoff_factor: Factor by which the delay increases each retry.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Allow overriding retries via kwargs
            actual_retries = kwargs.pop('max_retries', retries)
            delay = initial_delay
            last_exception = None
            
            for attempt in range(actual_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RuntimeError as e:
                    # Hard-fail for proxy blocks or security violations
                    logger.error(f"Fatal error in {func.__name__}, skipping retries: {e}")
                    raise e
                except Exception as e:
                    last_exception = e
                    if attempt >= actual_retries:
                        logger.error(f"Function {func.__name__} failed after {actual_retries} retries: {e}")
                        break
                    
                    logger.warning(f"Retry {attempt+1}/{actual_retries} for {func.__name__} in {delay:.1f}s: {e}")
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            
            if last_exception:
                raise last_exception
        return wrapper
    return decorator

@retry_with_backoff(retries=3, initial_delay=2.0)
async def robust_request(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    """
    Performs a network request with built-in retry and proxy-block detection.
    It uses httpx.AsyncClient for asynchronous requests and handles common
    HTTP status codes that indicate proxy issues or rate limiting.
    
    Args:
        client: An httpx.AsyncClient instance.
        method: The HTTP method (e.g., "GET", "POST").
        url: The URL to request.
        **kwargs: Additional keyword arguments passed to client.request. 
               Can include 'max_retries' to override default decorator behavior.
        
    Raises:
        RuntimeError: If a fatal proxy block (403, 429, 407) is detected.
        httpx.HTTPStatusError: For other HTTP errors, especially 4xx client errors.
        Exception: For network-related errors.
        
    Returns:
        The httpx.Response object if the request is successful.
    """
    # Strict No-Bypass: Verify client has a proxy configured
    if not hasattr(client, "_mounts") or not any("proxy" in str(type(t)).lower() for t in client._mounts.values()):
        logger.error("FATAL: robust_request called with a non-proxied client.")
        raise RuntimeError("No bypass allowed. Requests must use a proxy.")

    try:
        response = await client.request(method, url, **kwargs)
        
        # Hard fail on fatal proxy-block symptoms
        if response.status_code == 407:
            raise RuntimeError("Proxy Authentication Required: 407")
        
        if response.status_code == 403:
            raise RuntimeError("Access Forbidden: 403 (Potential Proxy Block)")
            
        if response.status_code == 429:
            raise RuntimeError("Rate Limited: 429")

        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as e:
        # Re-raise for retry_with_backoff to handle if it's a 5xx or other transient error
        if e.response.status_code >= 500:
            raise e
        # For 4xx (other than 403/429/407 which we handled), log and raise
        logger.warning(f"HTTP Error {e.response.status_code} for {url}")
        raise e
    except Exception as e:
        # Network errors, timeouts etc will be caught by retry_with_backoff
        raise e

def format_engagement_display(score: float) -> str:
    """
    Formats a numeric engagement score into a terminal-friendly string with an emoji
    and a descriptive text based on predefined thresholds.
    
    Args:
        score: The numerical engagement score.
        
    Returns:
        A formatted string representing the engagement level.
    """
    if score >= 8:
        return f"🔥 {score} (Very High)"
    elif score >= 6:
        return f"⚡ {score} (High)"
    elif score >= 4:
        return f"📈 {score} (Medium)"
    elif score >= 2:
        return f"📊 {score} (Low)"
    else:
        return f"📉 {score} (Very Low)"

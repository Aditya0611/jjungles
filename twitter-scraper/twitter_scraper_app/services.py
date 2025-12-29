import asyncio
import httpx
from bs4 import BeautifulSoup
from textblob import TextBlob
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from twitter_scraper_app.utils import (
    logger, 
    detect_language, 
    parse_post_count, 
    generate_twitter_search_link, 
    robust_request,
    format_engagement_display
)
from twitter_scraper_app.config import NITTER_INSTANCES, proxy_manager, TEST_MODE, SCRAPE_VERSION_ID
from twitter_scraper_app.db import (
    TrendRecord, 
    get_existing_trend, 
    supabase,
    process_retry_queue
)
from twitter_scraper_app.queue_manager import retry_queue

async def fetch_tweets_for_hashtag(hashtag: str, max_tweets: int = 5) -> List[str]:
    """
    Asynchronously fetches recent tweets for a hashtag via various Nitter instances.
    
    Args:
        hashtag: The hashtag to search for.
        max_tweets: Maximum number of tweet snippets to return.
        
    Returns:
        A list of tweet text snippets.
    """
    query = hashtag.replace('#', '%23')
    
    # We rotate through instances if one fails
    for instance in NITTER_INSTANCES:
        rss_url = f"{instance}/search/rss?f=tweets&q={query}"
        logger.debug(f"Attempting Nitter instance {instance} for {hashtag}")
        
        try:
            # We use max_retries=0 for Nitter to fail fast and move to the next instance
            response = await robust_fetch(rss_url, max_retries=0)
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item')
                tweets = [item.find('title').get_text() for item in items[:max_tweets] if item.find('title')]
                
                if tweets:
                    logger.info(f"Fetched {len(tweets)} tweets from {instance} for {hashtag}")
                    return tweets
        except Exception as e:
            # Short log for instance failure to keep terminal clean
            logger.warning(f"Instance {instance} failed for {hashtag}: {str(e)[:100]}")
            continue
    
    logger.warning(f"All Nitter instances failed for {hashtag}")
    return []

async def robust_fetch(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 30.0, max_retries: int = 3) -> httpx.Response:
    """
    Performs an HTTP GET request with manual proxy rotation and exponential backoff.
    
    Args:
        url: target URL.
        headers: Optional request headers.
        timeout: Request timeout in seconds.
        max_retries: Number of internal retries before giving up on this URL.
        
    Returns:
        The successful httpx.Response object.
    """
    delay = 1.0
    backoff = 2.0
    
    last_exc = None
    for attempt in range(max_retries + 1):
        current_proxy = proxy_manager.get_proxy()
        if not current_proxy:
            logger.error("FATAL: get_proxy() returned None. Enforcement failed.")
            raise RuntimeError("No proxy available for scraping. Proxy enforcement is strict.")
            
        proxy_url = current_proxy.get("http://")
        if not proxy_url:
            logger.error(f"FATAL: Proxy dict missing http key: {current_proxy}")
            raise RuntimeError("Selected proxy is invalid (missing URL).")
        
        try:
            async with httpx.AsyncClient(
                timeout=timeout, 
                proxy=proxy_url, 
                follow_redirects=True, 
                headers=headers,
                verify=False
            ) as client:
                # robust_request handles 403/429/407 and has its own internal decorator retries
                # We pass max_retries=0 to robust_request to prevent nested retries
                response = await robust_request(client, "GET", url, max_retries=0)
                return response
        except Exception as e:
            if max_retries > 0:
                logger.warning(f"Fetch attempt {attempt+1} failed: {e}")
            last_exc = e
            
        if attempt < max_retries:
            await asyncio.sleep(delay)
            delay *= backoff
            
    raise last_exc if last_exc else Exception("Unknown error in robust_fetch")

async def get_hashtag_post_content(hashtag: str) -> str:
    """Combines recent tweets into a single string for analysis."""
    tweets = await fetch_tweets_for_hashtag(hashtag)
    if tweets:
        return " ".join(tweets)
    return f"Trending topic: {hashtag}. Join the conversation on social media."

def analyze_hashtag_sentiment(hashtag: str, post_content: Optional[str] = None) -> Tuple[str, float]:
    """
    Analyzes sentiment using NLP (TextBlob) and keyword matching.
    
    Returns:
        A tuple of (sentiment_label, sentiment_score).
    """
    try:
        text_to_analyze = post_content if post_content else hashtag.replace('#', '').replace('_', ' ')
        hashtag_lower = hashtag.lower()
        keyword_score = 0.0
        
        positive = ['victory', 'success', 'amazing', 'great', 'love', 'proud', 'happy', 'win', 'good']
        negative = ['ban', 'crisis', 'disaster', 'attack', 'fail', 'problem', 'death', 'angry', 'bad']
        
        content_lower = (post_content or "").lower()
        for k in positive:
            if k in hashtag_lower or k in content_lower: keyword_score += 0.1
        for k in negative:
            if k in hashtag_lower or k in content_lower: keyword_score -= 0.1
            
        blob = TextBlob(text_to_analyze)
        text_polarity = blob.sentiment.polarity
        
        # Weighted combination
        combined = (text_polarity * 0.7) + (keyword_score * 0.3)
        combined = max(-1.0, min(1.0, combined))
        
        if combined > 0.05: sentiment = "Positive"
        elif combined < -0.05: sentiment = "Negative"
        else: sentiment = "Neutral"
        
        return sentiment, round(float(combined), 3)
    except Exception as e:
        logger.error(f"Sentiment analysis error for {hashtag}: {e}")
        return "Neutral", 0.0

def calculate_engagement_score(topic_data: Dict[str, Any], existing_record: Optional[TrendRecord] = None) -> float:
    """
    Calculates a 0-10 engagement score based on posts, retweets, and likes.
    """
    try:
        count_str = topic_data.get("count", "N/A")
        posts_count = parse_post_count(count_str)
        retweets = topic_data.get("retweets", 0)
        likes = topic_data.get("likes", 0)
        comments = topic_data.get("comments", 0)
        reactions = topic_data.get("reactions", 0)
        
        score = 1.0
        import math
        if posts_count > 0:
            score += min(4.0, max(0, math.log10(posts_count + 1) * 1.2))
        else:
            score += 0.3
            
        if retweets > 0:
            score += min(1.5, max(0, math.log10(retweets + 1) * 0.5))
        if likes > 0:
            score += min(1.5, max(0, math.log10(likes + 1) * 0.5))
        if comments > 0:
            score += min(1.0, max(0, math.log10(comments + 1) * 0.4))
        if reactions > 0:
            score += min(1.0, max(0, math.log10(reactions + 1) * 0.4))
        
        # Duration bonus if still trending
        if existing_record and existing_record.first_seen:
            score += 0.5
        
        return float(max(1.0, min(10.0, round(score, 2))))
    except Exception as e:
        logger.error(f"Engagement calculation error: {e}")
        return 1.0

async def process_single_topic(topic: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriches a single topic with sentiment, engagement, and language detection.
    """
    existing_trend = get_existing_trend(topic["topic"])
    topic["engagement_score"] = calculate_engagement_score(topic, existing_trend)
    
    post_content = await get_hashtag_post_content(topic["topic"])
    sentiment_label, sentiment_score = analyze_hashtag_sentiment(topic["topic"], post_content)
    
    topic["sentiment_label"] = sentiment_label
    topic["sentiment_score"] = sentiment_score
    topic["language"] = detect_language(post_content if post_content else topic["topic"])
    topic["post_content"] = post_content
    topic["first_seen"] = existing_trend.first_seen if existing_trend else None
    
    logger.info(f"Processed: {topic['topic']} ({topic['count']}) - Eng: {format_engagement_display(topic['engagement_score'])}")
    return topic

async def get_trending_topics() -> List[Dict[str, Any]]:
    """
    Scrapes trends24.in India trends concurrently across multiple mirrors.
    """
    urls = [
        "https://trends24.in/india/",
        "http://trends24.in/india/",
        "https://www.trends24.in/india/"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    async def fetch_one(url):
        try:
            return await robust_fetch(url, headers=headers)
        except RuntimeError as e:
            # Re-raise fatal proxy/security errors to trigger hard-fail
            raise e
        except Exception as e:
            logger.error(f"Failed to fetch trends from {url}: {e}")
            return None

    # concurrent fetch mirrors
    results = await asyncio.gather(*[fetch_one(u) for u in urls])
    
    for response in results:
        if not response or response.status_code != 200:
            continue
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            list_container = soup.find('div', class_='list-container')
            if not list_container: continue
            
            trend_list = list_container.find('ol', class_='trend-card__list') or list_container
            lis = trend_list.find_all('li')
            
            topics = []
            for li in lis:
                link = li.find('a')
                if link:
                    topic_name = link.get_text(strip=True)
                    count_span = li.find('span', class_='trend-card__list-count')
                    count = count_span.get_text(strip=True) if count_span else "N/A"
                    topics.append({"topic": topic_name, "count": count})
            
            if topics:
                # Deduplicate while preserving order
                unique = []
                seen = set()
                for t in topics:
                    if t['topic'] not in seen:
                        seen.add(t['topic'])
                        unique.append(t)
                logger.info(f"Found {len(unique)} trends from {response.url}")
                return unique
        except Exception as e:
            logger.error(f"Failed to parse trends: {e}")
            
    logger.error("All trend mirrors failed or returned no data.")
    return []

async def insert_fresh_data_only(topics_list: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Transforms enriched topics into DB records and upserts them to Supabase.
    """
    if not topics_list or TEST_MODE:
        return 0, 0

    try:
        await process_retry_queue()

        inserted_count = 0
        updated_count = 0
        
        for topic in topics_list:
            posts_val = parse_post_count(topic.get("count", "0"))
            
            record = TrendRecord.from_raw_topic(
                topic_data=topic,
                engagement_score=topic.get("engagement_score", 1.0),
                sentiment_label=topic.get("sentiment_label", "Neutral"),
                sentiment_score=topic.get("sentiment_score", 0.0),
                language=topic.get("language", "unknown"),
                post_content=topic.get("post_content", ""),
                posts=posts_val,
                views=topic.get("views", 0),
                retweets=topic.get("retweets", 0),
                likes=topic.get("likes", 0),
                comments=topic.get("comments", 0),
                reactions=topic.get("reactions", 0),
                twitter_link=generate_twitter_search_link(topic["topic"]),
                source="trends24.in",
                first_seen=topic.get("first_seen")
            )
            
            if not record.validate():
                continue

            data = record.to_dict()
            existing = get_existing_trend(record.topic_hashtag)
            
            try:
                if existing:
                    # preserve first_seen
                    if existing.first_seen:
                        data['first_seen'] = existing.first_seen.isoformat()
                    data['last_seen'] = datetime.now(timezone.utc).isoformat()
                    
                    data.pop('first_seen', None) # Prevent overwrite
                    supabase.table('twitter').update(data).eq('platform', 'Twitter').eq('topic_hashtag', record.topic_hashtag).execute()
                    updated_count += 1
                else:
                    supabase.table('twitter').insert(data).execute()
                    inserted_count += 1
            except Exception as e:
                logger.error(f"DB error for {record.topic_hashtag}: {e}")
                retry_queue.add(data)
                    
        logger.info(f"Sync complete: {inserted_count} new, {updated_count} updated.")
        return inserted_count, updated_count
        
    except Exception as e:
        logger.error(f"Data orchestration failure: {e}")
        return 0, 0

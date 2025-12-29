import time
import logging
import random
from typing import List, Dict, Any, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from textblob import TextBlob

# Local imports
from models import (
    Config, ErrorCode, DEFAULT_LANGUAGE,
    DELAY_POST_LOAD_MIN, DELAY_POST_LOAD_MAX,
    TIMEOUT_SELECTOR_WAIT
)
from observability import metrics
from engagement_calculator import calculate_engagement_score

# Optional third-party imports
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_ANALYZER = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

try:
    from langdetect import detect, detect_langs
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

# Logger instance
logger = logging.getLogger(__name__)

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyze sentiment using TextBlob and VADER (if available)."""
    if not text or len(text.strip()) < 3:
        return {'polarity': 0.0, 'label': 'neutral', 'combined_score': 0.0}
        
    try:
        # TextBlob sentiment
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # VADER sentiment (more accurate for social media)
        combined_score = polarity
        if VADER_AVAILABLE:
            vader_scores = VADER_ANALYZER.polarity_scores(text)
            combined_score = (polarity + vader_scores['compound']) / 2
            
        label = 'neutral'
        if combined_score > 0.05:
            label = 'positive'
        elif combined_score < -0.05:
            label = 'negative'
            
        return {'polarity': polarity, 'label': label, 'combined_score': combined_score}
    except Exception as e:
        logger.debug(f"Sentiment analysis error: {e}")
        return {'polarity': 0.0, 'label': 'neutral', 'combined_score': 0.0}

def detect_language(text: str) -> Dict[str, Any]:
    """Detect language from text."""
    if not LANGDETECT_AVAILABLE or not text or len(text.strip()) < 10:
        return {'language': DEFAULT_LANGUAGE, 'confidence': 0.0, 'detected': False}
        
    try:
        lang = detect(text)
        langs = detect_langs(text)
        confidence = langs[0].prob if langs else 0.0
        return {'language': lang, 'confidence': confidence, 'detected': True}
    except Exception as e:
        logger.debug(f"Language detection error: {e}")
        return {'language': DEFAULT_LANGUAGE, 'confidence': 0.0, 'detected': False}

def scrape_post_metrics(page: Page, post_url: str) -> Dict[str, Any]:
    """Scrape metrics from a single post."""
    try:
        page.goto(post_url, wait_until="networkidle")
        time.sleep(random.uniform(DELAY_POST_LOAD_MIN, DELAY_POST_LOAD_MAX))
        
        # Extract metrics (simplified for brevity, actual logic should be robust)
        likes = 0
        comments = 0
        views = 0
        
        # Try to find likes
        like_selectors = ["span:has-text('likes')", "button:has-text('likes')"]
        for sel in like_selectors:
            try:
                text = page.locator(sel).first.inner_text()
                nums = [int(s) for s in text.replace(',', '').split() if s.isdigit()]
                if nums:
                    likes = nums[0]
                    break
            except:
                continue
                
        # Get caption for sentiment/language
        caption = ""
        try:
            caption_element = page.locator("h1").first
            caption = caption_element.inner_text()
            except Exception as e:
                logger.debug(f"Could not extract caption: {e}")
                pass
            
        sentiment = analyze_sentiment(caption)
        language = detect_language(caption)
        
        return {
            'url': post_url,
            'likes': likes,
            'comments': comments,
            'views': views,
            'caption': caption,
            'sentiment': sentiment,
            'language': language
        }
    except Exception as e:
        logger.error(f"Error scraping post {post_url}: {e}")
        return None

def analyze_hashtag_engagement(page: Page, hashtag_info: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze engagement for a hashtag by scraping sample posts."""
    hashtag = hashtag_info['hashtag']
    logger.info(f"Analyzing engagement for #{hashtag}")
    
    posts = hashtag_info.get('sample_posts', [])[:Config.POSTS_PER_HASHTAG]
    if not posts:
        return None
        
    post_data = []
    for post_url in posts:
        if not post_url.startswith('http'):
            post_url = f"https://www.instagram.com{post_url}"
        data = scrape_post_metrics(page, post_url)
        if data:
            post_data.append(data)
            
    if not post_data:
        return None
        
    avg_likes = sum(p['likes'] for p in post_data) / len(post_data)
    avg_comments = sum(p['comments'] for p in post_data) / len(post_data)
    avg_views = sum(p['views'] for p in post_data) / len(post_data)
    
    score = calculate_engagement_score(avg_likes, avg_comments, avg_views)
    
    return {
        'avg_likes': avg_likes,
        'avg_comments': avg_comments,
        'avg_views': avg_views,
        'avg_engagement': score,
        'post_data': post_data,
        'language_summary': {
            'primary_language': post_data[0]['language']['language'] if post_data and post_data[0]['language']['detected'] else DEFAULT_LANGUAGE
        }
    }

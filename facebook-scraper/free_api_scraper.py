#!/usr/bin/env python3
"""
Free Third-Party API Facebook Scraper
=====================================

Uses free/open-source libraries and APIs for Facebook scraping:
1. facebook-scraper (kevinzg) - Completely free, open-source
2. Facebook Graph API - Official API (limited but free)
3. Crawlbase - 1,000 free requests
4. ScrapeCreators - 100 free API calls

Usage:
------
    from free_api_scraper import FreeAPIFacebookScraper
    
    scraper = FreeAPIFacebookScraper(api_type='facebook_scraper')
    results = scraper.get_trending_hashtags('technology')
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import logging

# Try to import free libraries
try:
    from facebook_scraper import get_posts, get_profile, get_group_info
    FACEBOOK_SCRAPER_AVAILABLE = True
except ImportError:
    FACEBOOK_SCRAPER_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

# Try to import language detection (optional but recommended)
try:
    from langdetect import detect as langdetect_detect, detect_langs, DetectorFactory
    DetectorFactory.seed = 0  # For consistent results
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    # Fallback: define placeholder functions
    def langdetect_detect(text):
        return 'en'
    def detect_langs(text):
        return []

from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# FREE API ADAPTERS
# ============================================================================

class FacebookScraperAPI:
    """
    Adapter for facebook-scraper library (kevinzg/facebook-scraper)
    Completely free, open-source, no credits required.
    """
    
    def __init__(self, cookies: Optional[str] = None, proxy: Optional[str] = None):
        """
        Initialize facebook-scraper API.
        
        Args:
            cookies: Optional cookies file path for authentication
            proxy: Optional proxy URL
        """
        if not FACEBOOK_SCRAPER_AVAILABLE:
            raise ImportError(
                "facebook-scraper not installed. "
                "Install with: pip install facebook-scraper"
            )
        self.cookies = cookies
        self.proxy = proxy
        self.logger = logging.getLogger(__name__)
    
    def get_posts_by_keyword(self, keyword: str, pages: int = 5) -> List[Dict]:
        """
        Get posts by searching for a keyword.
        
        Args:
            keyword: Search keyword
            pages: Number of pages to scrape
            
        Returns:
            List of post dictionaries
        """
        try:
            # Search URL format
            search_url = f"https://www.facebook.com/search/posts/?q={keyword}"
            
            posts = []
            options = {
                'posts_per_page': 25,
                'cookies': self.cookies,
                'proxy': self.proxy
            }
            
            # Get posts from search
            for post in get_posts(search_url, pages=pages, options=options):
                posts.append({
                    'text': post.get('text', ''),
                    'post_id': post.get('post_id', ''),
                    'time': post.get('time', None),
                    'likes': post.get('likes', 0),
                    'comments': post.get('comments', 0),
                    'shares': post.get('shares', 0),
                    'reactions': post.get('reactions', {}),
                    'post_url': post.get('post_url', ''),
                })
                
                if len(posts) >= pages * 25:
                    break
            
            return posts
            
        except Exception as e:
            self.logger.error(f"Error fetching posts: {e}")
            return []
    
    def get_page_posts(self, page_name: str, pages: int = 5) -> List[Dict]:
        """
        Get posts from a Facebook page.
        
        Args:
            page_name: Facebook page name or ID
            pages: Number of pages to scrape
            
        Returns:
            List of post dictionaries
        """
        try:
            posts = []
            options = {
                'posts_per_page': 25,
                'cookies': self.cookies
            }
            
            for post in get_posts(page_name, pages=pages, options=options):
                posts.append({
                    'text': post.get('text', ''),
                    'post_id': post.get('post_id', ''),
                    'time': post.get('time', None),
                    'likes': post.get('likes', 0),
                    'comments': post.get('comments', 0),
                    'shares': post.get('shares', 0),
                    'reactions': post.get('reactions', {}),
                    'post_url': post.get('post_url', ''),
                })
            
            return posts
            
        except Exception as e:
            self.logger.error(f"Error fetching page posts: {e}")
            return []


class FacebookGraphAPI:
    """
    Adapter for Facebook Graph API (Official, Free but Limited)
    Requires App ID and App Secret.
    """
    
    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        """
        Initialize Facebook Graph API.
        
        Args:
            app_id: Facebook App ID
            app_secret: Facebook App Secret
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library not installed")
        
        self.app_id = app_id or os.getenv('FACEBOOK_APP_ID')
        self.app_secret = app_secret or os.getenv('FACEBOOK_APP_SECRET')
        self.access_token = None
        self.base_url = "https://graph.facebook.com/v18.0"
        self.logger = logging.getLogger(__name__)
        
        if self.app_id and self.app_secret:
            self._get_access_token()
    
    def _get_access_token(self):
        """Get access token for Graph API"""
        try:
            url = f"{self.base_url}/oauth/access_token"
            params = {
                'client_id': self.app_id,
                'client_secret': self.app_secret,
                'grant_type': 'client_credentials'
            }
            response = requests.get(url, params=params)
            data = response.json()
            self.access_token = data.get('access_token')
        except Exception as e:
            self.logger.error(f"Error getting access token: {e}")
    
    def search_public_posts(self, query: str, limit: int = 25) -> List[Dict]:
        """
        Search public posts (limited functionality without user token).
        
        Args:
            query: Search query
            limit: Number of results
            
        Returns:
            List of post dictionaries
        """
        if not self.access_token:
            self.logger.warning("No access token available")
            return []
        
        try:
            # Note: Graph API has limited public search capabilities
            # Most endpoints require user authentication
            url = f"{self.base_url}/search"
            params = {
                'q': query,
                'type': 'post',
                'limit': limit,
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            posts = []
            for item in data.get('data', []):
                posts.append({
                    'text': item.get('message', ''),
                    'post_id': item.get('id', ''),
                    'created_time': item.get('created_time', ''),
                    'likes': item.get('likes', {}).get('summary', {}).get('total_count', 0),
                    'comments': item.get('comments', {}).get('summary', {}).get('total_count', 0),
                    'shares': item.get('shares', {}).get('count', 0),
                })
            
            return posts
            
        except Exception as e:
            self.logger.error(f"Error searching posts: {e}")
            return []


class CrawlbaseAPI:
    """
    Adapter for Crawlbase Facebook Scraper
    Free tier: 1,000 requests
    """
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Crawlbase API.
        
        Args:
            api_token: Crawlbase API token (get from crawlbase.com)
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library not installed")
        
        self.api_token = api_token or os.getenv('CRAWLBASE_API_TOKEN')
        self.base_url = "https://api.crawlbase.com"
        self.logger = logging.getLogger(__name__)
        
        if not self.api_token:
            self.logger.warning("No Crawlbase API token found. Sign up at crawlbase.com for 1,000 free requests")
    
    def scrape_facebook_page(self, page_url: str) -> Optional[Dict]:
        """
        Scrape a Facebook page using Crawlbase.
        
        Args:
            page_url: Facebook page URL
            
        Returns:
            Page data dictionary
        """
        if not self.api_token:
            return None
        
        try:
            url = f"{self.base_url}/scraper"
            params = {
                'token': self.api_token,
                'url': page_url,
                'format': 'json'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error scraping with Crawlbase: {e}")
            return None


# ============================================================================
# FREE API FACEBOOK SCRAPER
# ============================================================================

class FreeAPIFacebookScraper:
    """
    Free third-party API scraper for Facebook.
    Uses free/open-source libraries and APIs.
    """
    
    def __init__(self, api_type: str = 'facebook_scraper', **kwargs):
        """
        Initialize free API scraper.
        
        Args:
            api_type: Type of API to use
                - 'facebook_scraper': facebook-scraper library (recommended, free)
                - 'graph_api': Facebook Graph API (official, limited)
                - 'crawlbase': Crawlbase API (1,000 free requests)
        """
        self.api_type = api_type
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Proxy Support
        self.proxy = kwargs.get('proxy')
        if not self.proxy:
            proxy_string = os.getenv('PROXIES', '')
            if proxy_string:
                proxies = [p.strip() for p in proxy_string.split(',') if p.strip()]
                if proxies:
                    self.proxy = random.choice(proxies)
        
        if not self.proxy:
            self.logger.critical("FATAL: No proxy configured for Free API Scraper. Application cannot continue.")
            sys.exit(1)

        # Initialize API based on type
        if api_type == 'facebook_scraper':
            cookies = kwargs.get('cookies') or os.getenv('FACEBOOK_COOKIES_FILE')
            self.api = FacebookScraperAPI(cookies=cookies, proxy=self.proxy)
            self.logger.info("Using facebook-scraper library (free, open-source)")
            
        elif api_type == 'graph_api':
            self.api = FacebookGraphAPI()
            self.logger.info("Using Facebook Graph API (official, limited)")
            
        elif api_type == 'crawlbase':
            self.api = CrawlbaseAPI()
            self.logger.info("Using Crawlbase API (1,000 free requests)")
            
        else:
            raise ValueError(f"Unknown API type: {api_type}")
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        hashtags = re.findall(r'#(\w+)', text)
        return list(set(hashtags))
    
    def detect_language(self, text: str, min_confidence: float = 0.3) -> Tuple[str, float]:
        """
        Detect language of text using langdetect.
        
        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            Tuple of (language_code, confidence)
            - language_code: ISO 639-1 language code (e.g., 'en', 'es', 'fr')
            - confidence: Detection confidence (0.0 to 1.0)
        """
        if not text or len(text.strip()) < 10:
            return 'en', 0.0  # Default to English for very short text
        
        if not LANGDETECT_AVAILABLE:
            return 'en', 0.5  # Default if langdetect not available
        
        try:
            # Detect primary language
            detected_lang = langdetect_detect(text)
            
            # Get confidence score from multiple language probabilities
            try:
                languages = detect_langs(text)
                if languages:
                    # Confidence is the probability of the top language
                    confidence = languages[0].prob
                    detected_lang = languages[0].lang
                    
                    # If confidence is below threshold, default to 'en'
                    if confidence < min_confidence:
                        return 'en', confidence
                    
                    return detected_lang, round(confidence, 3)
                else:
                    return detected_lang, 0.5
            except:
                # Fallback if detect_langs fails
                return detected_lang, 0.7
            
        except Exception as e:
            self.logger.debug(f"Language detection failed: {e}", extra={'text_preview': text[:50]})
            return 'en', 0.0  # Default to English on error
    
    def analyze_sentiment(self, text: str) -> tuple:
        """Analyze sentiment using TextBlob"""
        if not TEXTBLOB_AVAILABLE:
            return "neutral", 0.0
        
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return sentiment, round(polarity, 3)
        except:
            return "neutral", 0.0
    
    def get_trending_hashtags(self, category: str, max_posts: int = 50) -> List[Dict]:
        """
        Get trending hashtags for a category.
        
        Args:
            category: Category name
            max_posts: Maximum posts to analyze
            
        Returns:
            List of hashtag dictionaries
        """
        # Category keywords
        category_keywords = {
            'technology': ['technology', 'tech', 'AI', 'software', 'coding'],
            'business': ['business', 'entrepreneur', 'startup', 'marketing'],
            'health': ['health', 'fitness', 'wellness', 'nutrition'],
            'food': ['food', 'recipe', 'cooking', 'restaurant'],
        }
        
        keywords = category_keywords.get(category.lower(), [category])
        all_hashtag_data = {}
        
        self.logger.info(f"Scraping trending hashtags for category: {category}")
        
        # Get posts for each keyword
        for keyword in keywords[:3]:  # Limit to 3 keywords
            self.logger.info(f"Searching for keyword: {keyword}")
            
            try:
                if self.api_type == 'facebook_scraper':
                    posts = self.api.get_posts_by_keyword(keyword, pages=max_posts // 25)
                elif self.api_type == 'graph_api':
                    posts = self.api.search_public_posts(keyword, limit=max_posts)
                else:
                    self.logger.warning(f"API type {self.api_type} not fully implemented for keyword search")
                    continue
                
                # Process posts
                for post in posts:
                    text = post.get('text', '')
                    if not text:
                        continue
                    
                    # Extract hashtags
                    hashtags = self.extract_hashtags(text)
                    
                    # Analyze sentiment
                    sentiment, polarity = self.analyze_sentiment(text)
                    
                    # Detect language
                    language, lang_confidence = self.detect_language(text)
                    
                    # Get engagement metrics
                    likes = post.get('likes', 0) or post.get('reactions', {}).get('total', 0)
                    comments = post.get('comments', 0)
                    shares = post.get('shares', 0)
                    engagement = likes + comments + shares
                    
                    # Process each hashtag
                    for tag in hashtags:
                        tag_lower = tag.lower()
                        
                        if tag_lower in all_hashtag_data:
                            # Update existing
                            data = all_hashtag_data[tag_lower]
                            data['post_count'] += 1
                            data['total_engagement'] += engagement
                            data['likes'] += likes
                            data['comments'] += comments
                            data['shares'] += shares
                            
                            # Update language statistics
                            if 'languages' not in data:
                                data['languages'] = {}
                            data['languages'][language] = data['languages'].get(language, 0) + 1
                            if 'language_confidences' not in data:
                                data['language_confidences'] = []
                            data['language_confidences'].append(lang_confidence)
                        else:
                            # Create new
                            all_hashtag_data[tag_lower] = {
                                'hashtag': tag,
                                'category': category,
                                'post_count': 1,
                                'total_engagement': engagement,
                                'likes': likes,
                                'comments': comments,
                                'shares': shares,
                                'sentiment': sentiment,
                                'sentiment_score': polarity,
                                'languages': {language: 1},
                                'language_confidences': [lang_confidence]
                            }
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                self.logger.error(f"Error processing keyword {keyword}: {e}")
                continue
        
        # Calculate final metrics
        results = []
        for tag_data in all_hashtag_data.values():
            count = tag_data['post_count']
            tag_data['avg_engagement'] = tag_data['total_engagement'] / count
            tag_data['avg_likes'] = tag_data['likes'] / count
            tag_data['avg_comments'] = tag_data['comments'] / count
            tag_data['avg_shares'] = tag_data['shares'] / count
            
            # Calculate engagement score (1-10)
            avg_eng = tag_data['avg_engagement']
            if avg_eng > 10000:
                engagement_score = 10.0
            elif avg_eng > 5000:
                engagement_score = 8.0
            elif avg_eng > 1000:
                engagement_score = 6.0
            elif avg_eng > 100:
                engagement_score = 4.0
            else:
                engagement_score = 2.0
            
            tag_data['engagement_score'] = engagement_score
            tag_data['trending_score'] = engagement_score * 10  # Scale to 0-100
            
            # Determine primary language (most common language)
            languages = tag_data.get('languages', {})
            if languages:
                primary_language = max(languages.items(), key=lambda x: x[1])[0]
                tag_data['primary_language'] = primary_language
                tag_data['language_distribution'] = languages
            else:
                tag_data['primary_language'] = 'en'
                tag_data['language_distribution'] = {'en': count}
            
            # Calculate average language confidence
            lang_confidences = tag_data.get('language_confidences', [])
            if lang_confidences:
                tag_data['avg_language_confidence'] = round(sum(lang_confidences) / len(lang_confidences), 3)
            else:
                tag_data['avg_language_confidence'] = 0.0
            
            # Clean up temporary fields
            tag_data.pop('language_confidences', None)  # Remove raw list, keep avg
            
            results.append(tag_data)
        
        # Sort by trending score
        results.sort(key=lambda x: x['trending_score'], reverse=True)
        
        self.logger.info(f"Found {len(results)} unique hashtags")
        
        return results[:10]  # Return top 10
    
    def save_results(self, results: List[Dict], category: str, filename: Optional[str] = None):
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/facebook_free_api_{category}_{timestamp}.json"
        
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Results saved to {filepath}")


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_free_api_scraper(api_type: str = 'facebook_scraper', **kwargs):
    """
    Factory function to create free API scraper.
    
    Args:
        api_type: 'facebook_scraper' (recommended), 'graph_api', or 'crawlbase'
        **kwargs: Additional API-specific parameters
        
    Returns:
        FreeAPIFacebookScraper instance
    """
    return FreeAPIFacebookScraper(api_type=api_type, **kwargs)


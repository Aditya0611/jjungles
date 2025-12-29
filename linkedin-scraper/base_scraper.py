"""
Base Scraper Class for Cross-Platform Hashtag Scraping
Supports LinkedIn, Instagram, Twitter, TikTok, Facebook
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime
from uuid import uuid4
import json
import re
from logger import logger
from utils.analysis import (
    analyze_sentiment_multi_method,
    detect_language,
    get_primary_language as get_primary_lang_util
)

class BaseHashtagScraper(ABC):
    """Base class for all platform-specific hashtag scrapers"""
    
    def __init__(self, platform_name: str, use_supabase: bool = True):
        """
        Initialize base scraper
        
        Args:
            platform_name: Name of the platform (e.g., 'linkedin', 'instagram', 'twitter')
            use_supabase: Whether to save data to Supabase
        """
        self.platform_name = platform_name.lower()
        self.hashtags = []
        self.hashtag_contexts = {}  # Store hashtag -> list of post texts for sentiment analysis
        self.hashtag_languages = {}  # Store hashtag -> list of detected languages from post contexts
        self.hashtag_captions = {}  # Store hashtag -> list of captions/titles from posts
        self.hashtag_sentiments = {}  # Store hashtag -> list of sentiment scores from multiple methods
        self.use_supabase = use_supabase
        self.version_id = str(uuid4())
        self.posts_scanned = 0
        self.scroll_count = 0
        
        # Initialize sentiment analyzers (lazy loading)
        self._vader_analyzer = None
        self._transformer_model = None
        self._transformer_tokenizer = None
        
        # Initialize Supabase if enabled
        self.supabase = None
        if use_supabase:
            self.init_supabase()
    
    @abstractmethod
    def login(self, **kwargs):
        """Login to the platform (platform-specific implementation)"""
        pass
    
    @abstractmethod
    def navigate_to_feed(self):
        """Navigate to the platform's feed/page (platform-specific implementation)"""
        pass
    
    @abstractmethod
    def scroll_and_collect_hashtags(self, max_scrolls: int = 30, scroll_pause_time: float = 2.0):
        """Scroll through feed and collect hashtags (platform-specific implementation)"""
        pass
    
    @abstractmethod
    def close(self):
        """Close browser/connection (platform-specific implementation)"""
        pass
    
    def extract_hashtags_from_text(self, text: str) -> List[str]:
        """Extract hashtags from text using regex, filtering out low-quality ones"""
        hashtag_pattern = r'#[\w]+'
        hashtags = re.findall(hashtag_pattern, text)
        
        # Filter out low-quality hashtags
        filtered_hashtags = []
        for tag in hashtags:
            tag_lower = tag.lower()
            # Remove the # for validation
            tag_content = tag_lower[1:] if tag_lower.startswith('#') else tag_lower
            
            # Filter criteria:
            # 1. Must be at least 2 characters (excluding #)
            # 2. Not just numbers
            # 3. Not single character after #
            if len(tag_content) >= 2 and not tag_content.isdigit() and tag_content.isalnum():
                filtered_hashtags.append(tag_lower)
        
        return filtered_hashtags
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """Detect language using external utility"""
        return detect_language(text)
    
    def get_primary_language(self, hashtag: str) -> Tuple[str, float]:
        """Get primary language using external utility"""
        if hashtag not in self.hashtag_languages or not self.hashtag_languages[hashtag]:
            return ('unknown', 0.0)
        return get_primary_lang_util(self.hashtag_languages[hashtag])
    
    def extract_caption_or_title(self, post_text: str, max_length: int = 300) -> str:
        """
        Extract caption or title from post text.
        This extracts the main content (excluding metadata, usernames, etc.)
        
        Args:
            post_text: Full post text
            max_length: Maximum length of caption to extract
            
        Returns:
            Extracted caption/title text
        """
        if not post_text:
            return ""
        
        # Remove common metadata patterns
        cleaned_text = post_text.strip()
        
        # Remove common patterns that aren't part of the main content
        # (This is platform-agnostic, platform-specific scrapers can override)
        lines = cleaned_text.split('\n')
        
        # Take the first few meaningful lines as caption
        caption_lines = []
        for line in lines[:5]:  # First 5 lines usually contain the main content
            line = line.strip()
            if line and len(line) > 3:
                caption_lines.append(line)
                if sum(len(l) for l in caption_lines) >= max_length:
                    break
        
        caption = ' '.join(caption_lines)
        
        # Truncate if too long
        if len(caption) > max_length:
            caption = caption[:max_length].rsplit(' ', 1)[0] + '...'
        
        return caption.strip()
    
    def store_hashtag_with_sentiment(self, hashtag: str, post_text: str, caption: str = None, 
                                     max_context_length: int = 200, analyze_sentiment: bool = True):
        """
        Helper method to store hashtag context, caption, language, and sentiment analysis.
        This is a convenience method for platform-specific scrapers to use when extracting hashtags.
        
        Args:
            hashtag: The hashtag found in the post
            post_text: The full post text containing the hashtag
            caption: Optional caption/title (if None, will be extracted from post_text)
            max_context_length: Maximum length of context text to store (default: 200 chars)
            analyze_sentiment: Whether to perform multi-method sentiment analysis (default: True)
        """
        # Initialize structures if needed
        if hashtag not in self.hashtag_contexts:
            self.hashtag_contexts[hashtag] = []
        if hashtag not in self.hashtag_languages:
            self.hashtag_languages[hashtag] = []
        if hashtag not in self.hashtag_captions:
            self.hashtag_captions[hashtag] = []
        if hashtag not in self.hashtag_sentiments:
            self.hashtag_sentiments[hashtag] = []
        
        # Store post text context (truncated to max length)
        context_snippet = post_text[:max_context_length] if len(post_text) > max_context_length else post_text
        self.hashtag_contexts[hashtag].append(context_snippet)
        
        # Extract and store caption if not provided
        if caption is None:
            caption = self.extract_caption_or_title(post_text)
        if caption:
            self.hashtag_captions[hashtag].append(caption)
        
        # Detect and store language
        detected_lang, _ = self.detect_language(post_text)
        if detected_lang != 'unknown':
            self.hashtag_languages[hashtag].append(detected_lang)
        
        # Perform multi-method sentiment analysis on caption
        if analyze_sentiment:
            sentiment_text = caption if caption else post_text[:500]  # Use caption or first 500 chars
            sentiment_results = self.analyze_sentiment_multi_method(sentiment_text)
            self.hashtag_sentiments[hashtag].append(sentiment_results)
    
    def get_aggregated_sentiment(self, hashtag: str) -> Dict:
        """
        Get aggregated sentiment scores for a hashtag across all occurrences
        
        Args:
            hashtag: The hashtag to get aggregated sentiment for
            
        Returns:
            Dictionary with aggregated sentiment scores from all methods
        """
        if hashtag not in self.hashtag_sentiments or not self.hashtag_sentiments[hashtag]:
            # Return default neutral sentiment
            return {
                'textblob': {'polarity': 0.0, 'label': 'neutral'},
                'vader': {'compound': 0.0, 'label': 'neutral'},
                'transformer': {'score': 0.0, 'label': 'neutral'},
                'consensus_label': 'neutral',
                'average_score': 0.0
            }
        
        sentiments = self.hashtag_sentiments[hashtag]
        
        # Aggregate scores
        textblob_scores = [s.get('textblob', {}).get('polarity', 0.0) for s in sentiments]
        vader_scores = [s.get('vader', {}).get('compound', 0.0) for s in sentiments]
        transformer_scores = [s.get('transformer', {}).get('score', 0.0) for s in sentiments]
        
        # Count labels
        textblob_labels = [s.get('textblob', {}).get('label', 'neutral') for s in sentiments]
        vader_labels = [s.get('vader', {}).get('label', 'neutral') for s in sentiments]
        transformer_labels = [s.get('transformer', {}).get('label', 'neutral') for s in sentiments]
        
        # Calculate averages
        avg_textblob = sum(textblob_scores) / len(textblob_scores) if textblob_scores else 0.0
        avg_vader = sum(vader_scores) / len(vader_scores) if vader_scores else 0.0
        avg_transformer = sum(transformer_scores) / len(transformer_scores) if transformer_scores else 0.0
        
        # Get most common labels
        from collections import Counter
        most_common_textblob = Counter(textblob_labels).most_common(1)[0][0] if textblob_labels else 'neutral'
        most_common_vader = Counter(vader_labels).most_common(1)[0][0] if vader_labels else 'neutral'
        most_common_transformer = Counter(transformer_labels).most_common(1)[0][0] if transformer_labels else 'neutral'
        
        # Overall consensus
        all_labels = textblob_labels + vader_labels + transformer_labels
        consensus_label = Counter(all_labels).most_common(1)[0][0] if all_labels else 'neutral'
        
        # Overall average
        all_scores = textblob_scores + vader_scores + transformer_scores
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        
        return {
            'textblob': {
                'polarity': round(avg_textblob, 3),
                'label': most_common_textblob
            },
            'vader': {
                'compound': round(avg_vader, 3),
                'label': most_common_vader
            },
            'transformer': {
                'score': round(avg_transformer, 3),
                'label': most_common_transformer
            },
            'consensus_label': consensus_label,
            'average_score': round(average_score, 3),
            'sample_count': len(sentiments)
        }
    
    def analyze_sentiment_multi_method(self, text: str) -> Dict:
        """Analyze sentiment using external utility"""
        return analyze_sentiment_multi_method(text)
    
    def analyze_sentiment(self, text: str) -> Tuple[float, str]:
        """
        Analyze sentiment of text using TextBlob (backward compatibility)
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (polarity, label) where:
            - polarity: float between -1 (negative) and 1 (positive)
            - label: 'positive', 'negative', or 'neutral'
        """
        return self.analyze_sentiment_textblob(text)
    
    def get_top_trending_hashtags(self, top_n: int = 10, min_occurrences: int = 1) -> List[Tuple[str, int]]:
        """
        Get top N trending hashtags with quality filtering
        
        Args:
            top_n: Number of top hashtags to return
            min_occurrences: Minimum number of occurrences to include
            
        Returns:
            List of tuples (hashtag, count) sorted by frequency
        """
        if not self.hashtags:
            return []
        
        hashtag_counter = Counter(self.hashtags)
        
        # Filter hashtags by minimum occurrences and quality
        filtered_hashtags = []
        for hashtag, count in hashtag_counter.items():
            # Skip if below minimum occurrences
            if count < min_occurrences:
                continue
            
            # Additional quality checks
            tag_content = hashtag.replace('#', '').strip()
            
            # Skip if it's just numbers or too short
            if tag_content.isdigit() or len(tag_content) < 2:
                continue
            
            # Skip common non-meaningful patterns
            if tag_content in ['a', 'i', 'the', 'an', 'is', 'are', 'was', 'were']:
                continue
            
            filtered_hashtags.append((hashtag, count))
        
        # Sort by count (descending) and return top N
        filtered_hashtags.sort(key=lambda x: x[1], reverse=True)
        return filtered_hashtags[:top_n]
    
    def init_supabase(self):
        """Initialize Supabase client"""
        try:
            from supabase import create_client
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info(f"Supabase client initialized for {self.platform_name}")
            else:
                logger.warning("Supabase credentials not found. Data will not be saved to Supabase.")
                self.supabase = None
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase: {e}")
            self.supabase = None
    
    def save_results(self, filename: Optional[str] = None, skip_supabase: bool = False) -> Dict:
        """Save results to JSON file and Supabase with enhanced data"""
        if filename is None:
            filename = f"trending_hashtags_{self.platform_name}.json"
        
        top_hashtags = self.get_top_trending_hashtags(10, min_occurrences=1)
        
        total_hashtags = len(self.hashtags)
        unique_hashtags = len(set(self.hashtags))
        
        # Enhanced results structure
        results = {
            "scrape_metadata": {
                "platform": self.platform_name,
                "scraped_at": datetime.utcnow().isoformat(),
                "version_id": str(self.version_id),
                "total_posts_scanned": self.posts_scanned,
                "scrolls_performed": self.scroll_count
            },
            "statistics": {
                "total_hashtags_collected": total_hashtags,
                "unique_hashtags": unique_hashtags,
                "average_occurrences": round(total_hashtags / unique_hashtags, 2) if unique_hashtags > 0 else 0,
                "top_10_percentage": round(sum(count for _, count in top_hashtags) / total_hashtags * 100, 2) if total_hashtags > 0 else 0
            },
            "top_10_trending_hashtags": [
                {
                    "rank": i + 1,
                    "hashtag": tag,
                    "count": count,
                    "percentage": round((count / total_hashtags * 100), 2) if total_hashtags > 0 else 0,
                    "sentiment": self.get_aggregated_sentiment(tag).get('consensus_label', 'neutral'),
                    "sentiment_scores": self.get_aggregated_sentiment(tag),
                    "caption": self.hashtag_captions.get(tag, [None])[0] if tag in self.hashtag_captions and self.hashtag_captions[tag] else None,
                    "language": self.get_primary_language(tag)[0] if tag in self.hashtag_languages else 'unknown',
                    "language_confidence": round(self.get_primary_language(tag)[1], 3) if tag in self.hashtag_languages else 0.0
                }
                for i, (tag, count) in enumerate(top_hashtags)
            ],
            "all_hashtags_summary": {
                "total_unique": unique_hashtags,
                "hashtags_with_context": len([h for h in set(self.hashtags) if h in self.hashtag_contexts])
            }
        }
        
        # Save to JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")
        
        # Save to Supabase
        if not skip_supabase and self.use_supabase and self.supabase:
            try:
                self.save_to_supabase(top_hashtags)
            except Exception as e:
                logger.error(f"Error saving to Supabase: {e}")
                logger.info("Results saved to JSON file only")
        
        return results
    
    def save_to_supabase(self, top_hashtags: List[Tuple[str, int]]):
        """Save hashtag data to Supabase database"""
        if not self.supabase:
            return
        
        logger.info("Saving data to Supabase...")
        
        # Calculate engagement metrics
        total_hashtags = len(self.hashtags)
        unique_hashtags = len(set(self.hashtags))
        
        # Prepare data for each hashtag
        records_to_insert = []
        
        for hashtag, count in top_hashtags:
            # Calculate engagement score (normalized count)
            engagement_score = (count / total_hashtags) * 100 if total_hashtags > 0 else 0
            
            # Get aggregated sentiment scores from all methods
            aggregated_sentiment = self.get_aggregated_sentiment(hashtag)
            
            # Get caption if available
            caption = None
            if hashtag in self.hashtag_captions and self.hashtag_captions[hashtag]:
                caption = self.hashtag_captions[hashtag][0]  # Get first caption
            
            # Detect primary language for hashtag
            primary_lang, lang_confidence = self.get_primary_language(hashtag)
            
            # Extract sentiment scores
            textblob_data = aggregated_sentiment.get('textblob', {})
            vader_data = aggregated_sentiment.get('vader', {})
            transformer_data = aggregated_sentiment.get('transformer', {})
            
            # Backward compatibility: use consensus label for sentiment_label
            sentiment_label = aggregated_sentiment.get('consensus_label', 'neutral')
            sentiment_polarity = aggregated_sentiment.get('average_score', 0.0)
            
            # Prepare metadata
            metadata = {
                "total_occurrences": count,
                "total_hashtags_collected": total_hashtags,
                "unique_hashtags": unique_hashtags,
                "percentage": round((count / total_hashtags) * 100, 2) if total_hashtags > 0 else 0,
                "scraped_from": f"{self.platform_name}_feed",
                "session_id": self.version_id,
                "sentiment_analyzed": True,
                "language_detected": primary_lang,
                "language_confidence": round(lang_confidence, 3),
                "sentiment_sample_count": aggregated_sentiment.get('sample_count', 0)
            }
            
            record = {
                "platform": self.platform_name,
                "topic_hashtag": hashtag,
                "engagement_score": round(engagement_score, 2),
                "sentiment_polarity": sentiment_polarity,  # Average score for backward compatibility
                "sentiment_label": sentiment_label,  # Consensus label for backward compatibility
                "sentiment_textblob_polarity": textblob_data.get('polarity', 0.0),
                "sentiment_textblob_label": textblob_data.get('label', 'neutral'),
                "sentiment_vader_compound": vader_data.get('compound', 0.0),
                "sentiment_vader_label": vader_data.get('label', 'neutral'),
                "sentiment_transformer_score": transformer_data.get('score', 0.0),
                "sentiment_transformer_label": transformer_data.get('label', 'neutral'),
                "sentiment_consensus_label": sentiment_label,
                "sentiment_average_score": sentiment_polarity,
                "sentiment_scores": aggregated_sentiment,  # Full sentiment scores JSON
                "caption": caption,
                "language": primary_lang,
                "language_confidence": round(lang_confidence, 3),
                "posts": count,
                "views": None,  # Views not available from feed scraping
                "metadata": metadata,
                "scraped_at": datetime.utcnow().isoformat(),
                "version_id": self.version_id
            }
            
            records_to_insert.append(record)
        
        # Insert records into Supabase using unified 'trends' table
        # All platforms (LinkedIn, Twitter, Instagram, etc.) write to the same table
        # The 'platform' field distinguishes the data source
        table_name = "trends"  # Unified cross-platform table
        
        if not records_to_insert:
            logger.warning("No records to insert into Supabase")
            return
            
        try:
            response = self.supabase.table(table_name).insert(records_to_insert).execute()
            logger.info(f"Successfully saved {len(records_to_insert)} hashtags to Supabase", context={"version_id": self.version_id, "platform": self.platform_name})
        except Exception as e:
            logger.error(f"Error inserting data to Supabase: {e}")
            # Try inserting one by one if batch fails
            logger.info("Attempting to insert records one by one...")
            success_count = 0
            for record in records_to_insert:
                try:
                    self.supabase.table(table_name).insert(record).execute()
                    success_count += 1
                except Exception as insert_error:
                    logger.warning(f"Failed to insert {record['topic_hashtag']}: {insert_error}")
            logger.info(f"Inserted {success_count}/{len(records_to_insert)} records")
    
    def print_results(self):
        """Print top trending hashtags to console with enhanced formatting"""
        top_hashtags = self.get_top_trending_hashtags(10, min_occurrences=1)
        
        print("\n" + "="*70)
        print(f"🔥 TOP 10 TRENDING HASHTAGS ON {self.platform_name.upper()}")
        print("="*70)
        
        if not top_hashtags:
            print("❌ No hashtags found. Try scrolling more or check if posts are loading.")
            return
        
        # Calculate statistics
        total_hashtags = len(self.hashtags)
        unique_hashtags = len(set(self.hashtags))
        total_occurrences = sum(count for _, count in top_hashtags)
        
        # Print hashtags with percentage and trend indicator
        for i, (hashtag, count) in enumerate(top_hashtags, 1):
            percentage = (count / total_hashtags * 100) if total_hashtags > 0 else 0
            # Create a simple bar visualization
            bar_length = int(percentage / 2)  # Scale bar to fit
            bar = "█" * min(bar_length, 30)
            
            # Add trend indicator based on count
            if count >= 5:
                trend = "📈"
            elif count >= 3:
                trend = "📊"
            else:
                trend = "📌"
            
            print(f"{i:2d}. {hashtag:30s} {trend} {count:3d} times ({percentage:5.1f}%) {bar}")
        
        print("="*70)
        
        # Enhanced statistics
        print(f"\n📊 COLLECTION STATISTICS")
        print(f"   • Total hashtags collected: {total_hashtags}")
        print(f"   • Unique hashtags found: {unique_hashtags}")
        print(f"   • Average occurrences per hashtag: {total_hashtags/unique_hashtags:.2f}" if unique_hashtags > 0 else "   • Average occurrences per hashtag: 0.00")
        print(f"   • Top 10 represent: {total_occurrences/total_hashtags*100:.1f}% of all hashtags" if total_hashtags > 0 else "   • Top 10 represent: 0.0% of all hashtags")
        
        # Show hashtag categories if available
        if top_hashtags:
            print(f"\n💡 INSIGHTS")
            # Categorize hashtags
            tech_keywords = ['tech', 'coding', 'programming', 'developer', 'software', 'data', 'ai', 'ml', 'python', 'java', 'sql']
            career_keywords = ['career', 'job', 'hiring', 'interview', 'growth', 'professional', 'skills']
            business_keywords = ['business', 'marketing', 'sales', 'leadership', 'entrepreneur', 'startup']
            
            tech_count = sum(1 for h, _ in top_hashtags if any(kw in h.lower() for kw in tech_keywords))
            career_count = sum(1 for h, _ in top_hashtags if any(kw in h.lower() for kw in career_keywords))
            business_count = sum(1 for h, _ in top_hashtags if any(kw in h.lower() for kw in business_keywords))
            
            if tech_count > 0:
                print(f"   • Technology-related: {tech_count} hashtags")
            if career_count > 0:
                print(f"   • Career-related: {career_count} hashtags")
            if business_count > 0:
                print(f"   • Business-related: {business_count} hashtags")


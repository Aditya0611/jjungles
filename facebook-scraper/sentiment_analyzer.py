"""
Enhanced Sentiment Analysis Module

Supports multiple sentiment analysis backends:
- TextBlob (simple, fast, default)
- HuggingFace Transformers (advanced, more accurate)

Features:
- Sentiment classification (positive/neutral/negative)
- Polarity scoring (-1 to +1)
- Brand safety filtering
- Sentiment-weighted trend ranking
"""

import logging
from typing import Tuple, Optional, List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentMethod(Enum):
    """Sentiment analysis method options"""
    TEXTBLOB = "textblob"
    HUGGINGFACE = "huggingface"
    AUTO = "auto"  # Try HuggingFace, fallback to TextBlob


class SentimentAnalyzer:
    """
    Enhanced sentiment analyzer with multiple backends.
    Supports TextBlob (simple) and HuggingFace transformers (advanced).
    """
    
    def __init__(self, method: SentimentMethod = SentimentMethod.AUTO, 
                 model_name: Optional[str] = None):
        """
        Initialize sentiment analyzer.
        
        Args:
            method: Analysis method (TEXTBLOB, HUGGINGFACE, or AUTO)
            model_name: HuggingFace model name (e.g., 'cardiffnlp/twitter-roberta-base-sentiment-latest')
        """
        self.method = method
        self.model_name = model_name or 'cardiffnlp/twitter-roberta-base-sentiment-latest'
        self.textblob_available = False
        self.transformers_available = False
        self.model = None
        self.tokenizer = None
        
        # Initialize backends
        self._init_textblob()
        self._init_transformers()
    
    def _init_textblob(self):
        """Initialize TextBlob backend"""
        try:
            from textblob import TextBlob
            self.textblob_available = True
            logger.debug("TextBlob backend available")
        except ImportError:
            self.textblob_available = False
            logger.warning("TextBlob not available. Install with: pip install textblob")
    
    def _init_transformers(self):
        """Initialize HuggingFace transformers backend"""
        if self.method == SentimentMethod.TEXTBLOB:
            return  # Skip if TextBlob-only mode
        
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            # Try to load model (this may take time on first run)
            try:
                logger.info(f"Loading HuggingFace model: {self.model_name}")
                self.sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.model_name,
                    device=-1 if not torch.cuda.is_available() else 0
                )
                self.transformers_available = True
                logger.info("HuggingFace transformers backend loaded successfully")
            except Exception as e:
                logger.warning(f"HuggingFace model loading failed: {e}. Falling back to TextBlob.")
                self.transformers_available = False
                
        except ImportError:
            self.transformers_available = False
            logger.debug(
                "HuggingFace transformers not available. "
                "Install with: pip install transformers torch"
            )
    
    def analyze(self, text: str) -> Tuple[str, float, Optional[float]]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (sentiment_label, polarity_score, confidence)
            - sentiment_label: "positive", "negative", or "neutral"
            - polarity_score: Float from -1.0 (very negative) to +1.0 (very positive)
            - confidence: Optional confidence score (0.0 to 1.0)
        """
        if not text or len(text.strip()) < 3:
            return "neutral", 0.0, None
        
        # Choose backend based on method
        if self.method == SentimentMethod.TEXTBLOB:
            return self._analyze_textblob(text)
        elif self.method == SentimentMethod.HUGGINGFACE:
            if self.transformers_available:
                return self._analyze_transformers(text)
            else:
                logger.warning("HuggingFace not available, falling back to TextBlob")
                return self._analyze_textblob(text)
        else:  # AUTO
            if self.transformers_available:
                return self._analyze_transformers(text)
            elif self.textblob_available:
                return self._analyze_textblob(text)
            else:
                logger.warning("No sentiment backend available, returning neutral")
                return "neutral", 0.0, None
    
    def _analyze_textblob(self, text: str) -> Tuple[str, float, Optional[float]]:
        """Analyze using TextBlob"""
        if not self.textblob_available:
            return "neutral", 0.0, None
        
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Classify sentiment
            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            # Use subjectivity as confidence proxy
            confidence = abs(polarity) + (1 - subjectivity) * 0.3
            
            return sentiment, round(polarity, 3), round(min(confidence, 1.0), 3)
        except Exception as e:
            logger.debug(f"TextBlob sentiment analysis failed: {e}")
            return "neutral", 0.0, None
    
    def _analyze_transformers(self, text: str) -> Tuple[str, float, Optional[float]]:
        """Analyze using HuggingFace transformers"""
        if not self.transformers_available:
            return self._analyze_textblob(text)
        
        try:
            # Truncate text if too long (most models have token limits)
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            result = self.sentiment_pipeline(text)[0]
            label = result['label'].lower()
            score = result['score']
            
            # Map labels to standard format
            if 'positive' in label or 'pos' in label:
                sentiment = "positive"
                polarity = score  # 0.0 to 1.0
            elif 'negative' in label or 'neg' in label:
                sentiment = "negative"
                polarity = -score  # -1.0 to 0.0
            else:  # neutral
                sentiment = "neutral"
                polarity = 0.0
            
            # Normalize polarity to -1 to +1 range if needed
            if 0 <= score <= 1:
                if sentiment == "negative":
                    polarity = -score
                else:
                    polarity = score
            
            return sentiment, round(polarity, 3), round(score, 3)
        except Exception as e:
            logger.debug(f"Transformers sentiment analysis failed: {e}")
            return self._analyze_textblob(text)  # Fallback
    
    def is_brand_safe(self, text: str, min_sentiment: float = 0.0) -> bool:
        """
        Check if text is brand-safe (non-negative sentiment).
        
        Args:
            text: Text to check
            min_sentiment: Minimum sentiment score threshold (default: 0.0 = neutral+)
            
        Returns:
            True if brand-safe, False otherwise
        """
        sentiment, polarity, _ = self.analyze(text)
        return polarity >= min_sentiment and sentiment != "negative"
    
    def filter_by_sentiment(self, items: List[Dict], 
                           sentiment_filter: Optional[str] = None,
                           min_polarity: Optional[float] = None) -> List[Dict]:
        """
        Filter items by sentiment.
        
        Args:
            items: List of items with 'text' or 'sentiment' field
            sentiment_filter: "positive", "negative", "neutral", or None (no filter)
            min_polarity: Minimum polarity score threshold
            
        Returns:
            Filtered list of items
        """
        if not sentiment_filter and min_polarity is None:
            return items
        
        filtered = []
        for item in items:
            text = item.get('text', '')
            existing_sentiment = item.get('sentiment')
            existing_polarity = item.get('sentiment_score', 0.0)
            
            # Use existing sentiment if available, otherwise analyze
            if existing_sentiment:
                sentiment = existing_sentiment
                polarity = existing_polarity
            else:
                sentiment, polarity, _ = self.analyze(text)
                item['sentiment'] = sentiment
                item['sentiment_score'] = polarity
            
            # Apply filters
            if sentiment_filter and sentiment != sentiment_filter:
                continue
            
            if min_polarity is not None and polarity < min_polarity:
                continue
            
            filtered.append(item)
        
        return filtered
    
    def rank_by_sentiment(self, items: List[Dict], 
                         prefer_positive: bool = True) -> List[Dict]:
        """
        Rank items by sentiment (positive first by default).
        
        Args:
            items: List of items with sentiment data
            prefer_positive: If True, rank positive items higher
            
        Returns:
            Ranked list of items
        """
        # Ensure sentiment is analyzed for all items
        for item in items:
            if 'sentiment' not in item:
                text = item.get('text', '')
                sentiment, polarity, _ = self.analyze(text)
                item['sentiment'] = sentiment
                item['sentiment_score'] = polarity
        
        # Sort by sentiment score
        if prefer_positive:
            return sorted(items, key=lambda x: x.get('sentiment_score', 0.0), reverse=True)
        else:
            return sorted(items, key=lambda x: x.get('sentiment_score', 0.0))


# Global instance for easy access
_default_analyzer = None


def get_analyzer(method: SentimentMethod = SentimentMethod.AUTO) -> SentimentAnalyzer:
    """Get or create default sentiment analyzer instance"""
    global _default_analyzer
    if _default_analyzer is None or _default_analyzer.method != method:
        _default_analyzer = SentimentAnalyzer(method=method)
    return _default_analyzer


def analyze_sentiment(text: str, method: SentimentMethod = SentimentMethod.AUTO) -> Tuple[str, float, Optional[float]]:
    """
    Quick sentiment analysis function.
    
    Args:
        text: Text to analyze
        method: Analysis method
        
    Returns:
        Tuple of (sentiment_label, polarity_score, confidence)
    """
    analyzer = get_analyzer(method)
    return analyzer.analyze(text)


def is_brand_safe(text: str, min_sentiment: float = 0.0, 
                  method: SentimentMethod = SentimentMethod.AUTO) -> bool:
    """
    Quick brand safety check.
    
    Args:
        text: Text to check
        min_sentiment: Minimum sentiment threshold
        method: Analysis method
        
    Returns:
        True if brand-safe
    """
    analyzer = get_analyzer(method)
    return analyzer.is_brand_safe(text, min_sentiment)


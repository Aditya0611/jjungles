"""
Analysis module for LinkedIn Scraper
Handles sentiment analysis and language detection
"""

import re
from typing import Dict, Tuple, Optional, List
from collections import Counter
from textblob import TextBlob
from langdetect import detect, detect_langs, LangDetectException
from logger import logger

# Lazy-loaded sentiment analyzers
_vader_analyzer_global = None
_transformer_model_global = None

def _init_vader_analyzer():
    """Initialize VADER sentiment analyzer (lazy loading with global cache)"""
    global _vader_analyzer_global
    if _vader_analyzer_global is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _vader_analyzer_global = SentimentIntensityAnalyzer()
        except ImportError:
            logger.warning("VADER not available. Install with: pip install vaderSentiment")
            _vader_analyzer_global = False
    return _vader_analyzer_global

def _init_transformer_model():
    """Initialize transformer-based sentiment model (lazy loading with global cache)"""
    global _transformer_model_global
    if _transformer_model_global is None:
        try:
            from transformers import pipeline
            # Use a popular sentiment analysis model
            _transformer_model_global = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                return_all_scores=True,
                device=-1  # Use CPU, set to 0 for GPU if available
            )
        except Exception as e:
            logger.warning(f"Transformer model not available: {e}")
            logger.warning("   Install with: pip install transformers torch")
            _transformer_model_global = False
    return _transformer_model_global

def analyze_sentiment_textblob(text: str) -> Tuple[float, str]:
    """Analyze sentiment using TextBlob"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.1:
            label = 'positive'
        elif polarity < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return round(polarity, 3), label
    except Exception:
        return 0.0, 'neutral'

def analyze_sentiment_vader(text: str) -> Tuple[float, str, Dict]:
    """Analyze sentiment using VADER"""
    analyzer = _init_vader_analyzer()
    if not analyzer:
        return 0.0, 'neutral', {}
    
    try:
        scores = analyzer.polarity_scores(text)
        compound = scores['compound']
        
        if compound >= 0.05:
            label = 'positive'
        elif compound <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        return round(compound, 3), label, scores
    except Exception:
        return 0.0, 'neutral', {}

def analyze_sentiment_transformer(text: str, max_length: int = 512) -> Tuple[float, str, Dict]:
    """Analyze sentiment using transformer model"""
    model = _init_transformer_model()
    if not model:
        return 0.0, 'neutral', {}
    
    try:
        # Simple truncation to avoid token limit issues
        if len(text) > max_length * 4:
            text = text[:max_length * 4]
        
        results = model(text)
        
        if isinstance(results, list) and len(results) > 0:
            if isinstance(results[0], list):
                results = results[0]
            
            label_map = {
                'LABEL_0': 'negative', 'LABEL_1': 'neutral', 'LABEL_2': 'positive',
                'NEGATIVE': 'negative', 'NEUTRAL': 'neutral', 'POSITIVE': 'positive'
            }
            
            scores_dict = {}
            best_label = 'neutral'
            best_score = 0.0
            
            for item in results:
                label = item.get('label', '')
                score = item.get('score', 0.0)
                mapped_label = label_map.get(label, label.lower())
                scores_dict[mapped_label] = score
                
                if score > best_score:
                    best_score = score
                    best_label = mapped_label
            
            pos_score = scores_dict.get('positive', 0.0)
            neg_score = scores_dict.get('negative', 0.0)
            normalized_score = pos_score - neg_score
            
            return round(normalized_score, 3), best_label, scores_dict
        else:
            return 0.0, 'neutral', {}
    except Exception:
        return 0.0, 'neutral', {}

def analyze_sentiment_multi_method(text: str) -> Dict:
    """Analyze sentiment using multiple methods (TextBlob, VADER, Transformer)"""
    results = {'textblob': {}, 'vader': {}, 'transformer': {}}
    
    # TextBlob
    textblob_polarity, textblob_label = analyze_sentiment_textblob(text)
    results['textblob'] = {'polarity': textblob_polarity, 'label': textblob_label}
    
    # VADER
    vader_compound, vader_label, vader_scores = analyze_sentiment_vader(text)
    results['vader'] = {'compound': vader_compound, 'label': vader_label, 'scores': vader_scores}
    
    # Transformer
    transformer_score, transformer_label, transformer_scores = analyze_sentiment_transformer(text)
    results['transformer'] = {'score': transformer_score, 'label': transformer_label, 'scores': transformer_scores}
    
    # Calculate consensus
    labels = [textblob_label, vader_label, transformer_label]
    label_counts = Counter(labels)
    consensus_label = label_counts.most_common(1)[0][0] if label_counts else 'neutral'
    
    # Calculate average
    scores = [textblob_polarity, vader_compound, transformer_score]
    valid_scores = [s for s in scores if s != 0.0]
    average_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    
    results['consensus_label'] = consensus_label
    results['average_score'] = round(average_score, 3)
    
    return results

def detect_language(text: str) -> Tuple[str, float]:
    """Detect language of text"""
    if not text or len(text.strip()) < 3:
        return ('unknown', 0.0)
    
    try:
        # Remove hashtags and URLs to improve detection accuracy
        cleaned_text = re.sub(r'#\w+', '', text)
        cleaned_text = re.sub(r'http\S+|www\.\S+', '', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        if len(cleaned_text) < 3:
            return ('unknown', 0.0)
        
        try:
            langs = detect_langs(cleaned_text)
            if langs:
                return (langs[0].lang, langs[0].prob)
        except Exception:
            lang_code = detect(cleaned_text)
            return (lang_code, 1.0)
    except LangDetectException:
        return ('unknown', 0.0)
    except Exception:
        return ('unknown', 0.0)
    return ('unknown', 0.0)

def get_primary_language(hashtag_languages: List[str]) -> Tuple[str, float]:
    """Get the primary language from a list of detected languages"""
    if not hashtag_languages:
        return ('unknown', 0.0)
    
    lang_counter = Counter(hashtag_languages)
    if not lang_counter:
        return ('unknown', 0.0)
    
    most_common_lang, count = lang_counter.most_common(1)[0]
    total_detections = len(hashtag_languages)
    confidence = count / total_detections if total_detections > 0 else 0.0
    
    return (most_common_lang, confidence)

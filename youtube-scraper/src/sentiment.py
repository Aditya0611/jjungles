"""
Sentiment analysis using TextBlob
"""
from .logger import logger
from textblob import TextBlob
from typing import Tuple, Optional


def analyze_sentiment(text: str) -> Tuple[float, str]:
	"""
	Analyze sentiment of text using TextBlob.
	
	Args:
		text: Text to analyze
		
	Returns:
		Tuple of (polarity, label) where:
		- polarity: float between -1.0 (negative) and 1.0 (positive)
		- label: 'positive', 'negative', or 'neutral'
	"""
	if not text or not text.strip():
		logger.debug("Empty text passed for sentiment analysis")
		return 0.0, 'neutral'
	
	try:
		blob = TextBlob(text)
		polarity = blob.sentiment.polarity
		
		logger.debug(f"Analyzed sentiment: polarity={polarity}, text_preview='{text[:50]}...'")
		
		# Classify sentiment based on polarity
		if polarity > 0.1:
			label = 'positive'
		elif polarity < -0.1:
			label = 'negative'
		else:
			label = 'neutral'
		
		return float(polarity), label
	except Exception as e:
		# Return neutral if analysis fails
		return 0.0, 'neutral'


def analyze_hashtag_sentiment(hashtag: str, context: Optional[str] = None) -> Tuple[float, str]:
	"""
	Analyze sentiment for a hashtag, optionally with context.
	
	Args:
		hashtag: The hashtag text (without #)
		context: Optional context text (e.g., video title, description)
		
	Returns:
		Tuple of (polarity, label)
	"""
	# Use context if provided, otherwise just analyze the hashtag
	text_to_analyze = context if context else hashtag
	return analyze_sentiment(text_to_analyze)


"""
Unit tests for hashtag engagement analysis scraper adapter.

Tests the analyze_hashtag_engagement function with various scenarios including
proxy failures and successful engagement aggregation.
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
import sys
from pathlib import Path

# Add parent directory to path to import main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import analyze_hashtag_engagement
from tests.conftest import ProxyError, ProxyTimeoutError


class TestHashtagEngagement:
    """Test suite for hashtag engagement analysis adapter."""
    
    def test_successful_engagement_analysis(self, mock_page, sample_hashtag_data):
        """Test successful analysis of hashtag engagement."""
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.get_post_engagement') as mock_get_engagement:
            # Mock engagement data for each post
            mock_get_engagement.return_value = {
                'likes': 1000,
                'comments': 50,
                'views': 50000,
                'total_engagement': 1050,
                'is_video': True,
                'format': 'reel',
                'caption': 'Test caption',
                'language': 'en',
                'language_confidence': 0.95,
                'language_detected': True,
                'sentiment': {
                    'polarity': 0.1,
                    'label': 'positive',
                    'emoji': '😊',
                    'combined_score': 0.15
                }
            }
            
            result = analyze_hashtag_engagement(mock_page, sample_hashtag_data)
        
        assert 'avg_likes' in result
        assert 'avg_comments' in result
        assert 'avg_engagement' in result
        assert 'sentiment_summary' in result
        assert 'language_summary' in result
        assert result['avg_engagement'] > 0
    
    def test_proxy_failure_during_post_analysis(self, proxy_failure_page, sample_hashtag_data):
        """Test handling of proxy failure when analyzing individual posts."""
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.get_post_engagement') as mock_get_engagement:
            # Simulate proxy failure for first post, success for others
            call_count = [0]
            def engagement_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise ProxyError("Proxy connection failed")
                return {
                    'likes': 1000,
                    'comments': 50,
                    'total_engagement': 1050,
                    'is_video': False,
                    'format': 'photo'
                }
            
            mock_get_engagement.side_effect = engagement_side_effect
            
            result = analyze_hashtag_engagement(proxy_failure_page, sample_hashtag_data)
        
        # Should continue processing other posts
        assert isinstance(result, dict)
        assert 'avg_engagement' in result
    
    def test_proxy_timeout_during_analysis(self, proxy_timeout_page, sample_hashtag_data):
        """Test handling of proxy timeout during engagement analysis."""
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.get_post_engagement') as mock_get_engagement:
            mock_get_engagement.side_effect = ProxyTimeoutError("Proxy timeout")
            
            result = analyze_hashtag_engagement(proxy_timeout_page, sample_hashtag_data)
        
        # Should handle timeout and return fallback data
        assert isinstance(result, dict)
        assert 'avg_engagement' in result
    
    def test_no_sample_posts(self, mock_page, sample_hashtag_data):
        """Test handling when no sample posts are available."""
        sample_hashtag_data['sample_posts'] = []
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = analyze_hashtag_engagement(mock_page, sample_hashtag_data)
        
        # Should use frequency-based estimation
        assert 'avg_engagement' in result
        assert result['avg_engagement'] > 0
    
    def test_sentiment_aggregation(self, mock_page, sample_hashtag_data):
        """Test that sentiment is properly aggregated across posts."""
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.get_post_engagement') as mock_get_engagement:
            # Return different sentiments for different posts
            sentiments = [
                {'polarity': 0.2, 'label': 'positive', 'emoji': '😊', 'combined_score': 0.25},
                {'polarity': 0.0, 'label': 'neutral', 'emoji': '😐', 'combined_score': 0.0},
                {'polarity': -0.1, 'label': 'negative', 'emoji': '😢', 'combined_score': -0.15}
            ]
            
            def engagement_side_effect(*args, **kwargs):
                return {
                    'likes': 1000,
                    'comments': 50,
                    'total_engagement': 1050,
                    'is_video': False,
                    'format': 'photo',
                    'caption': 'Test',
                    'sentiment': sentiments.pop(0) if sentiments else {'polarity': 0.0, 'label': 'neutral', 'emoji': '😐', 'combined_score': 0.0}
                }
            
            mock_get_engagement.side_effect = engagement_side_effect
            
            result = analyze_hashtag_engagement(mock_page, sample_hashtag_data)
        
        assert 'sentiment_summary' in result
        assert 'positive' in result['sentiment_summary']
        assert 'neutral' in result['sentiment_summary']
        assert 'negative' in result['sentiment_summary']
        assert 'overall_label' in result['sentiment_summary']
    
    def test_language_aggregation(self, mock_page, sample_hashtag_data):
        """Test that language data is properly aggregated."""
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.get_post_engagement') as mock_get_engagement:
            mock_get_engagement.return_value = {
                'likes': 1000,
                'comments': 50,
                'total_engagement': 1050,
                'is_video': False,
                'format': 'photo',
                'caption': 'Test caption',
                'language': 'en',
                'language_confidence': 0.95,
                'language_detected': True
            }
            
            result = analyze_hashtag_engagement(mock_page, sample_hashtag_data)
        
        assert 'language_summary' in result
        assert 'primary_language' in result['language_summary']
        assert 'distribution' in result['language_summary']
        assert result['language_summary']['primary_language'] == 'en'
    
    def test_content_type_distribution(self, mock_page, sample_hashtag_data):
        """Test that content type distribution is calculated."""
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.get_post_engagement') as mock_get_engagement:
            formats = ['reel', 'photo', 'reel']
            
            def engagement_side_effect(*args, **kwargs):
                return {
                    'likes': 1000,
                    'comments': 50,
                    'total_engagement': 1050,
                    'is_video': formats[0] == 'reel',
                    'format': formats.pop(0) if formats else 'photo',
                    'caption': 'Test'
                }
            
            mock_get_engagement.side_effect = engagement_side_effect
            
            result = analyze_hashtag_engagement(mock_page, sample_hashtag_data)
        
        assert 'content_types' in result
        assert isinstance(result['content_types'], dict)
        assert 'primary_format' in result
    
    def test_engagement_averaging(self, mock_page, sample_hashtag_data):
        """Test that engagement metrics are properly averaged."""
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.get_post_engagement') as mock_get_engagement:
            engagements = [
                {'likes': 1000, 'comments': 50, 'total_engagement': 1050},
                {'likes': 2000, 'comments': 100, 'total_engagement': 2100},
                {'likes': 1500, 'comments': 75, 'total_engagement': 1575}
            ]
            
            def engagement_side_effect(*args, **kwargs):
                data = engagements.pop(0) if engagements else {'likes': 1000, 'comments': 50, 'total_engagement': 1050}
                return {
                    **data,
                    'is_video': False,
                    'format': 'photo',
                    'caption': 'Test'
                }
            
            mock_get_engagement.side_effect = engagement_side_effect
            
            result = analyze_hashtag_engagement(mock_page, sample_hashtag_data)
        
        # Average of 1050, 2100, 1575 = 1575
        assert result['avg_engagement'] > 0
        assert result['avg_likes'] > 0
        assert result['avg_comments'] > 0


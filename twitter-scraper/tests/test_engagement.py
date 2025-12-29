"""Unit tests for engagement score calculation."""
import unittest
import sys
import os

# Add project root to sys.path to allow imports from twitter_scraper_app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from twitter_scraper_app.utils import parse_post_count
from twitter_scraper_app.services import calculate_engagement_score

class TestEngagementScore(unittest.TestCase):
    def test_parse_post_count(self):
        """Test parsing of various post count formats."""
        self.assertEqual(parse_post_count("38K"), 38000)
        self.assertEqual(parse_post_count("2.1M"), 2100000)
        self.assertEqual(parse_post_count("100K"), 100000)
        self.assertEqual(parse_post_count("5K"), 5000)
        self.assertEqual(parse_post_count("N/A"), 0)
        self.assertEqual(parse_post_count("invalid"), 0)
        self.assertEqual(parse_post_count("500"), 500)

    def test_calculate_engagement_score(self):
        """Test engagement score calculation logic."""
        # Case 1: High engagement
        topic_high = {"topic": "#High", "count": "2.1M", "retweets": 1000, "likes": 5000}
        score_high = calculate_engagement_score(topic_high)
        self.assertGreater(score_high, 5.0)
        
        # Case 2: Low engagement
        topic_low = {"topic": "#Low", "count": "500", "retweets": 0, "likes": 0}
        score_low = calculate_engagement_score(topic_low)
        self.assertLess(score_low, 5.0)

        # Case 3: No data
        topic_none = {"topic": "#None", "count": "N/A"}
        score_none = calculate_engagement_score(topic_none)
        self.assertLess(score_none, 2.0)
        
if __name__ == '__main__':
    unittest.main()

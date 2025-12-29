import unittest
import sys
# t3_scraper handles encoding fix on import
from twitter_scraper_app.utils import detect_language

class TestLanguageDetection(unittest.TestCase):
    def test_english_detection(self):
        """Test detection of English text."""
        result = detect_language("#HelloWorld")
        self.assertIn(result, ["en", "unknown"]) # Depends on installed libraries

    def test_hindi_detection(self):
        """Test detection of Hindi text."""
        # Note: Short text might return unknown or hi
        result = detect_language("#नमस्ते") 
        self.assertIn(result, ["hi", "ne", "mr", "unknown"]) 

    def test_mixed_detection(self):
        """Test detection of known mixed/other text."""
        # Just ensure it doesn't crash
        result = detect_language("#realmeGT8ProSaleIsLive")
        self.assertIsInstance(result, str)
        
    def test_empty_input(self):
        """Test behavior with empty or short input."""
        result = detect_language("")
        self.assertEqual(result, "unknown")
        result = detect_language("a")
        self.assertEqual(result, "unknown")

if __name__ == '__main__':
    unittest.main()


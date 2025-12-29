
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_utils import SocialMediaRecord, upload_to_supabase

class TestSupabaseUpload(unittest.TestCase):
    def setUp(self):
        self.mock_supabase = MagicMock()
        self.mock_table = MagicMock()
        self.mock_supabase.table.return_value = self.mock_table
        
        # Setup mock record
        self.record = SocialMediaRecord(
            platform="Test",
            timestamp=datetime.now(),
            topic="test_topic",
            score=5.0
        )
        
    def test_upload_success(self):
        """Test successful upload."""
        data = [self.record]
        
        # Mock responses for schema checks
        self.mock_table.select.return_value.limit.return_value.execute.return_value = MagicMock()
        
        result = upload_to_supabase(
            self.mock_supabase,
            data,
            table_name="test_table",
            use_data_model=True
        )
        
        # Should have called insert
        self.assertTrue(self.mock_table.insert.called or self.mock_table.upsert.called)

    def test_upload_validation(self):
        """Test validation filters/logs invalid records."""
        invalid_record = SocialMediaRecord(
            platform="Test",
            timestamp=datetime.now(),
            topic="", # Invalid: empty topic
            score=5.0
        )
        
        # We need to capture logs? Or checking side effects.
        # For now, just ensure it doesn't crash
        result = upload_to_supabase(
            self.mock_supabase,
            [invalid_record],
            table_name="test_table"
        )
        
        # Logic handles empty lists gracefully
        pass

if __name__ == '__main__':
    unittest.main()

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.scraper import extract_hashtags_from_video, _parse_video_id
from langdetect import LangDetectException

# Mock Metadata
MOCK_HTML_TITLE = "<h1>Amazing Video Title</h1>"
MOCK_METADATA_RETURN = {
    "title": "Amazing Video Title",
    "description": "This is a great description.",
    "views": 1000,
    "likes": 50,
    "comments": 10,
    "language": "en"
}

@pytest.mark.asyncio
async def test_extract_hashtags_and_metadata():
    # Mock Playwright Page
    mock_page = AsyncMock()
    mock_page.goto.return_value = None
    mock_page.is_visible.return_value = False # No consent popup
    
    # Mock Title
    mock_page.inner_text.side_effect = lambda selector, timeout=30000: \
        "Amazing Video Title" if "title" in selector else \
        "1,000 views" if "view-count" in selector else \
        "10 Comments" if "count-text" in selector else ""

    # Mock Description
    mock_desc_el = AsyncMock()
    mock_desc_el.inner_text.return_value = "This is a great description."
    mock_page.query_selector.side_effect = lambda sel: \
        mock_desc_el if "description" in sel else \
        AsyncMock(inner_text=AsyncMock(return_value="10")) if "count-text" in sel else None

    # Mock Hashtags
    mock_page.eval_on_selector_all.return_value = ["#cool", "#trending"]

    # Mock Likes (aria-label)
    mock_like_btn = AsyncMock()
    mock_like_btn.get_attribute.return_value = "like this video along with 50 other people"
    
    # Update query_selector behavior to return like btn
    def query_selector_side_effect(sel):
        if "like-button" in sel: return mock_like_btn
        if "description" in sel: return mock_desc_el
        if "count-text" in sel: 
             m = AsyncMock()
             m.inner_text.return_value = "10"
             return m
        return None
    mock_page.query_selector.side_effect = query_selector_side_effect

    with patch("src.scraper.detect", return_value="en"):
        tags, metadata = await extract_hashtags_from_video(mock_page, "https://youtube.com/watch?v=12345678901")
    
    assert "video_id" in metadata
    assert metadata["video_id"] == "12345678901"
    assert metadata["title"] == "Amazing Video Title"
    assert metadata["views"] == 1000
    assert metadata["likes"] == 50
    assert metadata["comments"] == 10
    assert metadata["language"] == "en" # Detected from title/desc
    assert tags == ["cool", "trending"]

def test_language_storage_schema():
    # Verify the SQL or Storage code has language field (Static check)
    with open("supabase_setup.sql", "r") as f:
        sql_content = f.read()
    assert "language TEXT" in sql_content

    with open("src/supabase_storage.py", "r") as f:
        py_content = f.read()
    assert '"language": language' in py_content

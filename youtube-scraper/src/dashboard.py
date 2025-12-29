import aiohttp
from typing import Dict, Any
from .logger import logger

async def notify_dashboard(stats: Dict[str, Any], url: str, token: str = "") -> None:
    """
    Send scraping statistics to a dashboard webhook using aiohttp.
    """
    if not url:
        return

    logger.info(f"Sending statistics to dashboard: {url}")
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "YoutubeScraper/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    try:
        async with aiohttp.ClientSession() as client:
            async with client.post(url, json=stats, headers=headers) as response:
                response.raise_for_status()
                logger.info("Dashboard notification sent successfully")
    except Exception as e:
        logger.error(f"Failed to notify dashboard: {e}")

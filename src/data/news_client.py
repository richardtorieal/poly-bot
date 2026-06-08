import httpx
from typing import List, Dict, Any
from src.utils.logger import logger

class NewsClient:
    """
    Client for fetching real-time crypto and macro news.
    Defaults to CryptoPanic (free tier friendly).
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://cryptopanic.com/api/v1/posts/"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def fetch_latest_news(self, filter: str = "hot") -> List[Dict[str, Any]]:
        """
        Fetches latest news from CryptoPanic.
        """
        params = {
            "auth_token": self.api_key,
            "public": "true", # Use public feed if no key
            "filter": filter
        }
        
        try:
            logger.debug(f"Fetching news from {self.base_url}")
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            return []

    async def close(self):
        await self.client.aclose()

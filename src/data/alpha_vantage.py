import httpx
from typing import List, Dict, Any
from src.utils.logger import logger

class AlphaVantageClient:
    """
    Client for Alpha Vantage News & Sentiment API (2026 edition).
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.client = httpx.AsyncClient(timeout=15.0)

    async def fetch_news_sentiment(self, tickers: str = None) -> List[Dict[ Any, Any]]:
        """
        Fetches macro and stock/crypto news with sentiment scores.
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": self.api_key,
            "sort": "LATEST"
        }
        if tickers:
            params["tickers"] = tickers

        try:
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("feed", [])
        except Exception as e:
            logger.error(f"Alpha Vantage fetch failed: {e}")
            return []

    async def close(self):
        await self.client.aclose()

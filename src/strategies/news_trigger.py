import asyncio
from typing import List, Dict, Any
from src.strategies.base import BaseStrategy
from src.utils.logger import logger
from src.security.safety import SafetyManager
from src.data.news_client import NewsClient
from src.data.alpha_vantage import AlphaVantageClient

class NewsTriggerStrategy(BaseStrategy):
    """
    Enhanced News Trigger Strategy using multi-source feeds.
    """
    def __init__(self, client, safety: SafetyManager, news_client: NewsClient, av_client: AlphaVantageClient = None):
        super().__init__(client, safety, name="NewsTrigger")
        self.news_client = news_client
        self.av_client = av_client
        self.processed_ids = set()

    async def run_iteration(self):
        logger.info("Scanning multi-source news (CryptoPanic + AlphaVantage)...")
        
        # 1. Fetch from CryptoPanic (Crypto Native)
        cp_news = await self.news_client.fetch_latest_news()
        await self._process_items(cp_news, "CryptoPanic")

        # 2. Fetch from Alpha Vantage (Macro/Sentiment)
        if self.av_client:
            av_news = await self.av_client.fetch_news_sentiment()
            await self._process_items(av_news, "AlphaVantage")

        await asyncio.sleep(60)

    async def _process_items(self, items: List[Dict[str, Any]], source: str):
        for item in items:
            # Alpha Vantage uses 'url' or 'title' as unique, CP uses 'id'
            unique_id = item.get("id") or item.get("url")
            if unique_id in self.processed_ids:
                continue
            
            title = item.get("title", "").lower()
            sentiment = item.get("overall_sentiment_label", "Neutral") # AV specific
            
            # Simplified trigger check
            if "bitcoin" in title or "fed" in title or "election" in title:
                logger.warning(f"🔥 NEWS MATCH [{source}]: {title[:60]}... | Sentiment: {sentiment}")
                self.safety.record_trade(1.0)
                self.processed_ids.add(unique_id)

import httpx
import pandas as pd
import os
import json
from typing import List, Dict, Any, Optional
from src.utils.logger import logger

class HistoricalDownloader:
    """
    Downloader for fetching historical market data with local caching.
    """
    def __init__(self, cache_dir: str = "data"):
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.clob_url = "https://clob.polymarket.com"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    async def get_market_metadata(self, slug: str) -> Dict[str, Any]:
        url = f"{self.gamma_url}/markets"
        params = {"slug": slug}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        market = data[0] if isinstance(data, list) and len(data) > 0 else {}
        ids = market.get("clobTokenIds", [])
        if isinstance(ids, str):
            try:
                market["clobTokenIds"] = json.loads(ids)
            except:
                market["clobTokenIds"] = []
        return market

    async def fetch_price_history(self, token_id: str, interval: str = "all") -> pd.DataFrame:
        """
        Fetches full price history (default 'all') for long-term backtesting.
        """
        cache_path = os.path.join(self.cache_dir, f"{token_id}_{interval}.csv")
        
        if os.path.exists(cache_path):
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df

        url = f"{self.clob_url}/prices-history"
        # Using fidelity=60 (1 hour snapshots) for 3-month backtests to ensure data density
        params = {"market": token_id, "interval": interval, "fidelity": 60}
        
        try:
            logger.info(f"Downloading LONG history for token: {token_id}...")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            history = data.get("history", [])
            if not history:
                return pd.DataFrame()
                
            df = pd.DataFrame(history)
            df['t'] = pd.to_datetime(df['t'], unit='s')
            df.set_index('t', inplace=True)
            df.sort_index(inplace=True)
            
            df.to_csv(cache_path)
            return df
        except Exception as e:
            logger.error(f"Failed to fetch {token_id}: {e}")
            return pd.DataFrame()

    async def close(self):
        await self.client.aclose()

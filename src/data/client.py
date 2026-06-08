import httpx
import time
import hmac
import hashlib
import base64
import pandas as pd
from typing import Dict, Any, Optional
from src.utils.logger import logger
from src.security.config import Settings

class KrakenClient:
    """
    Client for Kraken REST API to fetch high-fidelity OHLC data.
    """
    def __init__(self):
        self.base_url = "https://api.kraken.com/0/public"
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def get_btc_ohlc(self, interval: int = 1) -> pd.DataFrame:
        """
        Fetches BTC/USD OHLC data. Interval in minutes (1, 5, 15, 60, etc).
        """
        response = await self.client.get("/OHLC", params={"pair": "XBTUSD", "interval": interval})
        response.raise_for_status()
        data = response.json()['result']['XXBTZUSD']
        
        # Kraken returns: [time, open, high, low, close, vwap, volume, count]
        df = pd.DataFrame(data, columns=['t', 'o', 'h', 'l', 'c', 'vwap', 'v', 'count'])
        df['t'] = pd.to_datetime(df['t'], unit='s')
        df.set_index('t', inplace=True)
        df['price'] = df['c'].astype(float)
        return df[['price']]

    async def __aenter__(self): return self
    async def __aexit__(self, *args): await self.client.aclose()

class PolymarketClient:
    """
    Asynchronous client for Polymarket CLOB REST API.
    """
    def __init__(self, config: Settings):
        self.config = config
        self.base_url = "https://clob.polymarket.com"
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Generates Polymarket API L2 authentication headers.
        Note: Actual EIP-712 signing happens here in a full implementation.
        """
        timestamp = str(int(time.time()))
        # Placeholder for actual signature logic
        # Polymarket requires POLY_API_KEY, POLY_SIG, POLY_TIMESTAMP, POLY_PASSPHRASE
        headers = {
            "POLY-API-KEY": self.config.POLYMARKET_API_KEY,
            "POLY-PASSPHRASE": self.config.POLYMARKET_API_PASSPHRASE.get_secret_value(),
            "POLY-TIMESTAMP": timestamp,
            "POLY-SIGNATURE": "placeholder", # Will implement EIP-712 signing later
        }
        return headers

    async def search_markets(self, query: str) -> Dict[str, Any]:
        """
        Searches for markets using a query string via Gamma API.
        Note: The CLOB API doesn't have a direct search, so we use Gamma.
        """
        gamma_url = "https://gamma-api.polymarket.com/markets"
        async with httpx.AsyncClient() as client:
            response = await client.get(gamma_url, params={"active": "true", "search": query, "limit": 20})
            response.raise_for_status()
            return response.json()

    async def get_markets(self, next_cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches active markets.
        """
        params = {}
        if next_cursor:
            params["next_cursor"] = next_cursor
            
        logger.debug(f"Fetching markets... {params}")
        response = await self.client.get("/markets", params=params)
        response.raise_for_status()
        return response.json()

    async def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """
        Fetches orderbook for a specific token.
        """
        logger.debug(f"Fetching orderbook for {token_id}")
        response = await self.client.get(f"/book", params={"token_id": token_id})
        response.raise_for_status()
        return response.json()

    async def get_price(self, token_id: str, side: str = "buy") -> Dict[str, Any]:
        """
        Fetches current price for a token.
        """
        response = await self.client.get("/price", params={"token_id": token_id, "side": side})
        response.raise_for_status()
        return response.json()

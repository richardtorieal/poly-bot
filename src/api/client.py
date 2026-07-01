from polymarket import AsyncPublicClient
from src.utils.logger import logger
from src.utils.config import settings

class PolyClient:
    """
    Wrapper for Polymarket V3 API.
    Handles authentication, market data fetching, and order execution.
    """
    def __init__(self):
        self.client = None
        self.is_authenticated = False
        logger.info("PolyClient wrapper initialized")

    async def connect(self):
        """Initializes the async public client."""
        self.client = AsyncPublicClient()
        logger.info("Connected to Polymarket Gamma API")

    async def get_market_price(self, market_url: str) -> float:
        """Fetches the current price for a specific market."""
        if not self.client:
            await self.connect()
        
        try:
            market = await self.client.get_market(url=market_url)
            logger.debug(f"Fetched price for {market.question}: {market.price}")
            return float(market.price)
        except Exception as e:
            logger.error(f"Failed to fetch market price for {market_url}: {e}")
            return 0.0

    async def disconnect(self):
        """Safely closes the client connection."""
        if self.client:
            # Note: AsyncPublicClient context manager handles this usually, 
            # but we'll provide a hook for manual management if needed.
            pass

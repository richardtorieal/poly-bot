import asyncio
import websockets
import json
from src.utils.logger import logger

class WebSocketClient:
    """
    Client for Polymarket's real-time WebSocket CLOB (High-Throughput Production).
    """
    def __init__(self, uri: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"):
        self.uri = uri
        self.websocket = None
        self.is_running = False
        self._orderbooks = {} # asset_id -> book_data
        self._listen_task = None

    @property
    def connected(self) -> bool:
        return self.websocket is not None and self.is_running

    async def connect(self):
        if self.websocket:
            return
        logger.info(f"Connecting to WebSocket: {self.uri}")
        try:
            self.websocket = await websockets.connect(self.uri)
            self.is_running = True
            # Start background listener if not already running
            if not self._listen_task or self._listen_task.done():
                self._listen_task = asyncio.create_task(self._listen_internal())
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self.websocket = None

    async def _listen_internal(self):
        """
        Internal background listener to populate orderbooks.
        """
        while self.is_running:
            try:
                if not self.websocket:
                    await self.connect()
                    if not self.websocket:
                        await asyncio.sleep(5)
                        continue

                async for message in self.websocket:
                    data = json.loads(message)
                    # Polymarket CLOB MARKET stream sends arrays of market updates
                    if isinstance(data, list):
                        for update in data:
                            if 'asset_id' in update:
                                self._orderbooks[update['asset_id']] = update
                    elif isinstance(data, dict) and 'asset_id' in data:
                        self._orderbooks[data['asset_id']] = data
            except Exception as e:
                logger.error(f"WebSocket listen error: {e}")
                self.websocket = None
                await asyncio.sleep(5)

    def get_book(self, asset_id: str) -> dict:
        """
        Returns the latest book data for a given asset_id.
        """
        return self._orderbooks.get(asset_id)

    async def subscribe(self, asset_ids: list):
        """
        Subscribes to real-time market data (Best Bid/Ask).
        """
        if not self.connected:
            await self.connect()

        if not self.websocket:
            logger.error("Cannot subscribe: WebSocket not connected.")
            return
            
        msg = {
            "type": "MARKET",
            "assets_ids": asset_ids
        }
        try:
            await self.websocket.send(json.dumps(msg))
            logger.info(f"Subscribed to {len(asset_ids)} assets via MARKET stream.")
        except Exception as e:
            logger.error(f"Failed to send subscribe message: {e}")
            self.websocket = None # Force reconnect on next loop

    async def close(self):
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        if self._listen_task:
            self._listen_task.cancel()
        logger.info("WebSocket connection closed.")

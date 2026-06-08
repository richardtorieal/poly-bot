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

    async def connect(self):
        if self.websocket:
            return
        logger.info(f"Connecting to WebSocket: {self.uri}")
        self.websocket = await websockets.connect(self.uri)
        self.is_running = True

    async def listen(self, callback):
        """
        Listens for incoming messages and executes a callback.
        """
        while self.is_running:
            try:
                await self.connect()
                async for message in self.websocket:
                    data = json.loads(message)
                    await callback(data)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.websocket = None
                await asyncio.sleep(5) # Backoff

    async def subscribe(self, asset_ids: list):
        """
        Subscribes to real-time market data (Best Bid/Ask).
        """
        # Wait for connection if it's starting up
        for _ in range(10):
            if self.websocket: break
            await asyncio.sleep(0.5)

        if not self.websocket:
            await self.connect()
            
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
        if self.websocket:
            await self.websocket.close()
            self.is_running = False
            logger.info("WebSocket connection closed.")

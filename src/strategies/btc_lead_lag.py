import asyncio
import httpx
import os
from typing import List, Dict, Any
from src.strategies.base import BaseStrategy
from src.utils.logger import logger
from src.security.safety import SafetyManager
from src.data.websocket_client import WebSocketClient

class BTCLeadLagStrategy(BaseStrategy):
    """
    BTC Lead-Lag Strategy: Detects mispricing in BTC target markets by monitoring spot price.
    """
    def __init__(self, client, safety: SafetyManager, target_token_id: str, name="BTCLeadLag"):
        super().__init__(client, safety, name)
        self.target_token_id = target_token_id
        self.btc_price = 0.0
        self.poly_price = 0.0
        self.last_btc_price = 0.0
        self.threshold = 0.005 # 0.5% move
        self.wss = WebSocketClient()
        self.discord_thread_id = "1510658758106284052"
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.owner_id = '578742150213140490'

    async def _wss_callback(self, data):
        updates = data if isinstance(data, list) else [data]
        for msg in updates:
            if msg.get('asset_id') == self.target_token_id:
                asks = msg.get('asks', [])
                if asks:
                    self.poly_price = float(asks[0]['price'])

    async def fetch_btc_price(self):
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url)
                self.btc_price = resp.json()['bitcoin']['usd']
            except Exception as e:
                logger.error(f"Failed to fetch BTC price: {e}")

    async def run_iteration(self):
        logger.info(f"Scanning BTC Lead-Lag for token {self.target_token_id}...")
        
        # 1. Update prices
        await self.fetch_btc_price()
        if self.last_btc_price == 0:
            self.last_btc_price = self.btc_price
            return

        # 2. Check for Lead-Lag Signal
        btc_move = (self.btc_price / self.last_btc_price) - 1
        
        # Dummy logic: if BTC moves > threshold and we haven't seen a Poly move yet
        # In a real scenario, we'd compare against WSS cache
        if abs(btc_move) > self.threshold:
            direction = "UP" if btc_move > 0 else "DOWN"
            logger.warning(f"🚀 BTC {direction} MOVE DETECTED: {btc_move:.2%}")
            
            msg = (f"<@{self.owner_id}> ⚡ **BTC LEAD-LAG SIGNAL**\n\n"
                   f"• BTC moved **{btc_move:.2%}$** ({self.last_btc_price:.0f} -> {self.btc_price:.0f})\n"
                   f"• Target Market: [BTC $1M before GTA VI](https://polymarket.com/market/will-bitcoin-hit-1m-before-gta-vi-872-424)\n"
                   f"• Action: Consider buying {'YES' if btc_move > 0 else 'NO'}")
            
            await self._alert_discord(msg)
            self.last_btc_price = self.btc_price # Reset anchor

    async def _alert_discord(self, message: str):
        if not self.discord_token: return
        url = f"https://discord.com/api/v10/channels/{self.discord_thread_id}/messages"
        async with httpx.AsyncClient() as client:
            await client.post(url, 
                headers={"Authorization": f"Bot {self.discord_token}"},
                json={"content": message}
            )

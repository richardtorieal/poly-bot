import asyncio
import httpx
import os
import json
from typing import List, Dict, Any
from src.strategies.base import BaseStrategy
from src.utils.logger import logger
from src.security.safety import SafetyManager

from src.data.websocket_client import WebSocketClient

class NegativeRiskStrategy(BaseStrategy):
    """
    Recalibrated Scanner: Detects both Bundle Arb and Binary Arb using WebSocket data.
    """
    def __init__(self, client, safety: SafetyManager, name="NegativeRisk", profit_margin=0.005, polling_interval=900):
        super().__init__(client, safety, name)
        self.profit_margin = profit_margin # 0.5% to ensure activity
        self.polling_interval = polling_interval
        self.discord_thread_id = "1510658758106284052" 
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.owner_id = '578742150213140490'
        self.gamma_url = "https://gamma-api.polymarket.com/markets"
        self.semaphore = asyncio.Semaphore(10) # Rate limit protection
        self.wss = WebSocketClient()
        self.live_price_cache = {} # {token_id: best_ask}
        self.is_wss_ready = False

    async def _wss_callback(self, data):
        """
        Updates the live price cache from WebSocket messages.
        """
        # Data can be a list (initial book) or single object (update)
        updates = data if isinstance(data, list) else [data]
        for msg in updates:
            # Handle 'book' event type
            if msg.get('event_type') == 'book':
                tid = msg.get('asset_id')
                asks = msg.get('asks', [])
                if asks:
                    self.live_price_cache[tid] = float(asks[0]['price'])
            
            # Handle 'price_change' event type
            elif msg.get('event_type') == 'price_change':
                changes = msg.get('price_changes', [])
                for c in changes:
                    tid = c.get('asset_id')
                    if 'best_ask' in c:
                        self.live_price_cache[tid] = float(c['best_ask'])

    async def start_wss(self, asset_ids: list):
        if not self.is_wss_ready:
            self.wss.is_running = True
            asyncio.create_task(self.wss.listen(self._wss_callback))
            await asyncio.sleep(2) # Wait for connection
            await self.wss.subscribe(asset_ids)
            self.is_wss_ready = True
            logger.info("WebSocket listener active and subscribed.")

    async def get_best_ask(self, token_id: str) -> float:
        """
        Priority: 1. Live WSS Cache, 2. REST Fallback
        """
        if token_id in self.live_price_cache:
            return self.live_price_cache[token_id]
            
        async with self.semaphore:
            try:
                price_resp = await self.client.get_price(token_id, side="buy")
                return float(price_resp.get('price', 1.0))
            except:
                return 1.0

    async def run_iteration(self):
        logger.info(f"--- RECALIBRATED SCAN [Threshold: {self.profit_margin*100}%] ---")
        try:
            async with httpx.AsyncClient() as hclient:
                # Fetch 100 highest volume markets
                resp = await hclient.get(self.gamma_url, params={"active": "true", "limit": 100, "sort": "volume24hr:desc"})
                markets = resp.json()

            # Ensure WSS is subscribed to all active tokens
            all_tids = []
            for m in markets:
                clob_str = m.get("clobTokenIds", "[]")
                all_tids.extend(json.loads(clob_str))
            
            if all_tids:
                await self.start_wss(all_tids[:500]) # Cap for safety

            groups = {} 
            binary_arbs = []
            
            # 1. Grouping Pass
            for m in markets:
                if m.get('closed') == True: continue
                
                neg_risk_id = m.get("negRiskMarketID")
                clob_str = m.get("clobTokenIds", "[]")
                ids = json.loads(clob_str)
                if not ids: continue

                # Add to Group for NegRisk checks
                if neg_risk_id and neg_risk_id != "0x0000000000000000000000000000000000000000000000000000000000000000":
                    if neg_risk_id not in groups:
                        groups[neg_risk_id] = {
                            "title": m.get("events", [{}])[0].get("title", "Unknown Group"),
                            "slug": m.get("events", [{}])[0].get("slug", ""),
                            "markets": []
                        }
                    groups[neg_risk_id]["markets"].append(m)
                
                # Check for Individual Binary Market (Independent of groups)
                if len(ids) == 2:
                    y_ask = await self.get_best_ask(ids[0])
                    n_ask = await self.get_best_ask(ids[1])
                    total = y_ask + n_ask
                    if total < (1.0 - self.profit_margin) and y_ask < 0.99:
                        profit_pct = (1.0 - total) * 100
                        binary_arbs.append(f"• [{m.get('slug')}](https://polymarket.com/market/{m.get('slug')}): **{profit_pct:.2f}% Profit** (Sum: {total:.3f})\n    - YES: {y_ask:.3f} | NO: {n_ask:.3f}")

            alerts = []

            # 2. Check Negative Risk Groups with corrected math
            for grid, data in groups.items():
                if len(data["markets"]) < 2: continue
                
                # Gather all prices in parallel
                tasks = []
                for m in data["markets"]:
                    ids = json.loads(m.get("clobTokenIds", "[]"))
                    tasks.append(self.get_best_ask(ids[0])) # YES Ask
                    tasks.append(self.get_best_ask(ids[1])) # NO Ask
                
                all_prices = await asyncio.gather(*tasks)
                yes_asks = all_prices[0::2]
                no_asks = all_prices[1::2]
                
                count = len(data["markets"])
                total_yes_ask = sum(yes_asks)
                total_no_ask = sum(no_asks)
                
                # --- OPTION A: Buy ALL YES ---
                # Payout = 1.0, Cost = total_yes_ask
                if total_yes_ask < (1.0 - self.profit_margin):
                    profit_pct = (1.0 - total_yes_ask) * 100
                    event_url = f"https://polymarket.com/event/{data['slug']}"
                    alerts.append(f"🔥 **YES BUNDLE ARB: {data['title']}**\n• [View Event]({event_url}): **{profit_pct:.2f}% Profit** (Cost: **{total_yes_ask:.3f}** for $1.00 payout)")

                # --- OPTION B: Buy ALL NO ---
                # Payout = Count - 1, Cost = total_no_ask
                # Profit = (Count - 1) - total_no_ask
                payout = float(count - 1)
                if total_no_ask < (payout - self.profit_margin):
                    profit_amt = payout - total_no_ask
                    profit_pct = (profit_amt / total_no_ask) * 100
                    event_url = f"https://polymarket.com/event/{data['slug']}"
                    alerts.append(f"🔥 **NO BUNDLE ARB: {data['title']}**\n• [View Event]({event_url}): **{profit_pct:.2f}% Profit** (Cost: **{total_no_ask:.3f}** for ${payout:.2f} payout)")

            # 3. Final Combine and Send
            if binary_arbs:
                alerts.append("✨ **Individual Binary Glitches**\n" + "\n".join(binary_arbs))

            if alerts:
                msg = f"<@{self.owner_id}> 🎯 **LIVE ARBITRAGE DETECTED**\n\n" + "\n\n".join(alerts)
                await self._alert_discord(msg)

            await asyncio.sleep(self.polling_interval)
            
        except Exception as e:
            logger.error(f"Error in NegativeRisk loop: {e}")
            await asyncio.sleep(60)

    async def _alert_discord(self, message: str):
        if not self.discord_token: 
            logger.warning("No Discord token found, skipping alert.")
            return
            
        url = f"https://discord.com/api/v10/channels/{self.discord_thread_id}/messages"
        
        # Split message if it exceeds Discord's 2000 character limit
        chunks = []
        if len(message) > 1900:
            lines = message.split("\n")
            current_chunk = ""
            for line in lines:
                if len(current_chunk) + len(line) + 1 > 1900:
                    chunks.append(current_chunk)
                    current_chunk = ""
                current_chunk += line + "\n"
            if current_chunk:
                chunks.append(current_chunk)
        else:
            chunks = [message]

        async with httpx.AsyncClient() as client:
            for chunk in chunks:
                try:
                    resp = await client.post(url, 
                        headers={"Authorization": f"Bot {self.discord_token}"},
                        json={"content": chunk}
                    )
                    if resp.status_code >= 400:
                        logger.error(f"Discord API Error ({resp.status_code}): {resp.text}")
                    else:
                        logger.info("Discord alert sent successfully.")
                except Exception as e:
                    logger.error(f"Failed to send Discord alert: {e}")

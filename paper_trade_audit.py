import asyncio
import httpx
import pandas as pd
import os
import json
import uuid
from datetime import datetime, timedelta, timezone
from src.utils.logger import logger
from src.security.config import get_settings
from src.data.client import PolymarketClient, KrakenClient
from src.data.websocket_client import WebSocketClient
from src.utils.market_simulator import MarketSimulator
from src.utils.token_mapper import TokenMapper
from src.utils.strategy_manager import StrategyManager

class PaperTradeAudit:
    """
    Industry-grade Paper Trader with Real-time CLOB simulation via WebSocket.
    """
    def __init__(self, ledger_path="logs/paper_ledger.json"):
        self.active_signals = [] # List of tracked positions
        self.btc_buffer = [] 
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.settings = get_settings()
        self.poly_client = PolymarketClient(self.settings)
        self.kraken = KrakenClient()
        self.wss = WebSocketClient()
        self.mapper = TokenMapper()
        self.manager = StrategyManager()
        
        self.live_books = {}
        self.balance = 1000.0
        self.bet_size = 50.0
        
        self.strategies = {
            "btc_trend": {"name": "BTC Trend (Optimized)", "interval": 15, "thread_id": "1511145712841396355", "desc": "Lead-Lag Trend"},
            "sniper_v3": {"name": "Sniper V3", "interval": 15, "thread_id": "1511145712841396355", "desc": "15m Dual Confluence"}
        }
        
        # Load optimized parameters
        import yaml
        try:
            with open("config/strategy_config.yaml", "r") as f:
                self.config = yaml.safe_load(f)
        except:
            self.config = {}

    async def _alert_discord(self, msg: str, thread_id: str):
        url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
        headers = {"Authorization": f"Bot {self.discord_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            await client.post(url, headers=headers, json={"content": msg})

    async def fetch_btc(self):
        try:
            df = await self.kraken.get_btc_ohlc(interval=1)
            return df.iloc[-1]['price']
        except: return 0

    async def ensure_wss(self, token_ids: list):
        if not self.wss.connected:
            await self.wss.connect()
            # Subscribe to all current positions + new ones
            active_tids = [s['token_id'] for s in self.active_signals]
            await self.wss.subscribe(active_tids + token_ids)
        
        # Update local live_books from WSS
        for tid in token_ids:
            book = self.wss.get_book(tid)
            if book: self.live_books[tid] = book

    async def simulate_execution(self, prediction: str, current_price: float, interval: int = 15) -> dict:
        try:
            market = await self.mapper.get_market_for_prediction(prediction, current_price, interval)
            if not market: return {"error": f"No suitable {interval}m Polymarket found"}
            
            tid = market['token_id']
            await self.ensure_wss([tid])
            
            # Wait up to 3s for WSS book
            for _ in range(6):
                if tid in self.live_books: break
                await asyncio.sleep(0.5)
                
            if tid not in self.live_books:
                try: self.live_books[tid] = await self.poly_client.get_orderbook(tid)
                except: return {"error": "REST fallback failed"}

            orderbook = self.live_books[tid]
            execution = MarketSimulator.simulate_buy(orderbook, self.bet_size)
            if "error" in execution: return execution
            
            execution.update({
                "token_id": tid,
                "slug": market['slug'],
                "question": market['question']
            })
            return execution
        except Exception as e:
            return {"error": str(e)}

    async def run_loop(self):
        logger.info(f"🚀 Starting Unified Paper Trader (Run: {self.run_id})")
        
        # Load historical buffer for indicators
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart", params={"vs_currency": "usd", "days": "1"})
                for e in r.json().get("prices", []): self.btc_buffer.append((datetime.fromtimestamp(e[0]/1000), e[1]))
        except: pass

        while True:
            try:
                p = await self.fetch_btc()
                if p == 0: await asyncio.sleep(10); continue
                now = datetime.now()
                self.btc_buffer.append((now, p))
                # Keep 24h buffer
                self.btc_buffer = [b for b in self.btc_buffer if b[0] > now - timedelta(minutes=1440)]

                if len(self.btc_buffer) > 200:
                    df_btc = pd.DataFrame([b[1] for b in self.btc_buffer], columns=['price'])
                    df = self.manager.calculate_indicators(df_btc)
                    
                    # 1. CHECK FOR NEW SIGNALS
                    for strat_id, strat_info in self.strategies.items():
                        strat_params = self.config.get('strategy', {}).get('parameters', {}) if strat_id == "btc_trend" else None
                        pred = self.manager.check_entry_signal(strat_id, df, config=strat_params)
                        
                        if pred and self.balance >= self.bet_size:
                            # Cooldown check
                            if not any(s for s in self.active_signals if s['strat'] == strat_id and (now - s['start_t']).seconds < (strat_info['interval'] * 60)):
                                execution = await self.simulate_execution(pred, p, strat_info['interval'])
                                if "error" in execution: continue
                                    
                                trade_id = str(uuid.uuid4())[:8]
                                msg = (f"🔭 **{strat_info['name']} SIGNAL**\n"
                                       f"• **Trade ID:** `{trade_id}`\n"
                                       f"• **Market:** [{execution['slug']}](https://polymarket.com/market/{execution['slug']})\n"
                                       f"• **Bet Size:** ${self.bet_size:.2f}\n"
                                       f"• **Actual Avg Fill:** ${execution['avg_price']:.3f}\n"
                                       f"• **Action:** PAPER BUY {'YES' if pred == 'UP' else 'NO'}")
                                
                                await self._alert_discord(msg, strat_info['thread_id'])
                                self.active_signals.append({
                                    "trade_id": trade_id, "strat": strat_id, "start_t": now, 
                                    "token_id": execution['token_id'], "entry_price": execution['avg_price'],
                                    "shares": execution['shares'], "peak_roi": -100.0, "has_scaled_out": False,
                                    "interval_min": strat_info['interval'], "resolve_t": now + timedelta(minutes=strat_info['interval'])
                                })

                    # 2. ACTIVE MANAGEMENT (EXITS)
                    resolved = []
                    for s in self.active_signals:
                        tid = s['token_id']
                        # Fetch live bid side
                        try:
                            book = await self.poly_client.get_orderbook(tid)
                            sell_sim = MarketSimulator.simulate_sell(book, s['shares'])
                            curr_bid = sell_sim['avg_price']
                        except: continue

                        time_left = (s['resolve_t'] - now).total_seconds()
                        
                        # Evaluate exit via Centralized StrategyManager
                        exit_eval = self.manager.evaluate_exit(s, curr_bid, time_left)
                        
                        if exit_eval['action'] == "EXIT_FULL":
                            pnl = (s['shares'] * curr_bid) - self.bet_size
                            self.balance += pnl
                            msg = (f"⚡ **EARLY EXIT ({exit_eval['reason']})**\n"
                                   f"• **Trade ID:** `{s['trade_id']}`\n"
                                   f"• **Realized ROI:** {exit_eval['roi']:.2%}\n"
                                   f"• **PnL:** ${pnl:+.2f}")
                            await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                            resolved.append(s)
                        
                        elif exit_eval['action'] == "EXIT_HALF":
                            # Scale out 50%
                            half_shares = s['shares'] / 2
                            pnl = (half_shares * curr_bid) - (self.bet_size / 2)
                            self.balance += pnl
                            s['shares'] -= half_shares
                            s['has_scaled_out'] = True
                            msg = (f"✂️ **SCALING OUT (1/2)**\n"
                                   f"• **Trade ID:** `{s['trade_id']}`\n"
                                   f"• **ROI:** {exit_eval['roi']:.2%}\n"
                                   f"• **Locked PnL:** ${pnl:+.2f}")
                            await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                        
                        s['peak_roi'] = exit_eval['peak_roi']

                        # FINAL EXPIRY RESOLUTION
                        if now >= s['resolve_t'] and s not in resolved:
                            win = (s['entry_price'] > 0.5) # Simplified for paper resolve
                            # In real life, check BTC price vs entry BTC
                            final_val = s['shares'] * 1.0 if win else 0.0
                            pnl = final_val - (self.bet_size / 2 if s['has_scaled_out'] else self.bet_size)
                            self.balance += pnl
                            msg = f"🏁 **EXPIRED**\n• **Trade ID:** `{s['trade_id']}`\n• **Final PnL:** ${pnl:+.2f}"
                            await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                            resolved.append(s)

                    for r in resolved: self.active_signals.remove(r)

                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Loop Error: {e}"); await asyncio.sleep(10)

if __name__ == "__main__":
    audit = PaperTradeAudit()
    asyncio.run(audit.run_loop())

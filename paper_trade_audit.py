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
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.settings = get_settings()
        self.discord_token = self.settings.DISCORD_TOKEN
        self.poly_client = PolymarketClient(self.settings)
        self.kraken = KrakenClient()
        self.wss = WebSocketClient()
        self.mapper = TokenMapper()
        self.manager = StrategyManager()
        
        self.live_books = {}
        self._load_ledger()
        self.bet_size = 50.0
        
        self.strategies = {
            "btc_trend": {"name": "BTC Trend (Optimized)", "interval": 15, "thread_id": "1514487790623133790", "desc": "Lead-Lag Trend"},
            "sniper_v3": {"name": "Sniper V3", "interval": 15, "thread_id": "1514487790623133790", "desc": "15m Dual Confluence"}
        }
        
        # Load optimized parameters
        import yaml
        try:
            with open("config/strategy_config.yaml", "r") as f:
                self.config = yaml.safe_load(f)
        except:
            self.config = {}

    def _load_ledger(self):
        try:
            with open(self.ledger_path, "r") as f:
                data = json.load(f)
                self.balance = data.get("current_balance", 1000.0)
                logger.info(f"Loaded balance from ledger: ${self.balance:.2f}")
        except:
            self.balance = 1000.0
            logger.warning("No ledger found, starting with $1000")

    def _save_ledger(self, trade_data=None):
        try:
            history = []
            try:
                with open(self.ledger_path, "r") as f:
                    history = json.load(f).get("history", [])
            except: pass
            
            if trade_data:
                history.append(trade_data)
            
            with open(self.ledger_path, "w") as f:
                json.dump({
                    "current_balance": self.balance,
                    "last_update": datetime.now().isoformat(),
                    "history": history
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ledger: {e}")

    async def _alert_discord(self, msg: str, thread_id: str):
        if not self.discord_token:
            logger.error("No Discord Token found in settings!")
            return
            
        url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
        headers = {"Authorization": f"Bot {self.discord_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, headers=headers, json={"content": msg})
                print(f"[Discord] Sent to {thread_id}, Status: {r.status_code}")
                if r.status_code >= 400:
                    logger.error(f"Discord API Error ({r.status_code}): {r.text}")
            except Exception as e:
                logger.error(f"Failed to post to Discord: {e}")

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
        await self._alert_discord(f"🚀 **Paper Trader Online** (Run: `{self.run_id}`)\n• Balance: `${self.balance:.2f}`\n• Loop: `2s`\n• Parity: `Unified Strategy Classes`", "1514487790623133790")
        
        # Load historical buffer for indicators
        try:
            # Get last 4 hours of 1m data for EMA/RSI stability
            df_hist = await self.kraken.get_btc_ohlc(interval=1)
            for _, row in df_hist.iterrows():
                self.btc_buffer.append((row.name, row['price']))
        except Exception as e:
            logger.error(f"Failed to prime BTC buffer: {e}")

        last_check_min = None

        while True:
            try:
                # 1. Faster Poll (Kraken is <1s latency)
                p = await self.fetch_btc()
                if p == 0: await asyncio.sleep(2); continue
                
                now = datetime.now()
                self.btc_buffer.append((now, p))
                # Keep 24h buffer
                self.btc_buffer = [b for b in self.btc_buffer if b[0] > now - timedelta(minutes=1440)]

                # 2. Resample buffer to 1m bars for Strategy Parity
                df_ticks = pd.DataFrame(self.btc_buffer, columns=['timestamp', 'price'])
                df_ticks.set_index('timestamp', inplace=True)
                df_1m = df_ticks['price'].resample('1min').last().ffill().to_frame()
                
                # Update Indicators on 1m bars
                df = self.manager.calculate_indicators(df_1m)
                
                # 3. Check for Entry (Only once per minute to avoid double-entry)
                current_min = now.replace(second=0, microsecond=0)
                if current_min != last_check_min:
                    logger.debug(f"Checking minute {current_min} (Buffer rows: {len(df)})")
                    for strat_id, strat_info in self.strategies.items():
                        strat_params = self.config.get('strategy', {}).get('parameters', {}) if strat_id == "btc_trend" else None
                        pred = self.manager.check_entry_signal(strat_id, df, config=strat_params)
                        
                        if pred:
                            logger.warning(f"🎯 SIGNAL DETECTED: {strat_id} -> {pred}")
                            if self.balance < self.bet_size:
                                logger.error(f"Insufficient balance for {strat_id}: ${self.balance:.2f} < ${self.bet_size:.2f}")
                                continue
                                
                            # Cooldown check
                            if not any(s for s in self.active_signals if s['strat'] == strat_id and (now - s['start_t']).seconds < (strat_info['interval'] * 60)):
                                execution = await self.simulate_execution(pred, p, strat_info['interval'])
                                if "error" in execution:
                                    logger.error(f"Execution Error for {strat_id}: {execution['error']}")
                                    continue
                                    
                                trade_id = str(uuid.uuid4())[:8]
                                msg = (f"🔭 **{strat_info['name']} SIGNAL**\n"
                                       f"• **Trade ID:** `{trade_id}`\n"
                                       f"• **Market:** [{execution['slug']}](https://polymarket.com/market/{execution['slug']})\n"
                                       f"• **Bet Size:** ${self.bet_size:.2f}\n"
                                       f"• **Actual Avg Fill:** ${execution['avg_price']:.3f}\n"
                                       f"• **Action:** PAPER BUY {'YES' if pred == 'UP' else 'NO'}")
                                
                                await self._alert_discord(msg, strat_info['thread_id'])
                                
                                trade_entry = {
                                    "trade_id": trade_id, "strat": strat_id, "start_t": now, 
                                    "token_id": execution['token_id'], "entry_price": execution['avg_price'],
                                    "shares": execution['shares'], "peak_roi": -100.0, "has_scaled_out": False,
                                    "interval_min": strat_info['interval'], "resolve_t": now + timedelta(minutes=strat_info['interval'])
                                }
                                self.active_signals.append(trade_entry)
                                self.balance -= self.bet_size
                                self._save_ledger()
                            else:
                                logger.info(f"Signal for {strat_id} skipped due to cooldown.")

                    last_check_min = current_min

                # 4. Active Management (Exits)
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
                        self.balance += (s['shares'] * curr_bid)
                        msg = (f"⚡ **EARLY EXIT ({exit_eval['reason']})**\n"
                               f"• **Trade ID:** `{s['trade_id']}`\n"
                               f"• **Realized ROI:** {exit_eval['roi']:.2%}\n"
                               f"• **PnL:** ${pnl:+.2f}")
                        await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                        resolved.append(s)
                        self._save_ledger()
                    
                    elif exit_eval['action'] == "EXIT_HALF":
                        # Scale out 50%
                        half_shares = s['shares'] / 2
                        pnl = (half_shares * curr_bid) - (self.bet_size / 2)
                        self.balance += (half_shares * curr_bid)
                        s['shares'] -= half_shares
                        s['has_scaled_out'] = True
                        msg = (f"✂️ **SCALING OUT (1/2)**\n"
                               f"• **Trade ID:** `{s['trade_id']}`\n"
                               f"• **ROI:** {exit_eval['roi']:.2%}\n"
                               f"• **Locked PnL:** ${pnl:+.2f}")
                        await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                        self._save_ledger()
                    
                    s['peak_roi'] = exit_eval['peak_roi']

                    # FINAL EXPIRY RESOLUTION
                    if now >= s['resolve_t'] and s not in resolved:
                        win = (s['entry_price'] > 0.5) # Simplified for paper resolve
                        # In real life, check BTC price vs entry BTC
                        final_val = s['shares'] * 1.0 if win else 0.0
                        pnl = final_val - (self.bet_size / 2 if s['has_scaled_out'] else self.bet_size)
                        self.balance += final_val
                        msg = f"🏁 **EXPIRED**\n• **Trade ID:** `{s['trade_id']}`\n• **Final PnL:** ${pnl:+.2f}"
                        await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                        resolved.append(s)
                        self._save_ledger()

                for r in resolved: self.active_signals.remove(r)

                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Loop Error: {e}"); await asyncio.sleep(10)

if __name__ == "__main__":
    audit = PaperTradeAudit()
    asyncio.run(audit.run_loop())

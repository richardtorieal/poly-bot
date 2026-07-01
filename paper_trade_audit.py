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
    def __init__(self, ledger_path="logs/paper_ledger.json", strategy_id=None):
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
        
        all_strategies = {
            "btc_trend": {"name": "BTC Trend (Optimized)", "interval": 15, "thread_id": "1511091530385985707", "desc": "Lead-Lag Trend"},
            "sniper_v3": {"name": "Sniper V3", "interval": 15, "thread_id": "1511145712841396355", "desc": "15m Dual Confluence"},
            "scalper_v1": {"name": "Scalper V1", "interval": 5, "thread_id": "1511147705324277761", "desc": "5m Trend Pullback"}
        }

        if strategy_id:
            if strategy_id not in all_strategies:
                raise ValueError(f"Unknown strategy: {strategy_id}")
            self.strategies = {strategy_id: all_strategies[strategy_id]}
            logger.info(f"Running isolated process for strategy: {strategy_id}")
        else:
            self.strategies = all_strategies
            logger.info("Running unified process with all strategies")
        
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

    async def simulate_execution(self, prediction: str, current_price: float, interval: int = 15, bet_size: float = 50.0) -> dict:
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
            execution = MarketSimulator.simulate_buy(orderbook, bet_size)
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
        # Route startup message to the first active strategy's thread
        thread_id = list(self.strategies.values())[0]['thread_id'] if self.strategies else "1514487790623133790"
        await self._alert_discord(f"🚀 **Paper Trader Online** (Run: `{self.run_id}`)\n• Balance: `${self.balance:.2f}`\n• Loop: `2s`\n• Parity: `Unified Strategy Classes`", thread_id)
        
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
                            
                            # Dynamic position sizing (compounding)
                            pos_size_pct = 0.03
                            if strat_id == "btc_trend":
                                pos_size_pct = self.config.get('strategy', {}).get('parameters', {}).get('pos_size_pct', 0.03)
                            bet_size = max(5.0, round(self.balance * pos_size_pct, 2))
                            
                            if self.balance < bet_size:
                                logger.error(f"Insufficient balance for {strat_id}: ${self.balance:.2f} < ${bet_size:.2f}")
                                continue
                                
                            # Cooldown check
                            if not any(s for s in self.active_signals if s['strat'] == strat_id and (now - s['start_t']).seconds < (strat_info['interval'] * 60)):
                                execution = await self.simulate_execution(pred, p, strat_info['interval'], bet_size)
                                if "error" in execution:
                                    logger.error(f"Execution Error for {strat_id}: {execution['error']}")
                                    continue
                                    
                                trade_id = str(uuid.uuid4())[:8]
                                self.balance -= bet_size
                                
                                msg = (f"🔭 **{strat_info['name']} SIGNAL**\n"
                                       f"• **Trade ID:** `{trade_id}`\n"
                                       f"• **Market:** [{execution['slug']}](https://polymarket.com/market/{execution['slug']})\n"
                                       f"• **Bet Size:** ${bet_size:.2f}\n"
                                       f"• **Actual Avg Fill:** ${execution['avg_price']:.3f}\n"
                                       f"• **Action:** PAPER BUY {'YES' if pred == 'UP' else 'NO'}\n"
                                       f"• **Account Balance:** ${self.balance:.2f}")
                                
                                await self._alert_discord(msg, strat_info['thread_id'])
                                
                                trade_entry = {
                                    "trade_id": trade_id, "strat": strat_id, "start_t": now, 
                                    "token_id": execution['token_id'], "entry_price": execution['avg_price'],
                                    "shares": execution['shares'], "peak_roi": -100.0, "has_scaled_out": False,
                                    "interval_min": strat_info['interval'], "resolve_t": now + timedelta(minutes=strat_info['interval']),
                                    "bet_size": bet_size,
                                    "entry_btc": p,
                                    "prediction": pred
                                }
                                self.active_signals.append(trade_entry)
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
                        total_exit_value = s['shares'] * curr_bid
                        # PnL is (Total Cash Out) - (Total Cash In for these shares)
                        # When selling FULL, cash in is either bet_size (if no scale out) or bet_size/2 (if already scaled out)
                        initial_cost = s.get('bet_size', 50.0) if not s['has_scaled_out'] else (s.get('bet_size', 50.0) / 2)
                        pnl = total_exit_value - initial_cost
                        self.balance += total_exit_value
                        
                        msg = (f"⚡ **EARLY EXIT ({exit_eval['reason']})**\n"
                               f"• **Trade ID:** `{s['trade_id']}`\n"
                               f"• **Realized ROI:** {exit_eval['roi']:.2f}%\n"
                               f"• **PnL:** ${pnl:+.2f}\n"
                               f"• **Account Balance:** ${self.balance:.2f}")
                        await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                        resolved.append(s)
                        self._save_ledger()
                    
                    elif exit_eval['action'] == "EXIT_HALF":
                        # Scale out 50%
                        half_shares = s['shares'] / 2
                        exit_value = half_shares * curr_bid
                        initial_cost = s.get('bet_size', 50.0) / 2 # 50% of original bet
                        pnl = exit_value - initial_cost
                        self.balance += exit_value
                        s['shares'] -= half_shares
                        s['has_scaled_out'] = True
                        
                        msg = (f"✂️ **SCALING OUT (1/2)**\n"
                               f"• **Trade ID:** `{s['trade_id']}`\n"
                               f"• **ROI:** {exit_eval['roi']:.2f}%\n"
                               f"• **Locked PnL:** ${pnl:+.2f}\n"
                               f"• **Account Balance:** ${self.balance:.2f}")
                        await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                        self._save_ledger()
                    
                    s['peak_roi'] = exit_eval['peak_roi']

                    # FINAL EXPIRY RESOLUTION
                    if now >= s['resolve_t'] and s not in resolved:
                        curr_btc = await self.fetch_btc()
                        entry_btc = s.get('entry_btc', 0.0)
                        prediction = s.get('prediction', 'UP')
                        
                        if entry_btc > 0.0 and curr_btc > 0.0:
                            win = (prediction == 'UP' and curr_btc > entry_btc) or (prediction == 'DOWN' and curr_btc < entry_btc)
                            logger.info(f"Resolution for {s['trade_id']}: Pred={prediction}, Entry BTC={entry_btc:.2f}, Expiry BTC={curr_btc:.2f} -> Win={win}")
                        else:
                            win = (s['entry_price'] > 0.5) # Fallback to entry price rule
                            logger.warning(f"Resolution fallback for {s['trade_id']}: entry_btc or curr_btc missing.")
                            
                        final_val = s['shares'] * 1.0 if win else 0.0
                        initial_cost = s.get('bet_size', 50.0) if not s['has_scaled_out'] else (s.get('bet_size', 50.0) / 2)
                        pnl = final_val - initial_cost
                        self.balance += final_val
                        
                        msg = (f"🏁 **EXPIRED**\n"
                               f"• **Trade ID:** `{s['trade_id']}`\n"
                               f"• **Final PnL:** ${pnl:+.2f}\n"
                               f"• **Account Balance:** ${self.balance:.2f}")
                        await self._alert_discord(msg, self.strategies[s['strat']]['thread_id'])
                        resolved.append(s)
                        self._save_ledger()

                for r in resolved: self.active_signals.remove(r)

                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Loop Error: {e}"); await asyncio.sleep(10)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Poly-Bot Paper Trader")
    parser.add_argument("--strategy", type=str, help="Strategy ID to run (e.g. btc_trend, sniper_v3, scalper_v1)")
    parser.add_argument("--ledger", type=str, help="Path to ledger JSON file")
    args = parser.parse_args()

    ledger_path = args.ledger if args.ledger else "logs/paper_ledger.json"
    audit = PaperTradeAudit(ledger_path=ledger_path, strategy_id=args.strategy)
    asyncio.run(audit.run_loop())

import pandas as pd
import numpy as np
import json
from datetime import timedelta
from typing import List, Dict, Any
from src.utils.market_simulator import MarketSimulator
from src.utils.logger import logger
from src.utils.strategy_manager import StrategyManager

class ShortTermEngine:
    """
    TRUTHFUL Backtesting Engine using Centralized StrategyManager.
    """
    def __init__(self, initial_balance: float = 1000.0, bet_size: float = 50.0):
        self.initial_balance = initial_balance
        self.bet_size = bet_size
        self.manager = StrategyManager()

    def run_scenario(self, df: pd.DataFrame, 
                     interval_min: int = 15, 
                     strategy: str = "dual_confluence",
                     early_exit: bool = True,
                     final_minute_protector: bool = False,
                     simulate_spread: bool = True) -> Dict[str, Any]:
        
        # Determine strategy ID from name (compatibility layer)
        strat_id = "sniper_v3" if strategy == "dual_confluence" else "scalper_v1"
        
        # Pre-calculate indicators using centralized logic
        df = self.manager.calculate_indicators(df.copy())
        balance = self.initial_balance
        trades = []
        
        # Iterate through window boundaries
        window_starts = df.drop_duplicates(subset=['window_start']).index
        
        for t_entry in window_starts:
            if balance < self.bet_size: break
            
            # SIGNAL CHECK (Delegated to StrategyManager)
            # We must pass the slice up to current t_entry for indicators to be correct
            df_slice = df.loc[:t_entry]
            prediction = self.manager.check_entry_signal(strat_id, df_slice)

            if prediction:
                row = df.loc[t_entry]
                if np.isnan(row['yes_price']): continue
                
                mid_price = row['yes_price'] if prediction == "UP" else row['no_price']
                if mid_price <= 0 or mid_price >= 1: mid_price = 0.5

                # ENTRY
                if simulate_spread:
                    synthetic_book = {
                        "asks": [{"price": str(round(mid_price * 1.005, 4)), "size": "1000"}],
                        "bids": [{"price": str(round(mid_price * 0.995, 4)), "size": "1000"}]
                    }
                    execution = MarketSimulator.simulate_buy(synthetic_book, self.bet_size)
                    avg_entry_price = execution['avg_price']
                else:
                    avg_entry_price = mid_price
                
                initial_shares = self.bet_size / avg_entry_price
                
                # Active Position State
                pos = {
                    "entry_price": avg_entry_price,
                    "shares": initial_shares,
                    "peak_roi": -100.0,
                    "has_scaled_out": False,
                    "interval_min": interval_min
                }
                
                realized_pnl = 0.0
                exit_reason = "EXPIRED"
                
                # INTRA-WINDOW LOOP (1m candles)
                t_end = t_entry + timedelta(minutes=interval_min)
                if t_end not in df.index: 
                    next_avail = df.index[df.index > t_entry]
                    if len(next_avail) > 0: t_end = next_avail[min(len(next_avail)-1, interval_min-1)]
                    else: continue
                
                interval_candles = df.loc[t_entry : t_end - timedelta(minutes=1)]
                
                for ts, c_row in interval_candles.iterrows():
                    curr_mid = c_row['yes_price'] if prediction == "UP" else c_row['no_price']
                    if np.isnan(curr_mid): continue
                    
                    if simulate_spread:
                        # Selling at the Bid
                        curr_bid_price = curr_mid * 0.995
                    else:
                        curr_bid_price = curr_mid
                    
                    time_left = (t_end - ts).total_seconds()
                    
                    # EXIT EVALUATION (Delegated to StrategyManager)
                    exit_eval = self.manager.evaluate_exit(pos, curr_bid_price, time_left, final_minute_protector)
                    
                    if early_exit:
                        if exit_eval['action'] == "EXIT_FULL":
                            realized_pnl += (pos['shares'] * curr_bid_price) - (self.bet_size / 2 if pos['has_scaled_out'] else self.bet_size)
                            pos['shares'] = 0
                            exit_reason = exit_eval['reason']
                            break
                        
                        elif exit_eval['action'] == "EXIT_HALF":
                            sell_shares = initial_shares / 2
                            scaling_rev = sell_shares * curr_bid_price
                            realized_pnl += (scaling_rev - (self.bet_size / 2))
                            pos['shares'] -= sell_shares
                            pos['has_scaled_out'] = True
                    
                    pos['peak_roi'] = exit_eval['peak_roi']
                
                # FINAL RESOLUTION
                if pos['shares'] > 0:
                    end_btc = df.loc[t_end, 'price']
                    start_btc = row['price']
                    win = (prediction == "UP" and end_btc > start_btc) or (prediction == "DOWN" and end_btc < start_btc)
                    final_value = 1.0 if win else 0.0
                    realized_pnl += (pos['shares'] * final_value) - (self.bet_size / 2 if pos['has_scaled_out'] else self.bet_size)
                
                balance += realized_pnl
                trades.append({
                    "time": t_entry.strftime("%Y-%m-%d %H:%M"),
                    "prediction": prediction,
                    "exit": exit_reason,
                    "pnl": realized_pnl,
                    "balance": balance
                })

        wins = sum(1 for t in trades if t['pnl'] > 0)
        return {
            "strategy": strategy,
            "trades": len(trades),
            "win_rate": (wins / len(trades) * 100) if trades else 0,
            "final_balance": balance,
            "pnl": balance - self.initial_balance
        }

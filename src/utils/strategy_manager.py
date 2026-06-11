import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from src.strategies.btc_trend import BTCTrendStrategy

class StrategyManager:
    """
    Centralized hub for all strategy signals and trade management.
    Ensures parity between Backtester and Live Paper Trader.
    """
    
    def __init__(self):
        # Cache strategy instances to maintain state if needed
        self._strategy_instances = {}

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates standard indicators used across all strategies.
        Expects 'price' column.
        """
        df = df.copy()
        df['ema9'] = df['price'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['price'].ewm(span=21, adjust=False).mean()
        df['ema200'] = df['price'].ewm(span=200, adjust=False).mean()
        
        delta = df['price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    def check_entry_signal(self, strategy_id: str, df: pd.DataFrame, config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Checks for a trade entry signal at the current (last) row.
        """
        if len(df) < 200: return None
        
        row = df.iloc[-1]
        history = df.iloc[:-1] # Data excluding the current row for consistency with class .decide()
        
        if strategy_id == "btc_trend" and config:
            # Use the actual class to ensure parity
            params = {
                'btc_threshold': config.get('btc_threshold', 0.005),
                'lookback_minutes': config.get('lookback_minutes', 15),
                'er_threshold': config.get('er_threshold', 0.5)
            }
            
            strat_key = f"btc_trend_{hash(frozenset(params.items()))}"
            if strat_key not in self._strategy_instances:
                self._strategy_instances[strat_key] = BTCTrendStrategy(**params)
            
            # Map "YES"/"NO" from class to "UP"/"DOWN" for manager
            decision = self._strategy_instances[strat_key].decide(row.rename({'price': 'btc_price'}), history.rename(columns={'price': 'btc_price'}))
            if decision == "YES": return "UP"
            elif decision == "NO": return "DOWN"
            return None

        # Fallback for strategies not yet unified
        # h1_lookback: look at the EMA200 from 60 mins ago for persistence
        row_1h = df.iloc[-60] if len(df) >= 60 else df.iloc[0]

        if strategy_id == "sniper_v3":
            # 15m Dual Confluence
            if row['price'] > row_1h['ema200'] and row['ema9'] > row['ema21'] and row['rsi'] > 55:
                return "UP"
            elif row['price'] < row_1h['ema200'] and row['ema9'] < row['ema21'] and row['rsi'] < 45:
                return "DOWN"
                
        elif strategy_id == "scalper_v1":
            # 5m Trend Pullback
            if row['price'] > row_1h['ema200'] and row['rsi'] < 40:
                return "UP"
            elif row['price'] < row_1h['ema200'] and row['rsi'] > 60:
                return "DOWN"
                
        return None

    @staticmethod
    def evaluate_exit(position: Dict[str, Any], 
                      current_bid_price: float, 
                      time_left_sec: float,
                      final_minute_protector: bool = True) -> Dict[str, Any]:
        """
        Implements the 'Hybrid Power' exit logic.
        Position dict must contain: entry_price, shares, peak_roi, has_scaled_out, interval_min
        """
        entry_price = position['entry_price']
        peak_roi = position.get('peak_roi', -100.0)
        has_scaled_out = position.get('has_scaled_out', False)
        
        # Calculate Current ROI (Realized at Bid)
        running_roi = ((current_bid_price - entry_price) / entry_price) * 100
        peak_roi = max(peak_roi, running_roi)
        
        exit_action = None # "EXIT_FULL", "EXIT_HALF", or None
        reason = None
        
        # 1. Hard Stop Loss (-40%)
        if running_roi <= -40.0:
            return {"action": "EXIT_FULL", "reason": "STOP_LOSS", "roi": running_roi, "peak_roi": peak_roi}
            
        # 2. Milestone 1 (+100% ROI) -> Scale out 50%
        if running_roi >= 100.0 and not has_scaled_out:
            return {"action": "EXIT_HALF", "reason": "MILESTONE_100", "roi": running_roi, "peak_roi": peak_roi}
            
        # 3. Trailing Stop (20% from peak) - only after +50% ROI
        if peak_roi >= 50.0 and running_roi < (peak_roi - 20.0):
            return {"action": "EXIT_FULL", "reason": "TRAILING_STOP", "roi": running_roi, "peak_roi": peak_roi}
            
        # 4. Final Minute Protector
        if final_minute_protector:
            # Final 2 minutes for 15m, Final 45s for 5m
            is_final_stretch = False
            if position['interval_min'] == 15 and time_left_sec <= 120: is_final_stretch = True
            elif position['interval_min'] == 5 and time_left_sec <= 45: is_final_stretch = True
            
            if is_final_stretch:
                # If currently profitable, exit if we drop 5% from peak to lock it in
                if running_roi > 10.0 and running_roi < (peak_roi - 5.0):
                    return {"action": "EXIT_FULL", "reason": "FINAL_PROTECTOR", "roi": running_roi, "peak_roi": peak_roi}
                    
        return {"action": None, "roi": running_roi, "peak_roi": peak_roi}

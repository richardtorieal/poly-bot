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
                'btc_threshold_up': config.get('btc_threshold_up'),
                'btc_threshold_down': config.get('btc_threshold_down'),
                'lookback_minutes': config.get('lookback_minutes', 15),
                'er_threshold': config.get('er_threshold', 0.5),
                'max_minutes_elapsed': config.get('max_minutes_elapsed', 999.0),
                'volatility_adapt': config.get('volatility_adapt', False),
                'er_lookback': config.get('er_lookback'),
                'filter_strike_trend': config.get('filter_strike_trend', True),
                'use_ema_filter': config.get('use_ema_filter', False),
                'ema_span': config.get('ema_span', 30)
            }
            
            # Since some values might be None, filter them out before hashing/instantiation
            # to fall back to the class defaults correctly
            params_filtered = {k: v for k, v in params.items() if v is not None}
            
            strat_key = f"btc_trend_{hash(frozenset(params_filtered.items()))}"
            if strat_key not in self._strategy_instances:
                self._strategy_instances[strat_key] = BTCTrendStrategy(**params_filtered)
            
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
                      final_minute_protector: bool = True,
                      config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        
        # 1. Stop Loss (configured or fallback to -40%)
        if config and 'stop_loss_pct' in config:
            stop_loss_roi = -config['stop_loss_pct'] * 100.0
        else:
            stop_loss_roi = -40.0
            
        if running_roi <= stop_loss_roi:
            return {"action": "EXIT_FULL", "reason": "STOP_LOSS", "roi": running_roi, "peak_roi": peak_roi}
            
        # 2. Profit Target (configured or fallback to milestone +100%)
        if config and 'exit_profit_pct' in config:
            target_roi = config['exit_profit_pct'] * 100.0
            if running_roi >= target_roi:
                return {"action": "EXIT_FULL", "reason": "PROFIT_TARGET", "roi": running_roi, "peak_roi": peak_roi}
        else:
            if running_roi >= 100.0 and not has_scaled_out:
                return {"action": "EXIT_HALF", "reason": "MILESTONE_100", "roi": running_roi, "peak_roi": peak_roi}
            
        # 3. Trailing Stop
        if config and 'trailing_stop_activation_pct' in config and 'trailing_stop_drop_pct' in config:
            ts_activation_roi = config['trailing_stop_activation_pct'] * 100.0
            ts_drop_roi = config['trailing_stop_drop_pct'] * 100.0
            if peak_roi >= ts_activation_roi and running_roi < (peak_roi - ts_drop_roi):
                return {"action": "EXIT_FULL", "reason": "TRAILING_STOP_CUSTOM", "roi": running_roi, "peak_roi": peak_roi}
        else:
            if peak_roi >= 50.0 and running_roi < (peak_roi - 20.0):
                return {"action": "EXIT_FULL", "reason": "TRAILING_STOP", "roi": running_roi, "peak_roi": peak_roi}
            
        # 4. Final Minute Protector
        if final_minute_protector:
            # Final 2 minutes for 15m, Final 45s for 5m
            is_final_stretch = False
            interval_min = position.get('interval_min', 15)
            if interval_min == 15 and time_left_sec <= 120: is_final_stretch = True
            elif interval_min == 5 and time_left_sec <= 45: is_final_stretch = True
            
            if is_final_stretch:
                # If currently profitable, exit if we drop 5% from peak to lock it in
                if running_roi > 10.0 and running_roi < (peak_roi - 5.0):
                    return {"action": "EXIT_FULL", "reason": "FINAL_PROTECTOR", "roi": running_roi, "peak_roi": peak_roi}
                    
        return {"action": None, "roi": running_roi, "peak_roi": peak_roi}

import pandas as pd
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def decide(self, current_data: pd.Series, history: pd.DataFrame) -> str:
        """
        Decide whether to buy 'YES', 'NO', or 'HOLD'.
        """
        pass

class BTCTrendStrategy(BaseStrategy):
    """
    Simple Lead-Lag strategy: If BTC moves more than X% in Y minutes, 
    bet on Polymarket catching up.
    """
    def __init__(self, btc_threshold: float = 0.0005, lookback_minutes: int = 5, er_threshold: float = 0.5, max_minutes_elapsed: float = 999.0, btc_threshold_up: float = None, btc_threshold_down: float = None, filter_strike_trend: bool = True):
        self.btc_threshold = btc_threshold
        self.btc_threshold_up = btc_threshold_up if btc_threshold_up is not None else btc_threshold
        self.btc_threshold_down = btc_threshold_down if btc_threshold_down is not None else btc_threshold
        self.lookback_minutes = lookback_minutes
        self.er_threshold = er_threshold
        self.max_minutes_elapsed = max_minutes_elapsed
        self.filter_strike_trend = filter_strike_trend

    def decide(self, current_data: pd.Series, history: pd.DataFrame) -> str:
        # Determine timestamp and check if within prediction window filter
        if 'timestamp' in current_data:
            ts = current_data['timestamp']
        elif hasattr(current_data.name, 'timestamp'):
            ts = current_data.name.timestamp()
        else:
            ts = float(current_data.name)
            
        ts_int = int(ts)
        window_start = (ts_int // 900) * 900
        elapsed_min = (ts_int - window_start) / 60.0
        
        if elapsed_min > self.max_minutes_elapsed:
            return "HOLD"

        if len(history) < self.lookback_minutes:
            return "HOLD"
            
        relevant_history = history.iloc[-self.lookback_minutes:]
        past_price = relevant_history.iloc[0]['btc_price']
        current_btc = current_data['btc_price']
        
        change = (current_btc - past_price) / past_price
        
        # Efficiency Ratio (ER)
        # ER = total_change / sum_of_absolute_minute_changes
        price_diffs = relevant_history['btc_price'].diff().abs()
        volatility = price_diffs.sum() + abs(current_btc - relevant_history.iloc[-1]['btc_price'])
        
        if volatility == 0:
            er = 0
        else:
            er = abs(current_btc - past_price) / volatility

        # Only enter if the trend is "efficient"
        if er < self.er_threshold:
            return "HOLD"
        
        # Filter by cumulative trend since the start of the 15-minute resolution window
        if self.filter_strike_trend and 'timestamp' in history.columns:
            window_start_row = history[history['timestamp'] == window_start]
            if not window_start_row.empty:
                strike_price = window_start_row.iloc[0]['btc_price']
                window_change = (current_btc - strike_price) / strike_price
                if change > 0 and window_change <= 0:
                    return "HOLD"
                if change < 0 and window_change >= 0:
                    return "HOLD"
        
        if change > self.btc_threshold_up:
            return "YES"
        elif change < -self.btc_threshold_down:
            return "NO"
        return "HOLD"

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
    def __init__(self, btc_threshold: float = 0.0005, lookback_minutes: int = 5, er_threshold: float = 0.5, max_minutes_elapsed: float = 999.0, btc_threshold_up: float = None, btc_threshold_down: float = None, filter_strike_trend: bool = True, volatility_adapt: bool = False, er_lookback: int = None, use_ema_filter: bool = False, ema_span: int = 30):
        self.btc_threshold = btc_threshold
        self.btc_threshold_up = btc_threshold_up if btc_threshold_up is not None else btc_threshold
        self.btc_threshold_down = btc_threshold_down if btc_threshold_down is not None else btc_threshold
        self.lookback_minutes = lookback_minutes
        self.er_threshold = er_threshold
        self.max_minutes_elapsed = max_minutes_elapsed
        self.filter_strike_trend = filter_strike_trend
        self.volatility_adapt = volatility_adapt
        self.er_lookback = er_lookback if er_lookback is not None else lookback_minutes
        self.use_ema_filter = use_ema_filter
        self.ema_span = ema_span

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
        
        # Adaptive volatility multiplier
        if self.volatility_adapt and len(history) >= 60:
            btc_prices = history['btc_price'].iloc[-60:]
            returns = btc_prices.pct_change().dropna()
            current_vol = returns.std()
            if current_vol > 0:
                vol_mult = current_vol / 0.000655
                vol_mult = max(0.5, min(2.0, vol_mult))
            else:
                vol_mult = 1.0
        else:
            vol_mult = 1.0

        threshold_up = self.btc_threshold_up * vol_mult
        threshold_down = self.btc_threshold_down * vol_mult
        
        # Efficiency Ratio (ER)
        # Calculated over er_lookback minutes instead of lookback_minutes for stability
        er_lookback_val = self.er_lookback
        if len(history) >= er_lookback_val:
            er_history = history.iloc[-er_lookback_val:]
            er_past_price = er_history.iloc[0]['btc_price']
            price_diffs = er_history['btc_price'].diff().abs()
            volatility = price_diffs.sum() + abs(current_btc - er_history.iloc[-1]['btc_price'])
            
            if volatility == 0:
                er = 0
            else:
                er = abs(current_btc - er_past_price) / volatility
        else:
            er = 0

        # Only enter if the trend is "efficient"
        if er < self.er_threshold:
            return "HOLD"
        
        # EMA filter to avoid counter-trend entries in high/medium-term regimes
        if self.use_ema_filter:
            if len(history) >= self.ema_span:
                # Calculating EMA of last ema_span rows
                ema = history['btc_price'].ewm(span=self.ema_span, adjust=False).mean().iloc[-1]
                if change > 0 and current_btc < ema:
                    return "HOLD"
                if change < 0 and current_btc > ema:
                    return "HOLD"
        
        # Filter by cumulative trend since the start of the 15-minute resolution window
        if self.filter_strike_trend and 'timestamp' in history.columns:
            strike_price = None
            # Fast reverse search up to 20 rows since window_start is at most 15 mins ago
            for j in range(1, min(20, len(history) + 1)):
                if history.iloc[-j]['timestamp'] == window_start:
                    strike_price = history.iloc[-j]['btc_price']
                    break
            if strike_price is None:
                window_start_row = history[history['timestamp'] == window_start]
                if not window_start_row.empty:
                    strike_price = window_start_row.iloc[0]['btc_price']
            
            if strike_price is not None:
                window_change = (current_btc - strike_price) / strike_price
                if change > 0 and window_change <= 0:
                    return "HOLD"
                if change < 0 and window_change >= 0:
                    return "HOLD"
        
        if change > threshold_up:
            return "YES"
        elif change < -threshold_down:
            return "NO"
        return "HOLD"


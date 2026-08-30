import pandas as pd
import numpy as np
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
    def __init__(self, btc_threshold: float = 0.0005, lookback_minutes: int = 5, er_threshold: float = 0.5, max_minutes_elapsed: float = 999.0, btc_threshold_up: float = None, btc_threshold_down: float = None, filter_strike_trend: bool = True, volatility_adapt: bool = False, er_lookback: int = None, use_ema_filter: bool = False, ema_span: int = 30, volatility_base: float = 0.000655, vol_mult_min: float = 0.5, vol_mult_max: float = 2.0):
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
        self.volatility_base = volatility_base
        self.vol_mult_min = vol_mult_min
        self.vol_mult_max = vol_mult_max
        self._prev_ema = None
        self._prev_len = 0

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

        n_history = len(history)
        if n_history < self.lookback_minutes:
            return "HOLD"
            
        btc_price_arr = history['btc_price'].values
        past_price = btc_price_arr[-self.lookback_minutes]
        current_btc = current_data['btc_price']
        
        change = (current_btc - past_price) / past_price
        
        # Adaptive volatility multiplier
        if self.volatility_adapt and n_history >= 60:
            prices_60 = btc_price_arr[-60:]
            returns = np.diff(prices_60) / prices_60[:-1]
            current_vol = np.std(returns, ddof=1)
            if current_vol > 0:
                vol_mult = current_vol / self.volatility_base
                vol_mult = max(self.vol_mult_min, min(self.vol_mult_max, vol_mult))
            else:
                vol_mult = 1.0
        else:
            vol_mult = 1.0

        threshold_up = self.btc_threshold_up * vol_mult
        threshold_down = self.btc_threshold_down * vol_mult
        
        # Efficiency Ratio (ER)
        # Calculated over er_lookback minutes instead of lookback_minutes for stability
        er_lookback_val = self.er_lookback
        if n_history >= er_lookback_val:
            er_prices = btc_price_arr[-er_lookback_val:]
            er_past_price = er_prices[0]
            price_diffs = np.abs(np.diff(er_prices))
            volatility = np.sum(price_diffs) + abs(current_btc - er_prices[-1])
            
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
            if n_history >= self.ema_span:
                # Optimized O(1) EMA updating
                if self._prev_ema is None or n_history < self._prev_len:
                    ema_series = history['btc_price'].ewm(span=self.ema_span, adjust=False).mean()
                    self._prev_ema = ema_series.iloc[-1]
                    self._prev_len = n_history
                else:
                    if n_history == self._prev_len + 1:
                        multiplier = 2.0 / (self.ema_span + 1.0)
                        self._prev_ema = current_btc * multiplier + self._prev_ema * (1.0 - multiplier)
                        self._prev_len = n_history
                    else:
                        ema_series = history['btc_price'].ewm(span=self.ema_span, adjust=False).mean()
                        self._prev_ema = ema_series.iloc[-1]
                        self._prev_len = n_history
                ema = self._prev_ema
                if change > 0 and current_btc < ema:
                    return "HOLD"
                if change < 0 and current_btc > ema:
                    return "HOLD"
        
        # Filter by cumulative trend since the start of the 15-minute resolution window
        if self.filter_strike_trend and 'timestamp' in history.columns:
            strike_price = None
            history_ts = history['timestamp'].values
            # Fast reverse search up to 20 rows since window_start is at most 15 mins ago
            for j in range(1, min(20, n_history + 1)):
                if history_ts[-j] == window_start:
                    strike_price = btc_price_arr[-j]
                    break
            if strike_price is None:
                indices = np.where(history_ts == window_start)[0]
                if len(indices) > 0:
                    strike_price = btc_price_arr[indices[0]]
            
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


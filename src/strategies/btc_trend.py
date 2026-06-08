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
    def __init__(self, btc_threshold: float = 0.0005, lookback_minutes: int = 5):
        self.btc_threshold = btc_threshold
        self.lookback_minutes = lookback_minutes

    def decide(self, current_data: pd.Series, history: pd.DataFrame) -> str:
        if len(history) < self.lookback_minutes:
            return "HOLD"
            
        past_price = history.iloc[-self.lookback_minutes]['btc_price']
        current_btc = current_data['btc_price']
        
        change = (current_btc - past_price) / past_price
        
        if change > self.btc_threshold:
            return "YES"
        elif change < -self.btc_threshold:
            return "NO"
        return "HOLD"

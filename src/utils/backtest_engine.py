import pandas as pd
import numpy as np
from typing import Dict, Any, Type
from src.utils.logger import logger
from src.strategies.btc_trend import BaseStrategy

class BacktestEngine:
    def __init__(self, initial_capital: float = 1000.0, slippage_bps: int = 5):
        self.initial_capital = initial_capital
        self.slippage = slippage_bps / 10000

    def run(self, strategy: BaseStrategy, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        cash = self.initial_capital
        equity_curve = []
        positions = [] 
        trades_count = 0
        winning_trades = 0
        
        for i in range(len(data)):
            current_row = data.iloc[i]
            history = data.iloc[:i]
            
            # 1. Update existing positions (Exits)
            new_positions = []
            for pos in positions:
                price_col = 'yes_price' if pos['side'] == 'YES' else 'no_price'
                current_val = current_row[price_col]
                
                # Check Profit/Loss
                pnl_pct = (current_val - pos['entry_price']) / pos['entry_price']
                
                if pnl_pct >= config['exit_profit_pct'] or pnl_pct <= -config['stop_loss_pct']:
                    exit_price = current_val * (1 - self.slippage)
                    trade_revenue = pos['shares'] * exit_price
                    cash += trade_revenue
                    trades_count += 1
                    if (trade_revenue > pos['capital']):
                        winning_trades += 1
                else:
                    new_positions.append(pos)
            positions = new_positions
            
            # 2. Strategy Decision (Entry)
            if cash > (self.initial_capital * 0.01): # Min 1% cash
                decision = strategy.decide(current_row, history)
                
                if decision in ["YES", "NO"] and len(positions) == 0:
                    price_col = 'yes_price' if decision == 'YES' else 'no_price'
                    entry_price = current_row[price_col]
                    
                    # Prevent buying at dust prices or near-certainties
                    if 0.05 < entry_price < 0.95:
                        entry_price_slipped = entry_price * (1 + self.slippage)
                        risk_amount = cash * config['pos_size_pct']
                        shares = risk_amount / entry_price_slipped
                        positions.append({
                            'side': decision,
                            'entry_price': entry_price_slipped,
                            'shares': shares,
                            'capital': risk_amount
                        })
                        cash -= risk_amount

            # 3. Track Equity
            unrealized = 0
            for pos in positions:
                price_col = 'yes_price' if pos['side'] == 'YES' else 'no_price'
                unrealized += pos['shares'] * current_row[price_col]
            
            equity_curve.append(cash + unrealized)

        # Final Metrics
        final_equity = equity_curve[-1]
        equity_series = pd.Series(equity_curve)
        returns = equity_series.pct_change().fillna(0)
        
        # Daily/Minute scale Sharpe (approximate)
        sharpe = (returns.mean() / returns.std() * np.sqrt(252 * 1440)) if returns.std() != 0 else 0
        
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0

        return {
            "initial_balance": self.initial_capital,
            "final_balance": final_equity,
            "total_pnl_pct": ((final_equity - self.initial_capital) / self.initial_capital) * 100,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "total_trades": trades_count,
            "win_rate": win_rate
        }

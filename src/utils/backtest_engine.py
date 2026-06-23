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
        
        for i in range(len(data) - 1): # Stay one step behind to allow next-bar execution
            current_row = data.iloc[i]
            next_row = data.iloc[i+1] # The bar where we actually execute
            # Limit history slice to the last 250 rows to prevent O(N^2) performance slowdown.
            # BTCTrendStrategy only uses a lookback of a few minutes, so 250 rows is more than sufficient.
            history = data.iloc[max(0, i - 250) : i + 1] # All data available up to and including current_row
            
            # 1. Update existing positions (Exits)
            new_positions = []
            for pos in positions:
                price_col = 'yes_price' if pos['side'] == 'YES' else 'no_price'
                current_val = current_row[price_col]
                
                # Check Profit/Loss condition at current_row
                pnl_pct = (current_val - pos['entry_price']) / pos['entry_price']
                
                if pnl_pct >= config['exit_profit_pct'] or pnl_pct <= -config['stop_loss_pct']:
                    # Condition met at current_row, execute with realistic sniper latency
                    # Fill = 50% of signal price + 50% of next minute's price
                    exit_price_signal = current_val
                    exit_price_next = next_row[price_col]
                    exit_price_actual = (exit_price_signal * 0.50) + (exit_price_next * 0.50)
                    
                    exit_price_slipped = exit_price_actual * (1 - self.slippage)
                    
                    trade_revenue = pos['shares'] * exit_price_slipped
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
                    # Signal at current_row, execute with realistic sniper latency
                    entry_price_signal = current_row[price_col]
                    entry_price_next = next_row[price_col]
                    entry_price_actual = (entry_price_signal * 0.50) + (entry_price_next * 0.50)
                    
                    # Prevent buying at dust prices or near-certainties
                    if 0.05 < entry_price_actual < 0.95:
                        entry_price_slipped = entry_price_actual * (1 + self.slippage)
                        risk_amount = cash * config['pos_size_pct']
                        shares = risk_amount / entry_price_slipped
                        positions.append({
                            'side': decision,
                            'entry_price': entry_price_slipped,
                            'shares': shares,
                            'capital': risk_amount
                        })
                        cash -= risk_amount
                        logger.debug(f"Entry executed at {next_row.name if hasattr(next_row, 'name') else i+1}")

            # 3. Track Equity (using next_row to reflect state AFTER trades)
            unrealized = 0
            for pos in positions:
                price_col = 'yes_price' if pos['side'] == 'YES' else 'no_price'
                unrealized += pos['shares'] * next_row[price_col]
            
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

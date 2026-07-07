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
        from src.utils.strategy_manager import StrategyManager
        manager = StrategyManager()
        
        cash = self.initial_capital
        equity_curve = []
        positions = [] 
        trades_count = 0
        winning_trades = 0
        
        for i in range(len(data) - 1): # Stay one step behind to allow next-bar execution
            current_row = data.iloc[i]
            next_row = data.iloc[i+1] # The bar where we actually execute
            
            # 1. Update existing positions (Exits & Expirations)
            new_positions = []
            for pos in positions:
                price_col = 'yes_price' if pos['side'] == 'YES' else 'no_price'
                current_val = current_row[price_col]
                
                # Simulating spread: selling at the bid price (slipped down)
                curr_bid_price = current_val * (1 - self.slippage)
                
                # Calculate time left in seconds
                elapsed_sec = current_row['timestamp'] - pos['entry_timestamp']
                time_left_sec = (pos['interval_min'] * 60) - elapsed_sec
                
                # Evaluate exit using centralized logic
                exit_eval = manager.evaluate_exit(pos, curr_bid_price, time_left_sec, final_minute_protector=True, config=config)
                
                if exit_eval['action'] == "EXIT_FULL":
                    # Exit price simulation with latency
                    exit_price_signal = current_val
                    exit_price_next = next_row[price_col]
                    exit_price_actual = (exit_price_signal * 0.50) + (exit_price_next * 0.50)
                    exit_price_slipped = exit_price_actual * (1 - self.slippage)
                    
                    trade_revenue = pos['shares'] * exit_price_slipped
                    cash += trade_revenue
                    trades_count += 1
                    initial_cost = pos.get('bet_size', pos['capital']) if not pos['has_scaled_out'] else (pos.get('bet_size', pos['capital']) / 2)
                    if trade_revenue > initial_cost:
                        winning_trades += 1
                        
                elif exit_eval['action'] == "EXIT_HALF":
                    # Scale out 50%
                    exit_price_signal = current_val
                    exit_price_next = next_row[price_col]
                    exit_price_actual = (exit_price_signal * 0.50) + (exit_price_next * 0.50)
                    exit_price_slipped = exit_price_actual * (1 - self.slippage)
                    
                    half_shares = pos['shares'] / 2
                    trade_revenue = half_shares * exit_price_slipped
                    cash += trade_revenue
                    pos['shares'] -= half_shares
                    pos['has_scaled_out'] = True
                    pos['peak_roi'] = exit_eval['peak_roi']
                    
                    # Split initial cost so PnL calculations are correct on full exit or expiry
                    pos['bet_size'] = pos.get('bet_size', pos['capital'])
                    new_positions.append(pos)
                    
                elif time_left_sec <= 0:
                    # FINAL RESOLUTION AT EXPIRATION
                    strike_btc = pos['strike_btc']
                    expiry_btc = current_row['btc_price']
                    
                    win = (pos['side'] == 'YES' and expiry_btc > strike_btc) or (pos['side'] == 'NO' and expiry_btc < strike_btc)
                    final_val = pos['shares'] * 1.0 if win else 0.0
                    
                    cash += final_val
                    trades_count += 1
                    initial_cost = pos.get('bet_size', pos['capital']) if not pos['has_scaled_out'] else (pos.get('bet_size', pos['capital']) / 2)
                    if final_val > initial_cost:
                        winning_trades += 1
                else:
                    pos['peak_roi'] = exit_eval['peak_roi']
                    new_positions.append(pos)
                    
            positions = new_positions
            
            # 2. Strategy Decision (Entry)
            if cash > (self.initial_capital * 0.01) and len(positions) == 0:
                history = data.iloc[max(0, i - 250) : i + 1] # All data available up to and including current_row
                decision = strategy.decide(current_row, history)
                
                if decision in ["YES", "NO"]:
                    price_col = 'yes_price' if decision == 'YES' else 'no_price'
                    entry_price_signal = current_row[price_col]
                    entry_price_next = next_row[price_col]
                    entry_price_actual = (entry_price_signal * 0.50) + (entry_price_next * 0.50)
                    
                    # Prevent buying at dust prices or near-certainties
                    if 0.05 < entry_price_actual < 0.95:
                        entry_price_slipped = entry_price_actual * (1 + self.slippage)
                        risk_amount = cash * config['pos_size_pct']
                        shares = risk_amount / entry_price_slipped
                        
                        # Get true BTC strike price at start of the window
                        window_start = current_row['window_start']
                        window_start_row = data[data['timestamp'] == window_start]
                        strike_btc = window_start_row.iloc[0]['btc_price'] if not window_start_row.empty else current_row['btc_price']
                        
                        positions.append({
                            'side': decision,
                            'entry_price': entry_price_slipped,
                            'shares': shares,
                            'capital': risk_amount,
                            'entry_timestamp': current_row['timestamp'],
                            'interval_min': 15, # 15-minute resolution
                            'strike_btc': strike_btc,
                            'peak_roi': -100.0,
                            'has_scaled_out': False
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

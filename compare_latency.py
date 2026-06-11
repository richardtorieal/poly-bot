import pandas as pd
import yaml
import os
from src.utils.backtest_engine import BacktestEngine
from src.strategies.btc_trend import BTCTrendStrategy

def run_test(latency_model):
    with open("config/strategy_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    df = pd.read_csv("data/btc_truthful_1m_30d.csv")
    engine = BacktestEngine(initial_capital=1000.0, slippage_bps=10)
    strategy = BTCTrendStrategy(
        btc_threshold=0.005, 
        lookback_minutes=15, 
        er_threshold=0.62
    )
    
    # Monkey-patch the engine's execution logic for the comparison
    def run_custom(self, strategy, data, config):
        cash = self.initial_capital
        equity_curve = []
        positions = [] 
        trades_count = 0
        winning_trades = 0
        
        for i in range(len(data) - 1):
            current_row = data.iloc[i]
            next_row = data.iloc[i+1]
            history = data.iloc[:i+1]
            
            new_positions = []
            for pos in positions:
                price_col = 'yes_price' if pos['side'] == 'YES' else 'no_price'
                current_val = current_row[price_col]
                pnl_pct = (current_val - pos['entry_price']) / pos['entry_price']
                
                if pnl_pct >= config['exit_profit_pct'] or pnl_pct <= -config['stop_loss_pct']:
                    if latency_model == "T+1":
                        exit_price_actual = next_row[price_col]
                    else:
                        exit_price_actual = (current_val * 0.5) + (next_row[price_col] * 0.5)
                    
                    exit_price_slipped = exit_price_actual * (1 - self.slippage)
                    trade_revenue = pos['shares'] * exit_price_slipped
                    cash += trade_revenue
                    trades_count += 1
                    if (trade_revenue > pos['capital']): winning_trades += 1
                else:
                    new_positions.append(pos)
            positions = new_positions
            
            if cash > 10:
                decision = strategy.decide(current_row, history)
                if decision in ["YES", "NO"] and len(positions) == 0:
                    price_col = 'yes_price' if decision == 'YES' else 'no_price'
                    if latency_model == "T+1":
                        entry_price_actual = next_row[price_col]
                    else:
                        entry_price_actual = (current_row[price_col] * 0.5) + (next_row[price_col] * 0.5)
                    
                    if 0.05 < entry_price_actual < 0.95:
                        entry_price_slipped = entry_price_actual * (1 + self.slippage)
                        risk_amount = cash * config['pos_size_pct']
                        shares = risk_amount / entry_price_slipped
                        positions.append({'side': decision, 'entry_price': entry_price_slipped, 'shares': shares, 'capital': risk_amount})
                        cash -= risk_amount

            unrealized = sum(pos['shares'] * next_row['yes_price' if pos['side'] == 'YES' else 'no_price'] for pos in positions)
            equity_curve.append(cash + unrealized)
            
        return {"final_balance": equity_curve[-1], "trades": trades_count}

    # Bind the custom runner to the instance
    import types
    engine.run = types.MethodType(run_custom, engine)
    return engine.run(strategy, df, config['strategy']['parameters'])

print("--- Latency Comparison (30-Day Audit) ---")
res_t1 = run_test("T+1")
res_30s = run_test("30S")

pnl_t1 = res_t1['final_balance'] - 1000
pnl_30s = res_30s['final_balance'] - 1000

print(f"T+1 (60s Delay):  PnL: ${pnl_t1:+,.2f} | ROI: {pnl_t1/10:.2f}% | Trades: {res_t1['trades']}")
print(f"30s (50/50 Model): PnL: ${pnl_30s:+,.2f} | ROI: {pnl_30s/10:.2f}% | Trades: {res_30s['trades']}")

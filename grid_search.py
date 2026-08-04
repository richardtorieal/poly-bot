import pandas as pd
import numpy as np
import yaml
import os
from multiprocessing import Pool
from typing import Dict, Any, List

def load_config():
    with open("config/strategy_config.yaml", "r") as f:
        return yaml.safe_load(f)

# Global variables to be shared across processes (read-only)
DF_GLOBAL = None
TIMESTAMP = None
BTC_PRICE = None
YES_PRICE = None
NO_PRICE = None
WINDOW_START = None
STRIKE_PRICE = None
ER_BY_LOOKBACK = {}
CONFIG = None

def init_worker(shared_data):
    global DF_GLOBAL, TIMESTAMP, BTC_PRICE, YES_PRICE, NO_PRICE, WINDOW_START, STRIKE_PRICE, ER_BY_LOOKBACK, CONFIG
    DF_GLOBAL = shared_data['df']
    TIMESTAMP = shared_data['timestamp']
    BTC_PRICE = shared_data['btc_price']
    YES_PRICE = shared_data['yes_price']
    NO_PRICE = shared_data['no_price']
    WINDOW_START = shared_data['window_start']
    STRIKE_PRICE = shared_data['strike_price']
    ER_BY_LOOKBACK = shared_data['er_by_lookback']
    CONFIG = shared_data['config']

def run_backtest_fast(params) -> Dict[str, Any]:
    global TIMESTAMP, BTC_PRICE, YES_PRICE, NO_PRICE, WINDOW_START, STRIKE_PRICE, ER_BY_LOOKBACK, CONFIG
    
    initial_capital = CONFIG['backtest']['initial_capital']
    slippage = CONFIG['backtest']['slippage_bps'] / 10000
    pos_size_pct = CONFIG['strategy']['parameters'].get('pos_size_pct', 0.03)
    
    cash = initial_capital
    equity_curve = []
    
    has_position = False
    pos_side = ""
    pos_entry_price = 0.0
    pos_shares = 0.0
    pos_capital = 0.0
    pos_entry_timestamp = 0
    pos_strike_btc = 0.0
    pos_peak_roi = -100.0
    pos_has_scaled_out = False
    
    trades_count = 0
    winning_trades = 0
    
    stop_loss_roi = -params['stop_loss_pct'] * 100.0
    target_roi = params['exit_profit_pct'] * 100.0
    
    lookback_minutes = params['lookback_minutes']
    er = ER_BY_LOOKBACK[lookback_minutes]
    
    for i in range(len(BTC_PRICE) - 1):
        curr_ts = TIMESTAMP[i]
        curr_btc = BTC_PRICE[i]
        
        # 1. Update existing position
        if has_position:
            price_col_arr = YES_PRICE if pos_side == "YES" else NO_PRICE
            current_val = price_col_arr[i]
            curr_bid_price = current_val * (1 - slippage)
            
            elapsed_sec = curr_ts - pos_entry_timestamp
            time_left_sec = 900.0 - elapsed_sec
            
            running_roi = ((curr_bid_price - pos_entry_price) / pos_entry_price) * 100
            pos_peak_roi = max(pos_peak_roi, running_roi)
            
            exit_action = None
            
            if running_roi <= stop_loss_roi:
                exit_action = "EXIT_FULL"
            elif running_roi >= target_roi:
                exit_action = "EXIT_FULL"
            elif time_left_sec <= 0:
                # Expiration resolution
                win = (pos_side == "YES" and BTC_PRICE[i] > pos_strike_btc) or (pos_side == "NO" and BTC_PRICE[i] < pos_strike_btc)
                final_val = pos_shares * 1.0 if win else 0.0
                cash += final_val
                trades_count += 1
                initial_cost = pos_capital if not pos_has_scaled_out else (pos_capital / 2.0)
                if final_val > initial_cost:
                    winning_trades += 1
                has_position = False
            else:
                # Final minute protector
                if time_left_sec <= 120:
                    if running_roi > 10.0 and running_roi < (pos_peak_roi - 5.0):
                        exit_action = "EXIT_FULL"
                        
            if exit_action == "EXIT_FULL":
                exit_price_signal = current_val
                exit_price_next = price_col_arr[i+1]
                exit_price_actual = (exit_price_signal * 0.50) + (exit_price_next * 0.50)
                exit_price_slipped = exit_price_actual * (1 - slippage)
                
                trade_revenue = pos_shares * exit_price_slipped
                cash += trade_revenue
                trades_count += 1
                initial_cost = pos_capital if not pos_has_scaled_out else (pos_capital / 2.0)
                if trade_revenue > initial_cost:
                    winning_trades += 1
                has_position = False
                
        # 2. Entry signal
        if not has_position and cash > (initial_capital * 0.01):
            ts_int = int(curr_ts)
            win_start = (ts_int // 900) * 900
            elapsed_min = (ts_int - win_start) / 60.0
            
            if elapsed_min <= params['max_minutes_elapsed']:
                if i >= lookback_minutes - 1:
                    if er[i] >= params['er_threshold']:
                        past_price = BTC_PRICE[i - lookback_minutes + 1]
                        change = (curr_btc - past_price) / past_price
                        
                        decision = "HOLD"
                        
                        filter_passed = True
                        if params['filter_strike_trend']:
                            if WINDOW_START[i] >= TIMESTAMP[max(0, i - 80)] and not np.isnan(STRIKE_PRICE[i]):
                                strike_p = STRIKE_PRICE[i]
                                window_change = (curr_btc - strike_p) / strike_p
                                if change > 0 and window_change <= 0:
                                    filter_passed = False
                                elif change < 0 and window_change >= 0:
                                    filter_passed = False
                                    
                        if filter_passed:
                            if change > params['btc_threshold_up']:
                                decision = "YES"
                            elif change < -params['btc_threshold_down']:
                                decision = "NO"
                                
                        if decision in ["YES", "NO"]:
                            price_col_arr = YES_PRICE if decision == "YES" else NO_PRICE
                            entry_price_signal = price_col_arr[i]
                            entry_price_next = price_col_arr[i+1]
                            entry_price_actual = (entry_price_signal * 0.50) + (entry_price_next * 0.50)
                            
                            if 0.05 < entry_price_actual < 0.95:
                                entry_price_slipped = entry_price_actual * (1 + slippage)
                                risk_amount = cash * pos_size_pct
                                
                                has_position = True
                                pos_side = decision
                                pos_entry_price = entry_price_slipped
                                pos_shares = risk_amount / entry_price_slipped
                                pos_capital = risk_amount
                                pos_entry_timestamp = curr_ts
                                offset = int((curr_ts - WINDOW_START[i]) // 60)
                                if i - offset >= 0:
                                    pos_strike_btc = STRIKE_PRICE[i]
                                else:
                                    pos_strike_btc = curr_btc
                                pos_peak_roi = -100.0
                                pos_has_scaled_out = False
                                
                                cash -= risk_amount
                                
        unrealized = 0.0
        if has_position:
            price_col_arr = YES_PRICE if pos_side == "YES" else NO_PRICE
            unrealized = pos_shares * price_col_arr[i+1]
        equity_curve.append(cash + unrealized)
        
    final_equity = equity_curve[-1]
    equity_series = pd.Series(equity_curve)
    returns = equity_series.pct_change().fillna(0)
    
    std_returns = returns.std()
    sharpe = (returns.mean() / std_returns * np.sqrt(252 * 1440)) if std_returns != 0 else 0.0
    
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max
    max_dd = drawdown.min()
    
    return {
        'params': params,
        'is_sharpe': sharpe,
        'is_pnl': ((final_equity - initial_capital) / initial_capital) * 100,
        'is_trades': trades_count,
        'is_win_rate': (winning_trades / trades_count * 100) if trades_count > 0 else 0.0,
        'is_max_dd': max_dd
    }

def main():
    print("Initializing optimized grid search...")
    config = load_config()
    
    # Load dataset
    df = pd.read_csv("data/btc_truthful_1m_30d.csv")
    df['yes_price'] = df['yes_price'].ffill()
    df['no_price'] = df['no_price'].ffill()
    
    split_idx = int(len(df) * config['backtest']['is_oos_split'])
    df_is = df.iloc[:split_idx]
    
    timestamp = df_is['timestamp'].to_numpy()
    btc_price = df_is['btc_price'].to_numpy()
    yes_price = df_is['yes_price'].to_numpy()
    no_price = df_is['no_price'].to_numpy()
    window_start = df_is['window_start'].to_numpy()
    
    # Precompute strike_price (mapping timestamp to btc_price)
    ts_to_btc = {t: p for t, p in zip(timestamp, btc_price)}
    strike_price = np.array([ts_to_btc.get(ws, np.nan) for ws in window_start])
    
    # Precompute ER for lookbacks 2, 3, 4, 5
    er_by_lookback = {}
    diffs = np.abs(np.diff(btc_price))
    diffs = np.concatenate([[0.0], diffs])
    for n in [2, 3, 4, 5]:
        er = np.zeros_like(btc_price)
        for i in range(len(btc_price)):
            start_idx = max(0, i - n + 1)
            change = abs(btc_price[i] - btc_price[start_idx])
            vol = np.sum(diffs[start_idx + 1 : i + 1])
            er[i] = change / vol if vol > 0 else 0.0
        er_by_lookback[n] = er
        
    shared_data = {
        'df': df_is,
        'timestamp': timestamp,
        'btc_price': btc_price,
        'yes_price': yes_price,
        'no_price': no_price,
        'window_start': window_start,
        'strike_price': strike_price,
        'er_by_lookback': er_by_lookback,
        'config': config
    }
    
    # Generate 5,000 random parameter combinations satisfying all constraints
    num_samples = 5000
    np.random.seed(42)
    
    grid_params = []
    for _ in range(num_samples):
        # 1. Near-symmetry constraint: up/down within 10%
        up = np.random.uniform(0.00005, 0.00025)
        down = np.random.uniform(0.91 * up, 1.09 * up)
        
        # er_threshold >= 0.50
        er = np.random.uniform(0.50, 0.95)
        # exit_profit_pct >= 0.01 (1.0%)
        exit_profit = np.random.uniform(0.010, 0.025)
        # stop_loss_pct >= 0.015 (1.5%)
        stop_loss = np.random.uniform(0.015, 0.035)
        
        max_elapsed = np.random.uniform(5.0, 14.5)
        lookback = int(np.random.choice([2, 3, 4, 5]))
        
        grid_params.append({
            'btc_threshold_up': float(up),
            'btc_threshold_down': float(down),
            'er_threshold': float(er),
            'exit_profit_pct': float(exit_profit),
            'stop_loss_pct': float(stop_loss),
            'max_minutes_elapsed': float(max_elapsed),
            'lookback_minutes': lookback,
            'filter_strike_trend': True
        })
        
    # Always include baseline
    baseline_params = config['strategy']['parameters']
    grid_params.append({
        'btc_threshold_up': baseline_params['btc_threshold_up'],
        'btc_threshold_down': baseline_params['btc_threshold_down'],
        'er_threshold': baseline_params['er_threshold'],
        'exit_profit_pct': baseline_params['exit_profit_pct'],
        'stop_loss_pct': baseline_params['stop_loss_pct'],
        'max_minutes_elapsed': baseline_params['max_minutes_elapsed'],
        'lookback_minutes': baseline_params['lookback_minutes'],
        'filter_strike_trend': baseline_params['filter_strike_trend']
    })
    
    print(f"Running grid search with {len(grid_params)} combinations using 6 parallel workers...")
    
    with Pool(6, initializer=init_worker, initargs=(shared_data,)) as p:
        results = p.map(run_backtest_fast, grid_params)
        
    # Filter by constraints (already verified in generation, but double check)
    valid_results = []
    for r in results:
        params = r['params']
        up = params['btc_threshold_up']
        down = params['btc_threshold_down']
        ratio1 = up / down
        ratio2 = down / up
        if ratio1 > 1.10 or ratio2 > 1.10: continue
        if up < 0.00005 or down < 0.00005: continue
        if params['er_threshold'] < 0.50: continue
        if params['exit_profit_pct'] < 0.01: continue
        if params['stop_loss_pct'] < 0.015: continue
        valid_results.append(r)
        
    # Sort strictly by IS Sharpe
    valid_results.sort(key=lambda x: x['is_sharpe'], reverse=True)
    
    print("\n=== TOP 25 SEARCH RESULTS SORTED BY IS SHARPE ===")
    for i, r in enumerate(valid_results[:25]):
        is_baseline = (abs(r['params']['btc_threshold_up'] - baseline_params['btc_threshold_up']) < 1e-12 and 
                       abs(r['params']['btc_threshold_down'] - baseline_params['btc_threshold_down']) < 1e-12 and
                       abs(r['params']['er_threshold'] - baseline_params['er_threshold']) < 1e-12)
        prefix = "[BASELINE] " if is_baseline else ""
        print(f"Rank {i+1}: {prefix}")
        print(f"  IS Sharpe: {r['is_sharpe']:.4f} | IS PnL: {r['is_pnl']:.2f}% | IS Trades: {r['is_trades']} | IS Win Rate: {r['is_win_rate']:.2f}% | IS MaxDD: {r['is_max_dd']*100:.2f}%")
        print("  Params:")
        for k, v in r['params'].items():
            print(f"    {k}: {v}")
        print("-" * 50)
        
if __name__ == "__main__":
    main()

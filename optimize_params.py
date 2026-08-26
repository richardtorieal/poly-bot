import pandas as pd
import yaml
import os
import copy
from multiprocessing import Pool
from src.utils.backtest_engine import BacktestEngine
from src.strategies.btc_trend import BTCTrendStrategy

def load_config():
    with open("config/strategy_config.yaml", "r") as f:
        return yaml.safe_load(f)

def generate_volatility_candidates(base_params):
    candidates = []
    
    # 1. Candidate with volatility_adapt = False
    p_false = copy.deepcopy(base_params)
    p_false['volatility_adapt'] = False
    candidates.append(p_false)
    
    # 2. Candidates with volatility_adapt = True
    vol_base_vals = [0.0003, 0.0004, 0.0005, 0.0006, 0.000655, 0.0007, 0.0008, 0.001]
    vol_min_vals = [0.2, 0.3, 0.4, 0.5, 0.6]
    vol_max_vals = [1.2, 1.5, 1.8, 2.0, 2.2, 2.5]
    
    for vb in vol_base_vals:
        for vmin in vol_min_vals:
            for vmax in vol_max_vals:
                if vmin >= vmax:
                    continue
                p = copy.deepcopy(base_params)
                p['volatility_adapt'] = True
                p['volatility_base'] = vb
                p['vol_mult_min'] = vmin
                p['vol_mult_max'] = vmax
                candidates.append(p)
                
    # Remove duplicates
    seen = set()
    unique_candidates = []
    for c in candidates:
        k = (c['volatility_adapt'], c.get('volatility_base'), c.get('vol_mult_min'), c.get('vol_mult_max'))
        if k not in seen:
            seen.add(k)
            unique_candidates.append(c)
            
    return unique_candidates

df_is = None
initial_capital = None
slippage_bps = None

def init_worker(df_is_shared, cap, slip):
    global df_is, initial_capital, slippage_bps
    df_is = df_is_shared
    initial_capital = cap
    slippage_bps = slip

def evaluate_params(params):
    try:
        strategy = BTCTrendStrategy(
            btc_threshold=params['btc_threshold'],
            btc_threshold_up=params.get('btc_threshold_up'),
            btc_threshold_down=params.get('btc_threshold_down'),
            lookback_minutes=params['lookback_minutes'],
            er_threshold=params.get('er_threshold', 0.5),
            max_minutes_elapsed=params.get('max_minutes_elapsed', 999.0),
            filter_strike_trend=params.get('filter_strike_trend', True),
            volatility_adapt=params.get('volatility_adapt', False),
            er_lookback=params.get('er_lookback'),
            use_ema_filter=params.get('use_ema_filter', False),
            ema_span=params.get('ema_span', 30),
            volatility_base=params.get('volatility_base', 0.000655),
            vol_mult_min=params.get('vol_mult_min', 0.5),
            vol_mult_max=params.get('vol_mult_max', 2.0)
        )
        engine = BacktestEngine(initial_capital=initial_capital, slippage_bps=slippage_bps)
        res = engine.run(strategy, df_is, params)
        return params, res['sharpe_ratio']
    except Exception as e:
        return params, -1

def run_optimization():
    config = load_config()
    data_path = "data/btc_truthful_1m_30d.csv"
    
    if not os.path.exists(data_path):
        print("Data file missing.", flush=True)
        return

    df = pd.read_csv(data_path)
    df['yes_price'] = df['yes_price'].ffill()
    df['no_price'] = df['no_price'].ffill()
    
    split_idx = int(len(df) * config['backtest']['is_oos_split'])
    df_is_local = df.iloc[:split_idx]
    
    current_params = config['strategy']['parameters']
    
    # Pre-evaluate current baseline
    engine = BacktestEngine(
        initial_capital=config['backtest']['initial_capital'],
        slippage_bps=config['backtest']['slippage_bps']
    )
    strategy = BTCTrendStrategy(
        btc_threshold=current_params['btc_threshold'],
        btc_threshold_up=current_params.get('btc_threshold_up'),
        btc_threshold_down=current_params.get('btc_threshold_down'),
        lookback_minutes=current_params['lookback_minutes'],
        er_threshold=current_params.get('er_threshold', 0.5),
        max_minutes_elapsed=current_params.get('max_minutes_elapsed', 999.0),
        filter_strike_trend=current_params.get('filter_strike_trend', True),
        volatility_adapt=current_params.get('volatility_adapt', False),
        er_lookback=current_params.get('er_lookback'),
        use_ema_filter=current_params.get('use_ema_filter', False),
        ema_span=current_params.get('ema_span', 30),
        volatility_base=current_params.get('volatility_base', 0.000655),
        vol_mult_min=current_params.get('vol_mult_min', 0.5),
        vol_mult_max=current_params.get('vol_mult_max', 2.0)
    )
    is_results = engine.run(strategy, df_is_local, current_params)
    best_sharpe = is_results['sharpe_ratio']
    best_params = copy.deepcopy(current_params)
    
    print(f"Initial IS Sharpe: {best_sharpe:.4f}", flush=True)
    
    candidates = generate_volatility_candidates(best_params)
    print(f"Generated {len(candidates)} volatility candidates. Evaluating in parallel...", flush=True)
    
    with Pool(initializer=init_worker, initargs=(df_is_local, config['backtest']['initial_capital'], config['backtest']['slippage_bps'])) as pool:
        results = pool.map(evaluate_params, candidates)
        
    improved = False
    for params, sharpe in results:
        if sharpe > best_sharpe:
            print(f"Found improvement: Sharpe {sharpe:.4f} (was {best_sharpe:.4f})", flush=True)
            best_sharpe = sharpe
            best_params = params
            improved = True
            
    if improved:
        print("\nNew Best Parameters Found:", flush=True)
        print(best_params, flush=True)
        print(f"Best IS Sharpe: {best_sharpe:.4f}", flush=True)
        
        # Save the best parameters back to yaml to test with validate_loop.py
        config['strategy']['parameters'] = best_params
        with open("config/strategy_config.yaml", "w") as f:
            yaml.safe_dump(config, f)
        print("Updated config/strategy_config.yaml with best parameters.", flush=True)
    else:
        print("No improvement found. Kept original parameters.", flush=True)

if __name__ == "__main__":
    run_optimization()

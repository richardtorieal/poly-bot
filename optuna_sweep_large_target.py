import pandas as pd
import numpy as np
import yaml
import os
import optuna
import time
from multiprocessing import Process
from typing import Dict, Any
from src.utils.backtest_engine import BacktestEngine
from src.strategies.btc_trend import BTCTrendStrategy
from src.utils.logger import logger

optuna.logging.set_verbosity(optuna.logging.WARNING)

DATA_PATH = "data/btc_truthful_1m_30d.csv"
if os.path.exists(DATA_PATH):
    DF_GLOBAL = pd.read_csv(DATA_PATH)
    DF_GLOBAL['yes_price'] = DF_GLOBAL['yes_price'].ffill()
    DF_GLOBAL['no_price'] = DF_GLOBAL['no_price'].ffill()
else:
    DF_GLOBAL = None

def load_config():
    with open("config/strategy_config.yaml", "r") as f:
        return yaml.safe_load(f)

def objective(trial):
    config = load_config()
    
    lookback_minutes = 2
    btc_threshold = trial.suggest_float('btc_threshold', 0.000080, 0.000130)
    
    btc_threshold_up = trial.suggest_float('btc_threshold_up', max(0.00005, 0.93 * btc_threshold), 1.07 * btc_threshold)
    low_down = max(0.00005, 0.93 * btc_threshold_up)
    high_down = 1.07 * btc_threshold_up
    btc_threshold_down = trial.suggest_float('btc_threshold_down', low_down, high_down)
    
    er_threshold = trial.suggest_float('er_threshold', 0.50, 0.65)
    
    # Larger profit targets
    exit_profit_pct = trial.suggest_float('exit_profit_pct', 0.015, 0.025)
    stop_loss_pct = trial.suggest_float('stop_loss_pct', 0.040, 0.070)
    
    max_minutes_elapsed = trial.suggest_float('max_minutes_elapsed', 10.0, 11.5)
    
    # Trailing stop
    trailing_stop_activation_pct = trial.suggest_float('trailing_stop_activation_pct', 0.003, exit_profit_pct)
    trailing_stop_drop_pct = trial.suggest_float('trailing_stop_drop_pct', 0.001, trailing_stop_activation_pct)
    
    pos_size_pct = 0.03
    
    params = {
        'btc_threshold': btc_threshold,
        'btc_threshold_up': btc_threshold_up,
        'btc_threshold_down': btc_threshold_down,
        'lookback_minutes': lookback_minutes,
        'er_threshold': er_threshold,
        'pos_size_pct': pos_size_pct,
        'exit_profit_pct': exit_profit_pct,
        'stop_loss_pct': stop_loss_pct,
        'max_minutes_elapsed': max_minutes_elapsed,
        'filter_strike_trend': True,
        'trailing_stop_activation_pct': trailing_stop_activation_pct,
        'trailing_stop_drop_pct': trailing_stop_drop_pct
    }
    
    split_idx = int(len(DF_GLOBAL) * config['backtest']['is_oos_split'])
    df_is = DF_GLOBAL.iloc[:split_idx]
    df_oos = DF_GLOBAL.iloc[split_idx:]
    
    engine = BacktestEngine(
        initial_capital=config['backtest']['initial_capital'],
        slippage_bps=config['backtest']['slippage_bps']
    )
    
    strategy = BTCTrendStrategy(
        btc_threshold=btc_threshold,
        btc_threshold_up=btc_threshold_up,
        btc_threshold_down=btc_threshold_down,
        lookback_minutes=lookback_minutes,
        er_threshold=er_threshold,
        max_minutes_elapsed=max_minutes_elapsed,
        filter_strike_trend=True
    )
    
    is_results = engine.run(strategy, df_is, params)
    is_sharpe = is_results['sharpe_ratio']
    
    oos_results = engine.run(strategy, df_oos, params)
    oos_sharpe = oos_results['sharpe_ratio']
    oos_max_dd = oos_results['max_drawdown']
    
    trial.set_user_attr('oos_sharpe', oos_sharpe)
    trial.set_user_attr('oos_max_dd', oos_max_dd)
    trial.set_user_attr('is_sharpe', is_sharpe)
    trial.set_user_attr('is_pnl', is_results['total_pnl_pct'])
    trial.set_user_attr('oos_pnl', oos_results['total_pnl_pct'])
    trial.set_user_attr('oos_trades', oos_results['total_trades'])
    trial.set_user_attr('is_trades', is_results['total_trades'])
    
    return is_sharpe

def run_worker(study_name, storage, n_trials):
    study = optuna.load_study(study_name=study_name, storage=storage)
    time.sleep(np.random.rand() * 2)
    study.optimize(objective, n_trials=n_trials)

def main():
    logger.info("Initializing Optuna sweep with larger profit targets...")
    study_name = "btc_trend_opt_large"
    storage_url = "sqlite:///optuna_study_large.db"
    
    if os.path.exists("optuna_study_large.db"):
        try:
            os.remove("optuna_study_large.db")
        except Exception as e:
            logger.warning(f"Could not remove old DB: {e}")
            
    study = optuna.create_study(
        study_name=study_name,
        storage=storage_url,
        direction="maximize"
    )
    
    # Enqueue baseline parameters (functionally disabled custom trailing stop by setting activation high)
    baseline_params = {
        'btc_threshold': 0.00008934,
        'btc_threshold_up': 0.00009212,
        'btc_threshold_down': 0.00009377,
        'er_threshold': 0.5485,
        'exit_profit_pct': 0.015,  # Slightly modified baseline with larger target
        'stop_loss_pct': 0.05067,
        'max_minutes_elapsed': 10.85,
        'trailing_stop_activation_pct': 0.015,
        'trailing_stop_drop_pct': 0.015
    }
    study.enqueue_trial(baseline_params)
    study.optimize(objective, n_trials=1)
    
    num_workers = 6
    trials_per_worker = 20
    
    processes = []
    for i in range(num_workers):
        p = Process(target=run_worker, args=(study_name, storage_url, trials_per_worker))
        p.start()
        processes.append(p)
        
    for p in processes:
        p.join()
        
    logger.info("All workers finished. Analyzing trials...")
    
    study = optuna.load_study(study_name=study_name, storage=storage_url)
    trials = study.trials
    valid_trials = []
    
    for t in trials:
        if t.state != optuna.trial.TrialState.COMPLETE:
            continue
        
        oos_max_dd = t.user_attrs.get('oos_max_dd', -1.0)
        if oos_max_dd > -0.30:
            valid_trials.append(t)
            
    valid_trials.sort(key=lambda x: x.user_attrs.get('oos_sharpe', 0.0), reverse=True)
    
    print("\n=== TOP 5 TRIALS SORTED BY OOS SHARPE (Drawdown > -30%) ===")
    for i, t in enumerate(valid_trials[:5]):
        print(f"Rank {i+1}: Trial {t.number}")
        print(f"  IS Sharpe: {t.user_attrs.get('is_sharpe'):.4f} | OOS Sharpe: {t.user_attrs.get('oos_sharpe'):.4f} | OOS MaxDD: {t.user_attrs.get('oos_max_dd')*100:.2f}%")
        print("  Params:")
        for k, v in t.params.items():
            print(f"    {k}: {v}")
        print("-" * 50)

if __name__ == "__main__":
    main()

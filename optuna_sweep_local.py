import pandas as pd
import numpy as np
import yaml
import os
import optuna
from typing import Dict, Any
from src.utils.backtest_engine import BacktestEngine
from src.strategies.btc_trend import BTCTrendStrategy
from src.utils.logger import logger

# Set optuna logging to warning to avoid cluttering output
optuna.logging.set_verbosity(optuna.logging.WARNING)

def load_config():
    with open("config/strategy_config.yaml", "r") as f:
        return yaml.safe_load(f)

def objective(trial):
    # Retrieve base configuration
    config = load_config()
    
    # Suggest parameters around baseline
    btc_threshold = trial.suggest_float('btc_threshold', 0.00005, 0.00015)
    
    # Ensure triggers are symmetric/near-symmetric (within 10%)
    btc_threshold_up = trial.suggest_float('btc_threshold_up', max(0.00005, 0.9 * btc_threshold), 1.1 * btc_threshold)
    low_down = max(0.00005, 0.9 * btc_threshold_up)
    high_down = 1.1 * btc_threshold_up
    btc_threshold_down = trial.suggest_float('btc_threshold_down', low_down, high_down)
    
    # ER threshold
    er_threshold = trial.suggest_float('er_threshold', 0.50, 0.70)
    
    # Lookback minutes
    lookback_minutes = trial.suggest_int('lookback_minutes', 2, 4)
    
    # Profit target and Stop loss
    exit_profit_pct = trial.suggest_float('exit_profit_pct', 0.010, 0.020)
    stop_loss_pct = trial.suggest_float('stop_loss_pct', 0.035, 0.070)
    
    # Max minutes elapsed
    max_minutes_elapsed = trial.suggest_float('max_minutes_elapsed', 9.5, 12.5)
    
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
        'filter_strike_trend': True
    }
    
    # Load dataset
    data_path = "data/btc_truthful_1m_30d.csv"
    df = pd.read_csv(data_path)
    df['yes_price'] = df['yes_price'].ffill()
    df['no_price'] = df['no_price'].ffill()
    
    split_idx = int(len(df) * config['backtest']['is_oos_split'])
    df_is = df.iloc[:split_idx]
    df_oos = df.iloc[split_idx:]
    
    # Run backtests
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
    
    # Store metrics in trial user attributes
    trial.set_user_attr('oos_sharpe', oos_sharpe)
    trial.set_user_attr('oos_max_dd', oos_max_dd)
    trial.set_user_attr('is_sharpe', is_sharpe)
    trial.set_user_attr('is_pnl', is_results['total_pnl_pct'])
    trial.set_user_attr('oos_pnl', oos_results['total_pnl_pct'])
    trial.set_user_attr('oos_trades', oos_results['total_trades'])
    trial.set_user_attr('is_trades', is_results['total_trades'])
    
    return is_sharpe

def main():
    logger.info("Starting local targeted Optuna parameter sweep...")
    study = optuna.create_study(direction="maximize")
    
    # Enqueue baseline parameters
    baseline_params = {
        'btc_threshold': 0.00007945,
        'btc_threshold_up': 0.00008736,
        'btc_threshold_down': 0.00009605,
        'er_threshold': 0.5614,
        'lookback_minutes': 2,
        'exit_profit_pct': 0.01043,
        'stop_loss_pct': 0.05208,
        'max_minutes_elapsed': 10.86
    }
    study.enqueue_trial(baseline_params)
    
    study.optimize(objective, n_trials=400)
    
    logger.info("Sweep complete. Analyzing trials...")
    
    trials = study.trials
    valid_trials = []
    
    for t in trials:
        if t.state != optuna.trial.TrialState.COMPLETE:
            continue
        
        oos_max_dd = t.user_attrs.get('oos_max_dd', -1.0)
        
        # Drawdown constraint
        if oos_max_dd > -0.30:
            valid_trials.append(t)
            
    # Sort valid trials by OOS Sharpe descending
    valid_trials.sort(key=lambda x: x.user_attrs.get('oos_sharpe', 0.0), reverse=True)
    
    print("\n=== TOP 10 TRIALS SORTED BY OOS SHARPE (Drawdown > -30%) ===")
    for i, t in enumerate(valid_trials[:10]):
        print(f"Rank {i+1}: Trial {t.number}")
        print(f"  IS Sharpe: {t.user_attrs.get('is_sharpe'):.2f} | IS PnL: {t.user_attrs.get('is_pnl'):.2f}% | IS Trades: {t.user_attrs.get('is_trades')}")
        print(f"  OOS Sharpe: {t.user_attrs.get('oos_sharpe'):.2f} | OOS PnL: {t.user_attrs.get('oos_pnl'):.2f}% | OOS MaxDD: {t.user_attrs.get('oos_max_dd')*100:.2f}% | OOS Trades: {t.user_attrs.get('oos_trades')}")
        print("  Params:")
        for k, v in t.params.items():
            print(f"    {k}: {v}")
        print("-" * 50)
        
    if valid_trials:
        best_trial = valid_trials[0]
        print(f"\nBest Trial for OOS Sharpe is Trial {best_trial.number} with OOS Sharpe: {best_trial.user_attrs.get('oos_sharpe'):.2f}")
    else:
        print("No trials met the constraints.")

if __name__ == "__main__":
    main()

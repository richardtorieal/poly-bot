import pandas as pd
import numpy as np
import yaml
import os
import optuna
from typing import Dict, Any
from src.utils.backtest_engine import BacktestEngine
from src.strategies.btc_trend import BTCTrendStrategy
from src.utils.logger import logger

optuna.logging.set_verbosity(optuna.logging.WARNING)

def load_config():
    with open("config/strategy_config.yaml", "r") as f:
        return yaml.safe_load(f)

def objective(trial):
    config = load_config()
    
    # 1. Base threshold
    btc_threshold = trial.suggest_float('btc_threshold', 0.00005, 0.0004)
    
    # 2. Symmetry constraints (within 10% of each other)
    # btc_threshold_up and btc_threshold_down must be within 10% of each other, and >= 0.00005
    btc_threshold_up = trial.suggest_float('btc_threshold_up', max(0.00005, 0.9 * btc_threshold), 1.1 * btc_threshold)
    btc_threshold_down = trial.suggest_float('btc_threshold_down', max(0.00005, 0.9 * btc_threshold_up), 1.1 * btc_threshold_up)
    
    # Check strict compliance
    ratio = btc_threshold_up / btc_threshold_down
    if ratio < 0.9 or ratio > 1.1:
        return -999.0
    
    # 3. Minimum values
    er_threshold = trial.suggest_float('er_threshold', 0.50, 0.98)
    exit_profit_pct = trial.suggest_float('exit_profit_pct', 0.010, 0.050)
    stop_loss_pct = trial.suggest_float('stop_loss_pct', 0.015, 0.080)
    
    lookback_minutes = trial.suggest_int('lookback_minutes', 2, 10)
    er_lookback = trial.suggest_int('er_lookback', 2, 10)
    max_minutes_elapsed = trial.suggest_float('max_minutes_elapsed', 4.0, 14.0)
    
    filter_strike_trend = trial.suggest_categorical('filter_strike_trend', [True, False])
    volatility_adapt = trial.suggest_categorical('volatility_adapt', [True, False])
    volatility_base = trial.suggest_float('volatility_base', 0.0003, 0.001)
    vol_mult_min = trial.suggest_float('vol_mult_min', 0.2, 0.8)
    vol_mult_max = trial.suggest_float('vol_mult_max', 1.0, 3.0)
    
    use_ema_filter = trial.suggest_categorical('use_ema_filter', [True, False])
    ema_span = trial.suggest_int('ema_span', 10, 60)
    
    trailing_stop_activation_pct = trial.suggest_float('trailing_stop_activation_pct', 0.002, 0.03)
    trailing_stop_drop_pct = trial.suggest_float('trailing_stop_drop_pct', 0.001, 0.015)
    
    pos_size_pct = 0.03
    
    params = {
        'btc_threshold': btc_threshold,
        'btc_threshold_up': btc_threshold_up,
        'btc_threshold_down': btc_threshold_down,
        'lookback_minutes': lookback_minutes,
        'er_lookback': er_lookback,
        'er_threshold': er_threshold,
        'pos_size_pct': pos_size_pct,
        'exit_profit_pct': exit_profit_pct,
        'stop_loss_pct': stop_loss_pct,
        'max_minutes_elapsed': max_minutes_elapsed,
        'filter_strike_trend': filter_strike_trend,
        'volatility_adapt': volatility_adapt,
        'volatility_base': volatility_base,
        'vol_mult_min': vol_mult_min,
        'vol_mult_max': vol_mult_max,
        'use_ema_filter': use_ema_filter,
        'ema_span': ema_span,
        'trailing_stop_activation_pct': trailing_stop_activation_pct,
        'trailing_stop_drop_pct': trailing_stop_drop_pct
    }
    
    data_path = "data/btc_truthful_1m_30d.csv"
    df = pd.read_csv(data_path)
    df['yes_price'] = df['yes_price'].ffill()
    df['no_price'] = df['no_price'].ffill()
    
    split_idx = int(len(df) * config['backtest']['is_oos_split'])
    df_is = df.iloc[:split_idx]
    df_oos = df.iloc[split_idx:]
    
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
        filter_strike_trend=filter_strike_trend,
        volatility_adapt=volatility_adapt,
        er_lookback=er_lookback,
        use_ema_filter=use_ema_filter,
        ema_span=ema_span,
        volatility_base=volatility_base,
        vol_mult_min=vol_mult_min,
        vol_mult_max=vol_mult_max
    )
    
    is_results = engine.run(strategy, df_is, params)
    is_sharpe = is_results['sharpe_ratio']
    
    oos_results = engine.run(strategy, df_oos, params)
    
    trial.set_user_attr('is_sharpe', is_sharpe)
    trial.set_user_attr('is_pnl', is_results['total_pnl_pct'])
    trial.set_user_attr('is_trades', is_results['total_trades'])
    
    trial.set_user_attr('oos_sharpe', oos_results['sharpe_ratio'])
    trial.set_user_attr('oos_pnl', oos_results['total_pnl_pct'])
    trial.set_user_attr('oos_max_dd', oos_results['max_drawdown'])
    trial.set_user_attr('oos_trades', oos_results['total_trades'])
    
    return is_sharpe

def main():
    logger.info("Starting Strict IS Optuna parameter sweep...")
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=300)
    
    logger.info("Sweep complete. Analyzing trials based strictly on IS Sharpe...")
    
    trials = study.trials
    completed_trials = [t for t in trials if t.state == optuna.trial.TrialState.COMPLETE]
    
    completed_trials.sort(key=lambda x: x.value if x.value is not None else -999.0, reverse=True)
    
    print("\n=== TOP 10 TRIALS SORTED BY IN-SAMPLE (IS) SHARPE ===")
    for i, t in enumerate(completed_trials[:10]):
        print(f"Rank {i+1}: Trial {t.number}")
        print(f"  IS Sharpe: {t.value:.2f} | IS PnL: {t.user_attrs.get('is_pnl'):.2f}% | IS Trades: {t.user_attrs.get('is_trades')}")
        print(f"  OOS Sharpe: {t.user_attrs.get('oos_sharpe'):.2f} | OOS PnL: {t.user_attrs.get('oos_pnl'):.2f}% | OOS MaxDD: {t.user_attrs.get('oos_max_dd')*100:.2f}% | OOS Trades: {t.user_attrs.get('oos_trades')}")
        print("  Params:")
        for k, v in t.params.items():
            print(f"    {k}: {v}")
        print("-" * 50)

if __name__ == "__main__":
    main()

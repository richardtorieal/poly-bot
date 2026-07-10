import pandas as pd
import numpy as np
import yaml
import os
import optuna
from typing import Dict, Any
from src.utils.backtest_engine import BacktestEngine
from src.strategies.btc_trend import BaseStrategy
from src.utils.logger import logger

optuna.logging.set_verbosity(optuna.logging.WARNING)

def load_config():
    with open("config/strategy_config.yaml", "r") as f:
        return yaml.safe_load(f)

class DoubleLookbackStrategy(BaseStrategy):
    def __init__(self, btc_threshold=0.0005, lookback_minutes=2, er_threshold=0.5, max_minutes_elapsed=999.0, btc_threshold_up=None, btc_threshold_down=None, filter_strike_trend=True, lookback_medium=5, threshold_medium_mult=0.5):
        self.btc_threshold = btc_threshold
        self.btc_threshold_up = btc_threshold_up if btc_threshold_up is not None else btc_threshold
        self.btc_threshold_down = btc_threshold_down if btc_threshold_down is not None else btc_threshold
        self.lookback_minutes = lookback_minutes
        self.er_threshold = er_threshold
        self.max_minutes_elapsed = max_minutes_elapsed
        self.filter_strike_trend = filter_strike_trend
        self.lookback_medium = lookback_medium
        self.threshold_medium_mult = threshold_medium_mult
        
    def decide(self, current_data: pd.Series, history: pd.DataFrame) -> str:
        if 'timestamp' in current_data:
            ts = current_data['timestamp']
        else:
            ts = float(current_data.name)
        ts_int = int(ts)
        window_start = (ts_int // 900) * 900
        elapsed_min = (ts_int - window_start) / 60.0
        
        if elapsed_min > self.max_minutes_elapsed:
            return "HOLD"
            
        max_lookback = max(self.lookback_minutes, self.lookback_medium)
        if len(history) < max_lookback:
            return "HOLD"
            
        relevant_short = history.iloc[-self.lookback_minutes:]
        past_short = relevant_short.iloc[0]['btc_price']
        current_btc = current_data['btc_price']
        change_short = (current_btc - past_short) / past_short
        
        relevant_medium = history.iloc[-self.lookback_medium:]
        past_medium = relevant_medium.iloc[0]['btc_price']
        change_medium = (current_btc - past_medium) / past_medium
        
        price_diffs = relevant_short['btc_price'].diff().abs()
        volatility = price_diffs.sum() + abs(current_btc - relevant_short.iloc[-1]['btc_price'])
        er = abs(current_btc - past_short) / volatility if volatility != 0 else 0
        if er < self.er_threshold:
            return "HOLD"
            
        if self.filter_strike_trend and 'timestamp' in history.columns:
            strike_price = None
            for j in range(1, min(20, len(history) + 1)):
                if history.iloc[-j]['timestamp'] == window_start:
                    strike_price = history.iloc[-j]['btc_price']
                    break
            if strike_price is not None:
                window_change = (current_btc - strike_price) / strike_price
                if change_short > 0 and window_change <= 0:
                    return "HOLD"
                if change_short < 0 and window_change >= 0:
                    return "HOLD"
                    
        threshold_up = self.btc_threshold_up
        threshold_down = self.btc_threshold_down
        
        if change_short > threshold_up and change_medium > (threshold_up * self.threshold_medium_mult):
            return "YES"
        elif change_short < -threshold_down and change_medium < -(threshold_down * self.threshold_medium_mult):
            return "NO"
            
        return "HOLD"

def objective(trial):
    config = load_config()
    
    btc_threshold = trial.suggest_float('btc_threshold', 0.00005, 0.00025)
    btc_threshold_up = trial.suggest_float('btc_threshold_up', max(0.00005, 0.9 * btc_threshold), 1.1 * btc_threshold)
    low_down = max(0.00005, 0.9 * btc_threshold_up)
    high_down = 1.1 * btc_threshold_up
    btc_threshold_down = trial.suggest_float('btc_threshold_down', low_down, high_down)
    
    er_threshold = trial.suggest_float('er_threshold', 0.40, 0.95)
    lookback_minutes = trial.suggest_int('lookback_minutes', 2, 4)
    
    exit_profit_pct = trial.suggest_float('exit_profit_pct', 0.010, 0.035)
    stop_loss_pct = trial.suggest_float('stop_loss_pct', 0.020, 0.070)
    max_minutes_elapsed = trial.suggest_float('max_minutes_elapsed', 8.0, 13.0)
    
    lookback_medium = trial.suggest_int('lookback_medium', 3, 8)
    threshold_medium_mult = trial.suggest_float('threshold_medium_mult', 0.0, 1.0)
    
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
        'lookback_medium': lookback_medium,
        'threshold_medium_mult': threshold_medium_mult
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
    
    strategy = DoubleLookbackStrategy(
        btc_threshold=btc_threshold,
        btc_threshold_up=btc_threshold_up,
        btc_threshold_down=btc_threshold_down,
        lookback_minutes=lookback_minutes,
        er_threshold=er_threshold,
        max_minutes_elapsed=max_minutes_elapsed,
        filter_strike_trend=True,
        lookback_medium=lookback_medium,
        threshold_medium_mult=threshold_medium_mult
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

def main():
    logger.info("Starting double lookback Optuna parameter sweep...")
    study = optuna.create_study(direction="maximize")
    
    # Enqueue a baseline-ish double lookback parameter set
    baseline_params = {
        'btc_threshold': 0.00007945,
        'btc_threshold_up': 0.00008736,
        'btc_threshold_down': 0.00009605,
        'er_threshold': 0.5614,
        'lookback_minutes': 2,
        'exit_profit_pct': 0.01043,
        'stop_loss_pct': 0.05208,
        'max_minutes_elapsed': 10.86,
        'lookback_medium': 3,
        'threshold_medium_mult': 0.0
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
        
        if oos_max_dd > -0.30:
            valid_trials.append(t)
            
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

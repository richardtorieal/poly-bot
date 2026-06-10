import pandas as pd
import yaml
import os
from src.utils.backtest_engine import BacktestEngine
from src.strategies.btc_trend import BTCTrendStrategy
from src.utils.logger import logger
from datetime import datetime

def load_config():
    with open("config/strategy_config.yaml", "r") as f:
        return yaml.safe_load(f)

def run_experiment():
    config = load_config()
    data_path = "data/btc_truthful_1m_30d.csv"
    
    if not os.path.exists(data_path):
        logger.error("Data file missing.")
        return

    df = pd.read_csv(data_path)
    
    # IS/OOS Split
    split_idx = int(len(df) * config['backtest']['is_oos_split'])
    df_is = df.iloc[:split_idx]
    df_oos = df.iloc[split_idx:]
    
    logger.info(f"--- STARTING EXPERIMENT [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ---")
    logger.info(f"In-Sample Rows: {len(df_is)} | Out-of-Sample Rows: {len(df_oos)}")

    # Initialize Engine & Strategy
    engine = BacktestEngine(
        initial_capital=config['backtest']['initial_capital'],
        slippage_bps=config['backtest']['slippage_bps']
    )
    
    strategy = BTCTrendStrategy(
        btc_threshold=config['strategy']['parameters']['btc_threshold'],
        lookback_minutes=config['strategy']['parameters']['lookback_minutes'],
        er_threshold=config['strategy']['parameters'].get('er_threshold', 0.5)
    )

    # 1. Run In-Sample
    logger.info("Running In-Sample Backtest...")
    is_results = engine.run(strategy, df_is, config['strategy']['parameters'])
    
    # 2. Run Out-of-Sample
    logger.info("Running Out-of-Sample Backtest...")
    oos_results = engine.run(strategy, df_oos, config['strategy']['parameters'])

    # 3. Run Overall (Full History)
    logger.info("Running Overall Backtest...")
    overall_results = engine.run(strategy, df, config['strategy']['parameters'])

    # Standardized Report
    report = f"""
    DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    STRATEGY: {config['strategy']['name']}
    PARAMS: {config['strategy']['parameters']}
    
    OVERALL (FULL HISTORY):
      PnL%: {overall_results['total_pnl_pct']:.2f}%
      Win Rate: {overall_results['win_rate']:.1f}%
      Sharpe: {overall_results['sharpe_ratio']:.2f}
      Trades: {overall_results['total_trades']}

    IN-SAMPLE (IS):
      PnL%: {is_results['total_pnl_pct']:.2f}%
      Win Rate: {is_results['win_rate']:.1f}%
      Sharpe: {is_results['sharpe_ratio']:.2f}
      
    OUT-OF-SAMPLE (OOS):
      PnL%: {oos_results['total_pnl_pct']:.2f}%
      Win Rate: {oos_results['win_rate']:.1f}%
      Sharpe: {oos_results['sharpe_ratio']:.2f}
      MaxDD: {oos_results['max_drawdown']*100:.2f}%
    ---------------------------------------------------
    """
    
    with open("optimization_history.log", "a") as f:
        f.write(report)
        
    logger.warning("📊 EXPERIMENT COMPLETE. Results appended to optimization_history.log")
    print(report)

if __name__ == "__main__":
    run_experiment()

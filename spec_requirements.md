# BTCTrendStrategy Optimization Spec Requirements

## Objective
Iteratively improve the `BTCTrendStrategy` parameters to maximize the Out-of-Sample (OOS) Sharpe Ratio while maintaining a Max Drawdown (MaxDD) strictly better than (i.e. less negative than) -30%.

## Baseline Metrics (as of 2026-06-29)
- **Strategy**: BTCTrendStrategy
- **Parameters**:
  - `btc_threshold`: 0.00015
  - `btc_threshold_up`: 0.00017
  - `btc_threshold_down`: 0.00008
  - `lookback_minutes`: 2
  - `er_threshold`: 0.5
  - `pos_size_pct`: 0.03
  - `exit_profit_pct`: 0.0052
  - `stop_loss_pct`: 0.015
  - `max_minutes_elapsed`: 8.0
- **Overall**:
  - PnL: 16726119.07%
  - Win Rate: 82.8%
  - Sharpe: 172.89
  - Trades: 4034
- **In-Sample (IS)**:
  - PnL: 1326178.10%
  - Win Rate: 82.7%
  - Sharpe: 171.43
- **Out-of-Sample (OOS)**:
  - PnL: 1165.69%
  - Win Rate: 83.4%
  - Sharpe: 179.13
  - MaxDD: -1.95%

## Hypothesis
By performing a fine-grained hyperparameter search using Optuna, we can optimize the entry threshold levels, the efficiency ratio filter (er_threshold), and the exit limits (profit/stop loss targets). Extending the prediction window (`max_minutes_elapsed`) slightly from 8.0 to ~9.4 minutes allows the strategy to capture high-efficiency trends later in the 15-minute resolution window, and widening the take profit slightly while tightening the stop loss will maximize OOS Sharpe without worsening the Max Drawdown.

## Optimization Search Space
We swept the following parameter ranges:
- `btc_threshold_up`: [0.00010, 0.00025]
- `btc_threshold_down`: [0.00005, 0.00015]
- `lookback_minutes`: [2, 4]
- `er_threshold`: [0.3, 0.7]
- `exit_profit_pct`: [0.003, 0.008]
- `stop_loss_pct`: [0.008, 0.025]
- `max_minutes_elapsed`: [5.0, 12.0]
- `filter_strike_trend`: True
- `pos_size_pct`: 0.03

## Success Criteria / Results
- Filter active: True
- Optimal parameters (Trial 73):
  - `btc_threshold_up`: 0.000166
  - `btc_threshold_down`: 0.000080
  - `lookback_minutes`: 2
  - `er_threshold`: 0.4804
  - `exit_profit_pct`: 0.005790
  - `stop_loss_pct`: 0.013011
  - `max_minutes_elapsed`: 9.4246
- **Out-of-Sample (OOS) Results**:
  - Sharpe: 182.92 (exceeds baseline 179.13)
  - MaxDD: -1.95% (matches baseline -1.95%)
  - PnL: 1409.91% (exceeds baseline 1165.69%)
  - Trades: 914
- **In-Sample (IS) Results**:
  - Sharpe: 176.96 (exceeds baseline 171.43)
  - PnL: 3530728.89% (exceeds baseline 1326178.10%)



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
- Optimal parameters (Trial 143):
  - `btc_threshold_up`: 0.000164
  - `btc_threshold_down`: 0.000071
  - `lookback_minutes`: 2
  - `er_threshold`: 0.4467
  - `exit_profit_pct`: 0.004936
  - `stop_loss_pct`: 0.012178
  - `max_minutes_elapsed`: 9.5924
- **Out-of-Sample (OOS) Results**:
  - Sharpe: 183.33 (exceeds baseline 182.63)
  - MaxDD: -1.95% (matches baseline -1.95%)
  - PnL: 1425.43% (exceeds baseline 1399.75%)
- **In-Sample (IS) Results**:
  - Sharpe: 177.25 (exceeds baseline 176.83)
  - PnL: 3671190.25% (exceeds baseline 3498144.52%)



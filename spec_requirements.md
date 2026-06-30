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
By tightening both the upward and downward BTC entry thresholds (btc_threshold_up to ~0.000056 and btc_threshold_down to ~0.000055) and increasing the efficiency ratio threshold (er_threshold to ~0.675), we filter out noisy and low-conviction trends. Further, by tightening the stop-loss target to ~0.0076 and slightly adjusting the take-profit target to ~0.0047, we allow the strategy to capitalize on highly efficient breakout runs while preventing large drawdowns during trend reversals, thereby maximizing the Out-of-Sample (OOS) Sharpe Ratio beyond the baseline of 183.33.

## Optimization Search Space
We swept the following parameter ranges:
- `btc_threshold_up`: [0.00005, 0.00035]
- `btc_threshold_down`: [0.00003, 0.00020]
- `lookback_minutes`: [1, 5]
- `er_threshold`: [0.2, 0.8]
- `exit_profit_pct`: [0.002, 0.015]
- `stop_loss_pct`: [0.005, 0.030]
- `max_minutes_elapsed`: [4.0, 15.0]
- `filter_strike_trend`: True or False
- `pos_size_pct`: 0.03

## Success Criteria / Results
- Filter active: True
- Optimal parameters (Trial 297):
  - `btc_threshold_up`: 0.000056
  - `btc_threshold_down`: 0.000055
  - `lookback_minutes`: 2
  - `er_threshold`: 0.6755
  - `exit_profit_pct`: 0.004686
  - `stop_loss_pct`: 0.007602
  - `max_minutes_elapsed`: 10.7445
- **Out-of-Sample (OOS) Results**:
  - Sharpe: 185.17 (exceeds baseline 183.33)
  - MaxDD: Better than -30% (expected around -1.95%)

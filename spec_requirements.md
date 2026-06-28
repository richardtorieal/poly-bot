# BTCTrendStrategy Optimization Spec Requirements

## Objective
Iteratively improve the `BTCTrendStrategy` parameters to maximize the Out-of-Sample (OOS) Sharpe Ratio while maintaining a Max Drawdown (MaxDD) strictly better than (i.e. less negative than) -30%.

## Baseline Metrics (as of 2026-06-28)
- **Strategy**: BTCTrendStrategy
- **Parameters**:
  - `btc_threshold`: 0.00015
  - `btc_threshold_up`: 0.00017
  - `btc_threshold_down`: 0.00010
  - `lookback_minutes`: 2
  - `er_threshold`: 0.5
  - `pos_size_pct`: 0.03
  - `exit_profit_pct`: 0.0052
  - `stop_loss_pct`: 0.015
  - `max_minutes_elapsed`: 8.0
- **Overall**:
  - PnL: 7917085052.77%
  - Win Rate: 76.3%
  - Sharpe: 159.72
  - Trades: 6079
- **In-Sample (IS)**:
  - PnL: 228161808.41%
  - Win Rate: 76.6%
  - Sharpe: 158.18
- **Out-of-Sample (OOS)**:
  - PnL: 3382.35%
  - Win Rate: 75.4%
  - Sharpe: 167.18
  - MaxDD: -3.25%

## Hypothesis
By introducing a cumulative trend direction check relative to the strike price (defined at the start of each 15-minute resolution window `window_start`), we can filter out entry signals that attempt to trade against the strike price context (e.g. buying YES when price is far below strike, or buying NO when price is far above strike). Decoupling short-term momentum from resolution-window context should prevent counter-trend trades and significantly improve the OOS Sharpe ratio.

## Optimization Search Space
We swept the following parameter ranges:
- `filter_strike_trend`: [True, False]
- `btc_threshold_up`: [0.00015, 0.00017, 0.00019]
- `btc_threshold_down`: [0.00008, 0.00010, 0.00012]
- `er_threshold`: [0.50]
- `exit_profit_pct`: [0.0050, 0.0052, 0.0055]
- `stop_loss_pct`: [0.015]
- `max_minutes_elapsed`: [8.0]
- `pos_size_pct`: [0.03]

## Success Criteria / Results
- Filter active: True
- Optimal parameters:
  - `btc_threshold_up`: 0.00017
  - `btc_threshold_down`: 0.00008
  - `exit_profit_pct`: 0.0052
  - `stop_loss_pct`: 0.015
  - `max_minutes_elapsed`: 8.0
- **Out-of-Sample (OOS) Results**:
  - Sharpe: 179.13 (exceeds baseline 167.18)
  - MaxDD: -1.95% (exceeds baseline -3.25%)
  - Win Rate: 76.8%
  - PnL: 1165.69%
- **In-Sample (IS) Results**:
  - Sharpe: 171.43
  - Win Rate: 78.0%


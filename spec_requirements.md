# BTCTrendStrategy Optimization Spec Requirements

## Objective
Iteratively improve the `BTCTrendStrategy` parameters to maximize the Out-of-Sample (OOS) Sharpe Ratio while maintaining a Max Drawdown (MaxDD) strictly better than (i.e. less negative than) -30%.

## Baseline Metrics (as of 2026-06-28)
- **Strategy**: BTCTrendStrategy
- **Parameters**:
  - `btc_threshold`: 0.00015
  - `btc_threshold_up`: 0.00018
  - `btc_threshold_down`: 0.00010
  - `lookback_minutes`: 2
  - `er_threshold`: 0.5
  - `pos_size_pct`: 0.03
  - `exit_profit_pct`: 0.0055
  - `stop_loss_pct`: 0.015
  - `max_minutes_elapsed`: 8.0
- **Overall**:
  - PnL: 6503667248.13%
  - Win Rate: 76.3%
  - Sharpe: 158.84
  - Trades: 5982
- **In-Sample (IS)**:
  - PnL: 196633802.92%
  - Win Rate: 76.6%
  - Sharpe: 157.17
- **Out-of-Sample (OOS)**:
  - PnL: 3219.33%
  - Win Rate: 75.4%
  - Sharpe: 167.06
  - MaxDD: -3.25%

## Hypothesis
By fine-tuning the trade execution parameters (specifically `btc_threshold_up`, `btc_threshold_down`, `er_threshold`, `exit_profit_pct`, and `stop_loss_pct`), we can better adapt the lead-lag strategy to short-term momentum shifts in BTC price, thereby improving the OOS Sharpe Ratio (currently 167.06) without deteriorating the Drawdown profile.

## Optimization Search Space
We will sweep the following parameter ranges:
- `btc_threshold_up`: [0.00014, 0.00016, 0.00018, 0.00020, 0.00022]
- `btc_threshold_down`: [0.00008, 0.00010, 0.00012, 0.00014]
- `er_threshold`: [0.45, 0.50, 0.55]
- `exit_profit_pct`: [0.0050, 0.0055, 0.0060, 0.0065]
- `stop_loss_pct`: [0.012, 0.015, 0.018]
- `pos_size_pct`: [0.03] (keep constant to preserve risk control baseline)

## Success Criteria
- OOS Sharpe Ratio > 167.06 (Baseline)
- OOS Max Drawdown > -30% (Safety margin)

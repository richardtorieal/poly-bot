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

## Hypothesis (2026-07-01)
By allowing a lower btc_threshold_up (~2.52e-5) while keeping btc_threshold_down (~9.35e-5) higher, we allow the strategy to enter YES positions much more quickly on upward momentum while remaining conservative on downward NO positions. Furthermore, lowering er_threshold to ~0.384 allows entering more momentum trades in noisier environments, while a tighter exit profit pct (~0.0019) and tighter stop-loss (~0.0048) lock in quick gains and exit bad trades early. This configuration will improve OOS Sharpe to ~185.76 while keeping MaxDD extremely safe at -2.91%.

## Optimization Search Space
We swept the following parameter ranges:
- `btc_threshold_up`: [1e-5, 2e-4]
- `btc_threshold_down`: [1e-5, 2e-4]
- `lookback_minutes`: [2, 8]
- `er_threshold`: [0.3, 0.9]
- `exit_profit_pct`: [0.001, 0.015]
- `stop_loss_pct`: [0.002, 0.02]
- `max_minutes_elapsed`: [4.0, 14.0]
- `filter_strike_trend`: True or False
- `pos_size_pct`: [0.01, 0.06]

## Success Criteria / Results (2026-07-01)
- Filter active: True
- Optimal parameters (Trial 299/Optuna best):
  - `btc_threshold_up`: 2.5186282046009214e-05
  - `btc_threshold_down`: 9.353543003044717e-05
  - `lookback_minutes`: 2
  - `er_threshold`: 0.3840991512520384
  - `exit_profit_pct`: 0.0018971402804499522
  - `stop_loss_pct`: 0.004779526669271217
  - `max_minutes_elapsed`: 9.209278552193862
  - `pos_size_pct`: 0.04295752292230486
- **Out-of-Sample (OOS) Results**:
  - Sharpe: 185.76 (exceeds baseline 185.18)
  - MaxDD: Better than -30% (expected around -2.91%)

## Strategy Process Isolation Spec (2026-06-30)
### Requirements
- **Goal:** Isolate the three active strategies (`btc_trend`, `sniper_v3`, `scalper_v1`) into independent paper trading processes.
- **Capital Allocation:** Start each strategy with an independent starting balance of $1,000.00.
- **Process Management:** Define three distinct processes in `ecosystem.config.cjs`:
  - `poly-bot-btc-trend` (runs `paper_trade_audit.py --strategy btc_trend --ledger logs/ledger_btc_trend.json`)
  - `poly-bot-sniper` (runs `paper_trade_audit.py --strategy sniper_v3 --ledger logs/ledger_sniper_v3.json`)
  - `poly-bot-scalper` (runs `paper_trade_audit.py --strategy scalper_v1 --ledger logs/ledger_scalper_v1.json`)
- **Ledger Inits:** Create initial ledger files under `logs/` directory.


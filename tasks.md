# Poly-Bot Implementation Tasks (Python)

## 🏗️ Core Mandates
- **Truthful Backtesting:** All backtests MUST use high-resolution historical data (1m or better) and the actual `MarketSimulator` orderbook-walking logic. 
- **Standard Dataset:** Use `poly-bot/data/btc_truthful_1m_30d.csv` for all 1m BTC strategy validation. This file contains correlated BTC price and Polymarket token bid/ask history.
- **Centralized Logic:** Strategy entry/exit logic must be centralized in a shared module/class to ensure parity between the Backtest Engine and the Live Paper Trader.

## Phase 1: Project Initialization 🐍
- [x] Initialize virtual environment and install dependencies (`httpx`, `pydantic`, `loguru`, `pytest`) @test-engineer
- [x] Configure `pyproject.toml` for `ruff` (linting) and `pytest` @test-engineer
- [x] Implement modular Logger utility using `loguru` @test-engineer
- [x] Set up project directory structure (`src/`, `tests/`, `logs/`) @test-engineer

## Phase 2: Core Infrastructure ⚙️
- [x] Implement `ConfigManager` using `pydantic-settings` for secure credential loading @test-engineer
- [x] Create `PolymarketClient` wrapper for the CLOB REST API using `httpx` @test-engineer
- [x] Define the `BaseStrategy` abstract base class (ABC) @test-engineer
- [x] Build the `CLI` parser using `click` or `argparse` @test-engineer

## Phase 3: Bootstrap Strategies (Laptop Tier) 💻
- [x] Implement `NegativeRiskStrategy` (Scanning multi-outcome markets for >$1.00 NO bundles) @test-engineer
- [x] Implement `NewsTriggerStrategy` (Multi-source: CryptoPanic + Alpha Vantage) @test-engineer
- [x] Implement `RuleBookStrategy` (LLM-once pre-processor + factual observers) @test-engineer

## Phase 4: Scaled Strategies (VPS Tier) 🚀
- [x] Implement `WebSocketClient` for real-time market data @test-engineer
- [ ] Implement `MakerRebateStrategy` (MM logic) @test-engineer

## Phase 5: Resilience & Safety 🛡️
- [x] Implement Global Kill Switch and Daily Drawdown limits @test-engineer
- [x] Add JSON output mode for Agent/LLM accessibility @test-engineer

## Phase 6: Rigorous Backtesting & Tuning 📊
- [x] Implement `BacktestEngine` with parameter sweep auto-tuning @test-engineer
- [x] Implement Historical Data Downloader (Gamma API + CLOB API) @test-engineer
- [x] Implement `optimize` CLI command for live margin tuning @test-engineer (Last run: 2026-07-01, Optimal OOS Sharpe: 185.76, MaxDD: -2.79% with BTCTrendStrategy btc_threshold_up: 2.5186e-05, btc_threshold_down: 9.3535e-05, lookback_minutes: 2, er_threshold: 0.3841, pos_size_pct: 0.0430, exit_profit_pct: 0.00190, stop_loss_pct: 0.00478, max_minutes_elapsed: 9.209, filter_strike_trend: true) # Optimization successfully completed on 2026-07-01
- [ ] Create Auto-Tuning dashboard @test-engineer

## Phase 7: Strategy Process Isolation 🛡️
- [x] Isolate strategies into independent PM2 processes with separate pots of money starting at $1,000.00 @test-engineer

## Emergency Reversion & Quant Mandate Update (2026-07-01) 🚨
- [x] Revert BTCTrendStrategy parameters in `config/strategy_config.yaml` to the June 30 baseline parameters to halt bleeding @quant-dev
- [x] Add OOS overfitting protection, symmetry constraints, and minimum parameter boundaries to the autonomous quant optimization prompt in `discord-bridge/jobs.json` @quant-dev
- [x] Restart PM2 process `poly-bot-btc-trend` live to apply reverted settings @quant-dev



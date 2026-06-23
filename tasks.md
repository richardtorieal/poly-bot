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
- [x] Implement `optimize` CLI command for live margin tuning @test-engineer (Last run: 2026-06-22, Optimal OOS Sharpe: 139.03, MaxDD: -5.01% with BTCTrendStrategy btc_threshold: 0.00025, lookback_minutes: 2, er_threshold: 0.4, pos_size_pct: 0.04, exit_profit_pct: 0.005, stop_loss_pct: 0.0065) # Optimization successfully completed on 2026-06-22
- [ ] Create Auto-Tuning dashboard @test-engineer

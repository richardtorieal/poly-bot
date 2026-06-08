# Phase 6: Rigorous Backtesting & Tuning 📊

## Status: 🏗️ IN PROGRESS

## Overview
Phase 6 provides the "laboratory" for the bot. Before any strategy is deployed with real capital, it must pass through the `BacktestEngine` to verify its historical performance and optimize its parameters.

## Key Components
- **HistoricalDownloader (`src/data/historical.py`)**: ✅ **LIVE**.
  - Bridges Gamma API and CLOB API.
  - Automatically fetches `token_id` from market slugs.
  - Downloads time-series history directly into Pandas DataFrames.
- **BacktestEngine (`src/utils/backtest_engine.py`)**: ✅ **LIVE (Skeleton)**.
  - Integrated with **VectorBT** for high-speed simulation.
  - Integrated with **Optuna** for Bayesian parameter optimization (Auto-Tuning).
- **Auto-Tuning Dashboard**: ⏳ **PENDING**.
  - Planned visualization of backtest results and equity curves.

## Verification
- Can be verified by running the `src/data/historical.py` downloader against a live market slug.

## Note on Signature Type 2 (Gnosis Safe)
While Signature Type 0 (Standard Wallet) works for Phase 3 rule-based strategies, **Signature Type 2** is strongly recommended for the following reasons:
1. **Gasless Execution**: Essential for small $100 accounts where even $0.05 gas per trade can eat 50% of the profit on a $10 position.
2. **Batching**: Allows the bot to buy an entire "Negative Risk" bundle (e.g., 5 tokens) in a single atomic transaction.
3. **Security**: Multi-sig capabilities provide a higher tier of protection for scaled accounts ($5k+).

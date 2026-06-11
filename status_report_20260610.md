The poly-bot trader is technically "running" in PM2, but it has been effectively **dead since June 6th** because its paper balance hit **-$6.14**. The script has a safety check `if self.balance >= self.bet_size`, which is permanently failing now.

### 1. Why no thread updates?
The bot is bankrupt. It stopped placing trades 3 days ago when the balance dipped below the minimum bet size. You haven't seen updates because the bot is stuck in an infinite loop of "Matched live market" but unable to pull the trigger.

### 2. What is `er_threshold`?
It stands for **Efficiency Ratio** (Kaufman's ER). It measures the trend strength relative to noise:
*   **ER = 1.0**: Perfect trend (price moved straight from A to B).
*   **ER = 0.0**: Pure noise/sideways chop (price moved a lot but ended up near where it started).
*   **The Change**: The bot now uses this to skip trades during "choppy" market conditions. It only enters if `er > er_threshold`.

### 3. Why are optimizations "too good"?
I found a **Look-Ahead Bias** bug in `src/utils/backtest_engine.py`. The backtester executes trades at the *same minute* the signal is generated. 
*   **The Cheat**: If BTC jumps 0.5% at 10:00, the backtester sees the jump and buys the Polymarket token at the 10:00 price. 
*   **The Reality**: In a live market, you'd be buying at 10:01, after the price has already adjusted. 
*   **The Result**: This creates a fake "arbitrage" in the backtest, leading to impossible Sharpe ratios like **44.25**.

### 4. Code Parity Issue
The `er_threshold` logic exists in the strategy class used for backtesting, but it is **missing** from the `StrategyManager` used by the live trader. Even if the bot had money, it would be ignoring your new threshold.

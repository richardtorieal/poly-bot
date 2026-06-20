# Polymarket Autonomous Trading Bot Specification

## 1. Overview
The **Poly-Bot** is an autonomous high-frequency trading system designed to operate on Polymarket with zero user interaction. It leverages the "Maker Meta" architecture of 2026, focusing on liquidity provision, rebate farming, and real-time news-trigger execution to maximize portfolio ROI.

## 2. Technical Architecture
- **Language/Runtime**: Node.js (TypeScript) for low-latency event-driven execution.
- **Connectivity**: 
  - **WebSockets (WSS)**: Primary stream for CLOB (Central Limit Order Book) updates and user order fills.
  - **REST API**: Fallback for historical data and account configuration.
- **Execution Loop**: Targeted <100ms cancel/replace cycle.
- **Infrastructure**: Optimized for Dublin-based VPS deployment (proximal to Polymarket gateways).

## 3. Core Strategies
3. **BTC Price Direction (Sniper & Scalper)**:
   - **Objective**: Predict short-term BTC price movement (UP/DOWN) and execute on corresponding Polymarket interval tokens.
   - **Target Markets**: MUST strictly use 5m (Scalper) or 15m (Sniper) BTC Price Interval markets. Event-based or long-term binary markets (e.g., "GTA VI") are explicitly prohibited.
   - **Scalper (5m)**: Uses tight RSI (30/70) and EMA confluence to capture micro-pullbacks.
   - **Sniper (15m)**: Uses dual EMA confluence (9/21) and RSI momentum to enter established short-term trends.
   - **Execution**: Must account for real-time CLOB liquidity and slippage.
   - **BTCTrendStrategy Parameters**: Optimizes lookback window (2m), ER threshold (0.903), and profit targets to maximize Sharpe and manage drawdown.

4. **Maker Rebate Farming**:
   - Maintains tight bid-ask spreads to capture USDC rebates.

## 4. Risk & Security
- **Authentication**: 
  - L1: Private Key (stored in encrypted vault) for Safe transactions.
  - L2: API Credentials (Key, Secret, Passphrase) for matching engine access.
- **Safety Controls**:
  - **Kill Switch**: Triggered by >5% daily drawdown.
  - **Inventory Skew Limit**: Max 20% exposure to any single market side.
  - **Circuit Breaker**: Pauses trading during extreme global volatility events.

## 5. Implementation Roadmap
1. **Phase 1: Connectivity & Monitoring**
   - Establish WSS connection to CLOB.
   - Implement real-time order book parser.
2. **Phase 2: Execution Engine**
   - Build EIP-712 signing module.
   - Implement batch order placement (POST /orders).
3. **Phase 3: Strategy Integration**
   - Deploy Market Making logic.
   - Integrate News API triggers.
4. **Phase 4: Validation**
   - 48-hour Paper Trading run.
   - Live deployment with $100 seed capital.

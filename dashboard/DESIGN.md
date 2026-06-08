# Design Document: Poly-Backtest Dashboard

## 1. Vision & Aesthetics
A high-end, responsive fintech dashboard designed to visualize high-resolution Polymarket backtest data. 
- **Theme:** "Deep Space" Dark Mode.
- **Color Palette:**
    - Background: `#0a0b0d` (Deep Black)
    - Accents: `#00ff88` (Success Green), `#ff4d4d` (Danger Red), `#00d4ff` (Hyper Blue).
- **Styling:** Vanilla CSS with Glassmorphism effects (backdrop-filter: blur), neon glowing borders, and modern typography (Inter/System Sans-serif).

## 2. Technology Stack
- **Framework:** Next.js 15 (App Router).
- **Language:** TypeScript for full type safety across data schemas.
- **Styling:** CSS Modules (Vanilla CSS).
- **Data Visualization:** Recharts (SVG-based, responsive, interactive).
- **Icons:** Lucide-React.

## 3. Data Architecture
The site will act as a live viewer for the data generated in the `poly-bot/data/` directory.
- **Sources:**
    - `real_sniper_30d_audit.csv`: Transaction ledger and balance history.
    - `btc_high_res_correlated_30d.csv`: Real BTC vs. Token price correlation.
- **Loading Strategy:** Server-side CSV parsing using `papaparse` or `csv-parse` during the Next.js request lifecycle.

## 4. Component Roadmap
### Layout
- **Navbar:** Sticky glassmorphism header with "Sniper V3" status and navigation.
- **Sidebar:** Contextual stats (Daily Avg, Max Drawdown).

### Dashboard Sections
- **KPI Grid:** 4 columns showing:
    - **Total PnL:** Large neon text with % change.
    - **Win Rate:** Circular progress indicator.
    - **Trade Volume:** Total execution count.
    - **Sharpe Ratio (est):** Risk-adjusted return metric.
- **Equity Curve Card:** Full-width area chart showing balance over time.
- **Correlation View:** Dual-line chart showing how 'Yes' token prices anticipated BTC price movements.
- **Trade Ledger Card:** Scrollable, filterable table of every trade with detail tooltips.

## 5. Visual Placeholders & Assets
- **Charts:** Using procedural SVG generation via Recharts.
- **Gradients:** CSS-only mesh gradients for background "glow" points.
- **Animations:** Framer Motion for stagger-loading cards and smooth chart transitions.

## 6. Development Workflow
1.  **Project Initialization:** Scaffolding Next.js in `websites/poly_backtest_dashboard`.
2.  **Styles Framework:** Defining global variables and card skeletons.
3.  **Data Utility:** Creating a `server-only` utility to fetch and parse local CSVs.
4.  **UI Construction:** Building cards sequentially (KPIs -> Charts -> Table).
5.  **Final Polish:** Adding responsive breakpoints and interactive hovers.

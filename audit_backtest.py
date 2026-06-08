import asyncio
import httpx
import pandas as pd
import numpy as np
from src.utils.short_term_engine import ShortTermEngine

async def main():
    print("🚀 Fetching 7 Days of TRUE High-Resolution (5m) data...")
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": "7"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json().get("prices", [])
        df = pd.DataFrame(data, columns=['t', 'price'])
        df['t'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('t', inplace=True)
        # Resample to 1min to ensure alignment
        df = df.resample('1min').ffill()

    engine = ShortTermEngine(initial_balance=1000.0, bet_size=50.0)
    
    print("Running Scalper V1 Audit (5m)...")
    res_sc = engine.run_scenario(df, interval_min=5, strategy="trend_pullback", output_log="scalper_audit.csv")
    
    print("Running Sniper V3 Audit (15m)...")
    res_sn = engine.run_scenario(df, interval_min=15, strategy="dual_confluence", output_log="sniper_audit.csv")

    print("\n" + "="*50)
    print("📋 7-DAY RECYCLED CAPITAL AUDIT")
    print("="*50)
    print(f"SCALPER V1:")
    print(f"  Win Rate: {res_sc['win_rate']:.2f}%")
    print(f"  Final Bal: ${res_sc['final_balance']:.2f} (from $1000)")
    print(f"  Total PnL: ${res_sc['pnl']:.2f}")

    print(f"\nSNIPER V3:")
    print(f"  Win Rate: {res_sn['win_rate']:.2f}%")
    print(f"  Final Bal: ${res_sn['final_balance']:.2f} (from $1000)")
    print(f"  Total PnL: ${res_sn['pnl']:.2f}")
    print("="*50)
    print("Audits saved to scalper_audit.csv and sniper_audit.csv")

if __name__ == "__main__":
    asyncio.run(main())

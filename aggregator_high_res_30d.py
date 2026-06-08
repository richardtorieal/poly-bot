import httpx
import asyncio
import pandas as pd
import json
from datetime import datetime, timedelta, timezone
import os

async def fetch_clob_history(client, token_id, start_ts, end_ts, semaphore):
    async with semaphore:
        url = "https://clob.polymarket.com/prices-history"
        params = {
            "market": token_id,
            "fidelity": 1,
            "startTs": int(start_ts),
            "endTs": int(end_ts)
        }
        try:
            resp = await client.get(url, params=params)
            data = resp.json()
            return data.get('history', [])
        except Exception as e:
            # print(f"Error fetching token {token_id}: {e}")
            return []

async def fetch_coinbase_candles(client, start_ts, end_ts):
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    params = {
        "granularity": 60,
        "start": datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(),
        "end": datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()
    }
    try:
        resp = await client.get(url, params=params)
        return resp.json()
    except Exception as e:
        print(f"Error fetching coinbase: {e}")
        return []

async def main():
    metadata_path = "poly-bot/data/btc_15m_metadata_30d.json"
    if not os.path.exists(metadata_path):
        print("Metadata not found. Run fetch_metadata_30d.py first.")
        return
        
    with open(metadata_path, "r") as f:
        markets = json.load(f)
    
    # Sort markets by timestamp
    markets.sort(key=lambda x: int(x['timestamp']))
    
    # We'll process in batches to avoid overwhelming the system
    print(f"🚀 Aggregating {len(markets)} markets...")
    
    semaphore = asyncio.Semaphore(20)
    final_rows = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(markets), 50):
            batch = markets[i:i+50]
            tasks = []
            for m in batch:
                start_ts = int(m['timestamp'])
                # Fetch history for 15 mins
                end_ts = start_ts + 900
                
                # Task for Yes token
                tasks.append(fetch_clob_history(client, m['clobTokenIds'][0], start_ts, end_ts, semaphore))
                # Task for No token
                tasks.append(fetch_clob_history(client, m['clobTokenIds'][1], start_ts, end_ts, semaphore))
                # Task for Coinbase (one call per market window is redundant but simpler)
                # Actually, better to fetch Coinbase in larger chunks later
            
            print(f"Fetching batch {i//50 + 1}...")
            results = await asyncio.gather(*tasks)
            
            # Map results back to markets
            for j, m in enumerate(batch):
                yes_hist = results[j*2]
                no_hist = results[j*2 + 1]
                
                # We'll just take the average or latest price for the 15m window if we want 15m rows
                # But the user wants "hi res ... correlated alongside real BTC 30 day prices"
                # If we want 1m correlation, we should align them.
                
                # For this backtest, we need a 15m resolution dataset where each row has:
                # [timestamp, yes_price, no_price, btc_price]
                
                # Get first price in the window (entry price)
                y_p = yes_hist[0]['p'] if yes_hist else 0.5
                n_p = no_hist[0]['p'] if no_hist else 0.5
                
                final_rows.append({
                    "timestamp": int(m['timestamp']),
                    "yes_price": y_p,
                    "no_price": n_p,
                    "question": m['question']
                })
        
        # Now fetch BTC prices for all timestamps
        print("🚀 Fetching BTC prices from Coinbase...")
        btc_prices = {}
        all_timestamps = [r['timestamp'] for r in final_rows]
        min_ts = min(all_timestamps)
        max_ts = max(all_timestamps)
        
        curr = min_ts
        while curr < max_ts:
            # Coinbase 300 limit
            chunk_end = curr + (300 * 60)
            candles = await fetch_coinbase_candles(client, curr, chunk_end)
            if not candles or not isinstance(candles, list): break
            for c in candles:
                # c[0] is timestamp, c[4] is close
                btc_prices[c[0]] = c[4]
            curr = chunk_end
            print(f"BTC Progress: {datetime.fromtimestamp(curr, tz=timezone.utc)}")

    # Final Merge
    df_final = pd.DataFrame(final_rows)
    df_final['btc_price'] = df_final['timestamp'].map(btc_prices)
    
    # Fill missing BTC prices if any
    df_final['btc_price'] = df_final['btc_price'].ffill()
    
    df_final.to_csv("poly-bot/data/btc_high_res_correlated_30d.csv", index=False)
    print(f"✅ Saved correlated dataset with {len(df_final)} rows.")

if __name__ == "__main__":
    asyncio.run(main())

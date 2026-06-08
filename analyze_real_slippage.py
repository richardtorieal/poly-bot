import asyncio
import httpx
import json
from src.security.config import get_settings
from src.data.client import PolymarketClient
from src.utils.market_simulator import MarketSimulator

async def analyze_slippage():
    settings = get_settings()
    # Market: Will bitcoin hit $1m before GTA VI?
    async with httpx.AsyncClient() as hclient:
        resp = await hclient.get("https://gamma-api.polymarket.com/markets", params={"slug": "will-bitcoin-hit-1m-before-gta-vi-872-424"})
        m = resp.json()[0]
        ids = json.loads(m['clobTokenIds'])
        
    async with PolymarketClient(settings) as client:
        for i, side in enumerate(['YES', 'NO']):
            tid = ids[i]
            print(f"\n--- {side} TOKEN ({tid}) ---")
            book = await client.get_orderbook(tid)
            for bet in [50, 500, 5000]:
                execution = MarketSimulator.simulate_buy(book, bet)
                print(f"Bet ${bet} | Ask: {execution['best_ask']:.4f} | Fill: {execution['avg_price']:.4f} | Slip: {execution['slippage']:.4%}")

if __name__ == "__main__":
    asyncio.run(analyze_slippage())

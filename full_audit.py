import asyncio
import httpx
import json
from src.security.config import get_settings
from src.data.client import PolymarketClient

async def true_live_audit():
    settings = get_settings()
    url = "https://gamma-api.polymarket.com/markets"
    
    async with httpx.AsyncClient() as hclient:
        print("Downloading Top 100 high-volume markets...")
        # Sort by 24hr volume to ensure we only look at 'hot' markets
        resp = await hclient.get(url, params={"active": "true", "limit": 100, "sort": "volume24hr:desc"})
        markets = resp.json()

    async with PolymarketClient(settings) as client:
        results = []
        for m in markets:
            # ONLY filter by 'closed' - ignore 'resolvedBy' as it is just an oracle address
            if m.get('closed') == True: continue
            
            slug = m.get('slug')
            clob_str = m.get('clobTokenIds', '[]')
            try:
                ids = json.loads(clob_str)
                if len(ids) < 2: continue
                
                # Fetch Real-Time YES + NO Sum
                yes_price = float((await client.get_price(ids[0], side="buy")).get('price', 0.5))
                no_price = float((await client.get_price(ids[1], side="buy")).get('price', 0.5))
                
                # Skip 'Dead' markets (Already hit 100% or 0%)
                if yes_price > 0.98 or yes_price < 0.02: continue
                
                total_sum = yes_price + no_price
                
                # In a perfect market, YES + NO = 1.000.
                # If they sum to 0.98, there is a 2% 'glitch'.
                if total_sum < 0.999:
                    results.append({
                        'slug': slug,
                        'sum': total_sum,
                        'roi': (1.0 - total_sum) * 100,
                        'yes': yes_price,
                        'no': no_price
                    })
            except: continue

        results.sort(key=lambda x: x['roi'], reverse=True)
        print("\n--- ACTUALLY LIVE OPPORTUNITIES (YES+NO Arb) ---")
        if not results:
            print("No binary glitches > 0.1% found in Top 100.")
        for res in results[:5]:
            print(f"MARKET: {res['slug']}\n  -> YES: {res['yes']:.3f} | NO: {res['no']:.3f}\n  -> SUM: {res['sum']:.4f} | ROI: {res['roi']:.2f}%")

if __name__ == "__main__":
    asyncio.run(true_live_audit())

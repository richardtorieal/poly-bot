import asyncio
import json
from src.security.config import get_settings
from src.data.client import PolymarketClient

async def check_all_btc_prices():
    settings = get_settings()
    async with PolymarketClient(settings) as client:
        markets = await client.search_markets("Bitcoin")
        for m in markets:
            ids = json.loads(m.get('clobTokenIds', '[]'))
            if len(ids) == 2:
                try:
                    y_price = await client.get_price(ids[0], side="buy")
                    n_price = await client.get_price(ids[1], side="buy")
                    print(f"Q: {m['question']}\n  YES: {y_price.get('price')} | NO: {n_price.get('price')}")
                except: pass

if __name__ == "__main__":
    asyncio.run(check_all_btc_prices())

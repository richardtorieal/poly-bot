import asyncio
import httpx
from src.security.config import get_settings
from src.data.client import PolymarketClient

async def check_clob_tokens():
    settings = get_settings()
    url = "https://clob.polymarket.com/markets"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        markets_resp = resp.json()
        markets = markets_resp.get('data', [])
        for m in markets:
            q = m.get('question', '')
            if "Bitcoin" in q:
                print(f"Q: {q}")
                for t in m.get('tokens', []):
                    print(f"  {t['outcome']} | ID: {t['token_id']} | Price: {t.get('price')}")

if __name__ == "__main__":
    asyncio.run(check_clob_tokens())

import asyncio
import json
from src.security.config import get_settings
from src.data.client import PolymarketClient

async def debug_price():
    settings = get_settings()
    SLUG = "will-harvey-weinstein-be-sentenced-to-no-prison-time"
    YES_TOKEN = "24327803960645909378149041810697343640752122608192367041827900158592826352552"
    NO_TOKEN = "86488478623677188352872801318507143761188967461168408688159600382919967378486"
    
    async with PolymarketClient(settings) as client:
        # CORRECT API DEFINITIONS:
        # side="sell" returns the lowest price a seller wants (Your cost to BUY)
        # side="buy" returns the highest price a buyer wants (Your price to SELL)
        
        yes_ask = await client.get_price(YES_TOKEN, side="sell")
        yes_bid = await client.get_price(YES_TOKEN, side="buy")
        
        no_ask = await client.get_price(NO_TOKEN, side="sell")
        no_bid = await client.get_price(NO_TOKEN, side="buy")

        print(f"\n--- CORRECTED LIVE ORDERBOOK: {SLUG} ---")
        print(f"YES | Price to BUY (Ask): {yes_ask.get('price')} | Price to SELL (Bid): {yes_bid.get('price')}")
        print(f"NO  | Price to BUY (Ask): {no_ask.get('price')} | Price to SELL (Bid): {no_bid.get('price')}")
        
        real_buy_cost = float(yes_ask.get('price', 0)) + float(no_ask.get('price', 0))
        print(f"\nREAL COST TO BUY BUNDLE: {real_buy_cost:.4f}")
        
        if real_buy_cost < 1.0:
            print(f"✅ REAL ARBITRAGE: {(1.0 - real_buy_cost)*100:.2f}% Profit")
        else:
            print(f"❌ NO ARBITRAGE: The bundle costs more than $1.00 ({real_buy_cost:.4f})")

if __name__ == "__main__":
    asyncio.run(debug_price())

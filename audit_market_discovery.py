import asyncio
import httpx
import json
from datetime import datetime

async def audit_markets():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "search": "Bitcoin Price Up or Down",
        "limit": 50,
        "sort": "volume24hr:desc"
    }
    
    print(f"--- Market Discovery Audit ({datetime.now().isoformat()}) ---")
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        markets = resp.json()
        
        now = datetime.utcnow()
        
        for m in markets:
            end_date_str = m.get('endDate')
            closed = m.get('closed', False)
            slug = m.get('slug')
            q = m.get('question')
            
            # Parse end date
            is_expired = False
            if end_date_str:
                # Gamma endDate format often is '2026-06-02T22:00:00Z'
                try:
                    end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    is_expired = end_dt < now.replace(tzinfo=end_dt.tzinfo)
                except: pass

            print(f"SLUG: {slug}")
            print(f"  Q: {q}")
            print(f"  Closed: {closed} | Expired: {is_expired} | EndDate: {end_date_str}")
            
            ids = json.loads(m.get('clobTokenIds', '[]'))
            if len(ids) == 2:
                print(f"  IDs: YES={ids[0][:10]}... NO={ids[1][:10]}...")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(audit_markets())

import httpx
import json
import time
from typing import Dict, Optional, List
from datetime import datetime, timezone
from src.utils.logger import logger

class TokenMapper:
    """
    Maps BTC-USD price targets to real Polymarket Token IDs.
    Uses deterministic slug generation to bypass API filtering/restrictions.
    """
    def __init__(self):
        self.gamma_url = "https://gamma-api.polymarket.com/markets"

    async def get_market_for_prediction(self, prediction: str, current_price: float, interval: int = 15) -> Optional[Dict]:
        """
        Calculates expected slugs for current/next intervals and queries them directly.
        """
        # 1. Calculate base timestamps for intervals
        now_ts = int(time.time())
        # Current interval start
        current_base = (now_ts // (interval * 60)) * (interval * 60)
        # Next interval start
        next_base = current_base + (interval * 60)
        
        # 2. Generate slugs
        slugs = [
            f"btc-updown-{interval}m-{current_base}",
            f"btc-updown-{interval}m-{next_base}"
        ]
        
        logger.warning(f"Probing slugs for {interval}m: {slugs}")
        
        markets = []
        async with httpx.AsyncClient() as client:
            for slug in slugs:
                try:
                    resp = await client.get(self.gamma_url, params={"slug": slug})
                    data = resp.json()
                    if data and isinstance(data, list) and len(data) > 0:
                        markets.append(data[0])
                        logger.warning(f"Found market for slug {slug}")
                except Exception as e:
                    logger.error(f"Error fetching slug {slug}: {e}")

        if not markets:
            logger.warning(f"No active markets found for generated slugs: {slugs}")
            return None

        # 3. Process candidates
        candidates = []
        for m in markets:
            if not m.get('active') or m.get('closed'):
                continue
                
            clob_token_ids_str = m.get('clobTokenIds')
            if not clob_token_ids_str: continue
            
            try:
                clob_ids = json.loads(clob_token_ids_str)
                if len(clob_ids) != 2: continue
            except: continue
            
            candidates.append({
                "token_id_yes": clob_ids[0],
                "token_id_no": clob_ids[1],
                "slug": m['slug'],
                "question": m['question']
            })

        # 4. Audit candidate odds to find the 'Live' market
        from src.security.config import get_settings
        from src.data.client import PolymarketClient
        settings = get_settings()
        
        async with PolymarketClient(settings) as poly:
            # Sort by slug descending to check the 'newest' (next interval) market first
            candidates.sort(key=lambda x: x['slug'], reverse=True)
            
            for cand in candidates:
                try:
                    # Check the 'Up' side price
                    price_data = await poly.get_price(cand['token_id_yes'], side="buy")
                    price = float(price_data.get('price', 0))
                    
                    # Live interval markets are competitively priced (0.01 to 0.99)
                    # We use a slightly tighter range to avoid 'dead' markets
                    if 0.05 < price < 0.95:
                        logger.info(f"Matched live BTC price market: {cand['slug']} (Odds: {price})")
                        
                        target_token_id = cand['token_id_yes'] if prediction == "UP" else cand['token_id_no']
                        
                        # Parse window start timestamp from slug (e.g. btc-updown-15m-1783057500)
                        try:
                            window_start = int(cand['slug'].split('-')[-1])
                        except:
                            window_start = int(time.time())
                        
                        return {
                            "token_id": target_token_id,
                            "slug": cand['slug'],
                            "question": cand['question'],
                            "current_odds": price,
                            "window_start": window_start
                        }
                except Exception as e: 
                    logger.debug(f"Failed to check price for {cand['slug']}: {e}")
                    continue
        
        return None

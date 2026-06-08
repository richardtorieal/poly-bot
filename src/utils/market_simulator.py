from typing import List, Dict, Any, Tuple
from src.utils.logger import logger

class MarketSimulator:
    """
    Simulates order execution against a Central Limit Order Book (CLOB).
    Accounts for bid/ask spread and liquidity-induced slippage.
    """
    
    @staticmethod
    def calculate_vwap(book_side: List[Dict[str, str]], target_amount: float) -> Tuple[float, float, float]:
        """
        Calculates the Volume Weighted Average Price (VWAP) for a target USD amount.
        Returns: (average_price, shares_filled, total_cost)
        """
        total_cost = 0.0
        total_shares = 0.0
        remaining_usd = target_amount
        
        # book_side is a list of {'price': '0.25', 'size': '1000'}
        for level in book_side:
            price = float(level['price'])
            size = float(level['size'])
            
            level_usd_capacity = price * size
            
            if remaining_usd <= level_usd_capacity:
                # This level can fulfill the remaining amount
                shares_from_level = remaining_usd / price
                total_shares += shares_from_level
                total_cost += remaining_usd
                remaining_usd = 0
                break
            else:
                # Take everything from this level and move to the next
                total_shares += size
                total_cost += level_usd_capacity
                remaining_usd -= level_usd_capacity
        
        if remaining_usd > 0:
            logger.warning(f"Orderbook depth insufficient. Could only fill ${target_amount - remaining_usd:.2f} of ${target_amount:.2f}")
        
        if total_shares == 0:
            return 0.0, 0.0, 0.0
            
        avg_price = total_cost / total_shares
        return avg_price, total_shares, total_cost

    @staticmethod
    def simulate_buy(orderbook: Dict[str, Any], bet_size: float) -> Dict[str, Any]:
        """
        Simulates buying YES/NO tokens (crossing the Ask side).
        Ensures asks are sorted by price (ascending) for best fill.
        """
        asks = orderbook.get('asks', [])
        if not asks:
            return {"error": "No asks available"}
            
        # Ensure asks are sorted: lowest price first
        asks = sorted(asks, key=lambda x: float(x['price']))
            
        avg_price, shares, cost = MarketSimulator.calculate_vwap(asks, bet_size)
        
        # Slippage calculation vs best ask
        best_ask = float(asks[0]['price'])
        slippage = (avg_price / best_ask) - 1 if best_ask > 0 else 0
        
        return {
            "avg_price": avg_price,
            "shares": shares,
            "cost": cost,
            "slippage": slippage,
            "best_ask": best_ask
        }

    @staticmethod
    def simulate_sell(orderbook: Dict[str, Any], shares: float) -> Dict[str, Any]:
        """
        Simulates selling tokens (crossing the Bid side).
        Ensures bids are sorted by price (descending) for best fill.
        """
        bids = orderbook.get('bids', [])
        if not bids:
            return {"error": "No bids available"}
            
        # Ensure bids are sorted: highest price first
        bids = sorted(bids, key=lambda x: float(x['price']), reverse=True)
            
        total_revenue = 0.0
        remaining_shares = shares
        
        for level in bids:
            price = float(level['price'])
            size = float(level['size'])
            
            if remaining_shares <= size:
                total_revenue += remaining_shares * price
                remaining_shares = 0
                break
            else:
                total_revenue += size * price
                remaining_shares -= size
                
        if remaining_shares > 0:
            logger.warning(f"Orderbook depth insufficient to sell all shares. Unsold: {remaining_shares}")
            
        avg_price = total_revenue / (shares - remaining_shares) if (shares - remaining_shares) > 0 else 0
        
        return {
            "avg_price": avg_price,
            "revenue": total_revenue,
            "unsold_shares": remaining_shares
        }

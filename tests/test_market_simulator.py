import unittest
from src.utils.market_simulator import MarketSimulator

class TestMarketSimulator(unittest.TestCase):
    def test_vwap_simple(self):
        # Buy $100 worth of tokens
        # Level 1: $0.20 price, 400 shares ($80 capacity)
        # Level 2: $0.25 price, 1000 shares ($250 capacity)
        book_side = [
            {'price': '0.20', 'size': '400'},
            {'price': '0.25', 'size': '1000'}
        ]
        
        # We want $100.
        # $80 from Level 1 -> 400 shares
        # $20 from Level 2 -> $20 / $0.25 = 80 shares
        # Total shares = 480
        # Avg price = $100 / 480 = $0.208333...
        
        avg_price, shares, cost = MarketSimulator.calculate_vwap(book_side, 100.0)
        
        self.assertAlmostEqual(cost, 100.0)
        self.assertAlmostEqual(shares, 480.0)
        self.assertAlmostEqual(avg_price, 100.0 / 480.0)

    def test_simulate_buy_slippage(self):
        orderbook = {
            'asks': [
                {'price': '0.50', 'size': '10'}, # Only $5 capacity
                {'price': '0.60', 'size': '100'}
            ]
        }
        # Buy $50.
        # $5 from Level 1 -> 10 shares
        # $45 from Level 2 -> 45/0.6 = 75 shares
        # Total shares = 85.
        # Avg Price = 50 / 85 = 0.588...
        # Best Ask = 0.50
        # Slippage = (0.588 / 0.50) - 1 = 17.6%
        
        result = MarketSimulator.simulate_buy(orderbook, 50.0)
        self.assertEqual(result['shares'], 85.0)
        self.assertAlmostEqual(result['avg_price'], 50.0 / 85.0)
        self.assertAlmostEqual(result['best_ask'], 0.50)
        self.assertAlmostEqual(result['slippage'], (50.0/85.0 / 0.50) - 1)

if __name__ == '__main__':
    unittest.main()

import unittest
from matcher import Market

class TestMarket(unittest.TestCase):
    def setUp(self):
        # Create a fresh market instance before each test
        self.market = Market()

    # --- 1. Validation and Edge Cases ---

    def test_invalid_odds(self):
        # Odds must be > 100
        with self.assertRaisesRegex(RuntimeError, "odds must be > 100"):
            self.market.receive_bet(ts=1.0, is_back=True, amount=100, odds=100)
        with self.assertRaises(RuntimeError):
            self.market.receive_bet(ts=1.0, is_back=True, amount=100, odds=99)
        with self.assertRaises(RuntimeError):
            self.market.receive_bet(ts=1.0, is_back=True, amount=100, odds=0)

    def test_invalid_amounts(self):
        # Amount must be >= 100
        with self.assertRaisesRegex(RuntimeError, "amount must be >= 100"):
            self.market.receive_bet(ts=1.0, is_back=True, amount=99, odds=200)
        
        # Amount must be in steps of 50
        with self.assertRaisesRegex(RuntimeError, "must be in steps of 50"):
            self.market.receive_bet(ts=1.0, is_back=True, amount=125, odds=200)
        with self.assertRaises(RuntimeError):
            self.market.receive_bet(ts=1.0, is_back=True, amount=101, odds=200)

    # --- 2. Queue Priority (Price/Time/ID) ---

    def test_back_queue_ordering(self):
        # Back bets prioritize LOWEST odds first. 
        # If odds tie, oldest TS first.
        self.market.receive_bet(ts=1.0, is_back=True, amount=100, odds=200) # ID 1 (Lowest odds)
        self.market.receive_bet(ts=2.0, is_back=True, amount=100, odds=210) # ID 2 
        self.market.receive_bet(ts=3.0, is_back=True, amount=100, odds=210) # ID 3

        queue = self.market.get_queue_back(3)
        self.assertEqual([b[0] for b in queue], [1, 2, 3])

    def test_lay_queue_ordering(self):
        # Lay bets prioritize HIGHEST odds first.
        self.market.receive_bet(ts=3.0, is_back=False, amount=100, odds=200) # ID 1
        self.market.receive_bet(ts=1.0, is_back=False, amount=100, odds=210) # ID 2 (Highest odds)
        self.market.receive_bet(ts=2.0, is_back=False, amount=100, odds=200) # ID 3 

        queue = self.market.get_queue_lay(3)
        self.assertEqual([b[0] for b in queue], [2, 1, 3])

    # --- 3. Matching Logic & Price Improvement ---

    def test_no_match_spread(self):
        # Back asks for 200, Lay offers 210. Cross.
        match_back = self.market.receive_bet(ts=1.0, is_back=True, amount=100, odds=200)
        match_lay = self.market.receive_bet(ts=2.0, is_back=False, amount=100, odds=210)
        
        self.assertEqual(match_back, {})
        self.assertEqual(match_lay, {200:100})
        self.assertEqual(self.market.get_num_matched(), 1)
        self.assertEqual(self.market.get_fair_odds(), 0)

    def test_exact_match(self):
        self.market.receive_bet(ts=1.0, is_back=False, amount=150, odds=200)
        matches = self.market.receive_bet(ts=2.0, is_back=True, amount=150, odds=200)
        
        self.assertEqual(matches, {200: 150})
        self.assertEqual(len(self.market.get_queue_back()), 0)
        self.assertEqual(len(self.market.get_queue_lay()), 0)
        self.assertEqual(self.market.get_num_matched(), 1)

    def test_partial_match_incoming_larger(self):
        # Resting lay bet of 100
        self.market.receive_bet(ts=1.0, is_back=False, amount=100, odds=200)
        
        # Incoming back bet of 250
        matches = self.market.receive_bet(ts=2.0, is_back=True, amount=250, odds=200)
        
        # Should match 100 at 200, and leave 150 resting on the back queue
        self.assertEqual(matches, {200: 100})
        self.assertEqual(len(self.market.get_queue_lay()), 0)
        
        back_queue = self.market.get_queue_back()
        self.assertEqual(len(back_queue), 1)
        self.assertEqual(back_queue[0][3], 150) # amount remaining

    def test_partial_match_resting_larger(self):
        # Resting lay bet of 300
        self.market.receive_bet(ts=1.0, is_back=False, amount=300, odds=200)
        
        # Incoming back bet of 100
        matches = self.market.receive_bet(ts=2.0, is_back=True, amount=100, odds=200)
        
        # Should match 100 at 200, resting lay should be reduced to 200
        self.assertEqual(matches, {200: 100})
        self.assertEqual(len(self.market.get_queue_back()), 0)
        
        lay_queue = self.market.get_queue_lay()
        self.assertEqual(len(lay_queue), 1)
        self.assertEqual(lay_queue[0][3], 200) # amount remaining

    def test_walk_the_book_multiple_price_levels(self):
        # Resting lays at various levels
        self.market.receive_bet(ts=1.0, is_back=False, amount=100, odds=200) 
        self.market.receive_bet(ts=2.0, is_back=False, amount=100, odds=210) 
        self.market.receive_bet(ts=3.0, is_back=False, amount=100, odds=220) # best lay
        
        # Incoming back bet for 250, willing to accept down to odds 215
        # It should sweep the 220, leave 150 unmatched (because 210 < 215)
        matches = self.market.receive_bet(ts=4.0, is_back=True, amount=250, odds=215)
        
        self.assertEqual(matches, {220: 100})
        
        # Check queues
        lay_queue = self.market.get_queue_lay()
        self.assertEqual(len(lay_queue), 2)
        
        back_queue = self.market.get_queue_back()
        self.assertEqual(len(back_queue), 1)
        self.assertEqual(back_queue[0][3], 150)

    # --- 4. Liquidity & Math Edge Cases ---

    def test_liability_calculation(self):
        # Lay bet liability: (odds - 100) * stake // 100
        self.market.receive_bet(ts=1.0, is_back=False, amount=100, odds=250)
        # 150 liability
        self.assertEqual(self.market.odds_liq_dict_lay[250], 150)

        self.market.receive_bet(ts=2.0, is_back=False, amount=150, odds=300)
        # (300 - 100) * 150 // 100 = 200 * 150 // 100 = 300 liability
        self.assertEqual(self.market.odds_liq_dict_lay[300], 300)

    def test_total_liquidity_update(self):
        self.assertEqual(self.market.get_total_liquidity(), 0)

        self.market.receive_bet(ts=1.0, is_back=True, amount=100, odds=300) # +100 back liq
        self.assertEqual(self.market.get_total_liquidity(), 100)

        self.market.receive_bet(ts=2.0, is_back=False, amount=100, odds=250) # +150 lay liq
        self.assertEqual(self.market.get_total_liquidity(), 250)

        # Match occurs
        self.market.receive_bet(ts=3.0, is_back=True, amount=100, odds=250) 
        # The new match creates MA liquidity: 100 (stake) + 150 (liability) = 250
        # The resting lay liability (150) is consumed (subtracted).
        # Total liquidity should now reflect the initial 100 back liq + 250 MA liq = 350
        self.assertEqual(self.market.get_total_liquidity(), 350)

    def test_get_liquidity_data_empty(self):
        # Should handle completely empty order book gracefully
        odds_range, lay_liq, back_liq, ma_liq = self.market.get_liquidity_data()
        self.assertEqual(odds_range, [0])
        self.assertEqual(lay_liq, [0])
        self.assertEqual(back_liq, [0])
        self.assertEqual(ma_liq, [0])

    def test_reset(self):
        self.market.receive_bet(ts=1.0, is_back=True, amount=100, odds=200)
        self.market.reset()
        
        self.assertEqual(len(self.market.bet_queue_back), 0)
        self.assertEqual(self.market.next_id, 1)
        self.assertEqual(self.market.get_total_liquidity(), 0)

if __name__ == '__main__':
    unittest.main()
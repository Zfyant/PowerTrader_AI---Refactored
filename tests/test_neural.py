import unittest
from src.core.neural import NeuralEngine

class TestNeuralEngine(unittest.TestCase):
    def test_calculate_difference(self):
        # 100 and 110. Avg 105. Diff 10. (10/105)*100 = 9.52...
        d = NeuralEngine.calculate_difference(100, 110)
        self.assertAlmostEqual(d, 9.5238, places=4)
        
        # 0 and 0
        self.assertEqual(NeuralEngine.calculate_difference(0, 0), 0.0)

    def test_parse_memory_entry(self):
        # Format: Pattern {} Move {} High {} Low
        entry = "1.0 2.0 3.0 {} 500.0 {} 600.0 {} 700.0"
        pat, move, h, l = NeuralEngine.parse_memory_entry(entry)
        self.assertEqual(pat, [1.0, 2.0, 3.0])
        self.assertEqual(move, 5.0) # 500/100
        self.assertEqual(h, 6.0) # 600/100
        self.assertEqual(l, 7.0) # 700/100

    def test_find_matches(self):
        current = [10.0, 11.0]
        # Memory matches exactly
        # Pattern {} Move(500.0) {} High(500.0) {} Low(500.0)
        mem_list = ["10.0 11.0 {} 500.0 {} 500.0 {} 500.0"]
        w_list = ["1.0"]
        h_list = ["1.0"]
        l_list = ["1.0"]
        
        result = NeuralEngine.find_matches(current, mem_list, w_list, h_list, l_list, threshold=1.0)
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['matches'][0], 0)
        self.assertAlmostEqual(result['prediction'][0], 5.0) # 5.0 * 1.0

    def test_update_weights(self):
        # Match details from above
        match_details = [{
            'index': 0,
            'weight': 1.0,
            'high_weight': 1.0,
            'low_weight': 1.0,
            'predicted_move': 0.05, # Decimal (5%)
            'predicted_high': 0.05,
            'predicted_low': 0.05
        }]
        
        # update_weights logic:
        # pred_move_pct = detail['predicted_move'] * 100 -> 5.0
        # tol = abs(5.0 * 0.1) = 0.5
        # pred range: 4.5 to 5.5
        
        # Case 1: Actual 6.0% (Increase)
        updates = NeuralEngine.update_weights(
            match_details, 
            actual_move_pct=6.0, 
            actual_high_pct=6.0, 
            actual_low_pct=6.0,
            current_weights=["1.0"],
            current_high_weights=["1.0"],
            current_low_weights=["1.0"]
        )
        self.assertEqual(updates[0]['weight'], 1.25)
        
        # Case 2: Actual 4.0% (Decrease)
        updates_down = NeuralEngine.update_weights(
            match_details, 
            actual_move_pct=4.0, 
            actual_high_pct=4.0, 
            actual_low_pct=4.0,
            current_weights=["1.0"],
            current_high_weights=["1.0"],
            current_low_weights=["1.0"]
        )
        self.assertEqual(updates_down[0]['weight'], 0.75)

if __name__ == '__main__':
    unittest.main()

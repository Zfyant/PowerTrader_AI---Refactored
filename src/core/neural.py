import math
import statistics
from typing import List, Dict, Any, Tuple, Optional

class NeuralEngine:
    """
    Pure logic engine for PowerTrader's pattern matching algorithm.
    Decouples the math from the file I/O and state management.
    """

    @staticmethod
    def calculate_difference(val1: float, val2: float) -> float:
        """
        Calculates the percentage difference between two values using the average method.
        Matches legacy logic: abs((abs(v1-v2)/((v1+v2)/2))*100)
        """
        if val1 + val2 == 0.0:
            return 0.0
        try:
            return abs((abs(val1 - val2) / ((val1 + val2) / 2)) * 100)
        except ZeroDivisionError:
            return 0.0

    @staticmethod
    def parse_memory_entry(entry: str) -> Tuple[List[float], float, float, float]:
        """
        Parses a memory string into (pattern, move, high_diff, low_diff).
        Format: "val1 val2 val3{}move{}high_diff{}low_diff"
        Returns values as DECIMALS (legacy stored as percents, e.g. 5.0 -> 0.05).
        """
        try:
            parts = entry.split('{}')
            # Part 0: Pattern (space separated)
            pattern_str = parts[0].strip()
            pattern = [float(x) for x in pattern_str.split(' ') if x]
            
            # Part 1: Move (Legacy stored as percent, e.g. 5.0)
            move = 0.0
            if len(parts) > 1:
                move = float(parts[1].strip()) / 100.0
            
            # Part 2: High Diff
            high = 0.0
            if len(parts) > 2:
                high = float(parts[2].strip()) / 100.0
                
            # Part 3: Low Diff
            low = 0.0
            if len(parts) > 3:
                low = float(parts[3].strip()) / 100.0
                
            return pattern, move, high, low
        except (ValueError, IndexError):
            return [], 0.0, 0.0, 0.0

    @staticmethod
    def find_matches(
        current_pattern: List[float],
        memory_list: List[str],
        weight_list: List[str], # Weights are strings in file
        high_weight_list: List[str],
        low_weight_list: List[str],
        threshold: float = 1.0
    ) -> Dict[str, Any]:
        """
        Scans memory for matches.
        """
        matches = []
        perfect_diffs = []
        
        # Prediction accumulators
        moves = []
        high_moves = []
        low_moves = []
        
        # Track best diff for fallback
        min_diff = float('inf')
        closest_index = -1
        
        for i, entry in enumerate(memory_list):
            if not entry.strip(): continue
            
            mem_pattern, mem_move, mem_high, mem_low = NeuralEngine.parse_memory_entry(entry)
            
            if len(mem_pattern) != len(current_pattern):
                continue
                
            # Calculate Similarity
            diffs = []
            for j, val in enumerate(current_pattern):
                d = NeuralEngine.calculate_difference(val, mem_pattern[j])
                diffs.append(d)
                
            if not diffs: continue
            
            diff_avg = sum(diffs) / len(diffs)
            
            # Track global minimum
            if diff_avg < min_diff:
                min_diff = diff_avg
                closest_index = i
            
            # Check Threshold
            if diff_avg <= threshold:
                # MATCH FOUND
                matches.append(i)
                perfect_diffs.append(diff_avg)
                
                # Get weights (safe parsing)
                w = float(weight_list[i]) if i < len(weight_list) else 1.0
                hw = float(high_weight_list[i]) if i < len(high_weight_list) else 1.0
                lw = float(low_weight_list[i]) if i < len(low_weight_list) else 1.0
                
                # Weighted predictions
                moves.append(mem_move * w)
                high_moves.append(mem_high * hw)
                low_moves.append(mem_low * lw)

        # Calculate Final Predictions
        final_move = 0.0
        final_high = 0.0
        final_low = 0.0
        is_new = False
        
        if matches:
            # Average of all matches
            if moves: final_move = sum(moves) / len(moves)
            if high_moves: final_high = sum(high_moves) / len(high_moves)
            if low_moves: final_low = sum(low_moves) / len(low_moves)
        else:
            is_new = True
            
        return {
            "matches": matches,
            "prediction": (final_move, final_high, final_low),
            "is_new_memory": is_new,
            "closest_match_index": closest_index,
            "closest_match_diff": min_diff,
            "match_details": [
                {
                    "index": idx,
                    "weight": float(weight_list[idx]) if idx < len(weight_list) else 1.0,
                    "high_weight": float(high_weight_list[idx]) if idx < len(high_weight_list) else 1.0,
                    "low_weight": float(low_weight_list[idx]) if idx < len(low_weight_list) else 1.0,
                    "predicted_move": moves[k], # Weighted
                    "predicted_high": high_moves[k],
                    "predicted_low": low_moves[k]
                }
                for k, idx in enumerate(matches)
            ]
        }


    @staticmethod
    def update_weights(
        match_details: List[Dict[str, Any]],
        actual_move_pct: float,
        actual_high_pct: float,
        actual_low_pct: float,
        current_weights: List[str],
        current_high_weights: List[str],
        current_low_weights: List[str]
    ) -> Dict[int, Dict[str, float]]:
        """
        Calculates new weights based on prediction accuracy.
        Returns a dict of {index: {'weight': new_w, 'high': new_h, 'low': new_l}}
        """
        updates = {}
        
        for detail in match_details:
            idx = detail['index']
            
            # Legacy Logic:
            # var3 = moves[indy] * 100  (legacy 'moves' was decimal * weight, so *100 makes it percent * weight)
            # Wait, if memory stores decimal (0.05), and we multiply by weight (1.0) -> 0.05
            # Then * 100 -> 5.0.
            # 'actual_move_pct' should be 5.0.
            
            # But detail['predicted_move'] is (val * weight).
            # So predicted_val_pct = detail['predicted_move'] * 100
            
            pred_move_pct = detail['predicted_move'] * 100
            pred_high_pct = detail['predicted_high'] * 100
            pred_low_pct = detail['predicted_low'] * 100
            
            w = detail['weight']
            hw = detail['high_weight']
            lw = detail['low_weight']
            
            # --- Main Weight Update ---
            # if actual > predicted + 10%: increase weight
            # if actual < predicted - 10%: decrease weight
            # Tolerance is 10% of the PREDICTED value (var3 * 0.1)
            
            tol = abs(pred_move_pct * 0.1)
            if actual_move_pct > pred_move_pct + tol:
                w += 0.25
            elif actual_move_pct < pred_move_pct - tol:
                w -= 0.25
                
            # --- High Weight Update ---
            h_tol = abs(pred_high_pct * 0.1)
            if actual_high_pct > pred_high_pct + h_tol:
                hw += 0.25
            elif actual_high_pct < pred_high_pct - h_tol:
                hw -= 0.25
                
            # --- Low Weight Update ---
            l_tol = abs(pred_low_pct * 0.1)
            # Legacy logic for low is inverted? 
            # "if low_perc_diff_now_actual < low_var3-(low_var3*0.1): low_new_weight = low_move_weights[indy] + 0.25"
            # It rewards being LOWER than predicted low? Or implies "Safety"?
            # Legacy: if actual < predicted_low - tol: INCREASE weight.
            # This means if the price went EVEN LOWER than we thought, we want to listen to this memory MORE?
            # Or is it "this memory predicted a low drop, and it dropped MORE, so it was RIGHT about the direction"?
            # Let's stick to legacy exactly.
            if actual_low_pct < pred_low_pct - l_tol:
                lw += 0.25
            elif actual_low_pct > pred_low_pct + l_tol:
                lw -= 0.25
                
            # Clamp
            w = max(-2.0, min(2.0, w))
            hw = max(0.0, min(2.0, hw))
            lw = max(0.0, min(2.0, lw))
            
            updates[idx] = {'weight': w, 'high': hw, 'low': lw}
            
        return updates

    @staticmethod
    def format_memory_entry(pattern: List[float], move_pct: float, high_pct: float, low_pct: float) -> str:
        """
        Formats a new memory string.
        """
        # Legacy format: "val1 val2 ... {} move {} high {} low"
        # Note: move/high/low are stored as raw decimals in string?
        # In parse: float(parts[1].strip()) / 100.0
        # So they are stored as PERCENT * 100? No.
        # "parts[1]" is read as string.
        # If legacy code writes: "str(perc_diff_now_actual)" where perc_diff is e.g. 5.0.
        # Then parse reads "5.0" and divides by 100 -> 0.05.
        # So we should store the Percentage Value (e.g. 5.0).
        
        pat_str = " ".join([str(x) for x in pattern])
        return f"{pat_str} {{}} {move_pct} {{}} {high_pct} {{}} {low_pct}"

"""
[src/core/trainer.py]
---------------------
The 'Trainer' module is the dedicated learning engine of PowerTrader AI.

Responsibilities:
1.  **Data Acquisition**: Fetches historical market data (Klines/Candles) from the KuCoin API.
2.  **Pattern Recognition Training**:
    -   Iterates through historical data using a sliding window.
    -   Identifies "patterns" (candle body size, wicks).
    -   Correlates patterns with subsequent price movements (High/Low outcomes).
3.  **Memory Persistence**:
    -   Updates the "Neural Memory" files (`memories_*.txt`, `memory_weights_*.txt`).
    -   These files serve as the "brain" that the `Thinker` uses to predict future movements.

Refactoring Note:
-   This module replaces the legacy `pt_trainer.py`.
-   It has been decoupled from the GUI logic. The GUI (in `src/ui/app.py`) now launches this class in a background thread.
-   It uses `FileManager` for safe, atomic file writes to prevent data corruption.
"""

import time
import json
import sys
import os
from typing import List, Dict, Any

from kucoin.client import Market
from src.core.neural import NeuralEngine
from src.utils.file_manager import FileManager
from src.config.settings import DEFAULT_SETTINGS

class Trainer:
    """
    Manages the machine learning training lifecycle for crypto assets.
    
    The Trainer builds the "knowledge base" for the AI. It does not trade; it only learns.
    It runs independently for each coin and updates the shared memory files on disk.
    
    Attributes:
        settings (dict): Global application settings.
        market (Market): KuCoin API client for fetching public historical data.
        tf_choices (list): The list of timeframes to train (e.g., '1hour', '4hour').
        status_file (str): Path to the JSON file where training progress is reported for the UI.
        stop_requested (bool): Flag to allow graceful interruption of the training loop.
    """

    def __init__(self):
        """Initializes the Trainer with API clients and default settings."""
        self.settings = DEFAULT_SETTINGS
        self.market = Market(url='https://api.kucoin.com')
        self.tf_choices = ['1hour', '2hour', '4hour', '8hour', '12hour', '1day', '1week']
        
        # Map timeframe names to minutes (for potential future calculation)
        self.tf_minutes = {
            '1hour': 60, '2hour': 120, '4hour': 240, '8hour': 480, 
            '12hour': 720, '1day': 1440, '1week': 10080
        }
        
        # The UI watches this file to update the progress bar
        self.status_file = os.path.join(FileManager.BASE_DIR, "trainer_status.json")
        self.stop_requested = False

    def _update_status(self, coin: str, state: str, progress: float = 0.0, tf: str = ""):
        """
        Writes the current training status to a JSON file.
        
        Args:
            coin (str): The coin being trained.
            state (str): Current state (e.g., "STARTING", "TRAINING", "FINISHED").
            progress (float): Percentage complete (0.0 to 100.0).
            tf (str): The specific timeframe currently being processed.
        """
        data = {
            "coin": coin,
            "state": state,
            "progress": progress,
            "current_tf": tf,
            "timestamp": time.time()
        }
        try:
            with open(self.status_file, 'w') as f:
                json.dump(data, f)
        except:
            pass

    def _load_memories(self, coin: str, tf: str) -> Dict[str, List[Any]]:
        """
        Loads existing neural memories from disk for a specific coin and timeframe.
        
        Args:
            coin (str): Coin symbol.
            tf (str): Timeframe (e.g., '1hour').
            
        Returns:
            Dict: A dictionary containing lists of memories and their weights.
        """
        # Note: FileManager.read_text handles coin folder paths automatically
        m_str = FileManager.read_text(coin, f"memories_{tf}.txt")
        w_str = FileManager.read_text(coin, f"memory_weights_{tf}.txt")
        hw_str = FileManager.read_text(coin, f"memory_weights_high_{tf}.txt")
        lw_str = FileManager.read_text(coin, f"memory_weights_low_{tf}.txt")

        # Parse using legacy delimiters (tilde for memories, space for weights)
        # The .replace() calls clean up artifacts from legacy file formats.
        return {
            "memories": m_str.replace("'", "").replace(',', '').replace('"', '').replace(']', '').replace('[', '').split('~') if m_str else [],
            "weights": w_str.replace("'", "").replace(',', '').replace('"', '').replace(']', '').replace('[', '').split(' ') if w_str else [],
            "high_weights": hw_str.replace("'", "").replace(',', '').replace('"', '').replace(']', '').replace('[', '').split(' ') if hw_str else [],
            "low_weights": lw_str.replace("'", "").replace(',', '').replace('"', '').replace(']', '').replace('[', '').split(' ') if lw_str else []
        }

    def _save_memories(self, coin: str, tf: str, data: Dict[str, List[Any]]):
        """
        Persists the updated memories back to disk.
        
        Args:
            coin (str): Coin symbol.
            tf (str): Timeframe.
            data (Dict): The dictionary of lists to save.
        """
        # Filter out empty strings to prevent file corruption
        m_list = [str(x) for x in data["memories"] if str(x).strip()]
        w_list = [str(x) for x in data["weights"] if str(x).strip()]
        hw_list = [str(x) for x in data["high_weights"] if str(x).strip()]
        lw_list = [str(x) for x in data["low_weights"] if str(x).strip()]

        # Use FileManager for atomic writes (safe against crashes)
        FileManager.write_text(coin, f"memories_{tf}.txt", "~".join(m_list))
        FileManager.write_text(coin, f"memory_weights_{tf}.txt", " ".join(w_list))
        FileManager.write_text(coin, f"memory_weights_high_{tf}.txt", " ".join(hw_list))
        FileManager.write_text(coin, f"memory_weights_low_{tf}.txt", " ".join(lw_list))

    def train_coin(self, coin: str):
        """
        Executes the full training lifecycle for a single coin.
        
        This is the core logic of the Trainer. It follows these steps:
        1.  Initializes the status.
        2.  Iterates through every timeframe (1h -> 1w).
        3.  Fetches historical candle data from KuCoin.
        4.  Runs the Neural Learning Loop:
            -   For each historical candle, it treats it as a "pattern".
            -   It checks if this pattern already exists in memory.
            -   If YES: It updates the weights based on the actual outcome (prediction accuracy).
            -   If NO: It creates a new memory entry.
        5.  Saves the updated "brain" to disk.
        
        Args:
            coin (str): The symbol to train (e.g., 'BTC').
        """
        print(f"Starting training for {coin}...")
        self._update_status(coin, "STARTING")
        
        # Ensure the coin's data folder exists
        FileManager.ensure_coin_folder(coin)
        
        # 1. Loop through all defined Timeframes
        for i, tf in enumerate(self.tf_choices):
            if self.stop_requested: break
            
            print(f"  Processing {tf}...")
            # Update UI progress bar
            self._update_status(coin, "TRAINING", progress=(i / len(self.tf_choices)) * 100, tf=tf)
            
            # 2. Fetch Historical Data
            # We fetch a chunk of history to learn from.
            history = self._fetch_full_history(coin, tf)
            if not history:
                print(f"    No history found for {tf}")
                continue
                
            # 3. Load Existing Memories (The "Brain")
            mem_data = self._load_memories(coin, tf)
            
            # 4. Training Loop (Sliding Window over History)
            # We pre-calculate percentage changes to optimize the loop.
            changes = []
            high_changes = []
            low_changes = []
            
            for kline in history:
                # KuCoin Kline: [time, open, close, high, low, ...]
                o = float(kline[1])
                c = float(kline[2])
                h = float(kline[3])
                l = float(kline[4])
                
                # Avoid division by zero
                if o == 0: o = 0.000001
                
                # Calculate percentage moves relative to Open
                change = 100 * ((c - o) / o)
                h_change = 100 * ((h - o) / o)
                l_change = 100 * ((l - o) / o)
                
                changes.append(change)
                high_changes.append(h_change)
                low_changes.append(l_change)
            
            # Threshold for pattern matching (Legacy default = 1.0)
            threshold = 1.0
            
            # Iterate through the pre-calculated history
            for j in range(len(changes)):
                # The "Pattern" is simply the body size (%) of the candle
                pat = [changes[j]]
                
                # The "Outcome" is the move itself, plus the High/Low wicks
                move = changes[j]
                high = high_changes[j]
                low = low_changes[j]
                
                # A. Find similar patterns in memory
                result = NeuralEngine.find_matches(
                    pat, 
                    mem_data["memories"], 
                    mem_data["weights"], 
                    mem_data["high_weights"], 
                    mem_data["low_weights"], 
                    threshold
                )
                
                if result["matches"]:
                    # B. Update Weights (Reinforcement Learning)
                    # If we've seen this pattern before, we refine our expectation of the High/Low
                    updates = NeuralEngine.update_weights(
                        result["match_details"],
                        move, high, low,
                        mem_data["weights"], mem_data["high_weights"], mem_data["low_weights"]
                    )
                    
                    # Apply the updates to the in-memory lists
                    for idx, vals in updates.items():
                        if idx < len(mem_data["weights"]):
                            mem_data["weights"][idx] = str(vals['weight'])
                            mem_data["high_weights"][idx] = str(vals['high'])
                            mem_data["low_weights"][idx] = str(vals['low'])
                else:
                    # C. Create New Memory
                    # If this is a novel pattern, add it to the brain
                    new_entry = NeuralEngine.format_memory_entry(pat, move, high, low)
                    
                    mem_data["memories"].append(new_entry)
                    # Initialize weights to 1.0
                    mem_data["weights"].append("1.0")
                    mem_data["high_weights"].append("1.0")
                    mem_data["low_weights"].append("1.0")
            
            # Save the brain after finishing this timeframe
            self._save_memories(coin, tf, mem_data)
            
        # 5. Finalize
        self._update_status(coin, "FINISHED", progress=100.0)
        print(f"Training finished for {coin}.")

    def _fetch_full_history(self, coin: str, tf: str) -> List[List[Any]]:
        """
        Fetches historical candle data from KuCoin.
        
        Args:
            coin (str): Coin symbol.
            tf (str): Timeframe.
            
        Returns:
            List[List]: List of klines [time, open, close, high, low, ...].
        """
        symbol = f"{coin}-USDT"
        try:
            # Fetch last 1500 candles (KuCoin limit per request)
            # This provides a reasonable dataset for "refreshing" the memory.
            klines = self.market.get_kline(symbol, tf)
            if klines:
                # KuCoin returns newest first. We reverse to oldest first for logical training flow.
                return klines[::-1] 
        except Exception as e:
            print(f"Error fetching history for {coin} {tf}: {e}")
            return []
        return []

if __name__ == "__main__":
    # CLI Entry Point
    # Allows running the trainer directly: `python -m src.core.trainer BTC`
    if len(sys.argv) > 1:
        coin = sys.argv[1]
        trainer = Trainer()
        trainer.train_coin(coin)

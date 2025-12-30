import sys
import os
import traceback

# Ensure the directory containing this script is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

print(f"Running from: {os.getcwd()}")
print(f"Script dir: {script_dir}")
print(f"Sys path[0]: {sys.path[0]}")
print(f"Sys path[-1]: {sys.path[-1]}")

def test_core_init():
    print("Testing Core Module Initialization...")
    
    # 1. Trainer
    try:
        print("\n--- Initializing Trainer ---")
        from src.core.trainer import Trainer
        # Trainer connects to Market(url='...') which usually doesn't require keys for public data
        t = Trainer()
        print("✅ Trainer initialized successfully.")
    except Exception as e:
        print(f"❌ Trainer Init Failed: {e}")
        traceback.print_exc()
        
    # 2. Thinker
    try:
        print("\n--- Initializing Thinker ---")
        from src.core.thinker import Thinker
        th = Thinker()
        print("✅ Thinker initialized successfully.")
    except Exception as e:
        print(f"❌ Thinker Init Failed: {e}")
        traceback.print_exc()

    # 3. Trader
    try:
        print("\n--- Initializing Trader ---")
        from src.core.trader import Trader
        # Trader might need keys if it inits User/Trade clients.
        # Check if it fails on missing keys or network.
        tr = Trader()
        print("✅ Trader initialized successfully.")
    except Exception as e:
        print(f"❌ Trader Init Failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_core_init()

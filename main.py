import threading
import time
import os
import sys
import tkinter as tk
from src.ui.app import PowerTraderApp
from src.core.trader import Trader
from src.core.thinker import Thinker
# Trainer is launched on-demand by the UI, so we don't start it here.
# from src.core.trainer import Trainer 

def run_trader():
    """
    Wrapper to run the Trader loop in a separate thread.
    Catches top-level exceptions to prevent thread silent failure.
    """
    try:
        trader = Trader()
        trader.run()
    except Exception as e:
        print(f"Trader Process Error: {e}")

def run_thinker():
    """
    Wrapper to run the Thinker loop in a separate thread.
    Catches top-level exceptions to prevent thread silent failure.
    """
    try:
        thinker = Thinker()
        thinker.run()
    except Exception as e:
        print(f"Thinker Process Error: {e}")

if __name__ == "__main__":
    """
    Main Entry Point for PowerTrader AI.
    
    Architecture:
    1.  **Main Thread**: Runs the Tkinter GUI (PowerTraderApp).
    2.  **Trader Thread**: Runs the execution logic (buying/selling/DCA).
    3.  **Thinker Thread**: Runs the signal generation logic (market monitoring).
    4.  **Trainer Thread**: (Optional) Spawned by the GUI when user requests model training.
    
    The background threads are set as `daemon=True`, ensuring they automatically
    terminate when the main GUI window is closed.
    """
    print("Starting PowerTrader AI Modular System...")
    
    # 1. Start Background Services
    # We use daemon threads so they die when the GUI closes
    trader_thread = threading.Thread(target=run_trader, daemon=True)
    trader_thread.start()
    print(" -> Trader module started.")
    
    thinker_thread = threading.Thread(target=run_thinker, daemon=True)
    thinker_thread.start()
    print(" -> Thinker module started.")
    
    # 2. Start GUI (Main Thread)
    # The GUI must run on the main thread due to OS window manager constraints.
    try:
        root = tk.Tk()
        app = PowerTraderApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        print(" -> GUI initializing...")
        root.mainloop()
    except KeyboardInterrupt:
        print("\nShutdown requested via KeyboardInterrupt.")
        sys.exit(0)
    except Exception as e:
        print(f"Critical Application Error: {e}")
        sys.exit(1)

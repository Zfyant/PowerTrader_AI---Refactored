"""
[src/ui/app.py]
---------------
The 'PowerTraderApp' is the graphical user interface (GUI) entry point for PowerTrader.
It serves as the 'Hub' (replacing the legacy `pt_hub.py`) that brings all components together.

Responsibilities:
1.  **Visualization**: Displays real-time neural signals, price charts, and account history.
2.  **Control**: Allows the user to start/stop training and monitor system status.
3.  **Integration**: Connects the `Trainer` (backend learning) with the UI via threading.
4.  **Data Management**: Periodically refreshes data from the file system (Hub Data) to keep the UI in sync with the `Thinker` and `Trader`.

Architecture:
-   Built using `tkinter` (Python's standard GUI library).
-   Uses a polling mechanism (`_update_loop`) to check for file updates rather than complex inter-process communication (IPC).
    -   This allows the `Trader` and `Thinker` to run as separate processes (or threads) that simply write to JSON files.
    -   The UI reads these JSON files to update the display.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import time
import threading
from typing import Dict, Any, Optional

from src.ui.styles.theme import Theme
from src.ui.components.tiles import NeuralSignalTile, WrapFrame
from src.ui.components.chart import CandleChart
from src.ui.components.account_history import AccountHistoryChart
from src.ui.data import CandleFetcher
from src.utils.file_manager import FileManager
from src.config.settings import DEFAULT_SETTINGS
from src.core.trainer import Trainer


class PowerTraderApp:
    """
    The main application class for the PowerTrader Neural Hub.
    
    This class initializes the main window, sets up the layout, and manages the
    application lifecycle (startup, update loop, shutdown).
    
    **Architecture Overview:**
    The App acts as a passive viewer and active controller:
    -   **Passive Viewer**: It reads `trader_status.json` and `trainer_status.json` every second to update the UI. It does NOT calculate signals itself.
    -   **Active Controller**: It launches the `Trainer` in a background thread when the user requests a model retrain.
    
    Attributes:
        root (tk.Tk): The root Tkinter window.
        running (bool): Flag to control the update loop. If False, the loop stops.
        coins (list): List of cryptocurrency symbols to track (e.g., ['BTC', 'ETH']).
        settings (dict): Global application settings loaded from config.
        training_active (bool): Semaphore to prevent multiple simultaneous training sessions.
        
        hub_dir (str): Directory for shared data (signals, status).
        trader_status_path (str): Path to the JSON file where the Trader writes its state.
        trainer_status_path (str): Path to the JSON file where the Trainer writes progress.
        account_hist_path (str): Path to account value history (JSONL).
        trade_hist_path (str): Path to trade execution history (JSONL).
        
        fetcher (CandleFetcher): Helper to get market data for charts.
        tiles (Dict[str, NeuralSignalTile]): Map of coin symbol -> Tile widget.
        charts (Dict[str, CandleChart]): Map of coin symbol -> Chart widget.
    """

    def __init__(self, root: tk.Tk):
        """
        Initialize the PowerTrader GUI.
        
        Args:
            root (tk.Tk): The main window handle passed from `main.py`.
        """
        self.root = root
        self.root.title("PowerTrader AI - Neural Hub")
        self.root.geometry("1400x900")
        self.root.configure(bg=Theme.DARK_BG)
        
        # Apply Theme to global ttk styles
        self._setup_styles()
        
        # State Management
        self.running = True
        self.coins = DEFAULT_SETTINGS.get("coins", ["BTC", "ETH", "XRP", "BNB", "DOGE"])
        self.settings = DEFAULT_SETTINGS.copy()
        self.training_active = False
        
        # File Paths
        # The Hub reads data that the Core modules (Trader/Thinker) write.
        self.hub_dir = os.path.join(FileManager.BASE_DIR, "hub_data")
        os.makedirs(self.hub_dir, exist_ok=True)
        
        self.trader_status_path = os.path.join(self.hub_dir, "trader_status.json")
        self.trainer_status_path = os.path.join(FileManager.BASE_DIR, "trainer_status.json")
        self.account_hist_path = os.path.join(self.hub_dir, "account_value_history.jsonl")
        self.trade_hist_path = os.path.join(self.hub_dir, "trade_history.jsonl")
        
        # Core Components
        self.fetcher = CandleFetcher()
        self.tiles: Dict[str, NeuralSignalTile] = {}
        
        # Build the Visual Elements
        self._build_ui()
        
        # Start the Data Refresh Loop
        self._start_update_loop()

    def _setup_styles(self):
        """
        Configures the visual theme (colors, fonts) for Tkinter widgets.
        Uses a 'dark mode' palette defined in `src.ui.styles.theme`.
        
        We use the 'clam' theme as a base because it allows for more customization
        of widget colors than the default system themes.
        """
        style = ttk.Style(self.root)
        style.theme_use("clam")
        
        style.configure(".", background=Theme.DARK_BG, foreground=Theme.DARK_FG, font=("Segoe UI", 9))
        style.configure("TFrame", background=Theme.DARK_BG)
        style.configure("TLabel", background=Theme.DARK_BG, foreground=Theme.DARK_FG)
        style.configure("TButton", background=Theme.DARK_PANEL, foreground=Theme.DARK_FG, borderwidth=1)
        style.map("TButton", background=[("active", Theme.DARK_PANEL2)])
        style.configure("TNotebook", background=Theme.DARK_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=Theme.DARK_PANEL, foreground=Theme.DARK_FG, padding=(10, 5))
        style.map("TNotebook.Tab", background=[("selected", Theme.DARK_BG)], foreground=[("selected", Theme.DARK_ACCENT)])
        style.configure("TLabelframe", background=Theme.DARK_BG, bordercolor=Theme.DARK_BORDER)
        style.configure("TLabelframe.Label", background=Theme.DARK_BG, foreground=Theme.DARK_FG)

    def _build_ui(self):
        """
        Constructs the widget hierarchy:
        1. Top Bar: Title and System Status.
        2. Main Split:
           - Left: Neural Signal Tiles (Grid of small summary cards).
           - Right: Detailed Analysis (Charts and Account History).
        """
        # 1. Top Bar (Status & Controls)
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(top_bar, text="PowerTrader AI", font=("Segoe UI", 14, "bold"), foreground=Theme.DARK_ACCENT).pack(side="left")
        
        self.status_label = ttk.Label(top_bar, text="System Status: Initializing...", foreground=Theme.DARK_MUTED)
        self.status_label.pack(side="left", padx=20)
        
        # 2. Main Split (Left: Tiles, Right: Details)
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=10, pady=5)
        
        # --- Left Panel: Signal Tiles ---
        # Displays a grid of cards, one for each coin, showing buy/sell signals.
        left_frame = ttk.LabelFrame(main_paned, text="Neural Signals")
        main_paned.add(left_frame, weight=1)
        
        self.tile_container = WrapFrame(left_frame)
        self.tile_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create a tile for each coin
        for coin in self.coins:
            t = NeuralSignalTile(self.tile_container, coin)
            self.tile_container.add(t, padx=(5,5), pady=(5,5))
            self.tiles[coin] = t
            
        # --- Right Panel: Charts & History ---
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)
        
        # Vertical Split in Right Panel (Top: Charts, Bottom: Account)
        right_paned = ttk.PanedWindow(right_frame, orient="vertical")
        right_paned.pack(fill="both", expand=True)
        
        # A. Chart Notebook (Tabs for each coin)
        self.chart_notebook = ttk.Notebook(right_paned)
        right_paned.add(self.chart_notebook, weight=2)
        
        self.charts: Dict[str, CandleChart] = {}
        for coin in self.coins:
            # Lambda is used to pass current settings dynamically
            chart = CandleChart(self.chart_notebook, self.fetcher, coin, lambda: self.settings, self.trade_hist_path)
            # Hook up the 'Train Model' button on the chart to our handler
            chart.set_train_callback(self._start_training_thread)
            self.chart_notebook.add(chart, text=coin)
            self.charts[coin] = chart
            
        # B. Account History (PnL Graph)
        hist_frame = ttk.Frame(right_paned)
        right_paned.add(hist_frame, weight=1)
        
        self.acc_chart = AccountHistoryChart(hist_frame, self.account_hist_path, self.trade_hist_path)
        self.acc_chart.pack(fill="both", expand=True)

    def _start_training_thread(self, coin: str):
        """
        Initiates the model training process for a specific coin.
        
        This runs in a separate thread to keep the UI responsive.
        It uses a 'training_active' flag to ensure only one training session runs at a time.
        
        Args:
            coin (str): The symbol to train (e.g., 'BTC').
        """
        if self.training_active:
            messagebox.showwarning("Busy", "Training is already in progress.")
            return
            
        if not messagebox.askyesno("Confirm Training", f"Start training model for {coin}?\nThis may take a while."):
            return
            
        self.training_active = True
        
        # Initialize the status file so the UI knows we are starting
        try:
             with open(self.trainer_status_path, 'w') as f:
                 json.dump({"coin": coin, "state": "STARTING", "progress": 0.0, "timestamp": time.time()}, f)
        except Exception as e:
            print(f"Failed to write init status: {e}")
        
        def _run():
            """The actual worker function running in the thread."""
            try:
                # Instantiate Trainer only when needed to save resources
                trainer = Trainer()
                trainer.train_coin(coin)
            except Exception as e:
                print(f"Training Error: {e}")
            finally:
                # Release the lock
                self.training_active = False
                
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _update_loop(self):
        """
        The main heartbeat of the UI.
        
        Scheduled to run every 1000ms (1 second). It calls `_refresh_data`
        to pull the latest state from disk and update widgets.
        
        This recursive `after` call pattern is standard in Tkinter for periodic tasks.
        """
        if not self.running:
            return
            
        try:
            self._refresh_data()
        except Exception as e:
            # We catch all exceptions here to prevent the UI from freezing/crashing
            # due to a single bad read or transient error.
            print(f"UI Update Error: {e}")
            
        # Schedule next update
        self.root.after(1000, self._update_loop)

    def _start_update_loop(self):
        """Kickstarts the update loop."""
        self._update_loop()

    def _refresh_data(self):
        """
        Reads external status files and updates UI components.
        
        1. Reads 'trader_status.json' to update system health and positions.
        2. Reads 'trainer_status.json' to update training progress bars.
        3. Refreshes the currently visible chart.
        """
        # 1. Read Trader Status
        trader_data = {}
        if os.path.exists(self.trader_status_path):
            try:
                with open(self.trader_status_path, 'r', encoding='utf-8') as f:
                    trader_data = json.load(f)
            except: pass
            
        # Update Header Status
        if trader_data:
            ts = trader_data.get("timestamp", 0)
            ago = time.time() - ts
            status_txt = f"System Active (Last Update: {ago:.1f}s ago)"
            # Turn text red if system hasn't updated in > 30 seconds
            self.status_label.config(text=status_txt, foreground=Theme.DARK_FG if ago < 30 else "red")
            
            # Update Account Chart (PnL)
            self.acc_chart.refresh()
            
            # Update Tiles with Positions and Signals
            positions = trader_data.get("positions", {})
            for coin, tile in self.tiles.items():
                pos = positions.get(coin, {})
                
                # In the new architecture, Thinker writes signals to text files.
                # We read them here to update the UI.
                l_sig = self._read_signal(coin, "long_dca_signal.txt")
                s_sig = self._read_signal(coin, "short_dca_signal.txt")
                
                tile.set_values(l_sig, s_sig)
        
        # 2. Update Trainer Status (Progress Bars)
        train_status = {}
        if os.path.exists(self.trainer_status_path):
            try:
                with open(self.trainer_status_path, 'r') as f:
                    train_status = json.load(f)
            except: pass
            
        if train_status:
            t_coin = train_status.get("coin")
            t_state = train_status.get("state", "IDLE")
            t_prog = train_status.get("progress", 0.0)
            
            # Auto-reset "FINISHED" status after 30 seconds
            if t_state == "FINISHED":
                if time.time() - train_status.get("timestamp", 0) > 30:
                    t_state = "IDLE"
                    self.training_active = False 
            
            # Update the specific chart that is training
            for c, chart in self.charts.items():
                if c == t_coin:
                    chart.update_training_status(t_state, t_prog)
                else:
                    # Others show IDLE
                    chart.update_training_status("IDLE")

        # 3. Update Currently Visible Chart
        # We only update the visible chart to save performance.
        try:
            current_tab_idx = self.chart_notebook.index("current")
            current_coin = self.coins[current_tab_idx]
            chart = self.charts.get(current_coin)
            if chart:
                # Provide the chart with the paths to data folders
                coin_folders = {c: FileManager.get_coin_folder(c) for c in self.coins}
                chart.refresh(coin_folders)
        except:
            pass

    def _read_signal(self, coin: str, filename: str) -> float:
        """
        Helper to safely read a signal value from a text file.
        
        Args:
            coin (str): Coin symbol.
            filename (str): Name of the signal file (e.g., 'long_dca_signal.txt').
            
        Returns:
            float: The signal value (0.0 to 1.0), or 0 if file missing/error.
        """
        try:
            path = os.path.join(FileManager.get_coin_folder(coin), filename)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return float(f.read().strip())
        except:
            return 0.0
        return 0.0

    def on_close(self):
        """Handle application shutdown event."""
        self.running = False
        self.root.destroy()

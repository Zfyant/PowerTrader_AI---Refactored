"""
src/ui/components/chart.py

The Visualization Engine of the PowerTrader Neural Hub.
This module handles the embedding of Matplotlib charts within the Tkinter GUI.
It is responsible for:
1.  Fetching Candle Data (via CandleFetcher).
2.  Rendering Candlestick Charts.
3.  Overlaying Neural Bounds (Support/Resistance).
4.  Overlaying Trading Lines (Trailing Stops, DCA levels).
5.  Mapping Historical Trades onto the chart as markers.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, List
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
from matplotlib.transforms import blended_transform_factory
import math
import json
import os

from src.ui.styles.theme import Theme
from src.ui.data import CandleFetcher

class CandleChart(ttk.Frame):
    """
    A Complex Tkinter Widget that wraps a Matplotlib Figure.
    
    This class manages the entire lifecycle of a crypto chart:
    -   Initialization: Sets up the figure, axes, and canvas.
    -   Interaction: Handles timeframe changes and window resizing.
    -   Data Integration: Fetches market data and neural memory files.
    -   Rendering: Draws candlesticks, indicators, and overlays.
    
    Attributes:
        fetcher (CandleFetcher): Reference to the data fetching utility.
        coin (str): The symbol being displayed (e.g., "BTC").
        settings_getter (callable): Function to retrieve global app settings.
        trade_history_path (str): Path to the `trade_history.jsonl` file for plotting executions.
        timeframe_var (tk.StringVar): Bound variable for the timeframe dropdown.
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        fetcher: CandleFetcher,
        coin: str,
        settings_getter,
        trade_history_path: str,
    ):
        """
        Initialize the CandleChart.
        
        Args:
            parent: The parent Tkinter widget.
            fetcher: The data fetcher instance.
            coin: The cryptocurrency symbol.
            settings_getter: A callable that returns the current settings dict.
            trade_history_path: Absolute path to the trade history log file.
        """
        super().__init__(parent)
        self.fetcher = fetcher
        self.coin = coin
        self.settings_getter = settings_getter
        self.trade_history_path = trade_history_path

        self.timeframe_var = tk.StringVar(value=self.settings_getter()["default_timeframe"])

        # Top Control Bar
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=6)

        ttk.Label(top, text=f"{coin} chart").pack(side="left")

        ttk.Label(top, text="Timeframe:").pack(side="left", padx=(12, 4))
        self.tf_combo = ttk.Combobox(
            top,
            textvariable=self.timeframe_var,
            values=self.settings_getter()["timeframes"],
            state="readonly",
            width=10,
        )
        self.tf_combo.pack(side="left")

        # Debounce rapid timeframe changes so redraws don't stack
        self._tf_after_id = None

        def _debounced_tf_change(*_):
            """
            Handle timeframe selection changes with debouncing.
            Prevents UI freezing if the user scrolls through options quickly.
            """
            try:
                if self._tf_after_id:
                    self.after_cancel(self._tf_after_id)
            except Exception:
                pass

            def _do():
                # Ask the hub to refresh charts on the next tick (single refresh)
                try:
                    self.event_generate("<<TimeframeChanged>>", when="tail")
                except Exception:
                    pass

            self._tf_after_id = self.after(120, _do)

        self.tf_combo.bind("<<ComboboxSelected>>", _debounced_tf_change)

        self.neural_status_label = ttk.Label(top, text="Neural: Ready")
        self.neural_status_label.pack(side="left", padx=12)
        
        # Train Button - Launches the Trainer in a background thread
        self.train_btn = ttk.Button(top, text="Train Model", command=self._on_train_click, width=12)
        self.train_btn.pack(side="right", padx=6)
        
        self.train_callback = None

        self.last_update_label = ttk.Label(top, text="Last: N/A")
        self.last_update_label.pack(side="right")

        # Matplotlib Figure Initialization
        self.fig = Figure(figsize=(6.5, 3.5), dpi=100)
        self.fig.patch.set_facecolor(Theme.DARK_BG)

        # Adjust margins to maximize chart area
        self.fig.subplots_adjust(bottom=0.20, right=0.87, top=0.8)

        self.ax = self.fig.add_subplot(111)
        self._apply_dark_chart_style()
        self.ax.set_title(f"{coin}", color=Theme.DARK_FG)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        canvas_w = self.canvas.get_tk_widget()
        canvas_w.configure(bg=Theme.DARK_BG)

        # Remove horizontal padding here so the chart widget truly fills the container.
        canvas_w.pack(fill="both", expand=True, padx=0, pady=(0, 6))

        self._last_canvas_px = (0, 0)
        self._resize_after_id = None

        def _on_canvas_configure(e):
            """
            Handle window resize events.
            Adjusts the Matplotlib figure size to match the Tkinter widget size.
            Includes debouncing to avoid excessive redraws during dragging.
            """
            try:
                w = int(e.width)
                h = int(e.height)
                if w <= 1 or h <= 1:
                    return

                if (w, h) == self._last_canvas_px:
                    return
                self._last_canvas_px = (w, h)

                dpi = float(self.fig.get_dpi() or 100.0)
                self.fig.set_size_inches(w / dpi, h / dpi, forward=True)

                # Debounce redraws during live resize
                if self._resize_after_id:
                    try:
                        self.after_cancel(self._resize_after_id)
                    except Exception:
                        pass
                self._resize_after_id = self.after_idle(self.canvas.draw_idle)
            except Exception:
                pass

        canvas_w.bind("<Configure>", _on_canvas_configure, add="+")

        self._last_refresh = 0.0

    def set_train_callback(self, cb):
        """Register the callback function to be called when 'Train Model' is clicked."""
        self.train_callback = cb
        
    def _on_train_click(self):
        """Internal handler for the train button click."""
        if self.train_callback:
            self.train_callback(self.coin)
            
    def update_training_status(self, status: str, progress: float = 0.0):
        """
        Update the UI based on the training state.
        
        Args:
            status (str): "IDLE", "STARTING", "TRAINING", or "FINISHED".
            progress (float): Completion percentage (0-100).
        """
        if status == "IDLE":
             self.train_btn.config(state="normal", text="Train Model")
             self.neural_status_label.config(text="Neural: Ready")
        elif status == "TRAINING" or status == "STARTING":
             self.train_btn.config(state="disabled", text=f"{int(progress)}%")
             self.neural_status_label.config(text=f"Training... {int(progress)}%")
        elif status == "FINISHED":
             self.train_btn.config(state="normal", text="Train Model")
             self.neural_status_label.config(text="Training Complete")

    def _apply_dark_chart_style(self) -> None:
        """
        Apply the application's dark theme to the Matplotlib axes and figure.
        This must be called after every ax.clear() because clearing resets styles.
        """
        try:
            self.fig.patch.set_facecolor(Theme.DARK_BG)
            self.ax.set_facecolor(Theme.DARK_PANEL)
            self.ax.tick_params(colors=Theme.DARK_FG)
            for spine in self.ax.spines.values():
                spine.set_color(Theme.DARK_BORDER)
            self.ax.grid(True, color=Theme.DARK_BORDER, linewidth=0.6, alpha=0.35)
        except Exception:
            pass

    def refresh(
        self,
        coin_folders: Dict[str, str],
        current_buy_price: Optional[float] = None,
        current_sell_price: Optional[float] = None,
        trail_line: Optional[float] = None,
        dca_line_price: Optional[float] = None,
    ) -> None:
        """
        The Main Render Loop for the Chart.
        
        This method:
        1.  Fetches fresh candle data.
        2.  Reads neural memory files (support/resistance bounds).
        3.  Clears and redraws the chart.
        4.  Overlays price lines (Bid, Ask, Stop, DCA).
        5.  Plots historical trade markers.
        
        Args:
            coin_folders: Dictionary mapping coin symbols to their data directory paths.
            current_buy_price: The current Ask price.
            current_sell_price: The current Bid price.
            trail_line: The active trailing stop price (if any).
            dca_line_price: The active DCA trigger price (if any).
        """

        cfg = self.settings_getter()

        tf = self.timeframe_var.get().strip()
        limit = int(cfg.get("candles_limit", 120))

        # Fetch Data
        candles = self.fetcher.get_klines(self.coin, tf, limit=limit)

        folder = coin_folders.get(self.coin, "")
        low_path = os.path.join(folder, "low_bound_prices.html")
        high_path = os.path.join(folder, "high_bound_prices.html")

        # --- Cached neural reads (per path, by mtime) ---
        # This prevents re-reading files from disk if they haven't changed.
        if not hasattr(self, "_neural_cache"):
            self._neural_cache = {}  # path -> (mtime, value)

        def _cached(path: str, loader, default):
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                return default
            hit = self._neural_cache.get(path)
            if hit and hit[0] == mtime:
                return hit[1]
            v = loader(path)
            self._neural_cache[path] = (mtime, v)
            return v
        
        # Loader for bound lists (strings like "100.5 102.3 ...")
        def _load_floats(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                # content format: "1.1 2.2 3.3"
                return [float(x) for x in content.split()]
            except:
                return []

        low_bounds = _cached(low_path, _load_floats, [])
        high_bounds = _cached(high_path, _load_floats, [])

        # --- Begin Drawing ---
        self.ax.clear()
        self._apply_dark_chart_style()
        self.ax.set_title(f"{self.coin} ({tf})", color=Theme.DARK_FG)

        if not candles:
            self.canvas.draw()
            return

        # Prepare data for plotting
        
        # 1. Candlestick Drawing
        # We manually draw rectangles for bodies and lines for wicks for full control.
        xs = list(range(len(candles)))
        rects = []
        
        for i, c in enumerate(candles):
            o = float(c["open"])
            cl = float(c["close"])
            h = float(c["high"])
            l = float(c["low"])

            up = cl >= o
            candle_color = "green" if up else "red"

            # wick
            self.ax.plot([i, i], [l, h], linewidth=1, color=candle_color)

            # body
            bottom = min(o, cl)
            height = abs(cl - o)
            if height < 1e-12:
                height = 1e-12

            rects.append(
                Rectangle(
                    (i - 0.35, bottom),
                    0.7,
                    height,
                    facecolor=candle_color,
                    edgecolor=candle_color,
                    linewidth=1,
                    alpha=0.9,
                )
            )

        for r in rects:
            self.ax.add_patch(r)

        # 2. Lock Y-Limits (Critical for overlay lines)
        # We calculate limits based on candles so that overlay lines outside the view
        # don't squash the candles into a flat line.
        try:
            y_low = min(float(c["low"]) for c in candles)
            y_high = max(float(c["high"]) for c in candles)
            pad = (y_high - y_low) * 0.03
            if not math.isfinite(pad) or pad <= 0:
                pad = max(abs(y_low) * 0.001, 1e-6)
            self.ax.set_ylim(y_low - pad, y_high + pad)
        except Exception:
            pass

        # 3. Overlay Neural Levels (Support/Resistance)
        for b in low_bounds:
             self.ax.axhline(y=b, color="blue", alpha=0.8, linewidth=1)
        for b in high_bounds:
             self.ax.axhline(y=b, color="orange", alpha=0.8, linewidth=1)

        # 4. Overlay Trading Lines (Trailing Stop, DCA, Bid/Ask)
        if trail_line is not None and float(trail_line) > 0:
            self.ax.axhline(y=float(trail_line), linewidth=1.5, color="green", alpha=0.95)
            
        if dca_line_price is not None and float(dca_line_price) > 0:
            self.ax.axhline(y=float(dca_line_price), linewidth=1.5, color="red", alpha=0.95)
            
        if current_buy_price is not None and float(current_buy_price) > 0:
            self.ax.axhline(y=float(current_buy_price), linewidth=1.5, color="purple", alpha=0.95)
            
        if current_sell_price is not None and float(current_sell_price) > 0:
            self.ax.axhline(y=float(current_sell_price), linewidth=1.5, color="teal", alpha=0.95)

        # 5. Right-Side Labels (Price Tags)
        # Adds floating labels to the right axis for specific price levels.
        # Includes simple collision detection to prevent label overlap.
        try:
            trans = blended_transform_factory(self.ax.transAxes, self.ax.transData)
            used_y: List[float] = []
            y0, y1 = self.ax.get_ylim()
            y_pad = max((y1 - y0) * 0.012, 1e-9)

            def _label_right(y: Optional[float], tag: str, color: str) -> None:
                if y is None: return
                try:
                    yy = float(y)
                    if not math.isfinite(yy) or yy <= 0: return
                except: return

                # Nudge labels to avoid overlap
                for prev in used_y:
                    if abs(yy - prev) < y_pad:
                        yy = prev + y_pad
                used_y.append(yy)

                # Format price helper
                def _fmt(val):
                    if val >= 1000: return f"${val:,.2f}"
                    if val >= 1: return f"${val:,.4f}"
                    return f"${val:,.6f}"

                self.ax.text(
                    1.01, yy, f"{tag} {_fmt(yy)}",
                    transform=trans, ha="left", va="center",
                    fontsize=8, color=color,
                    bbox=dict(facecolor=Theme.DARK_BG, edgecolor=color, boxstyle="round,pad=0.2", alpha=0.85),
                    zorder=20, clip_on=False
                )

            _label_right(current_buy_price, "ASK", "purple")
            _label_right(current_sell_price, "BID", "teal")
            _label_right(dca_line_price, "DCA", "red")
            _label_right(trail_line, "SELL", "green")
        except Exception:
            pass

        # 6. Trade History Dots
        # Plots triangles on the chart where trades actually occurred.
        if self.trade_history_path and os.path.exists(self.trade_history_path):
            try:
                trades = []
                with open(self.trade_history_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            obj = json.loads(line)
                            # Filter for this coin
                            if obj.get("symbol", "").split("-")[0] == self.coin:
                                trades.append(obj)
                        except: pass
                
                candle_ts = [c["ts"] for c in candles]
                if candle_ts:
                    min_ts = candle_ts[0]
                    max_ts = candle_ts[-1]
                    
                    for tr in trades:
                        ts = float(tr.get("ts", 0))
                        if min_ts <= ts <= max_ts:
                            # Find approximate x index (closest candle timestamp)
                            closest_idx = 0
                            min_dist = float('inf')
                            for i, c_ts in enumerate(candle_ts):
                                dist = abs(c_ts - ts)
                                if dist < min_dist:
                                    min_dist = dist
                                    closest_idx = i
                            
                            price = float(tr.get("price", 0))
                            side = tr.get("side", "")
                            tag = tr.get("tag", "")
                            
                            color = "red" # Buy default
                            marker = "^"
                            if side == "sell":
                                color = "green"
                                marker = "v"
                            elif tag == "DCA":
                                color = "purple"
                            
                            self.ax.scatter([closest_idx], [price], c=color, marker=marker, s=40, zorder=10, edgecolors="white")
            except Exception:
                pass

        self.canvas.draw()

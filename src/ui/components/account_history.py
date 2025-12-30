"""
src/ui/components/account_history.py

Visualization Component for Account Equity History.
This module defines a Tkinter widget that renders a Matplotlib chart showing:
1.  Total Account Value (USD) over time.
2.  Execution points (Buy/Sell/DCA) overlaid on the equity curve.
"""

import tkinter as tk
from tkinter import ttk
import json
import os
import time
import bisect
from typing import List, Dict, Any, Tuple
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime

from src.ui.styles.theme import Theme

class AccountHistoryChart(ttk.Frame):
    """
    A Chart Widget specifically for displaying Account Equity History.
    
    It reads from `account_history.jsonl` and `trade_history.jsonl` to create
    a visual timeline of portfolio performance and trading activity.
    
    Features:
    -   Auto-refreshing based on file modification times.
    -   Downsampling for performance with large datasets.
    -   Interactive resizing.
    -   Event markers for Buys (Red/Purple) and Sells (Green).
    """
    
    def __init__(self, parent: tk.Widget, history_path: str, trade_path: str):
        """
        Initialize the History Chart.
        
        Args:
            parent: The parent Tkinter widget.
            history_path: Path to the JSONL file containing account value snapshots.
            trade_path: Path to the JSONL file containing trade execution records.
        """
        super().__init__(parent)
        self.history_path = history_path
        self.trade_path = trade_path
        
        self.title_label = ttk.Label(self, text="Account Value History", font=("Segoe UI", 10, "bold"))
        self.title_label.pack(anchor="w", padx=6, pady=(6, 2))
        
        # Figure Initialization
        self.fig = Figure(figsize=(6, 3), dpi=100)
        self.fig.patch.set_facecolor(Theme.DARK_BG)
        
        self.ax = self.fig.add_subplot(111)
        self._apply_style()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_w = self.canvas.get_tk_widget()
        self.canvas_w.configure(bg=Theme.DARK_BG)
        self.canvas_w.pack(fill="both", expand=True, padx=2, pady=2)
        
        self._last_mtime_hist = 0.0
        self._last_mtime_trade = 0.0
        
        # Handle resize events with debouncing
        self._resize_after = None
        self.canvas_w.bind("<Configure>", self._on_resize)

    def _apply_style(self):
        """Apply the application's dark theme to the chart axes."""
        self.ax.set_facecolor(Theme.DARK_PANEL)
        self.fig.patch.set_facecolor(Theme.DARK_BG)
        self.ax.tick_params(colors=Theme.DARK_FG, labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(Theme.DARK_BORDER)
        self.ax.grid(True, color=Theme.DARK_BORDER, linewidth=0.5, alpha=0.3)
        self.ax.set_ylabel("USD", color=Theme.DARK_FG, fontsize=8)

    def _on_resize(self, event):
        """Debounced resize handler."""
        if self._resize_after:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(200, self._redraw)

    def _redraw(self):
        """Trigger a canvas redraw."""
        self.canvas.draw_idle()

    def _read_history(self) -> List[Tuple[float, float]]:
        """
        Read and parse the account value history file.
        
        Returns:
            List[Tuple[float, float]]: A sorted list of (timestamp, value) tuples.
        """
        data = []
        if not os.path.exists(self.history_path):
            return data
            
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        obj = json.loads(line)
                        ts = float(obj.get("ts", 0))
                        val = float(obj.get("total_account_value", 0))
                        if val > 0:
                            data.append((ts, val))
                    except:
                        pass
        except Exception:
            pass
        
        data.sort(key=lambda x: x[0])
        return data

    def _read_trades(self) -> List[dict]:
        """
        Read and parse the trade history file.
        
        Returns:
            List[dict]: A list of trade record dictionaries.
        """
        trades = []
        if not os.path.exists(self.trade_path):
            return trades
            
        try:
            with open(self.trade_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        obj = json.loads(line)
                        if obj.get("side") in ["buy", "sell"]:
                            trades.append(obj)
                    except:
                        pass
        except Exception:
            pass
        return trades

    def refresh(self, force=False):
        """
        Refresh the chart data if files have changed on disk.
        
        Args:
            force (bool): If True, ignore mtime checks and force a reload.
        """
        # Check modification times to avoid unnecessary I/O
        try:
            mt_h = os.path.getmtime(self.history_path) if os.path.exists(self.history_path) else 0
            mt_t = os.path.getmtime(self.trade_path) if os.path.exists(self.trade_path) else 0
        except:
            mt_h, mt_t = 0, 0

        if not force and (mt_h == self._last_mtime_hist and mt_t == self._last_mtime_trade):
            return

        self._last_mtime_hist = mt_h
        self._last_mtime_trade = mt_t
        
        points = self._read_history()
        trades = self._read_trades()
        
        self.ax.clear()
        self._apply_style()
        
        if not points:
            self.canvas.draw()
            return
            
        # Downsample if needed (simple stride) to prevent plotting thousands of points
        limit = 500
        if len(points) > limit:
            stride = len(points) // limit
            points = points[::stride]
            
        ts_list = [p[0] for p in points]
        vals = [p[1] for p in points]
        
        # Plot Equity Line
        # Convert timestamps to datetime for matplotlib
        dates = [datetime.fromtimestamp(ts) for ts in ts_list]
        self.ax.plot(dates, vals, color=Theme.DARK_ACCENT, linewidth=1.5)
        
        # Format X-Axis as Time
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.fig.autofmt_xdate()
        
        # Overlay Trade Markers
        if trades:
            t_min = ts_list[0]
            t_max = ts_list[-1]
            
            for tr in trades:
                try:
                    tts = float(tr.get("ts", 0))
                    if tts < t_min or tts > t_max:
                        continue
                        
                    side = str(tr.get("side", "")).lower()
                    tag = str(tr.get("tag", "")).upper()
                    
                    color = "red"
                    if side == "buy":
                        if "DCA" in tag:
                            color = "purple"
                    elif side == "sell":
                        color = "green"
                    else:
                        continue
                        
                    # Find nearest point on the equity line to place the marker
                    # bisect works on floats, so use ts_list
                    idx = bisect.bisect_left(ts_list, tts)
                    if idx >= len(ts_list): idx = len(ts_list) - 1
                    if idx < 0: idx = 0
                    
                    # Snap to the closest point for visual accuracy
                    if idx > 0:
                        diff1 = abs(ts_list[idx] - tts)
                        diff2 = abs(ts_list[idx-1] - tts)
                        if diff2 < diff1:
                            idx -= 1
                            
                    x_date = dates[idx]
                    y_val = vals[idx]
                    
                    self.ax.scatter([x_date], [y_val], s=30, c=color, zorder=5, edgecolors='white', linewidths=0.5)
                    
                except Exception:
                    pass

        self.canvas.draw()

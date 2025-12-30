"""
src/ui/components/tiles.py

Reusable UI Components for Layout and Signal Visualization.
Includes:
1.  WrapFrame: A layout container that automatically reflows widgets.
2.  NeuralSignalTile: A visual dashboard widget for a single coin.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple
from dataclasses import dataclass
from src.ui.styles.theme import Theme

@dataclass
class _WrapItem:
    """Internal helper to store widget references and padding."""
    w: tk.Widget
    padx: Tuple[int, int] = (0, 0)
    pady: Tuple[int, int] = (0, 0)

class WrapFrame(ttk.Frame):
    """
    A custom frame that arranges children in a left-to-right flow,
    wrapping to the next line when horizontal space is exhausted.
    
    Acts like a flex-wrap container in CSS.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._items: List[_WrapItem] = []
        self._reflow_pending = False
        self._in_reflow = False
        self.bind("<Configure>", self._schedule_reflow)

    def add(self, widget: tk.Widget, padx=(0, 0), pady=(0, 0)) -> None:
        """Add a widget to the flow layout."""
        self._items.append(_WrapItem(widget, padx=padx, pady=pady))
        self._schedule_reflow()

    def clear(self, destroy_widgets: bool = True) -> None:
        """Remove all widgets from the layout."""
        for it in list(self._items):
            try:
                it.w.grid_forget()
            except Exception:
                pass
            if destroy_widgets:
                try:
                    it.w.destroy()
                except Exception:
                    pass
        self._items = []
        self._schedule_reflow()

    def _schedule_reflow(self, event=None) -> None:
        """Trigger a reflow operation on the next idle cycle."""
        if self._reflow_pending:
            return
        self._reflow_pending = True
        self.after_idle(self._reflow)

    def _reflow(self) -> None:
        """Calculate grid positions based on available width."""
        if self._in_reflow:
            self._reflow_pending = False
            return

        self._reflow_pending = False
        self._in_reflow = True
        try:
            width = self.winfo_width()
            if width <= 1:
                return
            usable_width = max(1, width - 6)

            for it in self._items:
                it.w.grid_forget()

            row = 0
            col = 0
            x = 0

            for it in self._items:
                reqw = max(it.w.winfo_reqwidth(), it.w.winfo_width())

                needed = 10 + reqw + it.padx[0] + it.padx[1]

                if col > 0 and (x + needed) > usable_width:
                    row += 1
                    col = 0
                    x = 0

                it.w.grid(row=row, column=col, sticky="w", padx=it.padx, pady=it.pady)
                x += needed
                col += 1
        finally:
            self._in_reflow = False

class NeuralSignalTile(ttk.Frame):
    """
    Visual tile representing the AI signal state for a single coin.
    
    Displays:
    -   Coin Symbol (Title).
    -   Two vertical bar graphs (Long Confidence vs Short Confidence).
    -   Numeric signal levels.
    
    Visuals:
    -   Blue bars: Long Signal strength.
    -   Orange bars: Short Signal strength.
    -   Highlights on hover.
    """
    def __init__(self, parent: tk.Widget, coin: str, bar_height: int = 52, levels: int = 8):
        """
        Initialize the Tile.
        
        Args:
            parent: Parent widget.
            coin: Symbol string.
            bar_height: Pixel height of the bar graph area.
            levels: Resolution of the bar graph (default 8 segments).
        """
        super().__init__(parent)
        self.coin = coin

        self._hover_on = False
        self._normal_canvas_bg = Theme.DARK_PANEL2
        self._hover_canvas_bg = Theme.DARK_PANEL
        self._normal_border = Theme.DARK_BORDER
        self._hover_border = Theme.DARK_ACCENT2
        self._normal_fg = Theme.DARK_FG
        self._hover_fg = Theme.DARK_ACCENT2

        self._levels = max(2, int(levels))             
        self._display_levels = self._levels - 1        

        self._bar_h = int(bar_height)
        self._bar_w = 12
        self._gap = 16
        self._pad = 6

        self._base_fill = Theme.DARK_PANEL
        self._long_fill = "blue"
        self._short_fill = "orange"

        self.title_lbl = ttk.Label(self, text=coin)
        self.title_lbl.pack(anchor="center")

        w = (self._pad * 2) + (self._bar_w * 2) + self._gap
        h = (self._pad * 2) + self._bar_h

        self.canvas = tk.Canvas(
            self,
            width=w,
            height=h,
            bg=self._normal_canvas_bg,
            highlightthickness=1,
            highlightbackground=self._normal_border,
        )
        self.canvas.pack(padx=2, pady=(2, 0))

        x0 = self._pad
        x1 = x0 + self._bar_w
        x2 = x1 + self._gap
        x3 = x2 + self._bar_w
        yb = self._pad + self._bar_h

        self._long_segs: List[int] = []
        self._short_segs: List[int] = []

        # Create segments from bottom to top
        for seg in range(self._display_levels):
            y_top = int(round(yb - ((seg + 1) * self._bar_h / self._display_levels)))
            y_bot = int(round(yb - (seg * self._bar_h / self._display_levels)))

            self._long_segs.append(
                self.canvas.create_rectangle(
                    x0, y_top, x1, y_bot,
                    fill=self._base_fill,
                    outline=Theme.DARK_BORDER,
                    width=1,
                )
            )
            self._short_segs.append(
                self.canvas.create_rectangle(
                    x2, y_top, x3, y_bot,
                    fill=self._base_fill,
                    outline=Theme.DARK_BORDER,
                    width=1,
                )
            )

        # Divider line
        trade_y = int(round(yb - (2 * self._bar_h / self._display_levels)))
        self.canvas.create_line(x0, trade_y, x1, trade_y, fill=Theme.DARK_FG, width=2)

        self.value_lbl = ttk.Label(self, text="L:0 S:0")
        self.value_lbl.pack(anchor="center", pady=(1, 0))

        self.set_values(0, 0)
        
        # Bind events for hover effects
        self.canvas.bind("<Enter>", lambda e: self.set_hover(True))
        self.canvas.bind("<Leave>", lambda e: self.set_hover(False))

    def set_hover(self, on: bool) -> None:
        """Toggle visual hover state."""
        self._hover_on = on
        bg = self._hover_canvas_bg if on else self._normal_canvas_bg
        bd = self._hover_border if on else self._normal_border
        fg = self._hover_fg if on else self._normal_fg

        self.canvas.configure(bg=bg, highlightbackground=bd)
        self.title_lbl.configure(foreground=fg)
        self.value_lbl.configure(foreground=fg)

    def _clamp_level(self, value: int) -> int:
        """Ensure signal value stays within displayable range."""
        try:
            v = int(float(value))
        except Exception:
            v = 0
        return max(0, min(v, self._levels - 1))  # logical clamp: 0..7

    def _set_level(self, seg_ids: List[int], level: int, active_fill: str) -> None:
        """
        Fill the bar segments up to the specified level.
        """
        # Reset all segments to base
        for rid in seg_ids:
            self.canvas.itemconfigure(rid, fill=self._base_fill)

        # Level 0 -> show nothing (no highlight)
        if level <= 0:
            return

        # Level 1..7 -> fill from bottom up through the current level
        idx = level - 1  # level 1 maps to seg index 0
        if idx < 0:
            return
        if idx >= len(seg_ids):
            idx = len(seg_ids) - 1

        for i in range(idx + 1):
            self.canvas.itemconfigure(seg_ids[i], fill=active_fill)

    def set_values(self, long_sig: int, short_sig: int) -> None:
        """
        Update the displayed signal levels.
        
        Args:
            long_sig: Integer strength of Buy signal (0-8).
            short_sig: Integer strength of Sell signal (0-8).
        """
        ls = self._clamp_level(long_sig)
        ss = self._clamp_level(short_sig)

        self.value_lbl.config(text=f"L:{ls} S:{ss}")
        self._set_level(self._long_segs, ls, self._long_fill)
        self._set_level(self._short_segs, ss, self._short_fill)


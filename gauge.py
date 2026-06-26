"""
gauge.py — Smooth animated arc RAM gauge widget.
"""

import tkinter as tk
import math
from colors import C, usage_color

class RAMGauge(tk.Canvas):
    def __init__(self, parent, size=190, **kw):
        super().__init__(parent, width=size, height=size, bg=C.CARD,
                         highlightthickness=0, **kw)
        self.cx = self.cy = size // 2
        self.r = size // 2 - 18
        self.cur_a = self.cur_p = 0.0
        self._anim = False

    def update_val(self, pct, used_s, total_s):
        self._ta = pct / 100 * 270
        self._tp = pct
        self._us = used_s
        self._ts = total_s
        if not self._anim:
            self._anim = True
            self._tick()

    def _tick(self):
        d = self._ta - self.cur_a
        if abs(d) > 0.3:
            self.cur_a += d * 0.18
            self.cur_p += (self._tp - self.cur_p) * 0.18
            self._draw()
            self.after(16, self._tick)
        else:
            self.cur_a, self.cur_p = self._ta, self._tp
            self._draw()
            self._anim = False

    def _draw(self):
        self.delete("all")
        cx, cy, r, pct = self.cx, self.cy, self.r, self.cur_p
        
        # BG arc
        self.create_arc(cx-r, cy-r, cx+r, cy+r, start=135, extent=270,
                        outline=C.GAUGE_BG, width=14, style="arc")
        
        # FG arc
        color = usage_color(pct)
        ang = pct / 100 * 270
        if ang > 1:
            self.create_arc(cx-r, cy-r, cx+r, cy+r, start=135, extent=ang,
                            outline=color, width=14, style="arc")
            ea = math.radians(135 + ang)
            gx, gy = cx + r * math.cos(ea), cy - r * math.sin(ea)
            self.create_oval(gx-6, gy-6, gx+6, gy+6, fill=color, outline="")
            
        # Text
        self.create_text(cx, cy-14, text=f"{pct:.0f}%", fill=color,
                         font=("Segoe UI", 26, "bold"))
        self.create_text(cx, cy+12, text=self._us, fill=C.TEXT, font=("Segoe UI", 9))
        self.create_text(cx, cy+28, text=f"of {self._ts}", fill=C.TEXT2, font=("Segoe UI", 8))

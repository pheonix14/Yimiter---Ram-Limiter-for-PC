"""
widget.py — Draggable borderless desktop widget overlay for YIMITER.
"""

import tkinter as tk
import math
from colors import C, usage_color


class RAMWidget(tk.Toplevel):
    def __init__(self, parent, on_restore):
        super().__init__(parent)
        self.on_restore = on_restore

        # Borderless and always on top
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=C.BG)

        # Default size and position: Bottom-right corner of primary monitor
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.width = 130
        self.height = 130
        self.geometry(f"{self.width}x{self.height}+{sw - 160}+{sh - 200}")

        # Dragging variables
        self.drag_data = {"x": 0, "y": 0}

        self._build_ui()

    def _build_ui(self):
        # Outer container frame with border
        self.frame = tk.Frame(
            self, bg=C.CARD, highlightbackground=C.BORDER, highlightthickness=1
        )
        self.frame.pack(fill="both", expand=True)

        # Inner Canvas for arc gauge
        self.canvas = tk.Canvas(
            self.frame, width=120, height=120, bg=C.CARD, highlightthickness=0
        )
        self.canvas.pack(padx=4, pady=4)

        # Interactive bindings
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<Double-Button-1>", lambda e: self.on_restore())
        self.canvas.bind("<Button-3>", self.show_menu)

        # Right-click context menu
        self.menu = tk.Menu(
            self,
            tearoff=0,
            bg=C.CARD,
            fg=C.TEXT,
            activebackground=C.HOVER,
            activeforeground=C.CYAN,
            relief="flat",
        )
        self.menu.add_command(label="Restore Yimiter", command=self.on_restore)
        self.menu.add_separator()
        self.menu.add_command(label="Hide Widget", command=self.destroy)

        # Hover effects
        self.canvas.bind("<Enter>", lambda e: self.frame.config(highlightbackground=C.CYAN))
        self.canvas.bind("<Leave>", lambda e: self.frame.config(highlightbackground=C.BORDER))

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def update_val(self, pct, used_s):
        self.canvas.delete("all")

        cx, cy, r = 60, 60, 44

        # Background arc
        self.canvas.create_arc(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            start=135,
            extent=270,
            outline=C.GAUGE_BG,
            width=8,
            style="arc",
        )

        # Foreground arc
        color = usage_color(pct)
        ang = (pct / 100) * 270
        if ang > 1:
            self.canvas.create_arc(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                start=135,
                extent=ang,
                outline=color,
                width=8,
                style="arc",
            )
            # Dot indicator at end of arc
            ea = math.radians(135 + ang)
            gx, gy = cx + r * math.cos(ea), cy - r * math.sin(ea)
            self.canvas.create_oval(
                gx - 4, gy - 4, gx + 4, gy + 4, fill=color, outline=""
            )

        # Draw labels
        self.canvas.create_text(
            cx, cy - 8, text=f"{pct:.0f}%", fill=color, font=("Segoe UI", 16, "bold")
        )
        self.canvas.create_text(
            cx, cy + 12, text=used_s, fill=C.TEXT2, font=("Segoe UI", 8)
        )
        self.canvas.create_text(
            cx, cy + 26, text="RAM", fill=C.TEXT3, font=("Segoe UI", 7, "bold")
        )

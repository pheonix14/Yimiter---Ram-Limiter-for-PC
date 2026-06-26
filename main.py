"""
⚡ YIMITER — Desktop RAM Limiter & Manager (Main Entrypoint)
Splits code logic across modules and orchestrates the full desktop interface.
"""

import tkinter as tk
from tkinter import messagebox
import psutil
import ctypes
import time
import os
import sys

from colors import C, usage_color, fmt
from config import Config
from process_mgr import ProcessManager
from gauge import RAMGauge
from settings_ui import SettingsPanel


class YimiterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("⚡ YIMITER — RAM Manager")
        self.root.geometry("720x870")
        self.root.minsize(660, 700)
        self.root.configure(bg=C.BG)

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.cfg = Config()
        self.pm = ProcessManager(self.cfg)
        self.settings_open = False

        self._build_ui()

        if self.cfg.start_minimized:
            self.root.iconify()

        self._refresh()

    def _build_ui(self):
        r = self.root

        # ── Header ──
        hdr = tk.Frame(r, bg=C.BG)
        hdr.pack(fill="x", padx=16, pady=(12, 0))

        tk.Label(hdr, text="⚡ YIMITER", bg=C.BG, fg=C.CYAN,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(hdr, text="  RAM Limiter", bg=C.BG, fg=C.TEXT2,
                 font=("Segoe UI", 11)).pack(side="left", pady=(4, 0))

        # Settings button
        gear = tk.Label(hdr, text="  ⚙  ", bg=C.SETTINGS, fg=C.TEXT,
                        font=("Segoe UI", 14), cursor="hand2",
                        relief="flat")
        gear.pack(side="right", padx=(8, 0))
        gear.bind("<Button-1>", lambda e: self._open_settings())
        gear.bind("<Enter>", lambda e: gear.config(bg=C.HOVER, fg=C.CYAN))
        gear.bind("<Leave>", lambda e: gear.config(bg=C.SETTINGS, fg=C.TEXT))

        tk.Frame(r, bg=C.BORDER, height=1).pack(fill="x", padx=16, pady=(10, 0))

        # ── Top: Gauge + Stats + Actions ──
        top = tk.Frame(r, bg=C.BG)
        top.pack(fill="x", padx=16, pady=(10, 0))

        # Gauge
        gf = tk.Frame(top, bg=C.CARD, highlightbackground=C.BORDER, highlightthickness=1)
        gf.pack(side="left", padx=(0, 10))
        self.gauge = RAMGauge(gf, size=190)
        self.gauge.pack(padx=12, pady=12)

        # Right column
        right = tk.Frame(top, bg=C.BG)
        right.pack(side="left", fill="both", expand=True)

        # Stats
        sf = tk.Frame(right, bg=C.BG)
        sf.pack(fill="x")
        self.stats = {}
        for key, label, color in [
            ("used", "Used", C.CYAN), ("avail", "Available", C.GREEN),
            ("swap", "Swap", C.YELLOW), ("procs", "Processes", C.TEXT2),
            ("sleeping", "😴 Sleeping", C.SLEEP),
        ]:
            row = tk.Frame(sf, bg=C.CARD, highlightbackground=C.BORDER, highlightthickness=1)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, bg=C.CARD, fg=C.TEXT2,
                     font=("Segoe UI", 8), anchor="w").pack(side="left", padx=(8, 0), pady=3)
            v = tk.Label(row, text="—", bg=C.CARD, fg=color,
                         font=("Consolas", 10, "bold"), anchor="e")
            v.pack(side="right", padx=(0, 8), pady=3)
            self.stats[key] = v

        # Action buttons
        bf = tk.Frame(right, bg=C.BG)
        bf.pack(fill="x", pady=(8, 0))
        btns = [
            ("💤 Deep Sleep Hogs", C.SLEEP, self._act_deep_sleep),
            ("🔕 Kill Notifications", C.PINK, self._act_kill_notifs),
            ("🧹 Free Memory", C.PURPLE, self._act_flush),
            ("☀️ Wake All", C.GREEN, self._act_wake_all),
        ]
        for i, (text, color, cmd) in enumerate(btns):
            fg = "#0b0e14" if color in (C.GREEN, C.YELLOW) else "#ffffff"
            b = tk.Label(bf, text=f" {text} ", bg=color, fg=fg,
                         font=("Segoe UI", 9, "bold"), cursor="hand2")
            b.grid(row=i // 2, column=i % 2, padx=2, pady=2, sticky="ew")
            b.bind("<Button-1>", lambda e, c=cmd: c())
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)

        # Auto-sleep indicator
        self.auto_lbl = tk.Label(right, text="", bg=C.BG, fg=C.SLEEP,
                                  font=("Segoe UI", 8))
        self.auto_lbl.pack(anchor="w", padx=4, pady=(4, 0))

        # ── Alert banner (hidden) ──
        self.alert_frame = tk.Frame(r, bg=C.RED)
        self.alert_lbl = tk.Label(self.alert_frame, text="", bg=C.RED, fg="#fff",
                                   font=("Segoe UI", 10, "bold"))
        self.alert_lbl.pack(pady=5)

        # ── Process list ──
        lh = tk.Frame(r, bg=C.BG)
        lh.pack(fill="x", padx=16, pady=(10, 2))
        tk.Label(lh, text="🔥 Processes by RAM", bg=C.BG, fg=C.TEXT,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        self.time_lbl = tk.Label(lh, text="", bg=C.BG, fg=C.TEXT3,
                                  font=("Segoe UI", 8))
        self.time_lbl.pack(side="right")

        # Column header
        ch = tk.Frame(r, bg=C.CARD)
        ch.pack(fill="x", padx=16)
        for txt, w in [("#", 3), ("Process", 20), ("PID", 8), ("RAM", 9),
                        ("", 8), ("%", 5), ("Status", 7), ("", 10)]:
            tk.Label(ch, text=txt, bg=C.CARD, fg=C.TEXT3,
                     font=("Segoe UI", 7, "bold"), width=w, anchor="w").pack(side="left", padx=1)

        # Scrollable list
        lc = tk.Frame(r, bg=C.BG)
        lc.pack(fill="both", expand=True, padx=16, pady=(0, 4))
        self.pcanvas = tk.Canvas(lc, bg=C.BG, highlightthickness=0)
        sb = tk.Scrollbar(lc, orient="vertical", command=self.pcanvas.yview,
                          bg=C.BORDER, troughcolor=C.BG, width=6)
        self.pinner = tk.Frame(self.pcanvas, bg=C.BG)
        self.pinner.bind("<Configure>",
                          lambda e: self.pcanvas.configure(scrollregion=self.pcanvas.bbox("all")))
        self.cwin = self.pcanvas.create_window((0, 0), window=self.pinner, anchor="nw")
        self.pcanvas.configure(yscrollcommand=sb.set)
        self.pcanvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.pcanvas.bind("<Configure>",
                           lambda e: self.pcanvas.itemconfig(self.cwin, width=e.width))
        self.pcanvas.bind_all("<MouseWheel>",
                               lambda e: self.pcanvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # ── Footer ──
        ft = tk.Frame(r, bg=C.BG)
        ft.pack(fill="x", padx=16, pady=(0, 8))
        self.status_lbl = tk.Label(ft, text="Starting up...", bg=C.BG, fg=C.TEXT3,
                                    font=("Segoe UI", 8))
        self.status_lbl.pack(side="left")
        self.count_lbl = tk.Label(ft, text="", bg=C.BG, fg=C.TEXT3,
                                   font=("Segoe UI", 8))
        self.count_lbl.pack(side="right")

    # ─── Refresh cycle ───────────────────────────────────────────────────

    def _refresh(self):
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            pct = mem.percent

            self.gauge.update_val(pct, fmt(mem.used), fmt(mem.total))
            self.stats["used"].config(text=fmt(mem.used))
            self.stats["avail"].config(text=fmt(mem.available))
            self.stats["swap"].config(text=f"{fmt(swap.used)} / {fmt(swap.total)}")
            self.stats["procs"].config(text=str(len(psutil.pids())))
            self.stats["sleeping"].config(text=str(len(self.pm.sleeping)))

            # Check RAM limit
            if self.cfg.limit_mode == "gb":
                limit_bytes = self.cfg.limit_gb * (1024**3)
                limit_exceeded = mem.used >= limit_bytes
                limit_desc = f"{self.cfg.limit_gb:.1f} GB"
                current_desc = f"{fmt(mem.used)}"
            else:
                limit_exceeded = pct >= self.cfg.threshold
                limit_desc = f"{self.cfg.threshold}%"
                current_desc = f"{pct:.0f}%"

            # Auto-sleep indicator
            if self.cfg.auto_sleep:
                self.auto_lbl.config(text=f"⚙️ Auto-Sleep ON (limit {limit_desc})",
                                      fg=C.SLEEP)
            else:
                self.auto_lbl.config(text="⚙️ Auto-Sleep OFF — enable in Settings",
                                      fg=C.TEXT3)

            # Alert
            if limit_exceeded:
                self.alert_frame.pack(fill="x", padx=16, pady=(6, 0))
                self.alert_lbl.config(
                    text=f"⚠  RAM Limit {limit_desc} Exceeded! — Current: {current_desc}"
                )
                if self.cfg.auto_sleep:
                    name, rss = self.pm.auto_sleep_one()
                    if name:
                        self._status(f"⚙️ Auto-slept: {name} ({fmt(rss)})", C.SLEEP)
            else:
                self.alert_frame.pack_forget()

            # Crash prevention
            prevented = self.pm.enforce_crash_prevention()
            if prevented:
                self._status(prevented[-1], C.RED)

            # Process list
            procs = self.pm.get_sorted_processes(mem.total)
            self._render_list(procs)

            self.time_lbl.config(text=f"Updated {time.strftime('%H:%M:%S')}")
            self.count_lbl.config(text=f"{len(self.pm.sleeping)} sleeping  •  "
                                       f"Refresh {self.cfg.refresh_sec}s")

        except Exception as e:
            self._status(f"Error: {e}", C.RED)

        self.root.after(self.cfg.refresh_sec * 1000, self._refresh)

    def _render_list(self, procs):
        for w in self.pinner.winfo_children():
            w.destroy()
        for idx, (pid, name, rss, pct) in enumerate(procs[:self.cfg.max_rows]):
            self._make_row(idx, pid, name, rss, pct)

    def _make_row(self, idx, pid, name, rss, pct):
        nl = name.lower()
        essential = self.cfg.is_essential(nl)
        sleeping = pid in self.pm.sleeping

        bg = "#0e0a1a" if sleeping else (C.BG if idx % 2 == 0 else C.CARD)
        row = tk.Frame(self.pinner, bg=bg)
        row.pack(fill="x")

        # Rank
        rank = idx + 1
        bc = {1: C.RED, 2: C.ORANGE, 3: C.YELLOW}.get(rank, C.TEXT3)
        tk.Label(row, text=f" {rank} ", bg=bc, fg="#fff",
                 font=("Segoe UI", 7, "bold"), width=3).pack(side="left", padx=(6, 4), pady=3)

        # Classify
        cls = self.cfg.classify_process(nl, rss)

        # Name
        if sleeping:
            ico = "😴 "
            fg = C.SLEEP
        else:
            if cls == "SAFE":
                ico = "🛡️ "
                fg = C.TEXT3
            elif cls == "BAD":
                ico = "🔴 "
                fg = C.RED
            elif cls == "HOG":
                ico = "⚠️ "
                fg = C.ORANGE
            elif cls == "BLOAT":
                ico = "🔕 "
                fg = C.TEXT
            else:
                ico = ""
                fg = C.TEXT

        d = ico + (name[:20] + "…" if len(name) > 20 else name)
        tk.Label(row, text=d, bg=bg, fg=fg, font=("Segoe UI", 9),
                 anchor="w", width=20).pack(side="left", padx=(0, 2), pady=3)

        # PID
        tk.Label(row, text=str(pid), bg=bg, fg=C.TEXT3,
                 font=("Consolas", 8), width=7).pack(side="left", padx=2, pady=3)

        # RAM
        mc = usage_color(pct * 8)
        tk.Label(row, text=fmt(rss), bg=bg, fg=mc,
                 font=("Consolas", 9, "bold"), anchor="e", width=9).pack(side="left", padx=2, pady=3)

        # Bar
        bar = tk.Frame(row, bg=C.GAUGE_BG, height=5, width=60)
        bar.pack(side="left", padx=3, pady=3)
        bar.pack_propagate(False)
        bw = max(1, int(min(pct, 100) / 100 * 60))
        tk.Frame(bar, bg=mc, height=5, width=bw).place(x=0, y=0, height=5, width=bw)

        # %
        tk.Label(row, text=f"{pct:.1f}%", bg=bg, fg=C.TEXT2,
                 font=("Segoe UI", 8), width=5).pack(side="left", padx=2, pady=3)

        # Status tag
        if sleeping:
            tag, tc = "SLEEP", C.SLEEP
        else:
            if cls == "SAFE":
                tag, tc = "SAFE", C.GREEN
            elif cls == "BAD":
                tag, tc = "BAD", C.RED
            elif cls == "HOG":
                tag, tc = "HOG", C.ORANGE
            elif cls == "BLOAT":
                tag, tc = "BLOAT", C.PINK
            else:
                tag, tc = "—", C.TEXT3

        tk.Label(row, text=tag, bg=bg, fg=tc,
                 font=("Segoe UI", 7, "bold"), width=6).pack(side="left", padx=2, pady=3)

        # Action buttons
        if not essential:
            if sleeping:
                w = tk.Label(row, text=" ☀ Wake ", bg=C.GREEN, fg="#0b0e14",
                             font=("Segoe UI", 8, "bold"), cursor="hand2")
                w.pack(side="right", padx=(2, 6), pady=3)
                w.bind("<Button-1>", lambda e, p=pid, n=name: self._row_wake(p, n))
            else:
                k = tk.Label(row, text=" ✕ ", bg=C.RED, fg="#fff",
                             font=("Segoe UI", 8, "bold"), cursor="hand2")
                k.pack(side="right", padx=(1, 6), pady=3)
                k.bind("<Button-1>", lambda e, p=pid, n=name: self._row_kill(p, n))

                s = tk.Label(row, text=" 💤 ", bg=C.SLEEP, fg="#fff",
                             font=("Segoe UI", 8, "bold"), cursor="hand2")
                s.pack(side="right", padx=1, pady=3)
                s.bind("<Button-1>", lambda e, p=pid, n=name: self._row_sleep(p, n))


    # ─── Row actions ─────────────────────────────────────────────────────

    def _row_sleep(self, pid, name):
        ok, msg = self.pm.sleep(pid, name)
        self._status(msg, C.SLEEP if ok else C.RED)

    def _row_wake(self, pid, name):
        ok, msg = self.pm.wake(pid, name)
        self._status(msg, C.GREEN if ok else C.RED)

    def _row_kill(self, pid, name):
        if messagebox.askyesno("Kill Process", f"Kill \"{name}\" (PID {pid})?", icon="warning"):
            ok, msg = self.pm.kill(pid, name)
            self._status(msg, C.GREEN if ok else C.RED)

    # ─── Bulk actions ────────────────────────────────────────────────────

    def _act_deep_sleep(self):
        n = self.pm.deep_sleep_hogs()
        self._status(f"😴 Put {n} RAM hogs to deep sleep", C.SLEEP)

    def _act_kill_notifs(self):
        n = self.pm.kill_notifications()
        self._status(f"🔕 Silenced {n} notification/bloat processes", C.PINK)

    def _act_flush(self):
        n = self.pm.flush_memory()
        self._status(f"🧹 Trimmed {n} working sets", C.PURPLE)

    def _act_wake_all(self):
        n = self.pm.wake_all()
        self._status(f"☀️ Woke up {n} processes", C.GREEN)

    # ─── Settings ────────────────────────────────────────────────────────

    def _open_settings(self):
        if self.settings_open:
            return
        self.settings_open = True
        SettingsPanel(self.root, self.cfg, self.pm, self._on_settings_close)

    def _on_settings_close(self, action):
        self.settings_open = False
        if action == "saved":
            self._status("✓ Settings saved", C.GREEN)
        elif action == "added_whitelist":
            self.cfg.save()
            self._status("✓ App added to whitelist", C.BLUE)
            self._open_settings()
        elif action == "removed_whitelist":
            self.cfg.save()
            self._status("✓ App removed from whitelist", C.ORANGE)
            self._open_settings()

    # ─── Helpers ─────────────────────────────────────────────────────────

    def _status(self, text, color=C.TEXT3):
        self.status_lbl.config(text=text, fg=color)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self.cfg.save()
        # Wake all sleeping processes before exit
        self.pm.wake_all()
        self.root.destroy()


if __name__ == "__main__":
    app = YimiterApp()
    app.run()

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
import webbrowser

from colors import C, usage_color, fmt
from config import Config
from process_mgr import ProcessManager
from gauge import RAMGauge
from settings_ui import SettingsPanel
from widget import RAMWidget
from tray import YimiterTray
from notification import notifier
from startup import is_startup_enabled, enable_startup, disable_startup


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
        self.widget_win = None
        self.row_widgets = []

        # Resolve asset paths for frozen execution
        frozen = getattr(sys, 'frozen', False)
        if frozen:
            self.app_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            self.user_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            self.user_dir = self.app_dir

        self.logo_png = os.path.join(self.app_dir, "yimiter_logo.png")
        self.logo_ico = os.path.join(self.user_dir, "yimiter.ico")
        if not os.path.exists(self.logo_ico) and os.path.exists(self.logo_png):
            try:
                from PIL import Image
                img = Image.open(self.logo_png)
                img.save(self.logo_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
            except Exception as e:
                print("Logo conversion error:", e)

        # Apply icon if available
        if os.path.exists(self.logo_ico):
            try:
                self.root.iconbitmap(self.logo_ico)
            except Exception:
                pass

        # Sync registry startup settings
        try:
            if self.cfg.auto_start:
                if not is_startup_enabled():
                    enable_startup()
            else:
                if is_startup_enabled():
                    disable_startup()
        except Exception as e:
            print("Startup sync error:", e)

        self._build_ui()

        # System Tray Icon Setup
        self.tray_icon = YimiterTray(
            self.logo_ico if os.path.exists(self.logo_ico) else None,
            on_restore=self.restore_from_tray,
            on_widget=self.toggle_widget_from_tray,
            on_flush=self.flush_from_tray,
            on_exit=self.exit_from_tray
        )
        self.tray_icon.run()

        if self.cfg.start_minimized:
            self.root.withdraw()
            if self.cfg.notifications:
                notifier.send(
                    "Yimiter Active", 
                    "Yimiter has started minimized to the system tray.",
                    self.logo_ico if os.path.exists(self.logo_ico) else None
                )
        else:
            self.root.deiconify()

        self._refresh()

    def restore_from_tray(self):
        self.root.after(0, self._restore_main_win)

    def _restore_main_win(self):
        self.root.deiconify()
        self.root.state('normal')
        self.root.lift()
        self.root.focus_force()

    def toggle_widget_from_tray(self):
        self.root.after(0, self.toggle_widget)

    def flush_from_tray(self):
        self.root.after(0, self._act_flush)

    def exit_from_tray(self):
        self.root.after(0, self._on_close_full)

    def _build_ui(self):
        r = self.root

        # ── Header ──
        hdr = tk.Frame(r, bg=C.BG)
        hdr.pack(fill="x", padx=16, pady=(12, 0))

        # Stylized lightning canvas logo
        logo_canvas = tk.Canvas(hdr, width=32, height=32, bg=C.BG, highlightthickness=0)
        logo_canvas.pack(side="left", padx=(0, 6))
        logo_canvas.create_polygon(
            16, 2, 25, 14, 17, 14, 21, 30, 9, 16, 17, 16,
            fill=C.CYAN, outline=""
        )

        tk.Label(hdr, text="⚡ YIMITER", bg=C.BG, fg=C.CYAN,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(hdr, text="  RAM Limiter", bg=C.BG, fg=C.TEXT2,
                 font=("Segoe UI", 11)).pack(side="left", pady=(4, 0))

        # Settings gear button
        gear = tk.Label(hdr, text="  ⚙  ", bg=C.SETTINGS, fg=C.TEXT,
                        font=("Segoe UI", 14), cursor="hand2",
                        relief="flat")
        gear.pack(side="right", padx=(8, 0))
        gear.bind("<Button-1>", lambda e: self._open_settings())
        gear.bind("<Enter>", lambda e: gear.config(bg=C.HOVER, fg=C.CYAN))
        gear.bind("<Leave>", lambda e: gear.config(bg=C.SETTINGS, fg=C.TEXT))

        # Desktop Widget Toggle button
        widget_btn = tk.Label(hdr, text="  🔲  ", bg=C.SETTINGS, fg=C.TEXT,
                              font=("Segoe UI", 12), cursor="hand2",
                              relief="flat")
        widget_btn.pack(side="right", padx=(8, 0))
        widget_btn.bind("<Button-1>", lambda e: self.toggle_widget())
        widget_btn.bind("<Enter>", lambda e: widget_btn.config(bg=C.HOVER, fg=C.CYAN))
        widget_btn.bind("<Leave>", lambda e: widget_btn.config(bg=C.SETTINGS, fg=C.TEXT))

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
        self.count_lbl.pack(side="right", padx=(8, 0))

        # Prominent GitHub credits
        credit_lbl = tk.Label(ft, text="Made by @pheonix14 on GitHub", bg=C.BG, fg=C.TEXT3,
                              font=("Segoe UI", 8, "italic"), cursor="hand2")
        credit_lbl.pack(side="right")
        credit_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/pheonix14"))
        credit_lbl.bind("<Enter>", lambda e: credit_lbl.config(fg=C.CYAN))
        credit_lbl.bind("<Leave>", lambda e: credit_lbl.config(fg=C.TEXT3))

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

            # Alert and Auto-Sleep
            if limit_exceeded:
                self.alert_frame.pack(fill="x", padx=16, pady=(6, 0))
                self.alert_lbl.config(
                    text=f"⚠  RAM Limit {limit_desc} Exceeded! — Current: {current_desc}"
                )
                if self.cfg.auto_sleep:
                    name, rss = self.pm.auto_sleep_one()
                    if name:
                        self._status(f"⚙️ Auto-slept: {name} ({fmt(rss)})", C.SLEEP)
                        if self.cfg.notifications:
                            notifier.send(
                                "RAM Limit Exceeded",
                                f"Auto-slept process '{name}' ({fmt(rss)}) to free RAM.",
                                self.logo_ico if os.path.exists(self.logo_ico) else None
                            )
            else:
                self.alert_frame.pack_forget()

            # Per-Process Crash prevention
            prevented = self.pm.enforce_crash_prevention()
            if prevented:
                self._status(prevented[-1], C.RED)
                if self.cfg.notifications:
                    notifier.send(
                        "Crash Prevention Alert",
                        prevented[-1],
                        self.logo_ico if os.path.exists(self.logo_ico) else None
                    )

            # System-wide Crash Guard Prevention
            sys_actions = self.pm.system_crash_prevention(pct, mem.total)
            if sys_actions:
                self._status(sys_actions[-1], C.RED)
                if self.cfg.notifications:
                    for action in sys_actions:
                        notifier.send(
                            "System RAM Guard Alert",
                            action,
                            self.logo_ico if os.path.exists(self.logo_ico) else None
                        )

            # Update desktop widget if visible
            if self.widget_win and tk.Toplevel.winfo_exists(self.widget_win):
                self.widget_win.update_val(pct, fmt(mem.used))

            # Process list
            procs = self.pm.get_sorted_processes(mem.total)
            self._render_list(procs)

            self.time_lbl.config(text=f"Updated {time.strftime('%H:%M:%S')}")
            self.count_lbl.config(text=f"{len(self.pm.sleeping)} sleeping  •  "
                                       f"Refresh {self.cfg.refresh_sec}s")

        except Exception as e:
            self._status(f"Error: {e}", C.RED)

        self.root.after(self.cfg.refresh_sec * 1000, self._refresh)

    # ─── Process list rendering (In-place updates to eliminate lag) ──────

    def _render_list(self, procs):
        display_procs = procs[:self.cfg.max_rows]
        required_rows = len(display_procs)

        # 1. Expand row widget cache if needed
        while len(self.row_widgets) < required_rows:
            row_dict = self._create_row_skeleton(len(self.row_widgets))
            self.row_widgets.append(row_dict)

        # 2. Update existing rows in place
        for idx, (pid, name, rss, pct) in enumerate(display_procs):
            row_dict = self.row_widgets[idx]
            self._update_row(row_dict, idx, pid, name, rss, pct)
            row_dict['frame'].pack(fill="x")

        # 3. Hide any extra cached rows
        for idx in range(required_rows, len(self.row_widgets)):
            self.row_widgets[idx]['frame'].pack_forget()

    def _create_row_skeleton(self, idx):
        # Create container row frame
        row = tk.Frame(self.pinner)

        # Rank label
        rank_lbl = tk.Label(row, font=("Segoe UI", 7, "bold"), width=3)
        rank_lbl.pack(side="left", padx=(6, 4), pady=3)

        # Name label
        name_lbl = tk.Label(row, font=("Segoe UI", 9), anchor="w", width=20)
        name_lbl.pack(side="left", padx=(0, 2), pady=3)

        # PID label
        pid_lbl = tk.Label(row, font=("Consolas", 8), width=7)
        pid_lbl.pack(side="left", padx=2, pady=3)

        # RAM usage label
        ram_lbl = tk.Label(row, font=("Consolas", 9, "bold"), anchor="e", width=9)
        ram_lbl.pack(side="left", padx=2, pady=3)

        # Bar chart Frame
        bar = tk.Frame(row, bg=C.GAUGE_BG, height=5, width=60)
        bar.pack(side="left", padx=3, pady=3)
        bar.pack_propagate(False)
        bar_fg = tk.Frame(bar, height=5, width=1)
        bar_fg.place(x=0, y=0, height=5, width=1)

        # % label
        pct_lbl = tk.Label(row, font=("Segoe UI", 8), width=5)
        pct_lbl.pack(side="left", padx=2, pady=3)

        # Status Tag label
        status_lbl = tk.Label(row, font=("Segoe UI", 7, "bold"), width=6)
        status_lbl.pack(side="left", padx=2, pady=3)

        # Controls frame container
        ctrl_frame = tk.Frame(row)
        ctrl_frame.pack(side="right", fill="y", padx=(1, 6))

        # Create control buttons inside container
        wake_btn = tk.Label(ctrl_frame, text=" ☀ Wake ", bg=C.GREEN, fg="#0b0e14",
                            font=("Segoe UI", 8, "bold"), cursor="hand2")
        kill_btn = tk.Label(ctrl_frame, text=" ✕ ", bg=C.RED, fg="#fff",
                            font=("Segoe UI", 8, "bold"), cursor="hand2")
        sleep_btn = tk.Label(ctrl_frame, text=" 💤 ", bg=C.SLEEP, fg="#fff",
                             font=("Segoe UI", 8, "bold"), cursor="hand2")

        return {
            'frame': row,
            'rank_lbl': rank_lbl,
            'name_lbl': name_lbl,
            'pid_lbl': pid_lbl,
            'ram_lbl': ram_lbl,
            'bar_fg': bar_fg,
            'pct_lbl': pct_lbl,
            'status_lbl': status_lbl,
            'ctrl_frame': ctrl_frame,
            'wake_btn': wake_btn,
            'kill_btn': kill_btn,
            'sleep_btn': sleep_btn
        }

    def _update_row(self, row_dict, idx, pid, name, rss, pct):
        nl = name.lower()
        essential = self.cfg.is_essential(nl)
        sleeping = pid in self.pm.sleeping

        bg = "#0e0a1a" if sleeping else (C.BG if idx % 2 == 0 else C.CARD)

        # Update backgrounds
        row_dict['frame'].config(bg=bg)
        row_dict['ctrl_frame'].config(bg=bg)

        # Rank
        rank = idx + 1
        bc = {1: C.RED, 2: C.ORANGE, 3: C.YELLOW}.get(rank, C.TEXT3)
        row_dict['rank_lbl'].config(text=f" {rank} ", bg=bc, fg="#fff")

        # Classify
        cls = self.cfg.classify_process(nl, rss)
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
        row_dict['name_lbl'].config(text=d, bg=bg, fg=fg)

        # PID
        row_dict['pid_lbl'].config(text=str(pid), bg=bg, fg=C.TEXT3)

        # RAM
        mc = usage_color(pct * 8)
        row_dict['ram_lbl'].config(text=fmt(rss), bg=bg, fg=mc)

        # Bar Gauge
        bw = max(1, int(min(pct, 100) / 100 * 60))
        row_dict['bar_fg'].config(bg=mc)
        row_dict['bar_fg'].place(x=0, y=0, height=5, width=bw)
        row_dict['bar_fg'].master.config(bg=C.GAUGE_BG)

        # %
        row_dict['pct_lbl'].config(text=f"{pct:.1f}%", bg=bg, fg=C.TEXT2)

        # Status Tag
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
        row_dict['status_lbl'].config(text=tag, bg=bg, fg=tc)

        # Action Buttons configuration
        row_dict['wake_btn'].pack_forget()
        row_dict['kill_btn'].pack_forget()
        row_dict['sleep_btn'].pack_forget()

        if not essential:
            if sleeping:
                # Suspended processes can be WOKEN or KILLED directly
                row_dict['wake_btn'].pack(side="left", padx=2)
                row_dict['kill_btn'].pack(side="left", padx=2)

                row_dict['wake_btn'].bind("<Button-1>", lambda e, p=pid, n=name: self._row_wake(p, n))
                row_dict['kill_btn'].bind("<Button-1>", lambda e, p=pid, n=name: self._row_kill(p, n))
            else:
                # Active processes can be SLEPT or KILLED
                row_dict['sleep_btn'].pack(side="left", padx=2)
                row_dict['kill_btn'].pack(side="left", padx=2)

                row_dict['sleep_btn'].bind("<Button-1>", lambda e, p=pid, n=name: self._row_sleep(p, n))
                row_dict['kill_btn'].bind("<Button-1>", lambda e, p=pid, n=name: self._row_kill(p, n))

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

    # ─── Desktop Widget Toggle ───────────────────────────────────────────

    def toggle_widget(self):
        if self.widget_win and tk.Toplevel.winfo_exists(self.widget_win):
            try:
                self.widget_win.destroy()
            except Exception:
                pass
            self.widget_win = None
            self._status("Widget hidden", C.TEXT3)
        else:
            self.widget_win = RAMWidget(self.root, self.restore_from_tray)
            mem = psutil.virtual_memory()
            self.widget_win.update_val(mem.percent, fmt(mem.used))
            self._status("Widget visible", C.GREEN)

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

    # ─── Helpers & Exit ──────────────────────────────────────────────────

    def _status(self, text, color=C.TEXT3):
        self.status_lbl.config(text=text, fg=color)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        # Minimize to system tray on close instead of exiting
        self.root.withdraw()
        if self.cfg.notifications:
            notifier.send(
                "Yimiter Minimized", 
                "Yimiter is running in the background system tray.",
                self.logo_ico if os.path.exists(self.logo_ico) else None
            )

    def _on_close_full(self):
        self.cfg.save()
        # Wake all sleeping processes before exit to leave system clean
        self.pm.wake_all()
        if self.widget_win:
            try:
                self.widget_win.destroy()
            except Exception:
                pass
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = YimiterApp()
    app.run()

"""
settings_ui.py — Slide-in settings panel overlay widget for YIMITER.
"""

import tkinter as tk
import psutil
from colors import C
from startup import is_startup_enabled, enable_startup, disable_startup
from config import SYSTEM_ESSENTIALS

class SettingsPanel:
    """Full-height slide-in settings panel."""

    def __init__(self, parent, cfg, pm, on_close):
        self.cfg = cfg
        self.pm = pm
        self.on_close = on_close
        self.parent = parent

        # Overlay backdrop
        self.backdrop = tk.Frame(parent, bg="#000000")
        self.backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.backdrop.bind("<Button-1>", lambda e: self.close())

        # Panel frame (right side)
        self.panel = tk.Frame(parent, bg=C.SETTINGS, width=340,
                              highlightbackground=C.BORDER, highlightthickness=1)
        self.panel.place(relx=1, rely=0, relheight=1, width=340, anchor="ne")
        self.panel.pack_propagate(False)

        self._build()

    def _build(self):
        p = self.panel

        # Header
        hdr = tk.Frame(p, bg=C.SETTINGS)
        hdr.pack(fill="x", padx=16, pady=(16, 0))

        tk.Label(hdr, text="⚙️  Settings", bg=C.SETTINGS, fg=C.TEXT,
                 font=("Segoe UI", 16, "bold")).pack(side="left")

        close_btn = tk.Label(hdr, text=" ✕ ", bg=C.RED, fg="#fff",
                              font=("Segoe UI", 11, "bold"), cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.close())

        tk.Frame(p, bg=C.BORDER, height=1).pack(fill="x", padx=16, pady=(12, 0))

        # Scrollable content area
        sf = tk.Frame(p, bg=C.SETTINGS)
        sf.pack(fill="both", expand=True, padx=16, pady=8)

        # ── Section: General ──
        self._section(sf, "General")

        # Limit Mode selection
        self.limit_mode_var = tk.StringVar(value=self.cfg.limit_mode)
        self._setting_row(sf, "🎯 Limit Mode", "")
        lm_frame = tk.Frame(sf, bg=C.SETTINGS)
        lm_frame.pack(anchor="w", padx=8, pady=(0, 6))

        rb_pct = tk.Radiobutton(lm_frame, text="Percentage (%)", variable=self.limit_mode_var,
                                value="percent", bg=C.SETTINGS, fg=C.TEXT, selectcolor=C.CARD,
                                activebackground=C.SETTINGS, activeforeground=C.TEXT,
                                font=("Segoe UI", 9), command=self._update_spin_states)
        rb_pct.pack(side="left", padx=(0, 10))

        rb_gb = tk.Radiobutton(lm_frame, text="Physical RAM (GB)", variable=self.limit_mode_var,
                               value="gb", bg=C.SETTINGS, fg=C.TEXT, selectcolor=C.CARD,
                               activebackground=C.SETTINGS, activeforeground=C.TEXT,
                               font=("Segoe UI", 9), command=self._update_spin_states)
        rb_gb.pack(side="left", padx=(10, 0))

        # RAM Threshold
        self.threshold_var = tk.IntVar(value=self.cfg.threshold)
        self._setting_row(sf, "⚠️ Alert threshold (%)", "%")
        self.spin_pct = tk.Spinbox(sf, from_=10, to=99, textvariable=self.threshold_var, width=5,
                           bg=C.CARD, fg=C.YELLOW, font=("Consolas", 11, "bold"),
                           buttonbackground=C.CARD, relief="flat",
                           highlightthickness=1, highlightbackground=C.BORDER,
                           insertbackground=C.TEXT)
        self.spin_pct.pack(anchor="w", padx=8, pady=(0, 6))

        # Physical RAM limit GB
        total_gb = psutil.virtual_memory().total / (1024**3)
        self.limit_gb_var = tk.DoubleVar(value=self.cfg.limit_gb)
        self._setting_row(sf, "📏 Physical RAM Limit (GB)", "GB")
        self.spin_gb = tk.Spinbox(sf, from_=1.0, to=round(total_gb, 1), increment=0.5,
                          textvariable=self.limit_gb_var, width=5,
                          bg=C.CARD, fg=C.CYAN, font=("Consolas", 11, "bold"),
                          buttonbackground=C.CARD, relief="flat",
                          highlightthickness=1, highlightbackground=C.BORDER,
                          insertbackground=C.TEXT)
        self.spin_gb.pack(anchor="w", padx=8, pady=(0, 6))

        # Refresh interval
        self.refresh_var = tk.IntVar(value=self.cfg.refresh_sec)
        self._setting_row(sf, "🔄 Refresh interval", "seconds")
        spin2 = tk.Spinbox(sf, from_=1, to=10, textvariable=self.refresh_var, width=5,
                           bg=C.CARD, fg=C.CYAN, font=("Consolas", 11, "bold"),
                           buttonbackground=C.CARD, relief="flat",
                           highlightthickness=1, highlightbackground=C.BORDER,
                           insertbackground=C.TEXT)
        spin2.pack(anchor="w", padx=8, pady=(0, 6))

        # Max processes shown
        self.maxrows_var = tk.IntVar(value=self.cfg.max_rows)
        self._setting_row(sf, "📋 Max processes shown", "")
        spin3 = tk.Spinbox(sf, from_=5, to=50, textvariable=self.maxrows_var, width=5,
                           bg=C.CARD, fg=C.BLUE, font=("Consolas", 11, "bold"),
                           buttonbackground=C.CARD, relief="flat",
                           highlightthickness=1, highlightbackground=C.BORDER,
                           insertbackground=C.TEXT)
        spin3.pack(anchor="w", padx=8, pady=(0, 6))

        # Sleep threshold MB
        self.sleep_mb_var = tk.IntVar(value=self.cfg.sleep_above_mb)
        self._setting_row(sf, "💤 Sleep processes above", "MB")
        spin4 = tk.Spinbox(sf, from_=10, to=500, increment=10,
                           textvariable=self.sleep_mb_var, width=5,
                           bg=C.CARD, fg=C.SLEEP, font=("Consolas", 11, "bold"),
                           buttonbackground=C.CARD, relief="flat",
                           highlightthickness=1, highlightbackground=C.BORDER,
                           insertbackground=C.TEXT)
        spin4.pack(anchor="w", padx=8, pady=(0, 6))

        self._update_spin_states()

        tk.Frame(sf, bg=C.BORDER, height=1).pack(fill="x", pady=8)

        # ── Section: Automation ──
        self._section(sf, "Automation")

        self.auto_sleep_var = tk.BooleanVar(value=self.cfg.auto_sleep)
        self._checkbox(sf, "🔴 Auto-kill inactive apps (>20m)", self.auto_sleep_var, C.RED)

        self.auto_start_var = tk.BooleanVar(value=is_startup_enabled())
        self._checkbox(sf, "🚀 Start with Windows", self.auto_start_var, C.CYAN)

        self.minimized_var = tk.BooleanVar(value=self.cfg.start_minimized)
        self._checkbox(sf, "🔽 Start minimized to tray", self.minimized_var, C.TEXT2)

        self.notifications_var = tk.BooleanVar(value=self.cfg.notifications)
        self._checkbox(sf, "🔔 Enable desktop notifications", self.notifications_var, C.YELLOW)

        tk.Frame(sf, bg=C.BORDER, height=1).pack(fill="x", pady=8)

        # ── Section: Crash Prevention ──
        self._section(sf, "💥 Crash Prevention")

        self.crash_prev_var = tk.BooleanVar(value=self.cfg.crash_prevention)
        self._checkbox(sf, "Enable Per-Process RAM Cap", self.crash_prev_var, C.RED,
                       command=self._update_crash_prev_states)

        self.proc_limit_gb_var = tk.DoubleVar(value=self.cfg.proc_limit_gb)
        self._setting_row(sf, "   Max RAM per app (GB)", "GB")
        self.spin_proc_gb = tk.Spinbox(sf, from_=0.5, to=round(total_gb, 1), increment=0.5,
                                       textvariable=self.proc_limit_gb_var, width=5,
                                       bg=C.CARD, fg=C.RED, font=("Consolas", 11, "bold"),
                                       buttonbackground=C.CARD, relief="flat",
                                       highlightthickness=1, highlightbackground=C.BORDER,
                                       insertbackground=C.TEXT)
        self.spin_proc_gb.pack(anchor="w", padx=24, pady=(0, 6))

        self.proc_action_var = tk.StringVar(value=self.cfg.proc_limit_action)
        self._setting_row(sf, "   Action when exceeded", "")
        
        self.act_frame = tk.Frame(sf, bg=C.SETTINGS)
        self.act_frame.pack(anchor="w", padx=24, pady=(0, 6))

        rb_kill = tk.Radiobutton(self.act_frame, text="Kill", variable=self.proc_action_var,
                                 value="kill", bg=C.SETTINGS, fg=C.TEXT, selectcolor=C.CARD,
                                 activebackground=C.SETTINGS, activeforeground=C.TEXT,
                                 font=("Segoe UI", 9))
        rb_kill.pack(side="left", padx=(0, 8))

        rb_sleep = tk.Radiobutton(self.act_frame, text="Sleep", variable=self.proc_action_var,
                                  value="sleep", bg=C.SETTINGS, fg=C.TEXT, selectcolor=C.CARD,
                                  activebackground=C.SETTINGS, activeforeground=C.TEXT,
                                  font=("Segoe UI", 9))
        rb_sleep.pack(side="left", padx=8)

        rb_flush = tk.Radiobutton(self.act_frame, text="Flush", variable=self.proc_action_var,
                                  value="flush", bg=C.SETTINGS, fg=C.TEXT, selectcolor=C.CARD,
                                  activebackground=C.SETTINGS, activeforeground=C.TEXT,
                                  font=("Segoe UI", 9))
        rb_flush.pack(side="left", padx=8)

        self._update_crash_prev_states()

        # System-Wide Crash Guard
        tk.Frame(sf, bg=C.BORDER, height=1).pack(fill="x", pady=8)
        self.sys_crash_guard_var = tk.BooleanVar(value=self.cfg.system_crash_guard)
        self._checkbox(sf, "Enable System-Wide RAM Guard", self.sys_crash_guard_var, C.RED,
                       command=self._update_sys_crash_states)

        self.sys_crash_threshold_var = tk.IntVar(value=self.cfg.system_crash_threshold)
        self._setting_row(sf, "   Trigger threshold (%)", "%")
        self.spin_sys_pct = tk.Spinbox(sf, from_=50, to=99, textvariable=self.sys_crash_threshold_var, width=5,
                                       bg=C.CARD, fg=C.RED, font=("Consolas", 11, "bold"),
                                       buttonbackground=C.CARD, relief="flat",
                                       highlightthickness=1, highlightbackground=C.BORDER,
                                       insertbackground=C.TEXT)
        self.spin_sys_pct.pack(anchor="w", padx=24, pady=(0, 6))

        self.sys_crash_action_var = tk.StringVar(value=self.cfg.system_crash_action)
        self._setting_row(sf, "   Action when triggered", "")
        
        self.sys_act_frame = tk.Frame(sf, bg=C.SETTINGS)
        self.sys_act_frame.pack(anchor="w", padx=24, pady=(0, 6))

        rb_sys_flush = tk.Radiobutton(self.sys_act_frame, text="Flush", variable=self.sys_crash_action_var,
                                      value="flush", bg=C.SETTINGS, fg=C.TEXT, selectcolor=C.CARD,
                                      activebackground=C.SETTINGS, activeforeground=C.TEXT,
                                      font=("Segoe UI", 9))
        rb_sys_flush.pack(side="left", padx=(0, 8))

        rb_sys_sleep = tk.Radiobutton(self.sys_act_frame, text="Sleep Hog", variable=self.sys_crash_action_var,
                                      value="sleep", bg=C.SETTINGS, fg=C.TEXT, selectcolor=C.CARD,
                                      activebackground=C.SETTINGS, activeforeground=C.TEXT,
                                      font=("Segoe UI", 9))
        rb_sys_sleep.pack(side="left", padx=8)

        rb_sys_kill = tk.Radiobutton(self.sys_act_frame, text="Kill Hog", variable=self.sys_crash_action_var,
                                     value="kill", bg=C.SETTINGS, fg=C.TEXT, selectcolor=C.CARD,
                                     activebackground=C.SETTINGS, activeforeground=C.TEXT,
                                     font=("Segoe UI", 9))
        rb_sys_kill.pack(side="left", padx=8)

        self._update_sys_crash_states()

        tk.Frame(sf, bg=C.BORDER, height=1).pack(fill="x", pady=8)

        # ── Section: Whitelist ──
        self._section(sf, "Protected Apps (Whitelist)")

        tk.Label(sf, text="These apps will never be slept or killed:",
                 bg=C.SETTINGS, fg=C.TEXT3, font=("Segoe UI", 8)).pack(anchor="w", padx=8)

        wl_frame = tk.Frame(sf, bg=C.CARD, highlightbackground=C.BORDER, highlightthickness=1)
        wl_frame.pack(fill="x", padx=8, pady=4)

        if self.cfg.user_whitelist:
            for name in sorted(self.cfg.user_whitelist):
                row = tk.Frame(wl_frame, bg=C.CARD)
                row.pack(fill="x")
                tk.Label(row, text=f"  🛡️ {name}", bg=C.CARD, fg=C.GREEN,
                         font=("Segoe UI", 9), anchor="w").pack(side="left", padx=4, pady=2)
                rm = tk.Label(row, text=" ✕ ", bg=C.RED, fg="#fff",
                              font=("Segoe UI", 8), cursor="hand2")
                rm.pack(side="right", padx=4, pady=2)
                rm.bind("<Button-1>", lambda e, n=name: self._remove_whitelist(n))
        else:
            tk.Label(wl_frame, text="  No custom apps whitelisted", bg=C.CARD,
                     fg=C.TEXT3, font=("Segoe UI", 9)).pack(padx=8, pady=6)

        add_btn = tk.Label(sf, text="  ＋ Add running app to whitelist  ", bg=C.BLUE,
                           fg="#0b0e14", font=("Segoe UI", 9, "bold"), cursor="hand2")
        add_btn.pack(anchor="w", padx=8, pady=(4, 8))
        add_btn.bind("<Button-1>", lambda e: self._whitelist_picker())

        tk.Frame(sf, bg=C.BORDER, height=1).pack(fill="x", pady=4)

        # ── Save / Reset buttons ──
        btn_row = tk.Frame(sf, bg=C.SETTINGS)
        btn_row.pack(fill="x", pady=(8, 0))

        save = tk.Label(btn_row, text="  💾 Save Settings  ", bg=C.GREEN, fg="#0b0e14",
                        font=("Segoe UI", 11, "bold"), cursor="hand2")
        save.pack(side="left", padx=(0, 8))
        save.bind("<Button-1>", lambda e: self._save())

        reset = tk.Label(btn_row, text="  ↺ Reset Defaults  ", bg=C.TEXT3, fg=C.TEXT,
                         font=("Segoe UI", 10), cursor="hand2")
        reset.pack(side="left")
        reset.bind("<Button-1>", lambda e: self._reset())

    def _section(self, parent, title):
        tk.Label(parent, text=title, bg=C.SETTINGS, fg=C.TEXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=4, pady=(8, 4))

    def _setting_row(self, parent, label, unit):
        row = tk.Frame(parent, bg=C.SETTINGS)
        row.pack(fill="x", padx=8, pady=(2, 0))
        tk.Label(row, text=label, bg=C.SETTINGS, fg=C.TEXT2,
                 font=("Segoe UI", 9)).pack(side="left")
        if unit:
            tk.Label(row, text=unit, bg=C.SETTINGS, fg=C.TEXT3,
                     font=("Segoe UI", 8)).pack(side="right")

    def _checkbox(self, parent, text, var, color, command=None):
        cb = tk.Checkbutton(parent, text=f"  {text}", variable=var,
                            bg=C.SETTINGS, fg=color, selectcolor=C.CARD,
                            activebackground=C.SETTINGS, activeforeground=color,
                            font=("Segoe UI", 9, "bold"), anchor="w", command=command)
        cb.pack(fill="x", padx=8, pady=2)
        return cb

    def _remove_whitelist(self, name):
        self.cfg.user_whitelist.discard(name)
        self.close()
        self.on_close("removed_whitelist")

    def _whitelist_picker(self):
        dlg = tk.Toplevel(self.parent)
        dlg.title("Add to Whitelist")
        dlg.geometry("360x440")
        dlg.configure(bg=C.BG)
        dlg.transient(self.parent)
        dlg.grab_set()

        tk.Label(dlg, text="Click a process to whitelist it:", bg=C.BG, fg=C.TEXT,
                 font=("Segoe UI", 10, "bold")).pack(padx=12, pady=(12, 6))

        lf = tk.Frame(dlg, bg=C.BG)
        lf.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        canvas = tk.Canvas(lf, bg=C.BG, highlightthickness=0)
        sb = tk.Scrollbar(lf, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=C.BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        names = set()
        for p in psutil.process_iter(['name']):
            try:
                n = p.info['name']
                if n:
                    names.add(n)
            except Exception:
                continue

        for name in sorted(names, key=str.lower):
            nl = name.lower()
            if nl in SYSTEM_ESSENTIALS:
                continue
            already = nl in self.cfg.user_whitelist
            fg = C.GREEN if already else C.TEXT
            suffix = " ✓" if already else ""

            lbl = tk.Label(inner, text=f"  {name}{suffix}", bg=C.BG, fg=fg,
                           font=("Segoe UI", 9), anchor="w", cursor="hand2")
            lbl.pack(fill="x", padx=4, pady=1)
            lbl.bind("<Enter>", lambda e, w=lbl: w.config(bg=C.HOVER))
            lbl.bind("<Leave>", lambda e, w=lbl: w.config(bg=C.BG))

            def add(e, n=nl, d=dlg):
                self.cfg.user_whitelist.add(n)
                d.destroy()
                self.close()
                self.on_close("added_whitelist")

            if not already:
                lbl.bind("<Button-1>", add)

    def _update_spin_states(self):
        if self.limit_mode_var.get() == "percent":
            self.spin_pct.config(state="normal", fg=C.YELLOW)
            self.spin_gb.config(state="disabled", fg=C.TEXT3)
        else:
            self.spin_pct.config(state="disabled", fg=C.TEXT3)
            self.spin_gb.config(state="normal", fg=C.CYAN)

    def _update_crash_prev_states(self):
        state = "normal" if self.crash_prev_var.get() else "disabled"
        fg_spin = C.RED if self.crash_prev_var.get() else C.TEXT3
        self.spin_proc_gb.config(state=state, fg=fg_spin)
        for child in self.act_frame.winfo_children():
            if isinstance(child, tk.Radiobutton):
                child.config(state=state)

    def _update_sys_crash_states(self):
        state = "normal" if self.sys_crash_guard_var.get() else "disabled"
        fg_spin = C.RED if self.sys_crash_guard_var.get() else C.TEXT3
        self.spin_sys_pct.config(state=state, fg=fg_spin)
        for child in self.sys_act_frame.winfo_children():
            if isinstance(child, tk.Radiobutton):
                child.config(state=state)

    def _save(self):
        self.cfg.threshold = self.threshold_var.get()
        self.cfg.limit_mode = self.limit_mode_var.get()
        try:
            self.cfg.limit_gb = float(self.limit_gb_var.get())
        except ValueError:
            self.cfg.limit_gb = 8.0
        self.cfg.crash_prevention = self.crash_prev_var.get()
        try:
            self.cfg.proc_limit_gb = float(self.proc_limit_gb_var.get())
        except ValueError:
            self.cfg.proc_limit_gb = 4.0
        self.cfg.proc_limit_action = self.proc_action_var.get()
        self.cfg.system_crash_guard = self.sys_crash_guard_var.get()
        try:
            self.cfg.system_crash_threshold = int(self.sys_crash_threshold_var.get())
        except ValueError:
            self.cfg.system_crash_threshold = 95
        self.cfg.system_crash_action = self.sys_crash_action_var.get()
        self.cfg.refresh_sec = self.refresh_var.get()
        self.cfg.max_rows = self.maxrows_var.get()
        self.cfg.sleep_above_mb = self.sleep_mb_var.get()
        self.cfg.auto_sleep = self.auto_sleep_var.get()
        self.cfg.start_minimized = self.minimized_var.get()
        self.cfg.notifications = self.notifications_var.get()

        want_startup = self.auto_start_var.get()
        if want_startup and not is_startup_enabled():
            enable_startup()
        elif not want_startup and is_startup_enabled():
            disable_startup()
        self.cfg.auto_start = want_startup

        self.cfg.save()
        self.close()
        self.on_close("saved")

    def _reset(self):
        self.limit_mode_var.set("percent")
        self.threshold_var.set(85)
        self.limit_gb_var.set(8.0)
        self.crash_prev_var.set(False)
        self.proc_limit_gb_var.set(4.0)
        self.proc_action_var.set("kill")
        self.refresh_var.set(2)
        self.maxrows_var.set(20)
        self.sleep_mb_var.set(50)
        self.auto_sleep_var.set(False)
        self.auto_start_var.set(False)
        self.minimized_var.set(False)
        self.notifications_var.set(True)
        self.sys_crash_guard_var.set(True)
        self.sys_crash_threshold_var.set(95)
        self.sys_crash_action_var.set("flush")
        self._update_spin_states()
        self._update_crash_prev_states()
        self._update_sys_crash_states()

    def close(self):
        self.backdrop.destroy()
        self.panel.destroy()

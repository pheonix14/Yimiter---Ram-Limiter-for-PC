"""
config.py — Handles configuration persistence, whitelisting, and defaults for YIMITER.
"""

import os
import sys
import json

frozen = getattr(sys, 'frozen', False)
if frozen:
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "yimiter_config.json")

# ─── Essential / Bloat Whitelists ────────────────────────────────────────

SYSTEM_ESSENTIALS = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "lsaiso.exe",
    "svchost.exe", "fontdrvhost.exe", "dwm.exe", "explorer.exe",
    "taskhostw.exe", "sihost.exe", "ctfmon.exe", "conhost.exe",
    "runtimebroker.exe", "dllhost.exe", "wudfhost.exe",
    "searchindexer.exe", "securityhealthservice.exe", "securityhealthsystray.exe",
    "spoolsv.exe", "audiodg.exe", "msiexec.exe", "taskmgr.exe",
    "smartscreen.exe", "sgrmbroker.exe", "memcompression",
    "dashost.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "textinputhost.exe", "lockapp.exe",
    "nvcontainer.exe", "nvspcaps64.exe", "amdrsserv.exe", "amddvr.exe",
    "igfxem.exe", "igfxhk.exe", "reabordsvc.exe",
    "msmpeng.exe", "nissrv.exe", "mpcmdrun.exe",
    "python.exe", "pythonw.exe", "python3.exe",
    "cmd.exe", "powershell.exe", "windowsterminal.exe", "wt.exe", "code.exe",
    "yimiter.exe",
}

NOTIFICATION_BLOAT = {
    "yourphone.exe", "phoneexperiencehost.exe",
    "gamebar.exe", "gamebarftserver.exe", "gamebarpresencewriter.exe",
    "xbox.tcui.exe", "xboxgamecallableui.exe",
    "cortana.exe", "searchapp.exe", "searchhost.exe",
    "widgets.exe", "widgetservice.exe",
    "msedge.exe", "msedgewebview2.exe", "onedrive.exe",
    "skypeapp.exe", "skypebridge.exe",
    "teams.exe", "teamsupdate.exe", "msteams.exe",
    "slack.exe", "discord.exe", "spotify.exe",
    "steamwebhelper.exe", "epicwebhelper.exe",
    "backgroundtaskhost.exe", "windowscommunicationsapps.exe",
    "hxtsr.exe", "peopleapp.exe", "video.ui.exe", "calculator.exe",
    "whatsapp.exe", "telegram.exe",
    "microsoft.photos.exe", "winstore.app.exe",
    "feedbackhub.exe", "clipchamp.exe",
}

KNOWN_BAD_OR_UNNECESSARY = {
    # Telemetry and background services
    "telemetry.exe", "compattelrunner.exe", "wsqmcons.exe", "invagent.dll",
    "mscorsvw.exe", "jusched.exe", "adobearm.exe", "reader_sl.exe",
    # Notorious updaters
    "googleupdate.exe", "microsoftedgeupdate.exe", "nw_elf.dll",
    "updater.exe", "opera_autoupdate.exe", "firefoxupdater.exe",
    # Adware/Bloatware services
    "ccleaner64.exe", "speedupmycomputer.exe", "driverbooster.exe",
    "webcompanion.exe", "lghub_agent.exe", "overwolf.exe"
}

class Config:
    def __init__(self):
        self.user_whitelist = set()
        self.reserved_apps = {}
        self.threshold = 85
        self.safe_resume_threshold = 72
        self.limit_mode = "percent"
        self.limit_gb = 8.0
        self.crash_prevention = True
        self.proc_limit_gb = 4.0
        self.proc_limit_action = "sleep"
        self.system_crash_guard = True
        self.system_crash_threshold = 95
        self.system_crash_action = "flush"
        self.auto_sleep = True
        self.auto_start = True
        self.refresh_sec = 2
        self.max_rows = 20
        self.sleep_above_mb = 150
        self.activity_window_min = 10
        self.freeze_per_cycle = 1
        self.notifications = True
        self.start_minimized = False
        self.load()

    def load(self):
        try:
            with open(CONFIG_PATH, "r") as f:
                d = json.load(f)
            self.user_whitelist = {self.normalize_name(n) for n in d.get("user_whitelist", [])}
            self.reserved_apps = {
                self.normalize_name(name): int(mb)
                for name, mb in d.get("reserved_apps", {}).items()
                if str(name).strip()
            }
            self.threshold = d.get("threshold", self.threshold)
            self.safe_resume_threshold = d.get("safe_resume_threshold", self.safe_resume_threshold)
            self.limit_mode = d.get("limit_mode", self.limit_mode)
            self.limit_gb = d.get("limit_gb", self.limit_gb)
            self.crash_prevention = d.get("crash_prevention", self.crash_prevention)
            self.proc_limit_gb = d.get("proc_limit_gb", self.proc_limit_gb)
            self.proc_limit_action = d.get("proc_limit_action", self.proc_limit_action)
            self.system_crash_guard = d.get("system_crash_guard", self.system_crash_guard)
            self.system_crash_threshold = d.get("system_crash_threshold", self.system_crash_threshold)
            self.system_crash_action = d.get("system_crash_action", self.system_crash_action)
            self.auto_sleep = d.get("auto_sleep", self.auto_sleep)
            self.auto_start = d.get("auto_start", self.auto_start)
            self.refresh_sec = d.get("refresh_sec", self.refresh_sec)
            self.max_rows = d.get("max_rows", self.max_rows)
            self.sleep_above_mb = d.get("sleep_above_mb", self.sleep_above_mb)
            self.activity_window_min = d.get("activity_window_min", self.activity_window_min)
            self.freeze_per_cycle = d.get("freeze_per_cycle", self.freeze_per_cycle)
            self.notifications = d.get("notifications", self.notifications)
            self.start_minimized = d.get("start_minimized", self.start_minimized)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save(self):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump({
                    "user_whitelist": sorted(self.user_whitelist),
                    "reserved_apps": dict(sorted(self.reserved_apps.items())),
                    "threshold": self.threshold,
                    "safe_resume_threshold": self.safe_resume_threshold,
                    "limit_mode": self.limit_mode,
                    "limit_gb": self.limit_gb,
                    "crash_prevention": self.crash_prevention,
                    "proc_limit_gb": self.proc_limit_gb,
                    "proc_limit_action": self.proc_limit_action,
                    "system_crash_guard": self.system_crash_guard,
                    "system_crash_threshold": self.system_crash_threshold,
                    "system_crash_action": self.system_crash_action,
                    "auto_sleep": self.auto_sleep,
                    "auto_start": self.auto_start,
                    "refresh_sec": self.refresh_sec,
                    "max_rows": self.max_rows,
                    "sleep_above_mb": self.sleep_above_mb,
                    "activity_window_min": self.activity_window_min,
                    "freeze_per_cycle": self.freeze_per_cycle,
                    "notifications": self.notifications,
                    "start_minimized": self.start_minimized,
                }, f, indent=2)
        except Exception:
            pass

    def normalize_name(self, n):
        n = (n or "").strip().lower()
        if not n:
            return n
        return n if n.endswith(".exe") else f"{n}.exe"

    def is_reserved(self, n):
        return self.normalize_name(n) in self.reserved_apps

    def is_essential(self, n):
        n = self.normalize_name(n)
        return n in SYSTEM_ESSENTIALS or n in self.user_whitelist or n in self.reserved_apps

    def is_bloat(self, n):
        return self.normalize_name(n) in NOTIFICATION_BLOAT

    def classify_process(self, name_lower, rss_bytes):
        """Classifies a process, returning a status tag key (e.g. SAFE, BAD, HOG, BLOAT, NORMAL)."""
        name_lower = self.normalize_name(name_lower)
        if self.is_reserved(name_lower):
            return "RESERVED"
        if self.is_essential(name_lower):
            return "SAFE"
        if name_lower in KNOWN_BAD_OR_UNNECESSARY or "update" in name_lower:
            return "BAD"
        if rss_bytes > 500 * 1024 * 1024: # > 500 MB
            return "HOG"
        if self.is_bloat(name_lower):
            return "BLOAT"
        return "NORMAL"

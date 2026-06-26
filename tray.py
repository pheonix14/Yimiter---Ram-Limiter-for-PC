"""
tray.py — Windows system tray manager using pystray for YIMITER.
"""

import os
import threading
from PIL import Image

try:
    import pystray
except ImportError:
    pystray = None


class YimiterTray:
    def __init__(self, icon_path, on_restore, on_widget, on_flush, on_exit):
        self.icon_path = icon_path
        self.on_restore = on_restore
        self.on_widget = on_widget
        self.on_flush = on_flush
        self.on_exit = on_exit
        self.icon = None
        self.thread = None

    def run(self):
        if not pystray:
            return
        
        # Load icon image
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                img = Image.open(self.icon_path)
            except Exception:
                img = Image.new("RGB", (64, 64), (11, 14, 20))
        else:
            img = Image.new("RGB", (64, 64), (11, 14, 20))

        # Define context menu
        menu = pystray.Menu(
            pystray.MenuItem("Restore Yimiter", self.on_restore_wrapper, default=True),
            pystray.MenuItem("Toggle Widget", self.on_widget_wrapper),
            pystray.MenuItem("Free Memory", self.on_flush_wrapper),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.on_exit_wrapper),
        )

        self.icon = pystray.Icon("Yimiter", img, "Yimiter RAM Manager", menu)
        
        # Start pystray event loop in a daemon thread
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def on_restore_wrapper(self, icon, item):
        self.on_restore()

    def on_widget_wrapper(self, icon, item):
        self.on_widget()

    def on_flush_wrapper(self, icon, item):
        self.on_flush()

    def on_exit_wrapper(self, icon, item):
        self.on_exit()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None

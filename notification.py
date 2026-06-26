"""
notification.py — Asynchronous Windows Balloon Notifications using pywin32.
"""

import os
import time
import threading

try:
    import win32api
    import win32con
    import win32gui
except ImportError:
    win32api = None
    win32con = None
    win32gui = None


class WinNotificationManager:
    def __init__(self, app_name="Yimiter"):
        self.app_name = app_name
        self._class_atom = None
        self._registered = False
        if win32gui:
            self._register_class()

    def _register_class(self):
        try:
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = lambda hwnd, msg, wp, lp: win32gui.DefWindowProc(hwnd, msg, wp, lp)
            wc.lpszClassName = "YimiterNotificationWindow"
            wc.hInstance = win32api.GetModuleHandle(None)
            self._class_atom = win32gui.RegisterClass(wc)
            self._registered = True
        except Exception:
            # Class might already exist
            self._registered = True

    def send(self, title, message, icon_path=None):
        if not win32gui or not self._registered:
            # Fallback or silent if pywin32 is not available
            return

        def run():
            try:
                hwnd = win32gui.CreateWindow(
                    "YimiterNotificationWindow" if self._class_atom is None else self._class_atom,
                    "YimiterNotification",
                    win32con.WS_OVERLAPPED | win32con.WS_SYSMENU,
                    0, 0, 0, 0, 0, 0, win32api.GetModuleHandle(None), None
                )
                win32gui.UpdateWindow(hwnd)

                hicon = None
                if icon_path and os.path.exists(icon_path):
                    try:
                        hicon = win32gui.LoadImage(
                            None, icon_path, win32con.IMAGE_ICON,
                            0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
                        )
                    except Exception:
                        pass
                if not hicon:
                    hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

                flags = win32con.NIF_ICON | win32con.NIF_MESSAGE | win32con.NIF_TIP
                nid = (hwnd, 0, flags, win32con.WM_USER + 20, hicon, self.app_name)
                win32gui.Shell_NotifyIcon(win32con.NIM_ADD, nid)

                # Show balloon tip
                nid = (hwnd, 0, win32con.NIF_INFO, win32con.WM_USER + 20,
                       hicon, self.app_name, message, 5000, title, win32con.NIIF_INFO)
                win32gui.Shell_NotifyIcon(win32con.NIM_MODIFY, nid)

                # Sleep to let balloon tip display before cleaning up
                time.sleep(5)

                # Cleanup
                win32gui.Shell_NotifyIcon(win32con.NIM_DELETE, (hwnd, 0))
                win32gui.DestroyWindow(hwnd)
            except Exception as e:
                print(f"[Yimiter Notify Error] {e}")

        threading.Thread(target=run, daemon=True).start()


# Global notifier instance
notifier = WinNotificationManager()


if __name__ == "__main__":
    # Test notification
    print("Sending test notification...")
    notifier.send("Yimiter test", "This is a test notification from Yimiter.")
    time.sleep(6)

"""
startup.py — Windows startup registry configuration for YIMITER.
"""

import sys
import os
import winreg

APP_NAME = "Yimiter"
STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = "Yimiter"

def get_launch_command():
    # If compiled with PyInstaller, sys.executable points to the EXE.
    # Otherwise, it points to python.exe and we need the script path.
    frozen = getattr(sys, 'frozen', False)
    if frozen:
        return f'"{sys.executable}"'
    else:
        main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        return f'"{sys.executable}" "{main_script}"'

def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, STARTUP_REG_NAME)
        winreg.CloseKey(key)
        # Check if the command matches approximately
        cmd = get_launch_command().replace('"', '').lower()
        return cmd in val.replace('"', '').lower()
    except (FileNotFoundError, OSError):
        return False

def enable_startup():
    try:
        cmd = get_launch_command()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def disable_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, STARTUP_REG_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return True
    except Exception:
        return False

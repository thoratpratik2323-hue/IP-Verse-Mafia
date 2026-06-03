"""
startup_installer.py — IP Prime Windows Auto-Launch Installer

Run this ONCE to register IP Prime as a Windows startup program.
After this, every time your PC turns on → IP Prime starts automatically!

Usage:
    python startup_installer.py install    ← Register startup
    python startup_installer.py remove     ← Remove from startup
    python startup_installer.py status     ← Check if registered
"""

import sys
import os
import winreg
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent
PYTHON_EXE  = sys.executable
WATCHDOG    = BASE_DIR / "watchdog.py"
MAIN_PY     = BASE_DIR / "main.py"

APP_NAME    = "IPPrime"
REG_KEY     = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_launch_command() -> str:
    """Returns the command that Windows will run at startup."""
    # Use watchdog so Prime auto-recovers from crashes
    return f'"{PYTHON_EXE}" "{WATCHDOG}"'


def install_startup():
    """Adds IP Prime to Windows registry startup."""
    cmd = _get_launch_command()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_KEY,
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        print(f"✅ IP Prime registered for auto-start on Windows boot!")
        print(f"   Command: {cmd}")
        print(f"\n💡 Now every time your PC starts, IP Prime will launch automatically.")
        print(f"   To remove: python startup_installer.py remove")
    except Exception as e:
        print(f"❌ Failed to register startup: {e}")
        print("   Try running as Administrator if this fails.")


def remove_startup():
    """Removes IP Prime from Windows startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_KEY,
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print(f"✅ IP Prime removed from Windows startup.")
    except FileNotFoundError:
        print("ℹ️ IP Prime was not in startup list.")
    except Exception as e:
        print(f"❌ Failed to remove startup entry: {e}")


def check_status():
    """Checks if IP Prime is registered for startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_KEY,
            0,
            winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        print(f"✅ IP Prime IS registered for Windows startup.")
        print(f"   Command: {value}")
        return True
    except FileNotFoundError:
        print("❌ IP Prime is NOT registered for Windows startup.")
        print(f"   Run: python startup_installer.py install")
        return False
    except Exception as e:
        print(f"❌ Could not check status: {e}")
        return False


if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "status"

    print("=" * 55)
    print("  IP Prime -- Windows Startup Manager")
    print("=" * 55)

    if action == "install":
        install_startup()
    elif action == "remove":
        remove_startup()
    elif action == "status":
        check_status()
    else:
        print(f"Unknown action: {action}")
        print("Usage: python startup_installer.py [install|remove|status]")

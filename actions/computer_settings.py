"""
computer_settings.py — Manages clipboard, hardware metrics, running windows, and general PC settings.

This is a standard action module for the IP Prime personal assistant suite.
"""

#computer_settings.py
import json
import re
import sys
import time
import subprocess
import platform
import threading
import random
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_api_key() -> str:
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]

def _get_macos_wifi_interface() -> str:
    try:
        result = subprocess.run(
            ["networksetup", "-listallhardwareports"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.splitlines()
        for i, line in enumerate(lines):
            if "Wi-Fi" in line or "AirPort" in line:
                for j in range(i, min(i + 4, len(lines))):
                    if lines[j].startswith("Device:"):
                        return lines[j].split(":", 1)[1].strip()
    except Exception:
        pass
    return "en0" 

def get_open_windows() -> str:
    try:
        import pygetwindow as gw
        windows = gw.getAllWindows()
        titles = []
        for w in windows:
            if w.title and w.title.strip():
                try:
                    if w.width > 0 and w.height > 0:
                        titles.append(w.title.strip())
                except Exception:
                    pass
        seen = set()
        dedup = []
        for t in titles:
            if t not in seen:
                seen.add(t)
                dedup.append(t)
        if not dedup:
            return "No active, visible windows found."
        return "Active Windows:\n" + "\n".join(f"- {title}" for title in dedup)
    except Exception as e:
        return f"Failed to list open windows: {e}"

def focus_window_by_title(title: str) -> str:
    if not title:
        return "Please specify a window title to focus."
    try:
        import pygetwindow as gw
        import ctypes
        query = title.lower().strip()
        windows = gw.getAllWindows()
        best_match = None
        for w in windows:
            if w.title and query in w.title.lower():
                best_match = w
                break
        if not best_match:
            return f"Could not find any window matching '{title}'."
        
        hwnd = best_match._hWnd
        try:
            if best_match.isMinimized:
                ctypes.windll.user32.ShowWindow(hwnd, 9) # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return f"Focused window: '{best_match.title}'."
        except Exception:
            try:
                best_match.activate()
                return f"Focused window: '{best_match.title}'."
            except Exception as e2:
                return f"Found '{best_match.title}' but failed to focus: {e2}"
    except Exception as e:
        return f"Failed to focus window: {e}"

def resize_window_by_title(title: str, width: int, height: int) -> str:
    if not title:
        return "Please specify a window title to resize."
    try:
        import pygetwindow as gw
        query = title.lower().strip()
        windows = gw.getAllWindows()
        best_match = None
        for w in windows:
            if w.title and query in w.title.lower():
                best_match = w
                break
        if not best_match:
            return f"Could not find any window matching '{title}'."
        
        best_match.resizeTo(width, height)
        return f"Resized window '{best_match.title}' to {width}x{height}."
    except Exception as e:
        return f"Failed to resize window: {e}"

def move_window_by_title(title: str, x: int, y: int) -> str:
    if not title:
        return "Please specify a window title to move."
    try:
        import pygetwindow as gw
        query = title.lower().strip()
        windows = gw.getAllWindows()
        best_match = None
        for w in windows:
            if w.title and query in w.title.lower():
                best_match = w
                break
        if not best_match:
            return f"Could not find any window matching '{title}'."
        
        best_match.moveTo(x, y)
        return f"Moved window '{best_match.title}' to ({x}, {y})."
    except Exception as e:
        return f"Failed to move window: {e}"

def minimize_window_by_title(title: str) -> str:
    if not title:
        return "Please specify a window title to minimize."
    try:
        import pygetwindow as gw
        query = title.lower().strip()
        windows = gw.getAllWindows()
        best_match = None
        for w in windows:
            if w.title and query in w.title.lower():
                best_match = w
                break
        if not best_match:
            return f"Could not find any window matching '{title}'."
        
        best_match.minimize()
        return f"Minimized window '{best_match.title}'."
    except Exception as e:
        return f"Failed to minimize window: {e}"

def maximize_window_by_title(title: str) -> str:
    if not title:
        return "Please specify a window title to maximize."
    try:
        import pygetwindow as gw
        query = title.lower().strip()
        windows = gw.getAllWindows()
        best_match = None
        for w in windows:
            if w.title and query in w.title.lower():
                best_match = w
                break
        if not best_match:
            return f"Could not find any window matching '{title}'."
        
        best_match.maximize()
        return f"Maximized window '{best_match.title}'."
    except Exception as e:
        return f"Failed to maximize window: {e}"

def close_window_by_title(title: str) -> str:
    if not title:
        return "Please specify a window title to close."
    try:
        import pygetwindow as gw
        query = title.lower().strip()
        windows = gw.getAllWindows()
        best_match = None
        for w in windows:
            if w.title and query in w.title.lower():
                best_match = w
                break
        if not best_match:
            return f"Could not find any window matching '{title}'."
        
        best_match.close()
        return f"Closed window '{best_match.title}'."
    except Exception as e:
        return f"Failed to close window: {e}"

def get_clipboard() -> str:
    if not _PYPERCLIP:
        return "pyperclip is not installed."
    try:
        val = pyperclip.paste()
        if not val:
            return "Clipboard is empty."
        return f"Clipboard Content:\n{val}"
    except Exception as e:
        return f"Failed to read clipboard: {e}"

def set_clipboard(text: str) -> str:
    if not _PYPERCLIP:
        return "pyperclip is not installed."
    try:
        pyperclip.copy(text)
        return "Text copied to clipboard successfully."
    except Exception as e:
        return f"Failed to copy to clipboard: {e}"

def type_clipboard() -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed."
    try:
        pyautogui.hotkey("ctrl", "v")
        return "Clipboard content pasted/typed on screen."
    except Exception as e:
        return f"Failed to type clipboard content: {e}"

def _notes_file() -> Path:
    d = Path.home() / ".ipprime"
    d.mkdir(parents=True, exist_ok=True)
    return d / "notes.txt"

def add_note(note_text: str) -> str:
    if not note_text:
        return "No note text provided."
    from datetime import datetime
    file = _notes_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {note_text}\n"
    try:
        with open(file, "a", encoding="utf-8") as f:
            f.write(formatted)
        return "Note added successfully."
    except Exception as e:
        return f"Failed to write note: {e}"

def read_notes() -> str:
    file = _notes_file()
    if not file.exists() or file.stat().st_size == 0:
        return "You have no notes saved yet."
    try:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        return f"Your Saved Notes:\n{content}"
    except Exception as e:
        return f"Failed to read notes: {e}"

def clear_notes() -> str:
    file = _notes_file()
    if not file.exists():
        return "No notes to clear."
    try:
        file.unlink(missing_ok=True)
        return "All notes cleared successfully."
    except Exception as e:
        return f"Failed to clear notes: {e}" 

def volume_up():
    if _OS == "Windows":
        if not _PYAUTOGUI:
            print("[Settings] pyautogui not available for volume_up")
            return
        for _ in range(5): pyautogui.press("volumeup")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            "set volume output volume (output volume of (get volume settings) + 10)"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
            capture_output=True)

def volume_down():
    if _OS == "Windows":
        if not _PYAUTOGUI:
            print("[Settings] pyautogui not available for volume_down")
            return
        for _ in range(5): pyautogui.press("volumedown")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            "set volume output volume (output volume of (get volume settings) - 10)"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"],
            capture_output=True)

def volume_mute():
    if _OS == "Windows":
        pyautogui.press("volumemute")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", "set volume with output muted"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            capture_output=True)

def volume_set(value: int):
    value = max(0, min(100, int(value)))
    if _OS == "Windows":
        try:
            from pycaw.pycaw import AudioUtilities
            device = AudioUtilities.GetSpeakers()
            vol = device.EndpointVolume
            vol.SetMasterVolumeLevelScalar(value / 100.0, None)
            return
        except Exception as e:
            print(f"[Settings] pycaw failed, using keypress fallback: {e}")
            if _PYAUTOGUI:
                pyautogui.press("volumemute")
                pyautogui.press("volumemute")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", f"set volume output volume {value}"],
            capture_output=True)
        return
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{value}%"],
            capture_output=True)
        return

def _win_brightness_get() -> int:
    """Get current Windows brightness (0-100). Returns -1 on failure."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness"],
            capture_output=True, text=True, timeout=5
        )
        val = r.stdout.strip()
        if val.isdigit():
            return int(val)
    except Exception:
        pass
    return -1


def _win_brightness_set(level: int) -> bool:
    """Set Windows brightness to level (0-100). Returns True on success."""
    level = max(0, min(100, int(level)))
    # Method 1: screen-brightness-control Python library (most reliable)
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"[Settings] sbc failed: {e}")
    # Method 2: WMI via PowerShell
    try:
        ps_cmd = (
            f"$monitors = Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods; "
            f"if ($monitors) {{ $monitors | ForEach-Object {{ $_.WmiSetBrightness(1, {level}) }} }}"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=6
        )
        if r.returncode == 0:
            return True
        print(f"[Settings] WMI brightness failed: {r.stderr.strip()}")
    except Exception as e:
        print(f"[Settings] WMI brightness exception: {e}")
    # Method 3: nircmd (if installed)
    try:
        nircmd = subprocess.run(["where", "nircmd"], capture_output=True, text=True)
        if nircmd.returncode == 0:
            subprocess.run(["nircmd", "setbrightness", str(level)], capture_output=True, timeout=4)
            return True
    except Exception:
        pass
    return False


def brightness_up():
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to key code 144'],
            capture_output=True)
    elif _OS == "Linux":
        if subprocess.run(["which", "brightnessctl"],
                capture_output=True).returncode == 0:
            subprocess.run(["brightnessctl", "set", "+10%"], capture_output=True)
        else:
            subprocess.run(
                'xrandr --output $(xrandr | grep " connected" | head -1 | cut -d " " -f1)'
                ' --brightness $(python3 -c "import subprocess; '
                'b=float(subprocess.check_output([\"xrandr\",\"--verbose\"]).decode()'
                '.split(\"Brightness:\")[1].split()[0]); print(min(1.0,b+0.1))")',
                shell=True, capture_output=True
            )
    else:  # Windows
        cur = _win_brightness_get()
        new_val = min(100, (cur if cur >= 0 else 50) + 10)
        ok = _win_brightness_set(new_val)
        if not ok:
            print("[Settings] brightness_up: all methods failed. Consider: pip install screen-brightness-control")


def brightness_down():
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to key code 145'],
            capture_output=True)
    elif _OS == "Linux":
        if subprocess.run(["which", "brightnessctl"],
                capture_output=True).returncode == 0:
            subprocess.run(["brightnessctl", "set", "10%-"], capture_output=True)
        else:
            subprocess.run(
                'xrandr --output $(xrandr | grep " connected" | head -1 | cut -d " " -f1)'
                ' --brightness $(python3 -c "import subprocess; '
                'b=float(subprocess.check_output([\"xrandr\",\"--verbose\"]).decode()'
                '.split(\"Brightness:\")[1].split()[0]); print(max(0.1,b-0.1))")',
                shell=True, capture_output=True
            )
    else:  # Windows
        cur = _win_brightness_get()
        new_val = max(0, (cur if cur >= 0 else 50) - 10)
        ok = _win_brightness_set(new_val)
        if not ok:
            print("[Settings] brightness_down: all methods failed. Consider: pip install screen-brightness-control")


def brightness_set(value: int):
    """Set brightness to exact level (0-100)."""
    value = max(0, min(100, int(value)))
    if _OS == "Darwin":
        script = f'tell application "System Events" to set brightness of (first display) to {value / 100}'
        subprocess.run(["osascript", "-e", script], capture_output=True)
    elif _OS == "Linux":
        if subprocess.run(["which", "brightnessctl"], capture_output=True).returncode == 0:
            subprocess.run(["brightnessctl", "set", f"{value}%"], capture_output=True)
        else:
            frac = round(value / 100, 2)
            subprocess.run(
                f'xrandr --output $(xrandr | grep " connected" | head -1 | cut -d " " -f1) --brightness {frac}',
                shell=True, capture_output=True
            )
    else:  # Windows
        ok = _win_brightness_set(value)
        if not ok:
            print(f"[Settings] brightness_set({value}): all methods failed. Consider: pip install screen-brightness-control")

def close_app():
    if _OS == "Darwin": pyautogui.hotkey("command", "q")
    else:               pyautogui.hotkey("alt", "f4")

def close_window():
    if _OS == "Darwin": pyautogui.hotkey("command", "w")
    else:               pyautogui.hotkey("ctrl", "w")

def full_screen():
    if _OS == "Darwin": pyautogui.hotkey("ctrl", "command", "f")
    else:               pyautogui.press("f11")

def minimize_window():
    if _OS == "Darwin": pyautogui.hotkey("command", "m")
    else:               pyautogui.hotkey("win", "down")

def maximize_window():
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to keystroke "f" '
            'using {control down, command down}'],
            capture_output=True)
    elif _OS == "Windows":
        pyautogui.hotkey("win", "up")
    else:
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"],
                capture_output=True)
        except Exception:
            pyautogui.hotkey("super", "up")

def snap_left():
    if _OS == "Windows":
        pyautogui.hotkey("win", "left")
    elif _OS == "Linux":
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-e", "0,0,0,960,1080"],
                capture_output=True)
        except Exception:
            pass

def snap_right():
    if _OS == "Windows":
        pyautogui.hotkey("win", "right")
    elif _OS == "Linux":
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-e", "0,960,0,960,1080"],
                capture_output=True)
        except Exception:
            pass

def switch_window():
    if _OS == "Darwin": pyautogui.hotkey("command", "tab")
    else:               pyautogui.hotkey("alt", "tab")

def show_desktop():
    if _OS == "Darwin":   pyautogui.hotkey("fn", "f11")
    elif _OS == "Windows": pyautogui.hotkey("win", "d")
    else:                  pyautogui.hotkey("super", "d")

def open_task_manager():
    if _OS == "Windows":
        pyautogui.hotkey("ctrl", "shift", "esc")
    elif _OS == "Darwin":
        subprocess.Popen(["open", "-a", "Activity Monitor"])
    else:
        for cmd in [["gnome-system-monitor"], ["xfce4-taskmanager"], ["htop"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                break


def focus_search():
    if _OS == "Darwin": pyautogui.hotkey("command", "l")
    else:               pyautogui.hotkey("ctrl", "l")

def pause_video():      pyautogui.press("space")

def refresh_page():
    if _OS == "Darwin": pyautogui.hotkey("command", "r")
    else:               pyautogui.press("f5")

def close_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "w")
    else:               pyautogui.hotkey("ctrl", "w")

def new_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "t")
    else:               pyautogui.hotkey("ctrl", "t")

def next_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "bracketright")
    else:               pyautogui.hotkey("ctrl", "tab")

def prev_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "bracketleft")
    else:               pyautogui.hotkey("ctrl", "shift", "tab")

def go_back():
    if _OS == "Darwin": pyautogui.hotkey("command", "left")
    else:               pyautogui.hotkey("alt", "left")

def go_forward():
    if _OS == "Darwin": pyautogui.hotkey("command", "right")
    else:               pyautogui.hotkey("alt", "right")

def zoom_in():
    if _OS == "Darwin": pyautogui.hotkey("command", "equal")
    else:               pyautogui.hotkey("ctrl", "equal")

def zoom_out():
    if _OS == "Darwin": pyautogui.hotkey("command", "minus")
    else:               pyautogui.hotkey("ctrl", "minus")

def zoom_reset():
    if _OS == "Darwin": pyautogui.hotkey("command", "0")
    else:               pyautogui.hotkey("ctrl", "0")

def find_on_page():
    if _OS == "Darwin": pyautogui.hotkey("command", "f")
    else:               pyautogui.hotkey("ctrl", "f")

def reload_page_n(n: int):
    for _ in range(max(1, n)):
        refresh_page()
        time.sleep(0.8)


def scroll_up(amount: int = 500):    pyautogui.scroll(amount)
def scroll_down(amount: int = 500):  pyautogui.scroll(-amount)

def scroll_top():
    if _OS == "Darwin": pyautogui.hotkey("command", "up")
    else:               pyautogui.hotkey("ctrl", "home")

def scroll_bottom():
    if _OS == "Darwin": pyautogui.hotkey("command", "down")
    else:               pyautogui.hotkey("ctrl", "end")

def page_up():   pyautogui.press("pageup")
def page_down(): pyautogui.press("pagedown")


def copy():
    if _OS == "Darwin": pyautogui.hotkey("command", "c")
    else:               pyautogui.hotkey("ctrl", "c")

def paste():
    if _OS == "Darwin": pyautogui.hotkey("command", "v")
    else:               pyautogui.hotkey("ctrl", "v")

def cut():
    if _OS == "Darwin": pyautogui.hotkey("command", "x")
    else:               pyautogui.hotkey("ctrl", "x")

def undo():
    if _OS == "Darwin": pyautogui.hotkey("command", "z")
    else:               pyautogui.hotkey("ctrl", "z")

def redo():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "z")
    else:               pyautogui.hotkey("ctrl", "y")

def select_all():
    if _OS == "Darwin": pyautogui.hotkey("command", "a")
    else:               pyautogui.hotkey("ctrl", "a")

def save_file():
    if _OS == "Darwin": pyautogui.hotkey("command", "s")
    else:               pyautogui.hotkey("ctrl", "s")

def press_enter():   pyautogui.press("enter")
def press_escape():  pyautogui.press("escape")
def press_key(key: str): pyautogui.press(key)

def type_text(text: str, press_enter_after: bool = False):
    if not text:
        return
    if _PYPERCLIP:
        pyperclip.copy(str(text))
        time.sleep(0.15)
        paste()
    else:
        pyautogui.write(str(text), interval=0.03)
    if press_enter_after:
        time.sleep(0.1)
        pyautogui.press("enter")

def take_screenshot():
    if _OS == "Windows":
        pyautogui.hotkey("win", "shift", "s")
    elif _OS == "Darwin":
        pyautogui.hotkey("command", "shift", "3")
    else:
        for cmd in [["scrot"], ["gnome-screenshot"], ["import", "-window", "root", "screenshot.png"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return
        pyautogui.hotkey("ctrl", "print_screen")

def lock_screen():
    if _OS == "Windows":
        pyautogui.hotkey("win", "l")
    elif _OS == "Darwin":
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
    else:
        for cmd in [
            ["gnome-screensaver-command", "-l"],
            ["xdg-screensaver", "lock"],
            ["loginctl", "lock-session"],
        ]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.run(cmd, capture_output=True)
                return

def open_system_settings():
    if _OS == "Windows":
        pyautogui.hotkey("win", "i")
    elif _OS == "Darwin":
        subprocess.Popen(["open", "-a", "System Preferences"])
    else:
        for cmd in [["gnome-control-center"], ["xfce4-settings-manager"], ["kcmshell5"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return

def open_file_explorer():
    if _OS == "Windows":
        pyautogui.hotkey("win", "e")
    elif _OS == "Darwin":
        subprocess.Popen(["open", str(Path.home())])
    else:
        for cmd in [["nautilus"], ["thunar"], ["dolphin"], ["nemo"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return
        subprocess.Popen(["xdg-open", str(Path.home())])

def sleep_display():
    if _OS == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        except Exception as e:
            print(f"[Settings] sleep_display failed: {e}")
    elif _OS == "Darwin":
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
    else:
        subprocess.run(["xset", "dpms", "force", "off"], capture_output=True)

def open_run():
    if _OS == "Windows":
        pyautogui.hotkey("win", "r")

def dark_mode():
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell app "System Events" to tell appearance preferences '
            'to set dark mode to not dark mode'],
            capture_output=True)
    elif _OS == "Windows":
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            current, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 1 - current)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 1 - current)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[Settings] dark_mode registry failed: {e}")
    else:
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True
            )
            current = result.stdout.strip()
            new_scheme = "'default'" if "dark" in current else "'prefer-dark'"
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", new_scheme],
                capture_output=True
            )
        except Exception as e:
            print(f"[Settings] dark_mode Linux failed: {e}")

def toggle_wifi():
    if _OS == "Darwin":
        iface = _get_macos_wifi_interface()
        result = subprocess.run(
            ["networksetup", "-getairportpower", iface],
            capture_output=True, text=True
        )
        state = "off" if "On" in result.stdout else "on"
        subprocess.run(["networksetup", "-setairportpower", iface, state],
            capture_output=True)
    elif _OS == "Windows":
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "$adapter = Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'};"
                 "if ($adapter.Status -eq 'Up') { Disable-NetAdapter -Name $adapter.Name -Confirm:$false }"
                 "else { Enable-NetAdapter -Name $adapter.Name -Confirm:$false }"],
                capture_output=True, timeout=10
            )
        except Exception as e:
            print(f"[Settings] toggle_wifi Windows failed: {e}")
    else:
        try:
            result = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True)
            state  = "off" if "enabled" in result.stdout else "on"
            subprocess.run(["nmcli", "radio", "wifi", state], capture_output=True)
        except Exception as e:
            print(f"[Settings] toggle_wifi Linux failed: {e}")

def restart_computer():
    if _OS == "Windows":
        subprocess.run(["shutdown", "/r", "/t", "10"], capture_output=True)
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to restart'],
            capture_output=True)
    else:
        subprocess.run(["systemctl", "reboot"], capture_output=True)

def shutdown_computer():
    if _OS == "Windows":
        subprocess.run(["shutdown", "/s", "/t", "10"], capture_output=True)
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to shut down'],
            capture_output=True)
    else:
        subprocess.run(["systemctl", "poweroff"], capture_output=True)

def switch_app(name: str) -> str:
    """Activate an open application window by name using robust Win32 APIs via PowerShell."""
    if not name or name.strip() in ("", "None"):
        return "Which application should I switch to, Sir?"
    name_l = name.lower().strip()
    PROCESS_NAMES = {
        "chrome": "chrome", "browser": "chrome", "firefox": "firefox",
        "notepad": "notepad", "vs code": "code", "code": "code",
        "spotify": "spotify", "calculator": "calculator", "calc": "calculator",
        "paint": "mspaint", "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    }
    proc_name = PROCESS_NAMES.get(name_l, name_l)
    if _OS == "Windows":
        def worker():
            try:
                ps_script = (
                    "add-type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
                    "public class Win32 { [DllImport(\\\"user32.dll\\\")] public static extern bool SetForegroundWindow(IntPtr hWnd); "
                    "[DllImport(\\\"user32.dll\\\")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow); }';"
                    f"$proc = Get-Process | Where-Object {{ $_.ProcessName -eq '{proc_name}' -or $_.MainWindowTitle -like '*{name_l}*' -or $_.ProcessName -like '*{name_l}*' }} | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1;"
                    "if ($proc) { [Win32]::ShowWindowAsync($proc.MainWindowHandle, 9) | Out-Null; [Win32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null; Write-Output 'Success' } else { Write-Output 'NotFound' }"
                )
                subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                print(f"[SWITCH APP ERR] {e}")
        threading.Thread(target=worker, daemon=True).start()
        return random.choice([f"Switching to {name} now, Sir.", f"Bringing {name} to full focus, Sir.", f"Switched focus to {name}."])
    return "Window switching is only supported on Windows, Sir."


def automate_youtube(action: str) -> str:
    """Execute YouTube control shortcuts in the active browser."""
    if _OS != "Windows":
        return "YouTube controls are only supported on Windows, Sir."
    action_l = action.lower().strip()
    def worker():
        try:
            ps_script = '$wshell = New-Object -ComObject wscript.shell; Get-Process | Where-Object {$_.MainWindowTitle -like "*YouTube*"} | ForEach-Object { $wshell.AppActivate($_.Id) }'
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.3)
            if "pause" in action_l or "play" in action_l or "resume" in action_l:
                pyautogui.press('k')
            elif "mute" in action_l or "unmute" in action_l:
                pyautogui.press('m')
            elif "volume up" in action_l or "sound up" in action_l:
                pyautogui.press('up')
            elif "volume down" in action_l or "sound down" in action_l:
                pyautogui.press('down')
            elif "forward" in action_l or "skip forward" in action_l:
                pyautogui.press('l')
            elif "rewind" in action_l or "skip backward" in action_l:
                pyautogui.press('j')
            elif "next video" in action_l or "skip video" in action_l:
                pyautogui.hotkey('shift', 'n')
            elif "full screen" in action_l or "fullscreen" in action_l:
                pyautogui.press('f')
            elif "theater" in action_l:
                pyautogui.press('t')
            elif "subtitle" in action_l or "captions" in action_l:
                pyautogui.press('c')
        except Exception as e:
            print(f"[YOUTUBE ERR] {e}")
    threading.Thread(target=worker, daemon=True).start()
    responses = {
        "pause": "Toggled play/pause on YouTube, Sir.", "play": "Toggled play/pause on YouTube, Sir.",
        "resume": "Toggled play/pause on YouTube, Sir.", "mute": "Toggled mute on YouTube, Sir.",
        "unmute": "Toggled mute on YouTube, Sir.", "volume up": "Volume increased on YouTube, Sir.",
        "sound up": "Volume increased on YouTube, Sir.", "volume down": "Volume decreased on YouTube, Sir.",
        "sound down": "Volume decreased on YouTube, Sir.", "forward": "Skipped forward 10 seconds, Sir.",
        "skip forward": "Skipped forward 10 seconds, Sir.", "rewind": "Rewound 10 seconds, Sir.",
        "skip backward": "Rewound 10 seconds, Sir.", "next video": "Skipped to next video, Sir.",
        "skip video": "Skipped to next video, Sir.", "full screen": "Toggled fullscreen on YouTube, Sir.",
        "fullscreen": "Toggled fullscreen on YouTube, Sir.", "theater": "Toggled theater mode, Sir.",
        "subtitle": "Toggled captions on YouTube, Sir.", "captions": "Toggled captions on YouTube, Sir.",
    }
    for key, resp in responses.items():
        if key in action_l:
            return resp
    return "YouTube action not recognized, Sir."


def automate_browser(browser: str, action: str) -> str:
    """Execute browser shortcut automations in Chrome or Firefox."""
    if _OS != "Windows":
        return "Browser shortcuts are only supported on Windows, Sir."
    browser_l = browser.lower().strip()
    browser_title = "Chrome" if "chrome" in browser_l else "Firefox"
    action_l = action.lower().strip()
    def worker():
        try:
            ps_script = f'$wshell = New-Object -ComObject wscript.shell; $s = $wshell.AppActivate("{browser_title}"); Write-Output $s'
            res = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.stdout.strip().lower() != "true":
                ps_fallback = f'Get-Process | Where-Object {{$_.MainWindowTitle -like "*{browser_title.lower()}*"}} | ForEach-Object {{ $wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate($_.Id) }}'
                subprocess.run(["powershell", "-Command", ps_fallback], creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(0.3)
            if "new tab" in action_l or "open tab" in action_l:
                pyautogui.hotkey('ctrl', 't')
            elif "close tab" in action_l:
                pyautogui.hotkey('ctrl', 'w')
            elif "next tab" in action_l or "switch tab" in action_l:
                pyautogui.hotkey('ctrl', 'tab')
            elif "prev tab" in action_l or "previous tab" in action_l:
                pyautogui.hotkey('ctrl', 'shift', 'tab')
            elif "scroll down" in action_l:
                pyautogui.press('pagedown')
            elif "scroll up" in action_l:
                pyautogui.press('pageup')
            elif "zoom in" in action_l:
                pyautogui.hotkey('ctrl', '=')
            elif "zoom out" in action_l:
                pyautogui.hotkey('ctrl', '-')
            elif "back" in action_l:
                pyautogui.hotkey('alt', 'left')
            elif "forward" in action_l:
                pyautogui.hotkey('alt', 'right')
            elif "private" in action_l or "incognito" in action_l:
                if browser_title == "Chrome":
                    pyautogui.hotkey('ctrl', 'shift', 'n')
                else:
                    pyautogui.hotkey('ctrl', 'shift', 'p')
        except Exception as e:
            print(f"[BROWSER CTRL ERR] {e}")
    threading.Thread(target=worker, daemon=True).start()
    if "new tab" in action_l or "open tab" in action_l:
        return f"Opened a new tab in {browser_title}, Sir."
    elif "close tab" in action_l:
        return f"Closed the active tab in {browser_title}, Sir."
    elif "next tab" in action_l or "switch tab" in action_l:
        return "Switched to the next tab, Sir."
    elif "prev tab" in action_l or "previous tab" in action_l:
        return "Switched to the previous tab, Sir."
    elif "scroll down" in action_l:
        return f"Scrolling down on {browser_title}, Sir."
    elif "scroll up" in action_l:
        return f"Scrolling up on {browser_title}, Sir."
    elif "zoom in" in action_l:
        return f"Zoomed in {browser_title}, Sir."
    elif "zoom out" in action_l:
        return f"Zoomed out {browser_title}, Sir."
    elif "back" in action_l:
        return "Navigated back, Sir."
    elif "forward" in action_l:
        return "Navigated forward, Sir."
    elif "private" in action_l or "incognito" in action_l:
        return f"Opened a private window in {browser_title}, Sir."
    return f"Action not recognized for {browser_title}, Sir."


def automate_multitasking(action: str) -> str:
    """Execute multitasking and workspace window management controls."""
    if _OS != "Windows":
        return "Multitasking controls are only supported on Windows, Sir."
    action_l = action.lower().strip()
    def worker():
        try:
            if "minimize all" in action_l or "show desktop" in action_l or "clear screen" in action_l:
                pyautogui.hotkey('win', 'd')
            elif "restore all" in action_l or "undo minimize" in action_l:
                pyautogui.hotkey('win', 'shift', 'm')
            elif "snap left" in action_l:
                pyautogui.hotkey('win', 'left')
            elif "snap right" in action_l:
                pyautogui.hotkey('win', 'right')
            elif "snap up" in action_l or "maximize window" in action_l:
                pyautogui.hotkey('win', 'up')
            elif "snap down" in action_l or "minimize window" in action_l:
                pyautogui.hotkey('win', 'down')
            elif "new desktop" in action_l or "create virtual desktop" in action_l:
                pyautogui.hotkey('win', 'ctrl', 'd')
            elif "next desktop" in action_l or "switch right desktop" in action_l:
                pyautogui.hotkey('win', 'ctrl', 'right')
            elif "previous desktop" in action_l or "switch left desktop" in action_l:
                pyautogui.hotkey('win', 'ctrl', 'left')
            elif "close desktop" in action_l or "delete desktop" in action_l:
                pyautogui.hotkey('win', 'ctrl', 'f4')
            elif "task view" in action_l or "show apps" in action_l:
                pyautogui.hotkey('win', 'tab')
            elif "switch app" in action_l or "alt tab" in action_l:
                pyautogui.hotkey('alt', 'tab')
        except Exception as e:
            print(f"[MULTITASKING ERR] {e}")
    threading.Thread(target=worker, daemon=True).start()
    if "minimize all" in action_l or "show desktop" in action_l or "clear screen" in action_l:
        return "Minimizing all windows, Sir."
    elif "restore all" in action_l or "undo minimize" in action_l:
        return "Restoring all minimized windows, Sir."
    elif "snap left" in action_l:
        return "Snapping active window to the left, Sir."
    elif "snap right" in action_l:
        return "Snapping active window to the right, Sir."
    elif "snap up" in action_l or "maximize window" in action_l:
        return "Maximizing the active window, Sir."
    elif "snap down" in action_l or "minimize window" in action_l:
        return "Minimizing the active window, Sir."
    elif "new desktop" in action_l or "create virtual desktop" in action_l:
        return "Created a new Virtual Desktop, Sir."
    elif "next desktop" in action_l or "switch right desktop" in action_l:
        return "Switched to the next Virtual Desktop, Sir."
    elif "previous desktop" in action_l or "switch left desktop" in action_l:
        return "Switched to the previous Virtual Desktop, Sir."
    elif "close desktop" in action_l or "delete desktop" in action_l:
        return "Closed the current Virtual Desktop, Sir."
    elif "task view" in action_l or "show apps" in action_l:
        return "Opening Task View, Sir."
    elif "switch app" in action_l or "alt tab" in action_l:
        return "Toggled the active application, Sir."
    return "Multitasking action not recognized, Sir."


def system_diagnostics() -> str:
    """Gathers comprehensive OS telemetry, heavy processes, and returns a detailed diagnostics report."""
    import psutil
    import shutil
    import platform
    import sys

    report = []
    report.append("=== IP PRIME HARDWARE & SYSTEM TELEMETRY ===")

    # 1. OS & Platform Info
    report.append(f"OS: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    report.append(f"Python Version: {sys.version.split()[0]}")

    # 2. CPU Telemetry
    cpu_pct = psutil.cpu_percent(interval=0.2)
    cpu_cores = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    freq_str = f" @ {cpu_freq.current:.0f}MHz" if cpu_freq else ""
    report.append(f"CPU Load: {cpu_pct}% ({cpu_cores} Logical Cores{freq_str})")

    # 3. Memory Telemetry
    mem = psutil.virtual_memory()
    mem_total = mem.total / (1024**3)
    mem_avail = mem.available / (1024**3)
    mem_used = mem.used / (1024**3)
    report.append(f"Memory: {mem.percent}% used ({mem_used:.2f} GB used / {mem_total:.2f} GB total, {mem_avail:.2f} GB available)")

    # 4. Storage / Disk Capacity
    report.append("\nDisk Partitions:")
    for part in psutil.disk_partitions(all=False):
        if 'cdrom' in part.opts or not part.device:
            continue
        try:
            usage = shutil.disk_usage(part.mountpoint)
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            free_gb = usage.free / (1024**3)
            pct = (usage.used / usage.total) * 100
            report.append(f"  - [{part.device}] Mount: {part.mountpoint} | {pct:.1f}% used ({used_gb:.1f} GB used, {free_gb:.1f} GB free of {total_gb:.1f} GB)")
        except PermissionError:
            continue
        except Exception:
            continue

    # 5. Heavy Processes
    report.append("\nTop 5 Heavy Processes by CPU:")
    cpu_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            cpu_procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    cpu_procs_sorted = sorted(cpu_procs, key=lambda x: x['cpu_percent'] or 0.0, reverse=True)[:5]
    for p in cpu_procs_sorted:
        report.append(f"  - PID {p['pid']}: {p['name']} | CPU: {p['cpu_percent']:.1f}% | MEM: {p['memory_percent']:.1f}%")

    report.append("\nTop 5 Heavy Processes by Memory:")
    mem_procs_sorted = sorted(cpu_procs, key=lambda x: x['memory_percent'] or 0.0, reverse=True)[:5]
    for p in mem_procs_sorted:
        try:
            full_proc = psutil.Process(p['pid'])
            rss = full_proc.memory_info().rss / (1024*1024)
        except Exception:
            rss = 0.0
        report.append(f"  - PID {p['pid']}: {p['name']} | Memory: {rss:.1f} MB ({p['memory_percent']:.1f}%) | CPU: {p['cpu_percent']:.1f}%")

    # 6. Suggestions
    report.append("\n=== DIAGNOSTICS & SYSTEM OPTIMIZATION SUGGESTIONS ===")
    has_issues = False
    if cpu_pct > 80:
        report.append("⚠️ [HIGH CPU LOAD]: Your CPU utilization is extremely high. Consider terminating heavy background processes or closing idle tabs.")
        has_issues = True
    if mem.percent > 85:
        report.append("⚠️ [HIGH MEMORY USAGE]: RAM is heavily saturated. Closing memory-hogging web browser processes or dev tools will improve system response times.")
        has_issues = True
    for part in psutil.disk_partitions(all=False):
        try:
            usage = shutil.disk_usage(part.mountpoint)
            pct = (usage.used / usage.total) * 100
            if pct > 90:
                report.append(f"⚠️ [LOW DISK SPACE]: Drive {part.device} is {pct:.1f}% full. Consider running Disk Cleanup or moving large files to an external drive.")
                has_issues = True
        except Exception:
            pass

    if not has_issues:
        report.append("✅ [SYSTEM HEALTHY]: Telemetry indicates all systems are operating within optimal parameters. No performance bottlenecks detected, Sir!")

    return "\n".join(report)


def smart_workspace(layout: str = "dev", player=None) -> str:
    import subprocess
    import threading
    import time
    try:
        import pyautogui
    except ImportError:
        pass
    try:
        import pygetwindow as gw
    except ImportError:
        pass
    import ctypes

    layout = layout.lower().strip()
    if layout not in ("dev", "chill", "design"):
        layout = "dev"

    if player:
        player.write_log(f"SYS: Smart Workspace Launcher active for layout '{layout}'...")

    launched = []
    
    if layout == "dev":
        try:
            subprocess.Popen(["cmd", "/c", "start", "chrome", "https://github.com", "https://stackoverflow.com"], shell=True)
            launched.append("Chrome (GitHub, StackOverflow)")
            if player:
                player.write_log("SYS: Launching Google Chrome (GitHub, StackOverflow) in background...")
        except Exception as e:
            print(f"[Workspace] Chrome launch failed: {e}")
        
        try:
            subprocess.Popen(["cmd", "/c", "start", "spotify:"], shell=True)
            launched.append("Spotify")
            if player:
                player.write_log("SYS: Launching Spotify background daemon...")
        except Exception as e:
            print(f"[Workspace] Spotify launch failed: {e}")
            
        try:
            subprocess.Popen("code", shell=True)
            launched.append("VS Code")
            if player:
                player.write_log("SYS: Launching Visual Studio Code editor...")
        except Exception as e:
            print(f"[Workspace] VS Code launch failed: {e}")

    elif layout == "chill":
        try:
            subprocess.Popen(["cmd", "/c", "start", "chrome", "https://youtube.com"], shell=True)
            launched.append("Chrome (YouTube)")
            if player:
                player.write_log("SYS: Launching Google Chrome (YouTube) in background...")
        except Exception as e:
            print(f"[Workspace] Chrome launch failed: {e}")
        
        try:
            subprocess.Popen(["cmd", "/c", "start", "spotify:"], shell=True)
            launched.append("Spotify")
            if player:
                player.write_log("SYS: Launching Spotify background daemon...")
        except Exception as e:
            print(f"[Workspace] Spotify launch failed: {e}")

    elif layout == "design":
        try:
            subprocess.Popen(["cmd", "/c", "start", "chrome", "https://figma.com", "https://pinterest.com"], shell=True)
            launched.append("Chrome (Figma, Pinterest)")
            if player:
                player.write_log("SYS: Launching Google Chrome (Figma, Pinterest) in background...")
        except Exception as e:
            print(f"[Workspace] Chrome launch failed: {e}")

    def position_windows_thread():
        time.sleep(3.0)
        W, H = pyautogui.size()
        taskbar_h = 40
        usable_h = H - taskbar_h
        
        if player:
            player.write_log("SYS: [Workspace Snapper] Actively scanning active desktop windows...")

        start_time = time.time()
        while time.time() - start_time < 15.0:
            try:
                windows = gw.getAllWindows()
            except Exception:
                time.sleep(1.0)
                continue
            
            code_w = None
            chrome_w = None
            spotify_w = None
            
            for w in windows:
                if not w.title:
                    continue
                t_lower = w.title.lower()
                if "visual studio code" in t_lower or w.title.endswith(" - Code"):
                    code_w = w
                elif "google chrome" in t_lower or t_lower.endswith("chrome"):
                    chrome_w = w
                elif "spotify" in t_lower:
                    spotify_w = w
            
            if layout == "dev":
                if code_w:
                    try:
                        if code_w.isMinimized:
                            ctypes.windll.user32.ShowWindow(code_w._hWnd, 9)
                        code_w.moveTo(0, 0)
                        code_w.resizeTo(W // 2, usable_h)
                        if player:
                            player.write_log("SYS: [Workspace Snapper] Snapped Visual Studio Code split left (50%).")
                    except Exception:
                        pass
                if chrome_w:
                    try:
                        if chrome_w.isMinimized:
                            ctypes.windll.user32.ShowWindow(chrome_w._hWnd, 9)
                        chrome_w.moveTo(W // 2, 0)
                        chrome_w.resizeTo(W // 2, usable_h // 2)
                        if player:
                            player.write_log("SYS: [Workspace Snapper] Snapped Google Chrome split top-right (25%).")
                    except Exception:
                        pass
                if spotify_w:
                    try:
                        if spotify_w.isMinimized:
                            ctypes.windll.user32.ShowWindow(spotify_w._hWnd, 9)
                        spotify_w.moveTo(W // 2, usable_h // 2)
                        spotify_w.resizeTo(W // 2, usable_h // 2)
                        if player:
                            player.write_log("SYS: [Workspace Snapper] Snapped Spotify split bottom-right (25%).")
                    except Exception:
                        pass
                        
            elif layout == "chill":
                if chrome_w:
                    try:
                        if chrome_w.isMinimized:
                            ctypes.windll.user32.ShowWindow(chrome_w._hWnd, 9)
                        chrome_w.moveTo(0, 0)
                        chrome_w.resizeTo(int(W * 0.6), usable_h)
                        if player:
                            player.write_log("SYS: [Workspace Snapper] Snapped Google Chrome split left (60%).")
                    except Exception:
                        pass
                if spotify_w:
                    try:
                        if spotify_w.isMinimized:
                            ctypes.windll.user32.ShowWindow(spotify_w._hWnd, 9)
                        spotify_w.moveTo(int(W * 0.6), 0)
                        spotify_w.resizeTo(int(W * 0.4), usable_h)
                        if player:
                            player.write_log("SYS: [Workspace Snapper] Snapped Spotify split right (40%).")
                    except Exception:
                        pass
                        
            elif layout == "design":
                if chrome_w:
                    try:
                        if chrome_w.isMinimized:
                            ctypes.windll.user32.ShowWindow(chrome_w._hWnd, 9)
                        chrome_w.moveTo(0, 0)
                        chrome_w.resizeTo(W, usable_h)
                        if player:
                            player.write_log("SYS: [Workspace Snapper] Maximized Google Chrome window split (100%).")
                    except Exception:
                        pass
            
            if layout == "dev" and code_w and chrome_w and spotify_w:
                if player:
                    player.write_log("SYS: [Workspace Snapper] Snap alignment complete. Workspace fully aligned, Sir!")
                break
            if layout == "chill" and chrome_w and spotify_w:
                if player:
                    player.write_log("SYS: [Workspace Snapper] Snap alignment complete. Chill zone aligned, Sir!")
                break
            if layout == "design" and chrome_w:
                if player:
                    player.write_log("SYS: [Workspace Snapper] Snap alignment complete. Design board maximized, Sir!")
                break
                
            time.sleep(1.5)
            
    threading.Thread(target=position_windows_thread, daemon=True).start()
    
    return f"Initiated Smart Workspace for layout '{layout}'. Apps spawned: {', '.join(launched)}."


def pc_cleaner(player=None) -> str:
    import os
    import shutil
    import tempfile
    if player:
        player.write_log("SYS: Safe system temp cleaner initiated...")
    try:
        import psutil
    except ImportError:
        pass

    temp_paths = []
    try:
        temp_paths.append(Path(tempfile.gettempdir()))
    except Exception:
        pass
    
    if _OS == "Windows":
        system_root = os.environ.get("SystemRoot", "C:\\Windows")
        sys_temp = Path(system_root) / "Temp"
        if sys_temp.exists():
            temp_paths.append(sys_temp)
    else:
        sys_temp = Path("/tmp")
        if sys_temp.exists():
            temp_paths.append(sys_temp)

    deleted_files = 0
    deleted_dirs = 0
    freed_bytes = 0
    skipped_files = 0

    print(f"[Cleaner] Starting PC cleanup in paths: {temp_paths}")

    for temp_path in temp_paths:
        if not temp_path.exists():
            continue
            
        for item in temp_path.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    file_size = item.stat().st_size
                    try:
                        item.unlink()
                        deleted_files += 1
                        freed_bytes += file_size
                    except (PermissionError, FileNotFoundError, OSError):
                        skipped_files += 1
                elif item.is_dir():
                    dir_size = 0
                    try:
                        for root, dirs, files in os.walk(str(item)):
                            for f in files:
                                fp = os.path.join(root, f)
                                try:
                                    dir_size += os.path.getsize(fp)
                                except OSError:
                                    pass
                    except OSError:
                        pass
                    try:
                        shutil.rmtree(item)
                        deleted_dirs += 1
                        freed_bytes += dir_size
                    except (PermissionError, FileNotFoundError, OSError):
                        dir_deleted_files = 0
                        try:
                            for root, dirs, files in os.walk(str(item), topdown=False):
                                for name in files:
                                    fp = os.path.join(root, name)
                                    try:
                                        sz = os.path.getsize(fp)
                                        os.unlink(fp)
                                        deleted_files += 1
                                        freed_bytes += sz
                                        dir_deleted_files += 1
                                    except OSError:
                                        skipped_files += 1
                                for name in dirs:
                                    dp = os.path.join(root, name)
                                    try:
                                        os.rmdir(dp)
                                    except OSError:
                                        pass
                            os.rmdir(item)
                            deleted_dirs += 1
                        except OSError:
                            pass
            except Exception:
                skipped_files += 1

    ram_hogs = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                mem_bytes = proc.info['memory_info'].rss
                ram_hogs.append((proc.info['name'], mem_bytes))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        ram_hogs.sort(key=lambda x: x[1], reverse=True)
    except Exception as e:
        print(f"[Cleaner] RAM processes fetch failed: {e}")

    freed_mb = freed_bytes / (1024 * 1024)
    if player:
        player.write_log(f"SYS: Safe optimization completed. Reclaimed {freed_mb:.2f} MB.")
    
    report = []
    report.append("🧹 [PC CLEANER REPORT]")
    report.append(f"Successfully deleted {deleted_files} files and {deleted_dirs} directories.")
    report.append(f"Disk space reclaimed: {freed_mb:.2f} MB.")
    report.append(f"Skipped {skipped_files} active/locked system files safely.")
    
    if ram_hogs:
        report.append("\n💾 [TOP 3 RESOURCE-CONSUMING PROCESSES]:")
        for i, (name, size) in enumerate(ram_hogs[:3], 1):
            size_mb = size / (1024 * 1024)
            report.append(f"{i}. {name} — {size_mb:.1f} MB")
            
    report.append("\nOptimization complete, Sir! The system should feel much more responsive now.")
    return "\n".join(report)


ACTION_MAP: dict[str, callable] = {
    "smart_workspace":     smart_workspace,
    "pc_cleaner":          pc_cleaner,
    "volume_up":           volume_up,
    "volume_down":         volume_down,
    "mute":                volume_mute,
    "unmute":              volume_mute,
    "toggle_mute":         volume_mute,
    "brightness_up":       brightness_up,
    "brightness_down":     brightness_down,
    "brightness_set":      brightness_set,
    "sleep_display":       sleep_display,
    "screen_off":          sleep_display,
    "pause_video":         pause_video,
    "play_pause":          pause_video,
    "close_app":           close_app,
    "close_window":        close_window,
    "full_screen":         full_screen,
    "fullscreen":          full_screen,
    "minimize":            minimize_window,
    "maximize":            maximize_window,
    "snap_left":           snap_left,
    "snap_right":          snap_right,
    "switch_window":       switch_window,
    "show_desktop":        show_desktop,
    "task_manager":        open_task_manager,
    "focus_search":        focus_search,
    "refresh_page":        refresh_page,
    "reload":              refresh_page,
    "close_tab":           close_tab,
    "new_tab":             new_tab,
    "next_tab":            next_tab,
    "prev_tab":            prev_tab,
    "go_back":             go_back,
    "go_forward":          go_forward,
    "zoom_in":             zoom_in,
    "zoom_out":            zoom_out,
    "zoom_reset":          zoom_reset,
    "find_on_page":        find_on_page,
    "scroll_up":           scroll_up,
    "scroll_down":         scroll_down,
    "scroll_top":          scroll_top,
    "scroll_bottom":       scroll_bottom,
    "page_up":             page_up,
    "page_down":           page_down,
    "copy":                copy,
    "paste":               paste,
    "cut":                 cut,
    "undo":                undo,
    "redo":                redo,
    "select_all":          select_all,
    "save":                save_file,
    "enter":               press_enter,
    "escape":              press_escape,
    "screenshot":          take_screenshot,
    "lock_screen":         lock_screen,
    "open_settings":       open_system_settings,
    "file_explorer":       open_file_explorer,
    "open_run":            open_run,
    "dark_mode":           dark_mode,
    "toggle_wifi":         toggle_wifi,
    "restart":             restart_computer,
    "shutdown":            shutdown_computer,
    "list_windows":        get_open_windows,
    "focus_window":        focus_window_by_title,
    "resize_window":       resize_window_by_title,
    "move_window":         move_window_by_title,
    "minimize_window_by_title": minimize_window_by_title,
    "maximize_window_by_title": maximize_window_by_title,
    "close_window_by_title": close_window_by_title,
    "get_clipboard":       get_clipboard,
    "set_clipboard":       set_clipboard,
    "type_clipboard":      type_clipboard,
    "add_note":            add_note,
    "read_notes":          read_notes,
    "clear_notes":         clear_notes,
    "switch_app":          switch_app,
    "youtube_control":     automate_youtube,
    "browser_shortcut":    automate_browser,
    "multitasking":        automate_multitasking,
    "system_diagnostics":  system_diagnostics,
}

_DANGEROUS_ACTIONS = {"restart", "shutdown"}



def _detect_action(description: str) -> dict:

    try:
        from google import genai as _genai
        client = _genai.Client(api_key=_get_api_key())
    except Exception:
        try:
            import google.generativeai as genai
            genai.configure(api_key=_get_api_key())
            client = None
        except Exception as e:
            print(f"[Settings] genai import failed: {e}")
            return {"action": description.lower().replace(" ", "_"), "value": None}

    available = ", ".join(sorted(ACTION_MAP.keys())) + \
                ", volume_set, brightness_set, type_text, press_key, reload_n"

    prompt = f"""You are an intent detector for a computer control assistant.

The user issued a command (possibly in any language): "{description}"

Available actions: {available}

Return ONLY a valid JSON object:
{{"action": "action_name", "value": null_or_value}}

Rules:
- Pick the single best matching action from the available list.
- For volume_set: value is an integer 0-100.
- For brightness_set: value is an integer 0-100.
- For type_text: value is the exact text to type.
- For press_key: value is the key name (e.g. "f5", "tab", "enter").
- For reload_n: value is an integer (number of times to reload).
- If no clear match, pick the closest action.
- Return ONLY the JSON, no explanation, no markdown."""

    try:
        if client is not None:
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            raw  = resp.text
        else:
            resp = genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
            raw  = resp.text
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[Settings] Intent detection failed: {e}")
        return {"action": description.lower().replace(" ", "_"), "value": None}

def computer_settings(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    if not _PYAUTOGUI:
        return "pyautogui is not installed. Run: pip install pyautogui"

    params      = parameters or {}
    raw_action  = params.get("action", "").strip()
    description = params.get("description", "").strip()
    value       = params.get("value", None)

    if not raw_action and description:
        detected   = _detect_action(description)
        raw_action = detected.get("action", "")
        if value is None:
            value = detected.get("value")

    action = raw_action.lower().strip().replace(" ", "_").replace("-", "_")

    if not action:
        return "No action could be determined."

    print(f"[Settings] Action: {action}  Value: {value}  OS: {_OS}")
    if player:
        player.write_log(f"[Settings] {action}")

    if action in _DANGEROUS_ACTIONS:
        confirmed = str(params.get("confirmed", "")).lower()
        if confirmed not in ("yes", "true", "1", "confirm"):
            return (
                f"This will {action} the computer. "
                f"Please confirm by calling again with confirmed=yes."
            )

    if action == "volume_set":
        try:
            volume_set(int(value or 50))
            return f"Volume set to {value}%."
        except Exception as e:
            return f"Could not set volume: {e}"

    if action == "brightness_set":
        try:
            level = int(value or 50)
            brightness_set(level)
            return f"Brightness set to {level}%."
        except Exception as e:
            return f"Could not set brightness: {e}"

    if action in ("type_text", "write_on_screen", "type", "write"):
        text = str(value or params.get("text", "")).strip()
        if not text:
            return "No text provided to type."
        enter_after = str(params.get("press_enter", "false")).lower() in ("true", "1", "yes")
        type_text(text, press_enter_after=enter_after)
        return f"Typed: {text[:80]}"

    if action == "press_key":
        key = str(value or params.get("key", "")).strip()
        if not key:
            return "No key specified."
        press_key(key)
        return f"Pressed: {key}"

    if action in ("reload_n", "refresh_n", "reload_page_n"):
        try:
            reload_page_n(int(value or 1))
            return f"Reloaded {value or 1} time(s)."
        except Exception as e:
            return f"Reload failed: {e}"

    if action == "scroll_up":
        scroll_up(int(value or 500))
        return "Scrolled up."

    if action == "scroll_down":
        scroll_down(int(value or 500))
        return "Scrolled down."

    if action == "focus_window":
        title = str(value or params.get("value", "") or params.get("title", "")).strip()
        return focus_window_by_title(title)

    if action == "resize_window":
        val_str = str(value or params.get("value", "")).strip()
        parts = [p.strip() for p in val_str.split(",")]
        if len(parts) >= 3:
            title = parts[0]
            try:
                w = int(parts[1])
                h = int(parts[2])
                return resize_window_by_title(title, w, h)
            except ValueError:
                return "Width and Height must be integers."
        else:
            return "Please provide value in format: 'title,width,height'."

    if action == "move_window":
        val_str = str(value or params.get("value", "")).strip()
        parts = [p.strip() for p in val_str.split(",")]
        if len(parts) >= 3:
            title = parts[0]
            try:
                x = int(parts[1])
                y = int(parts[2])
                return move_window_by_title(title, x, y)
            except ValueError:
                return "Coordinates x and y must be integers."
        else:
            return "Please provide value in format: 'title,x,y'."

    if action == "minimize_window_by_title":
        title = str(value or params.get("value", "") or params.get("title", "")).strip()
        return minimize_window_by_title(title)

    if action == "maximize_window_by_title":
        title = str(value or params.get("value", "") or params.get("title", "")).strip()
        return maximize_window_by_title(title)

    if action == "close_window_by_title":
        title = str(value or params.get("value", "") or params.get("title", "")).strip()
        return close_window_by_title(title)

    if action == "set_clipboard":
        text = str(value or params.get("value", "") or params.get("text", "")).strip()
        return set_clipboard(text)

    if action == "add_note":
        note_text = str(value or params.get("value", "") or params.get("note", "")).strip()
        return add_note(note_text)

    if action == "switch_app":
        app = str(value or params.get("value", "") or params.get("title", "")).strip()
        return switch_app(app)

    if action == "youtube_control":
        yt_action = str(value or params.get("value", "") or description).strip()
        return automate_youtube(yt_action)

    if action in ("browser_shortcut", "browser_control_shortcut"):
        val_str = str(value or params.get("value", "")).strip()
        parts = [p.strip() for p in val_str.split(",", 1)]
        if len(parts) >= 2:
            return automate_browser(parts[0], parts[1])
        return automate_browser("firefox", val_str)

    if action == "multitasking":
        mt_action = str(value or params.get("value", "") or description).strip()
        return automate_multitasking(mt_action)

    if action == "system_diagnostics":
        return system_diagnostics()

    if action == "smart_workspace":
        layout = str(value or params.get("value", "") or params.get("layout", "dev")).strip()
        return smart_workspace(layout, player)

    if action == "pc_cleaner":
        return pc_cleaner(player)

    func = ACTION_MAP.get(action)
    if not func:
        return f"Unknown action: '{raw_action}'."

    try:
        res = func()
        if isinstance(res, str):
            return res
        return f"Done: {action}."
    except Exception as e:
        print(f"[Settings] Action failed ({action}): {e}")
        return f"Action failed ({action}): {e}"
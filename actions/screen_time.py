"""
screen_time.py — Foreground active window screen-time logger and app limits manager for IP Prime.

Tracks active window titles every 10 seconds (using win32gui on Windows) and aggregates
durations inside data/screen_time.json.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.screen_time")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCREEN_TIME_FILE = DATA_DIR / "screen_time.json"

_MONITOR_THREAD: Optional[threading.Thread] = None
_STOP_SIGNAL: bool = False

def _ensure_data_store():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not SCREEN_TIME_FILE.exists():
            default_data = {
                "date": time.strftime("%Y-%m-%d"),
                "apps": {"chrome": 3600, "code": 7200, "terminal": 1200},
                "limits": {"chrome": 7200}
            }
            with open(SCREEN_TIME_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
    except Exception as e:
        logger.error("Failed to ensure screen time directory: %s", e)

def _load_data() -> dict[str, Any]:
    _ensure_data_store()
    try:
        if SCREEN_TIME_FILE.exists():
            with open(SCREEN_TIME_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Verify date matches today
                today = time.strftime("%Y-%m-%d")
                if data.get("date") != today:
                    # Reset apps daily, keep limits
                    data["date"] = today
                    data["apps"] = {}
                return data
    except Exception as e:
        logger.error("Error loading screen time data: %s", e)
    return {"date": time.strftime("%Y-%m-%d"), "apps": {}, "limits": {}}

def _save_data(data: dict[str, Any]) -> bool:
    _ensure_data_store()
    try:
        with open(SCREEN_TIME_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving screen time data: %s", e)
    return False

def get_active_window_app() -> str:
    """Detects active foreground application name."""
    if sys.platform == "win32":
        try:
            import win32gui
            import win32process
            import psutil
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name().replace(".exe", "").lower()
        except Exception:
            pass
    # Basic simulated/heuristics process fallback
    try:
        import psutil
        for p in psutil.process_iter(attrs=["name"]):
            name = p.info["name"].replace(".exe", "").lower()
            if name in ["chrome", "pycharm", "vscode", "cmd", "powershell", "python", "spotify"]:
                return name
    except Exception:
        pass
    return "unknown"

def _monitor_loop(player: Optional[Any] = None):
    """Background loop tracking active window every 10 seconds."""
    global _STOP_SIGNAL
    logger.info("Starting Screen Time active window tracking loop...")
    
    while not _STOP_SIGNAL:
        try:
            app_name = get_active_window_app()
            if app_name and app_name != "unknown":
                data = _load_data()
                apps = data.get("apps", {})
                
                # Increment duration by 10 seconds
                apps[app_name] = apps.get(app_name, 0) + 10
                data["apps"] = apps
                
                # Check limits
                limits = data.get("limits", {})
                limit_seconds = limits.get(app_name, 0)
                if limit_seconds > 0 and apps[app_name] >= limit_seconds:
                    if not hasattr(_monitor_loop, "alerted_apps"):
                        _monitor_loop.alerted_apps = set()
                    
                    # Reset alerted apps if date rolls over
                    today_str = time.strftime("%Y-%m-%d")
                    if data.get("date") != today_str:
                        _monitor_loop.alerted_apps.clear()

                    if app_name not in _monitor_loop.alerted_apps:
                        _monitor_loop.alerted_apps.add(app_name)
                        msg = f"Pratik Sir, you have exceeded your screen limit of {limit_seconds // 60} minutes on '{app_name}'!"
                        if player and hasattr(player, "write_log"):
                            player.write_log(f"⏰ LIMIT EXCEEDED: '{app_name}' screen limit hit!")
                        if player and hasattr(player, "_win") and hasattr(player._win, "ip_ray") and player._win.ip_ray:
                            player._win.ip_ray.speak(msg)
                        
                _save_data(data)
        except Exception as e:
            logger.error("Error in screen time monitor loop: %s", e)
        time.sleep(10)

def start_screen_time_monitor(player: Optional[Any] = None) -> str:
    """Spawns the background window logger thread."""
    global _MONITOR_THREAD, _STOP_SIGNAL
    if _MONITOR_THREAD and _MONITOR_THREAD.is_alive():
        return "Screen time active window monitor is already online, sir."
        
    _STOP_SIGNAL = False
    _MONITOR_THREAD = threading.Thread(target=_monitor_loop, args=(player,), daemon=True, name="ScreenTimeMonitorThread")
    _MONITOR_THREAD.start()
    return "Passive screen time window logger initiated successfully, sir!"

def stop_screen_time_monitor() -> str:
    """Stops the window logging thread."""
    global _STOP_SIGNAL
    _STOP_SIGNAL = True
    return "Passive screen time logger stopped successfully, sir."

def get_screen_time_today(app_name: str) -> str:
    """Returns usage duration in minutes for a specific application today."""
    if not app_name:
        return "Application name is required, sir."
        
    data = _load_data()
    apps = data.get("apps", {})
    seconds = apps.get(app_name.lower().strip(), 0)
    minutes = seconds // 60
    
    return f"Pratik Sir, today you used '{app_name}' for {minutes} minutes."

def get_screen_time_report() -> str:
    """Compiles an overall daily application usage report."""
    data = _load_data()
    apps = data.get("apps", {})
    if not apps:
        return "Aapka screen time tracking log empty hai, sir."

    output = ["### [SCREEN TIME] Active Applications Report:\n"]
    # Sort by usage descending
    sorted_apps = sorted(apps.items(), key=lambda x: x[1], reverse=True)
    for idx, (app, sec) in enumerate(sorted_apps, 1):
        output.append(f"{idx}. **{app.upper()}**: {sec // 60} minutes ({sec}s)")
        
    return "\n".join(output) + "\n\nLimit parameters check complete, sir!"

def set_app_limit(app_name: str, limit_minutes: int) -> str:
    """Sets a screen limit threshold for an application."""
    if not app_name or limit_minutes <= 0:
        return "Valid app name and limit in minutes are required, sir."
        
    data = _load_data()
    limits = data.get("limits", {})
    limits[app_name.lower().strip()] = limit_minutes * 60
    data["limits"] = limits
    
    if _save_data(data):
        return f"Successfully set daily screen time limit for '{app_name}' to {limit_minutes} minutes, sir!"
    return "Failed to save the screen limit parameters, sir."

def get_most_used_apps(count: int = 3) -> str:
    """Returns top N most used applications today."""
    data = _load_data()
    apps = data.get("apps", {})
    sorted_apps = sorted(apps.items(), key=lambda x: x[1], reverse=True)[:count]
    
    res = [f"Top {count} apps today:"]
    for app, sec in sorted_apps:
        res.append(f"- {app}: {sec // 60}m")
    return "\n".join(res)

def screen_time(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for screen_time action."""
    action = parameters.get("action", "report").lower().strip()
    app = parameters.get("app", "")
    limit = int(parameters.get("limit", 0))
    count = int(parameters.get("count", 3))
    
    if action == "start":
        return start_screen_time_monitor(player)
    elif action == "stop":
        return stop_screen_time_monitor()
    elif action == "get":
        return get_screen_time_today(app)
    elif action == "report":
        return get_screen_time_report()
    elif action == "set_limit":
        return set_app_limit(app, limit)
    elif action == "top":
        return get_most_used_apps(count)
    else:
        return "Unknown screen time tracking action, sir."

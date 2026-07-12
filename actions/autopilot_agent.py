"""
actions/autopilot_agent.py — Autopilot computer use action tools.
Integrates custom keyboard shortcut trigger, Spotify play by query, and StartApps detection.
"""
from __future__ import annotations
import os
import time
import subprocess
import platform
import threading

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

def press_shortcut(keys: str) -> str:
    """
    Parses and presses keyboard shortcuts (e.g. 'ctrl+s', 'win+d', 'alt+tab').
    """
    if not _PYAUTOGUI:
        return "pyautogui is not installed or available."
        
    cleaned = keys.lower().replace(" ", "").split("+")
    try:
        def _press():
            pyautogui.hotkey(*cleaned)
        # Execute in main thread event loop or short delay thread to avoid block
        threading.Thread(target=_press, daemon=True).start()
        return f"✅ Keyboard shortcut pressed: {keys}"
    except Exception as e:
        return f"❌ Failed to press shortcut: {e}"

def play_spotify_track(query: str) -> str:
    """
    Searches for track on Spotify and opens/plays it on the desktop.
    """
    # Try to launch via custom spotify search query URI
    # 'spotify:search:<query>' will open Spotify desktop app and search
    try:
        import urllib.parse
        encoded = urllib.parse.quote(query)
        # On Windows, start URI directly
        if platform.system() == "Windows":
            os.system(f"start spotify:search:{encoded}")
            # Give it time to load, then press enter or play if possible (simulated via key press)
            def _play_delay():
                time.sleep(2.0)
                if _PYAUTOGUI:
                    # Press enter or space to play first result
                    pyautogui.press('enter')
            # Update local desktop HUD info
            update_desktop_media_info(query)
            return f"✅ Spotify launched and searched for '{query}'."
        else:
            return "Spotify automation is only supported on Windows."
    except Exception as e:
        return f"❌ Spotify launch failed: {e}"

def update_desktop_media_info(query: str):
    """Searches top-level widgets for desktop window to update media details."""
    try:
        from PyQt6.QtWidgets import QApplication
        for w in QApplication.topLevelWidgets():
            if w.inherits("QMainWindow") or w.__class__.__name__ == "IPPrimeOSDesktop":
                if hasattr(w, "media_hud") and w.media_hud:
                    parts = query.split("by")
                    if len(parts) > 1:
                        title = parts[0].strip().title()
                        artist = parts[1].strip().title()
                    else:
                        title = query.strip().title()
                        artist = "Spotify Playback"
                    
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: w.media_hud.set_track_info(title, artist))
                    break
    except Exception as e:
        print(f"[Autopilot] Failed to update Media HUD: {e}")

def open_system_app(app_name: str) -> str:
    """
    Tries to open a system application using Registry, StartApps, and fallback search.
    """
    from actions.open_app import _launch_windows
    
    # Try using existing open_app system logic
    try:
        success = _launch_windows(app_name)
        if success:
            return f"✅ Opened application: {app_name}"
            
        # Fallback to powershell Get-StartApps if on Windows
        if platform.system() == "Windows":
            cmd = f'powershell -Command "Get-StartApps | Where-Object {{ $_.Name -like \'*{app_name}*\' }} | Select-Object -First 1 | ForEach-Object {{ Start-Process \\"shell:AppsFolder\\$($_.AppID)\\" }}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0 and not res.stderr:
                return f"✅ Launched app via Get-StartApps: {app_name}"
                
        return f"❌ Could not locate or launch application: {app_name}"
    except Exception as e:
        return f"❌ Error launching application: {e}"

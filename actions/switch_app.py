import logging
# actions/switch_app.py
# Advanced App and Window Switcher for Saturday / Jarvis
# Uses ctypes for low-level window enumeration and force-foreground focus

import os
import platform
import ctypes
import ctypes.wintypes
import time
from pathlib import Path

# Try to import open_app to launch the app if it's not already open
try:
    from actions.open_app import open_app
except ImportError:
    try:
        from open_app import open_app
    except ImportError:
        open_app = None

def _force_foreground_window_win32(hwnd) -> bool:
    try:
        GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
        GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
        AttachThreadInput = ctypes.windll.user32.AttachThreadInput
        SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
        ShowWindow = ctypes.windll.user32.ShowWindow
        IsIconic = ctypes.windll.user32.IsIconic
        
        SW_RESTORE = 9
        SW_SHOW = 5
        
        fg_hwnd = GetForegroundWindow()
        fg_thread_id = GetWindowThreadProcessId(fg_hwnd, None)
        target_thread_id = GetWindowThreadProcessId(hwnd, None)
        current_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        
        attached = False
        if fg_thread_id != current_thread_id and fg_thread_id != 0:
            AttachThreadInput(current_thread_id, fg_thread_id, True)
            attached = True
            
        if IsIconic(hwnd):
            ShowWindow(hwnd, SW_RESTORE)
        else:
            ShowWindow(hwnd, SW_SHOW)
            
        success = SetForegroundWindow(hwnd)
        
        if attached:
            AttachThreadInput(current_thread_id, fg_thread_id, False)
            
        return bool(success)
    except Exception as e:
        print(f"[switch_app] Focus win32 error: {e}")
        return False

def _get_windows_by_title_keyword(keyword: str) -> list:
    matching_windows = []
    
    EnumWindows = ctypes.windll.user32.EnumWindows
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    
    keyword_lower = keyword.lower().strip()
    
    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                title_lower = title.lower()
                
                if keyword_lower in title_lower:
                    # Avoid matching our own UI window if the user searches "saturday"
                    if "s.a.t.u.r.d.a.y" in title_lower or "jarvis" in title_lower:
                        return True
                    matching_windows.append((hwnd, title))
        return True

    cb = WNDENUMPROC(foreach_window)
    EnumWindows(cb, 0)
    return matching_windows

def switch_app(parameters: dict, player=None) -> str:
    app_name = parameters.get("app_name", "").strip()
    if not app_name:
        return "Please specify the app name to switch to, sir."
        
    system = platform.system()
    if system != "Windows":
        return f"App switching is currently only fully supported on Windows, sir."
        
    app_lower = app_name.lower().strip()
    
    # Special alias mapping for search keywords
    aliases = {
        "file explorer": ["explorer", "downloads", "documents", "pictures", "desktop", "this pc", "local disk"],
        "explorer": ["explorer", "downloads", "documents", "pictures", "desktop", "this pc", "local disk"],
        "cmd": ["command prompt", "cmd", "administrator: cmd", "powershell"],
        "terminal": ["command prompt", "cmd", "powershell", "terminal"],
        "powershell": ["powershell", "windows powershell"],
        "chrome": ["google chrome", "chrome"],
        "browser": ["chrome", "firefox", "msedge", "edge", "opera", "brave", "google chrome"],
        "vscode": ["visual studio code", "vscode", " - code"],
        "notepad": ["notepad"],
        "task manager": ["task manager", "taskmgr"],
    }
    
    keywords = [app_lower]
    if app_lower in aliases:
        keywords.extend(aliases[app_lower])
        
    # Search visible windows for any of these keywords, removing duplicates preserving order
    seen_hwnds = set()
    unique_windows = []
    for kw in keywords:
        for hwnd, title in _get_windows_by_title_keyword(kw):
            if hwnd not in seen_hwnds:
                seen_hwnds.add(hwnd)
                unique_windows.append((hwnd, title))
            
    # Try to focus the first match
    if unique_windows:
        hwnd, title = unique_windows[0]
        # Clean title for logging
        safe_title = title.encode('ascii', errors='replace').decode('ascii')
        success = _force_foreground_window_win32(hwnd)
        if success:
            msg = f"Switched to window: '{safe_title}', sir."
            if player:
                try:
                    player.write_log(f"[switch_app] Focused: {safe_title}")
                except Exception as _exc:  # noqa: BLE001
                    logging.debug("[%s] Suppressed: %s", __name__, _exc)
            return msg
            
    # If not found, try to search via win32com Shell.Application for File Explorer windows specifically
    if "explorer" in app_lower or "file" in app_lower:
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            windows = shell.Windows()
            for i in range(windows.Count):
                w = windows.Item(i)
                if w.Document and hasattr(w.Document, "Folder"):
                    hwnd = w.HWND
                    success = _force_foreground_window_win32(hwnd)
                    if success:
                        msg = "Switched to File Explorer window, sir."
                        if player:
                            try:
                                player.write_log("[switch_app] Focused Explorer")
                            except Exception as _exc:  # noqa: BLE001
                                logging.debug("[%s] Suppressed: %s", __name__, _exc)
                        return msg
        except Exception as e:
            print(f"[switch_app] win32com search failed: {e}")

    # Fallback: Launch the app since it's not open
    if open_app:
        print(f"[switch_app] App '{app_name}' not found open. Launching it...")
        if player:
            try:
                player.write_log(f"[switch_app] Launching: {app_name}")
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
        return open_app(parameters={"app_name": app_name}, player=player)
        
    return f"Could not find an open window for '{app_name}' and could not launch it, sir."

import logging
# actions/explorer_control.py
# Advanced Windows File Explorer automation using COM interfaces

import win32com.client
import os
import ctypes
import time
from pathlib import Path

def _get_explorer_windows():
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
        explorer_wins = []
        for i in range(windows.Count):
            try:
                w = windows.Item(i)
                # Filter for File Explorer windows (which have Document.Folder.Self)
                if w.Document and hasattr(w.Document, "Folder"):
                    explorer_wins.append(w)
            except Exception:
                continue
        return explorer_wins
    except Exception as e:
        print(f"[Explorer] Error getting shell windows: {e}")
        return []

def _get_active_explorer():
    fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
    wins = _get_explorer_windows()
    if not wins:
        return None
    for w in wins:
        if w.HWND == fg_hwnd:
            return w
    # Fallback to the first one (typically the most recently used/created)
    return wins[0]

def _activate_window(hwnd):
    try:
        # Show and restore if minimized (SW_RESTORE = 9)
        ctypes.windll.user32.ShowWindow(hwnd, 9)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f"[Explorer] Error activating window {hwnd}: {e}")

def open_folder(path: str) -> str:
    abs_path = os.path.abspath(os.path.expanduser(path))
    # Make sure path exists
    if not os.path.exists(abs_path):
        return f"Path does not exist: {abs_path}"
    
    wins = _get_explorer_windows()
    for w in wins:
        try:
            w_path = os.path.abspath(w.Document.Folder.Self.Path)
            if w_path.lower() == abs_path.lower():
                _activate_window(w.HWND)
                return f"Activated already open File Explorer window at: {abs_path}"
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
            
    # Open new window
    os.startfile(abs_path)
    return f"Opened File Explorer at: {abs_path}"

def get_active_folder() -> str:
    w = _get_active_explorer()
    if w:
        try:
            return f"Active File Explorer folder path: {w.Document.Folder.Self.Path}"
        except Exception as e:
            return f"Could not retrieve active folder path: {e}"
    return "No active File Explorer windows found."

def navigate_active(path: str) -> str:
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        return f"Destination path does not exist: {abs_path}"
        
    w = _get_active_explorer()
    if w:
        try:
            w.Navigate(abs_path)
            _activate_window(w.HWND)
            return f"Navigated active File Explorer window to: {abs_path}"
        except Exception as e:
            return f"Could not navigate active window: {e}"
            
    # If no window is open, open a new one
    os.startfile(abs_path)
    return f"No active window found. Opened new File Explorer at: {abs_path}"

def get_selected() -> str:
    w = _get_active_explorer()
    if not w:
        return "No open File Explorer windows found."
    try:
        selected = w.Document.SelectedItems()
        if selected.Count == 0:
            return f"No items selected in folder: {w.Document.Folder.Self.Path}"
        paths = [selected.Item(i).Path for i in range(selected.Count)]
        return f"Selected items in '{w.Document.Folder.Self.Path}':\n" + "\n".join(paths)
    except Exception as e:
        return f"Error retrieving selected items: {e}"

def select_file(name: str) -> str:
    w = _get_active_explorer()
    if not w:
        return "No open File Explorer windows found."
    try:
        folder = w.Document.Folder
        items = folder.Items()
        for i in range(items.Count):
            item = items.Item(i)
            if item.Name.lower() == name.lower() or os.path.abspath(item.Path).lower() == os.path.abspath(name).lower():
                w.Document.SelectItem(item, 3)  # 3 = Select and Focus
                _activate_window(w.HWND)
                return f"Selected item '{item.Name}' in active File Explorer window."
        return f"Item '{name}' not found in folder: {folder.Self.Path}"
    except Exception as e:
        return f"Error selecting file: {e}"

def show_properties(name: str = "") -> str:
    w = _get_active_explorer()
    if not w:
        return "No open File Explorer windows found."
    try:
        folder = w.Document.Folder
        if name:
            items = folder.Items()
            for i in range(items.Count):
                item = items.Item(i)
                if item.Name.lower() == name.lower() or os.path.abspath(item.Path).lower() == os.path.abspath(name).lower():
                    item.InvokeVerb("properties")
                    _activate_window(w.HWND)
                    return f"Opened properties dialog for: '{item.Name}'"
            return f"Item '{name}' not found in folder: {folder.Self.Path}"
        else:
            selected = w.Document.SelectedItems()
            if selected.Count == 0:
                folder.Self.InvokeVerb("properties")
                _activate_window(w.HWND)
                return f"No item selected. Opened properties dialog for folder: '{folder.Self.Path}'"
            else:
                item = selected.Item(0)
                item.InvokeVerb("properties")
                _activate_window(w.HWND)
                return f"Opened properties dialog for: '{item.Name}' (and {selected.Count - 1} others selected)"
    except Exception as e:
        return f"Error opening properties: {e}"

def close_active() -> str:
    w = _get_active_explorer()
    if w:
        try:
            path = w.Document.Folder.Self.Path
            w.Quit()
            return f"Closed active File Explorer window for: {path}"
        except Exception as e:
            return f"Error closing window: {e}"
    return "No active File Explorer windows found."

def explorer_action(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    path   = parameters.get("path", "downloads/sat output").strip()
    name   = parameters.get("name", "").strip()
    
    # Resolve shortcuts
    path_norm = path.replace("\\", "/").lower().strip()
    if path_norm in ["downloads/sat output", "sat output"]:
        path = str(Path.home() / "Downloads" / "sat output")
    elif path_norm in ["desktop"]:
        path = str(Path.home() / "Desktop")
    elif path_norm in ["downloads"]:
        path = str(Path.home() / "Downloads")
    elif path_norm in ["documents"]:
        path = str(Path.home() / "Documents")
    elif path_norm in ["home"]:
        path = str(Path.home())
        
    result = "Unknown action."
    try:
        if action == "open":
            result = open_folder(path)
        elif action == "get_active":
            result = get_active_folder()
        elif action == "navigate":
            result = navigate_active(path)
        elif action == "get_selected":
            result = get_selected()
        elif action == "select":
            result = select_file(name or path)
        elif action == "properties":
            result = show_properties(name)
        elif action == "close":
            result = close_active()
        else:
            result = f"Unknown explorer action: {action}"
    except Exception as e:
        result = f"Explorer control error: {e}"
        
    if player:
        try:
            player.write_log(f"[explorer] {result[:60]}")
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
            
    return result

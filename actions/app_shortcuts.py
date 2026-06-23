import os
import platform
import subprocess
import time
import threading

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

def automate_calculator(action):
    """Execute dynamic Calculator controls and shortcuts in a background thread."""
    if platform.system() != "Windows":
        return "Calculator controls are only supported on Windows, Sir."
        
    if not _PYAUTOGUI:
        return "pyautogui is required for Calculator controls."
        
    action_l = action.lower().strip()
    
    def worker():
        try:
            # 1. First ensure it is open
            ps_script = 'Get-Process -Name "Calculator" -ErrorAction SilentlyContinue'
            res = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if "calculator" not in res.stdout.lower():
                subprocess.Popen("calc")
                time.sleep(0.8)
                
            # 2. Focus Calculator
            ps_script_focus = '$wshell = New-Object -ComObject wscript.shell; Get-Process | Where-Object {$_.MainWindowTitle -like "*Calculator*" -or $_.ProcessName -like "*calc*"} | ForEach-Object { $wshell.AppActivate($_.Id) }'
            subprocess.run(["powershell", "-Command", ps_script_focus], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.3)
            
            if "scientific" in action_l:
                pyautogui.hotkey('alt', '2')
            elif "standard" in action_l:
                pyautogui.hotkey('alt', '1')
            elif "history" in action_l:
                pyautogui.hotkey('ctrl', 'h')
            elif "clear" in action_l or "reset" in action_l:
                pyautogui.press('esc')
            elif "close" in action_l:
                pyautogui.hotkey('alt', 'f4')
        except Exception as e:
            print(f"[CALCULATOR WORKER ERR] {e}")

    threading.Thread(target=worker, daemon=True).start()
    
    if "scientific" in action_l:
        return "Switched Calculator to Scientific mode, Sir."
    elif "standard" in action_l:
        return "Switched Calculator to Standard mode, Sir."
    elif "history" in action_l:
        return "Opened Calculator history log, Sir."
    elif "clear" in action_l or "reset" in action_l:
        return "Cleared the Calculator screen, Sir."
    elif "close" in action_l:
        return "Closed the Calculator, Sir."
        
    return "Calculator is ready, Sir."

def automate_clock(action):
    """Launch Windows Clock app or trigger alarms/timers in a background thread."""
    if platform.system() != "Windows":
        return "Clock controls are only supported on Windows, Sir."
        
    action_l = action.lower().strip()
    
    uri = "ms-clock:"
    msg = "Opening Windows Clock app, Sir."
    
    if "timer" in action_l:
        uri = "ms-clock:timer"
        msg = "Opening Timer in Clock app, Sir."
    elif "alarm" in action_l:
        uri = "ms-clock:alarm"
        msg = "Opening Alarms in Clock app, Sir."
    elif "stopwatch" in action_l:
        uri = "ms-clock:stopwatch"
        msg = "Opening Stopwatch in Clock app, Sir."
        
    def worker():
        try:
            subprocess.Popen(["explorer", uri])
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()
    return msg

def automate_paint(action):
    """Execute Paint shortcuts and canvas controls in a background thread."""
    if platform.system() != "Windows":
        return "Paint controls are only supported on Windows, Sir."
        
    if not _PYAUTOGUI:
        return "pyautogui is required for Paint controls."
        
    action_l = action.lower().strip()
    
    def worker():
        try:
            # 1. Launch Paint if not running
            ps_script = 'Get-Process -Name "mspaint" -ErrorAction SilentlyContinue'
            res = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if "mspaint" not in res.stdout.lower():
                subprocess.Popen("mspaint")
                time.sleep(0.8)
                
            # 2. Focus Paint
            ps_script_focus = '$wshell = New-Object -ComObject wscript.shell; Get-Process | Where-Object {$_.MainWindowTitle -like "*Paint*" -or $_.ProcessName -eq "mspaint"} | ForEach-Object { $wshell.AppActivate($_.Id) }'
            subprocess.run(["powershell", "-Command", ps_script_focus], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.3)
            
            if "new canvas" in action_l or "clear" in action_l:
                pyautogui.hotkey('ctrl', 'n')
            elif "save" in action_l:
                pyautogui.hotkey('ctrl', 's')
            elif "resize" in action_l:
                pyautogui.hotkey('ctrl', 'w')
            elif "full screen" in action_l or "maximize" in action_l:
                pyautogui.press('f11')
            elif "close" in action_l:
                pyautogui.hotkey('alt', 'f4')
        except Exception as e:
            print(f"[PAINT WORKER ERR] {e}")

    threading.Thread(target=worker, daemon=True).start()
    
    if "new canvas" in action_l or "clear" in action_l:
        return "Opened a new Paint canvas, Sir."
    elif "save" in action_l:
        return "Saving the Paint project, Sir."
    elif "resize" in action_l:
        return "Opened Paint resize popup window, Sir."
    elif "full screen" in action_l or "maximize" in action_l:
        return "Toggled full screen mode in Paint, Sir."
    elif "close" in action_l:
        return "Closed Microsoft Paint, Sir."
        
    return "Paint canvas is active and ready, Sir."

def automate_settings(action):
    """Launch Windows System Settings app or specific sub-settings pages in a background thread."""
    if platform.system() != "Windows":
        return "Settings controls are only supported on Windows, Sir."
        
    action_l = action.lower().strip()
    
    uri = "ms-settings:"
    msg = "Opening Windows System Settings, Sir."
    
    if "wifi" in action_l or "internet" in action_l or "network" in action_l:
        uri = "ms-settings:network"
        msg = "Opening Network and Internet Settings, Sir."
    elif "bluetooth" in action_l or "devices" in action_l:
        uri = "ms-settings:bluetooth"
        msg = "Opening Bluetooth and Devices Settings, Sir."
    elif "update" in action_l or "windows update" in action_l:
        uri = "ms-settings:windowsupdate"
        msg = "Opening Windows Update Settings, Sir."
    elif "display" in action_l or "personalization" in action_l:
        uri = "ms-settings:personalization"
        msg = "Opening Personalization Settings, Sir."
    elif "apps" in action_l or "applications" in action_l:
        uri = "ms-settings:apps"
        msg = "Opening Installed Apps Settings, Sir."
        
    def worker():
        try:
            subprocess.Popen(["explorer", uri])
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()
    return msg

def automate_explorer(action, arg=None):
    """Execute dynamic Windows File Explorer controls or navigate to system folders in a background thread."""
    if platform.system() != "Windows":
        return "File Explorer controls are only supported on Windows, Sir."
        
    action_l = action.lower().strip()
    
    target = (arg or "").lower().strip()
    path = None
    msg = "Opening File Explorer, Sir."
    
    if "open" in action_l:
        if "download" in target:
            path = os.path.expanduser('~/Downloads')
            msg = "Opening Downloads folder, Sir."
        elif "document" in target:
            path = os.path.expanduser('~/Documents')
            msg = "Opening Documents folder, Sir."
        elif "desktop" in target:
            path = os.path.expanduser('~/Desktop')
            msg = "Opening Desktop folder, Sir."
        elif "picture" in target or "photo" in target:
            path = os.path.expanduser('~/Pictures')
            msg = "Opening Pictures folder, Sir."
        elif "video" in target:
            path = os.path.expanduser('~/Videos')
            msg = "Opening Videos folder, Sir."
        elif "music" in target:
            path = os.path.expanduser('~/Music')
            msg = "Opening Music folder, Sir."

    def worker():
        try:
            if "open" in action_l:
                if path and os.path.exists(path):
                    os.startfile(path)
                else:
                    subprocess.Popen("explorer")
                return
                
            if not _PYAUTOGUI:
                return
                
            # For keyboard shortcuts, bring explorer window to focus
            ps_script = '$wshell = New-Object -ComObject wscript.shell; Get-Process | Where-Object {$_.MainWindowTitle -like "*File Explorer*" -or $_.ProcessName -eq "explorer"} | ForEach-Object { $wshell.AppActivate($_.Id) }'
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.3)
            
            if "new folder" in action_l or "create folder" in action_l:
                pyautogui.hotkey('ctrl', 'shift', 'n')
            elif "back" in action_l or "go back" in action_l:
                pyautogui.hotkey('alt', 'left')
            elif "forward" in action_l or "go forward" in action_l:
                pyautogui.hotkey('alt', 'right')
            elif "up" in action_l or "go up" in action_l:
                pyautogui.hotkey('alt', 'up')
            elif "search" in action_l or "find" in action_l:
                pyautogui.hotkey('ctrl', 'f')
            elif "close" in action_l or "shutdown" in action_l:
                pyautogui.hotkey('ctrl', 'w')
        except Exception as e:
            print(f"[EXPLORER WORKER ERR] {e}")

    threading.Thread(target=worker, daemon=True).start()
    
    if "open" in action_l:
        return msg
    elif "new folder" in action_l or "create folder" in action_l:
        return "Creating a new folder in File Explorer, Sir."
    elif "back" in action_l or "go back" in action_l:
        return "Navigated back in File Explorer, Sir."
    elif "forward" in action_l or "go forward" in action_l:
        return "Navigated forward in File Explorer, Sir."
    elif "up" in action_l or "go up" in action_l:
        return "Navigated up one level in File Explorer, Sir."
    elif "search" in action_l or "find" in action_l:
        return "Focused the search bar in File Explorer, Sir."
    elif "close" in action_l or "shutdown" in action_l:
        return "Closed the File Explorer window, Sir."
        
    return "File Explorer action not recognized, Sir."

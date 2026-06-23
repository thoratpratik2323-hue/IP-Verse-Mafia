import platform
import subprocess
import time
import threading

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

def automate_gmail(action):
    """Execute dynamic Gmail control shortcuts in active browser tab containing Gmail in a background thread."""
    if platform.system() != "Windows":
        return "Gmail controls are only supported on Windows, Sir."
        
    if not _PYAUTOGUI:
        return "pyautogui is required for Gmail controls."
        
    action_l = action.lower().strip()
    
    def worker():
        try:
            ps_script = '$wshell = New-Object -ComObject wscript.shell; Get-Process | Where-Object {$_.MainWindowTitle -like "*Gmail*"} | ForEach-Object { $wshell.AppActivate($_.Id) }'
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.3)
            if "compose" in action_l or "new mail" in action_l or "write email" in action_l:
                pyautogui.press('c')
            elif "search" in action_l or "find mail" in action_l:
                pyautogui.press('/')
            elif "inbox" in action_l or "go to inbox" in action_l:
                pyautogui.press('g')
                time.sleep(0.1)
                pyautogui.press('i')
            elif "sent" in action_l or "go to sent" in action_l:
                pyautogui.press('g')
                time.sleep(0.1)
                pyautogui.press('t')
            elif "starred" in action_l or "go to starred" in action_l:
                pyautogui.press('g')
                time.sleep(0.1)
                pyautogui.press('s')
            elif "draft" in action_l or "go to drafts" in action_l:
                pyautogui.press('g')
                time.sleep(0.1)
                pyautogui.press('d')
            elif "refresh" in action_l or "reload inbox" in action_l:
                pyautogui.press('u')
        except Exception as e:
            print(f"[GMAIL WORKER ERR] {e}")

    threading.Thread(target=worker, daemon=True).start()
    
    if "compose" in action_l or "new mail" in action_l or "write email" in action_l:
        return "Opened a new compose window in Gmail, Sir."
    elif "search" in action_l or "find mail" in action_l:
        return "Focused the search bar in Gmail, Sir."
    elif "inbox" in action_l or "go to inbox" in action_l:
        return "Navigating to your Gmail Inbox, Sir."
    elif "sent" in action_l or "go to sent" in action_l:
        return "Navigating to your Sent Mail in Gmail, Sir."
    elif "starred" in action_l or "go to starred" in action_l:
        return "Navigating to Starred messages in Gmail, Sir."
    elif "draft" in action_l or "go to drafts" in action_l:
        return "Navigating to Drafts in Gmail, Sir."
    elif "refresh" in action_l or "reload inbox" in action_l:
        return "Refreshed Gmail Inbox, Sir."
        
    return "Gmail action not recognized, Sir."

def automate_drive(action):
    """Execute dynamic Google Drive control shortcuts in active browser tab containing Google Drive in a background thread."""
    if platform.system() != "Windows":
        return "Google Drive controls are only supported on Windows, Sir."
        
    if not _PYAUTOGUI:
        return "pyautogui is required for Google Drive controls."
        
    action_l = action.lower().strip()
    
    def worker():
        try:
            ps_script = '$wshell = New-Object -ComObject wscript.shell; Get-Process | Where-Object {$_.MainWindowTitle -like "*Drive*"} | ForEach-Object { $wshell.AppActivate($_.Id) }'
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.3)
            if "new document" in action_l or "create doc" in action_l or "new doc" in action_l:
                pyautogui.hotkey('shift', 't')
            elif "new sheet" in action_l or "create sheet" in action_l or "new spreadsheet" in action_l:
                pyautogui.hotkey('shift', 's')
            elif "new folder" in action_l or "create folder" in action_l:
                pyautogui.press('shift')
                pyautogui.press('f')
            elif "search" in action_l or "find file" in action_l:
                pyautogui.press('/')
            elif "recent" in action_l or "go to recent" in action_l:
                pyautogui.press('g')
                time.sleep(0.1)
                pyautogui.press('r')
        except Exception as e:
            print(f"[DRIVE WORKER ERR] {e}")

    threading.Thread(target=worker, daemon=True).start()
    
    if "new document" in action_l or "create doc" in action_l or "new doc" in action_l:
        return "Creating a new Google Document, Sir."
    elif "new sheet" in action_l or "create sheet" in action_l or "new spreadsheet" in action_l:
        return "Creating a new Google Sheet, Sir."
    elif "new folder" in action_l or "create folder" in action_l:
        return "Creating a new Google Drive folder, Sir."
    elif "search" in action_l or "find file" in action_l:
        return "Focused the search bar in Google Drive, Sir."
    elif "recent" in action_l or "go to recent" in action_l:
        return "Navigating to Recent files in Google Drive, Sir."
        
    return "Google Drive action not recognized, Sir."

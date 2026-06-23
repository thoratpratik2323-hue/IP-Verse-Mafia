import platform
import subprocess
import time
import threading
import re

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

def automate_notepad(action, arg=None):
    """Execute dynamic Notepad control shortcuts and typing safely in a background thread."""
    if platform.system() != "Windows":
        return "Notepad controls are only supported on Windows, Sir."
        
    if not _PYAUTOGUI:
        return "pyautogui is required for Notepad controls."
        
    action_l = action.lower().strip()
    
    def worker():
        try:
            # Check if Notepad is running and has a window handle, if not, launch it!
            res = subprocess.run(["powershell", "-Command", "Get-Process -Name notepad -ErrorAction SilentlyContinue"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if "notepad" not in res.stdout.lower():
                subprocess.Popen("notepad")
                time.sleep(1.2)
                
            # Bring Notepad to focus using robust Win32 script
            ps_script = (
                "add-type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
                "public class Win32 { [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd); "
                "[DllImport(\"user32.dll\")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow); }';"
                "$proc = Get-Process -Name notepad | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1;"
                "if ($proc) { [Win32]::ShowWindowAsync($proc.MainWindowHandle, 9) | Out-Null; [Win32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null }"
            )
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.4)
            
            if "new document" in action_l or "new window" in action_l or "clear" in action_l:
                pyautogui.hotkey('ctrl', 'n')
            elif "save file" in action_l or "save" in action_l:
                pyautogui.hotkey('ctrl', 's')
            elif "find text" in action_l or "search" in action_l:
                pyautogui.hotkey('ctrl', 'f')
            elif "replace" in action_l:
                pyautogui.hotkey('ctrl', 'h')
            elif "write" in action_l or "type" in action_l:
                if arg:
                    # Clean up common trailing target descriptions
                    text_to_type = arg
                    text_to_type = re.sub(r'\s+in\s+notepad$', '', text_to_type, flags=re.IGNORECASE)
                    text_to_type = re.sub(r'\s+on\s+notepad$', '', text_to_type, flags=re.IGNORECASE)
                    pyautogui.write(text_to_type, interval=0.005)
        except Exception as e:
            print(f"[NOTEPAD WORKER ERR] {e}")

    threading.Thread(target=worker, daemon=True).start()

    if "new document" in action_l or "new window" in action_l or "clear" in action_l:
        return "Opened a new document in Notepad, Sir."
    elif "save file" in action_l or "save" in action_l:
        return "Saving the Notepad document, Sir."
    elif "find text" in action_l or "search" in action_l:
        return "Opened search/find window in Notepad, Sir."
    elif "replace" in action_l:
        return "Opened find and replace window in Notepad, Sir."
    elif "write" in action_l or "type" in action_l:
        if arg:
            return f"Typed the text in Notepad, Sir."
        else:
            return "No text was provided to type, Sir."
            
    return "Notepad action not recognized, Sir."

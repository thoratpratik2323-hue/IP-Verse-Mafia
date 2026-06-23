import os
import platform
import subprocess
import time
import threading
import random
import re
import urllib.parse
import webbrowser

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

def open_in_firefox(url):
    """Force launch URLs in Google Chrome (updated per user preference) and forcefully bring to foreground in a background thread using robust Win32 APIs."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        print(f"[SECURITY] Blocked non-http/https URL execution: {url}")
        return
        
    def worker():
        try:
            if platform.system() == "Windows":
                chrome_exe = None
                standard_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")
                ]
                for p in standard_paths:
                    if p and os.path.exists(p):
                        chrome_exe = p
                        break
                
                if chrome_exe:
                    subprocess.Popen([chrome_exe, url], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen(["cmd", "/c", "start", "chrome", url], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(0.8)
                
                ps_script = (
                    "add-type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
                    "public class Win32 { [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd); "
                    "[DllImport(\"user32.dll\")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow); }';"
                    "$proc = Get-Process | Where-Object { $_.ProcessName -eq 'chrome' } | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1;"
                    "if ($proc) { [Win32]::ShowWindowAsync($proc.MainWindowHandle, 9) | Out-Null; [Win32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null }"
                )
                subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                try:
                    webbrowser.get('chrome').open(url)
                except Exception:
                    webbrowser.open(url)
        except Exception:
            try:
                webbrowser.open(url)
            except Exception:
                pass
                
    threading.Thread(target=worker, daemon=True).start()

def play_youtube(query):
    """Search and play a video on YouTube in Chrome."""
    if not query:
        return "What would you like to watch on YouTube, Sir?"
    
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    open_in_firefox(url)
    
    # Automate first search result click
    def click_first():
        if not _PYAUTOGUI:
            return
        time.sleep(6)
        pyautogui.press('tab')
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(2)
        pyautogui.press('f')
        
    threading.Thread(target=click_first, daemon=True).start()
    
    yt_responses = [
        f"Sure, playing {query} on YouTube via Chrome, Sir.",
        f"Searching and playing {query} on YouTube in Chrome right away.",
        f"Understood Sir, launching {query} on YouTube via Chrome.",
        f"Right away, Sir! Streaming {query} on YouTube via Chrome.",
        f"Initiating YouTube uplink for {query} on Chrome, Sir."
    ]
    return random.choice(yt_responses)

def automate_youtube(action):
    """Execute dynamic YouTube control shortcuts in active browser playing YouTube in a background thread."""
    if platform.system() != "Windows":
        return "YouTube controls are only supported on Windows, Sir."
        
    if not _PYAUTOGUI:
        return "pyautogui is required for YouTube shortcuts."
        
    action_l = action.lower().strip()
    
    def worker():
        try:
            ps_script = '$wshell = New-Object -ComObject wscript.shell; Get-Process | Where-Object {$_.MainWindowTitle -like "*YouTube*"} | ForEach-Object { $wshell.AppActivate($_.Id) }'
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.3)
            
            if "pause" in action_l or "play" in action_l or "resume" in action_l or "stop video" in action_l:
                pyautogui.press('k')
            elif "mute" in action_l or "unmute" in action_l or "silent" in action_l:
                pyautogui.press('m')
            elif "volume up" in action_l or "sound up" in action_l or "volume bada" in action_l:
                pyautogui.press('up')
            elif "volume down" in action_l or "sound down" in action_l or "volume kam" in action_l:
                pyautogui.press('down')
            elif "forward" in action_l or "seek right" in action_l or "skip forward" in action_l:
                pyautogui.press('l')
            elif "rewind" in action_l or "seek left" in action_l or "skip backward" in action_l:
                pyautogui.press('j')
            elif "next video" in action_l or "skip video" in action_l or "agla video" in action_l:
                pyautogui.hotkey('shift', 'n')
            elif "full screen" in action_l or "maximize video" in action_l:
                pyautogui.press('f')
            elif "theater mode" in action_l:
                pyautogui.press('t')
            elif "subtitle" in action_l or "captions" in action_l:
                pyautogui.press('c')
        except Exception as e:
            print(f"[YOUTUBE WORKER ERR] {e}")

    threading.Thread(target=worker, daemon=True).start()
    
    if "pause" in action_l or "play" in action_l or "resume" in action_l or "stop video" in action_l:
        return "Toggled play/pause on YouTube, Sir."
    elif "mute" in action_l or "unmute" in action_l or "silent" in action_l:
        return "Toggled mute status on YouTube, Sir."
    elif "volume up" in action_l or "sound up" in action_l or "volume bada" in action_l:
        return "Volume increased on YouTube, Sir."
    elif "volume down" in action_l or "sound down" in action_l or "volume kam" in action_l:
        return "Volume decreased on YouTube, Sir."
    elif "forward" in action_l or "seek right" in action_l or "skip forward" in action_l:
        return "Skipped forward 10 seconds, Sir."
    elif "rewind" in action_l or "seek left" in action_l or "skip backward" in action_l:
        return "Skipped backward 10 seconds, Sir."
    elif "next video" in action_l or "skip video" in action_l or "agla video" in action_l:
        return "Skipped to the next video, Sir."
    elif "full screen" in action_l or "maximize video" in action_l:
        return "Toggled full screen on YouTube, Sir."
    elif "theater mode" in action_l:
        return "Toggled theater mode on YouTube, Sir."
    elif "subtitle" in action_l or "captions" in action_l:
        return "Toggled captions on YouTube, Sir."
        
    return "YouTube action not recognized, Sir."

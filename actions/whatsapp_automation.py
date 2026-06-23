import os
import platform
import subprocess
import time
import threading
import re
import urllib.parse
import webbrowser
from actions.send_message import resolve_contact

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

def open_in_firefox(url):
    """Force launch URLs in Google Chrome (updated per user preference) and forcefully bring to foreground using Win32."""
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

def send_whatsapp(target, message):
    """Prefill WhatsApp Web with the number and message, bring Chrome/Firefox to focus, and auto-send after load."""
    phone = resolve_contact(target)
    if not phone:
        return f"Contact '{target}' could not be resolved, Sir."
        
    phone_clean = re.sub(r'[\s\-()]', '', phone)
    if phone_clean.isdigit() and len(phone_clean) == 10:
        phone_clean = "+91" + phone_clean
    elif not phone_clean.startswith("+") and phone_clean.isdigit():
        phone_clean = "+" + phone_clean
        
    encoded_msg = urllib.parse.quote(message)
    url = f"https://web.whatsapp.com/send?phone={phone_clean}&text={encoded_msg}"
    
    # Open in Browser
    open_in_firefox(url)
    
    def auto_send_worker():
        if not _PYAUTOGUI:
            return
            
        # Wait for WhatsApp Web to load securely (10 seconds)
        time.sleep(10.0)
        
        # Bring Chrome/Firefox to focus
        if platform.system() == "Windows":
            ps_script = (
                "add-type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
                "public class Win32 { [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd); "
                "[DllImport(\"user32.dll\")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow); }';"
                "$proc = Get-Process | Where-Object { $_.ProcessName -eq 'chrome' -or $_.ProcessName -eq 'firefox' } | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1;"
                "if ($proc) { [Win32]::ShowWindowAsync($proc.MainWindowHandle, 9) | Out-Null; [Win32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null }"
            )
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.5)
            
        pyautogui.press('enter')
        print(f"[WHATSAPP AUTOMATION] Message sent to {phone_clean}")
        
    threading.Thread(target=auto_send_worker, daemon=True).start()
    return f"WhatsApp transmission protocol initiated for contact '{target}', Sir."

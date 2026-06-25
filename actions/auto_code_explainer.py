import pygetwindow as gw
import pyautogui
import pyperclip
import time

def auto_code_explainer(parameters: dict, player=None) -> str:
    try:
        active_win = gw.getActiveWindow()
        if not active_win:
            return "No active window detected, sir."
            
        title = active_win.title
        title_lower = title.lower()
        
        is_code = "visual studio code" in title_lower or "vscode" in title_lower or "sublime" in title_lower or "notepad++" in title_lower or "pycharm" in title_lower
        is_terminal = "cmd" in title_lower or "powershell" in title_lower or "terminal" in title_lower or "command prompt" in title_lower or "bash" in title_lower
        
        if not (is_code or is_terminal):
            return f"The active window is '{title}', which does not seem to be a code editor or terminal, sir."
            
        # Try to capture highlighted text by simulating Ctrl+C
        original_clip = pyperclip.paste()
        pyperclip.copy("")
        
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.15) # Wait for OS clipboard update
        
        selected_text = pyperclip.paste().strip()
        
        # Restore original clipboard value to be polite
        pyperclip.copy(original_clip)
        
        if selected_text:
            return (
                f"### [AUTO CODE EXPLAINER] Active Window: {title}\n"
                f"Selected code context detected:\n"
                f"```\n{selected_text}\n```\n"
                f"Analyze this code block and explain or debug it."
            )
        else:
            return (
                f"Active Window is '{title}'. "
                f"Please select/highlight the code or command you want explained in this window, and ask me again, sir."
            )
            
    except Exception as e:
        return f"Could not analyze the active editor: {e}, sir."

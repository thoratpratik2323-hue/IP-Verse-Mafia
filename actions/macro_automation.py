"""
macro_automation.py — System level GUI macro execution tool using pyautogui.

This is a standard action module for the IP Prime personal assistant suite.
"""

import time
import threading

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

def execute_macro_sequence(parameters: dict, player=None) -> str:
    """
    Executes a sequence of mouse clicks, movements, typing, delays, and hotkeys.
    """
    if not _PYAUTOGUI:
        return "pyautogui is not installed in the virtual environment, Sir."
        
    sequence = parameters.get("sequence", [])
    if not sequence:
        return "No macro sequence steps were provided to execute, Sir."
        
    def worker():
        try:
            pyautogui.FAILSAFE = True
            
            for step in sequence:
                action = step.get("action", "").lower().strip()
                if action == "move_to":
                    x = int(step.get("x", 0))
                    y = int(step.get("y", 0))
                    pyautogui.moveTo(x, y, duration=0.3)
                elif action == "click":
                    pyautogui.click()
                elif action == "type":
                    text = step.get("text", "")
                    pyautogui.write(text, interval=0.01)
                elif action == "hotkey":
                    keys = step.get("keys", [])
                    if keys:
                        pyautogui.hotkey(*keys)
                elif action == "delay":
                    seconds = float(step.get("seconds", 0.5))
                    time.sleep(seconds)
        except Exception as e:
            print(f"[Macro Worker Exception] {e}")
            
    threading.Thread(target=worker, daemon=True).start()
    return f"Started executing the macro sequence containing {len(sequence)} steps, Sir."

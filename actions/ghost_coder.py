"""
ghost_coder.py — Stealth pair-programming code advisor.

This is a standard action module for the IP Prime personal assistant suite.
"""

import keyboard
import threading
import time
import pyperclip
import pyautogui
from actions.computer_control import phantom_type

def _ghost_coder_callback():
    """Triggered on Ctrl+Alt+Space. Copies selected text and feeds it to Phantom Typer."""
    print("[Ghost Coder] Triggered! Copying selected text...")
    
    # Backup original clipboard to not destroy user data
    old_clip = pyperclip.paste()
    
    # Try copying selected text
    pyperclip.copy("")
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.15)
    
    prompt = pyperclip.paste()
    if not prompt or prompt.isspace():
        print("[Ghost Coder] No text selected or clipboard empty. Reverting clipboard.")
        pyperclip.copy(old_clip)
        return
        
    print(f"[Ghost Coder] Processing prompt: {prompt[:50]}...")
    
    # Execute Phantom Typer
    result = phantom_type(prompt)
    print(f"[Ghost Coder] Phantom Result: {result}")
    
    # Restore clipboard
    time.sleep(0.1)
    pyperclip.copy(old_clip)

def start_ghost_coder():
    try:
        keyboard.add_hotkey("ctrl+alt+space", _ghost_coder_callback)
        print("[Ghost Coder] Global hotkey registered: Ctrl+Alt+Space")
    except Exception as e:
        print(f"[Ghost Coder] Error registering hotkey: {e}")

def run_in_background():
    """Starts the ghost coder listener safely in a background thread."""
    thread = threading.Thread(target=start_ghost_coder, daemon=True, name="GhostCoderThread")
    thread.start()

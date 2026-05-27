"""
clipboard_manager.py — Smart background clipboard history logger and classifier for IP Prime.

Monitors pyperclip.paste() every 500ms in an optimized thread.
Classifies entries as url, email, code, phone, or text, keeping the last 500 entries.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import pyperclip
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.clipboard_manager")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CLIPBOARD_FILE = DATA_DIR / "clipboard_history.json"

_MONITOR_THREAD: Optional[threading.Thread] = None
_STOP_SIGNAL: bool = False

def _ensure_data_store():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not CLIPBOARD_FILE.exists():
            with open(CLIPBOARD_FILE, "w", encoding="utf-8") as f:
                json.dump({"entries": []}, f, indent=4)
    except Exception as e:
        logger.error("Failed to ensure clipboard history directory: %s", e)

def _load_history() -> list[dict[str, Any]]:
    _ensure_data_store()
    try:
        if CLIPBOARD_FILE.exists():
            with open(CLIPBOARD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("entries", [])
    except Exception as e:
        logger.error("Error loading clipboard history: %s", e)
    return []

def _save_history(entries: list[dict[str, Any]]) -> bool:
    _ensure_data_store()
    try:
        with open(CLIPBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump({"entries": entries}, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving clipboard history: %s", e)
    return False

def classify_text(text: str) -> str:
    """Auto-detects structure patterns inside a string snippet."""
    txt = text.strip()
    
    # URL check
    if txt.startswith("http://") or txt.startswith("https://") or txt.startswith("www."):
        return "url"
        
    # Email check
    if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", txt):
        return "email"
        
    # Phone check
    if re.match(r"^\+?[\d\s-]{7,15}$", txt):
        return "phone"
        
    # Code check
    code_keywords = ["def ", "import ", "class ", "const ", "let ", "function ", "public class ", "struct ", "using namespace "]
    if any(kw in txt for kw in code_keywords) or ("{" in txt and "}" in txt and ";" in txt):
        return "code"
        
    return "text"

def add_clipboard_entry(text: str) -> bool:
    """Logs and auto-classifies a new clipboard copy transaction."""
    if not text or not text.strip():
        return False
        
    entries = _load_history()
    
    # Check if duplicate is the most recent copy
    if entries and entries[0].get("content", "").strip() == text.strip():
        return False

    content_type = classify_text(text)
    new_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "content": text.strip(),
        "type": content_type
    }
    
    # Prepend new entry
    entries.insert(0, new_entry)
    
    # Keep history capped at 500 items
    if len(entries) > 500:
        entries = entries[:500]
        
    return _save_history(entries)

def _monitor_loop():
    """Background polling worker evaluating clipboard updates."""
    global _STOP_SIGNAL
    logger.info("Starting Clipboard Monitor background thread...")
    last_text = ""
    
    try:
        last_text = pyperclip.paste()
    except Exception:
        pass

    while not _STOP_SIGNAL:
        try:
            current_text = pyperclip.paste()
            if current_text and current_text != last_text:
                add_clipboard_entry(current_text)
                last_text = current_text
        except Exception as err:
            logger.debug("Failed reading system clipboard: %s", err)
        time.sleep(0.5)

def start_clipboard_monitor() -> str:
    """Spawns the background monitor thread."""
    global _MONITOR_THREAD, _STOP_SIGNAL
    if _MONITOR_THREAD and _MONITOR_THREAD.is_alive():
        return "Clipboard history monitor thread is already online, sir."
        
    _STOP_SIGNAL = False
    _MONITOR_THREAD = threading.Thread(target=_monitor_loop, daemon=True, name="ClipboardMonitorThread")
    _MONITOR_THREAD.start()
    return "Smart clipboard history monitor thread initialized successfully, sir!"

def stop_clipboard_monitor() -> str:
    """Terminates the clipboard watcher."""
    global _STOP_SIGNAL
    _STOP_SIGNAL = True
    return "Clipboard history monitor stopped successfully, sir."

def search_clipboard(query: str) -> str:
    """Searches historically copied snippets for matching terms."""
    if not query:
        return "Search query cannot be empty, sir."
        
    entries = _load_history()
    matches = [e for e in entries if query.lower() in e.get("content", "").lower()]
    
    if not matches:
        return f"Aapki clipboard history mein query '{query}' se matching kuch nahi mila, sir."

    output = [f"### [CLIPBOARD] Search matches for '{query}':\n"]
    for idx, e in enumerate(matches[:10], 1):
        snippet = e['content'][:150] + "..." if len(e['content']) > 150 else e['content']
        output.append(f"{idx}. **[{e['type'].upper()}]** | Copied: {e['timestamp']}\n   - *Value*: `{snippet}`")
        
    return "\n".join(output)

def get_clipboard_history(count: int = 10) -> str:
    """Lists the most recently copied clipboard items."""
    entries = _load_history()
    if not entries:
        return "Aapka clipboard history memory empty hai, sir."

    output = ["### [CLIPBOARD] Recent Copied Entries:\n"]
    for idx, e in enumerate(entries[:count], 1):
        snippet = e['content'][:80].replace("\n", " ")
        if len(e['content']) > 80:
            snippet += "..."
        output.append(f"{idx}. **[{e['type'].upper()}]** ({e['timestamp']}): `{snippet}`")
        
    return "\n".join(output)

def restore_clipboard_item(index_or_content: str) -> str:
    """Restores a past clipboard entry back to the active system copy register."""
    entries = _load_history()
    target_text = ""
    
    # Try parsing index
    try:
        idx = int(index_or_content) - 1
        if 0 <= idx < len(entries):
            target_text = entries[idx]["content"]
    except ValueError:
        # Search content
        for e in entries:
            if index_or_content.lower() in e["content"].lower():
                target_text = e["content"]
                break

    if not target_text:
        return f"Could not find clipboard item matching '{index_or_content}', sir."

    try:
        pyperclip.copy(target_text)
        return "Sabash sir! Target item restored back to your active system copy register successfully."
    except Exception as e:
        return f"Failed to restore clipboard register: {e}, sir."

def clear_clipboard_history() -> str:
    """Sweeps all historical clipboard database entries."""
    if _save_history([]):
        return "System clipboard history swept successfully, sir!"
    return "Failed to clear the clipboard history, sir."

def clipboard_manager(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for clipboard_manager action."""
    action = parameters.get("action", "history").lower().strip()
    query = parameters.get("query", "")
    count = int(parameters.get("count", 10))
    value = parameters.get("value", "")
    
    if action == "start":
        return start_clipboard_monitor()
    elif action == "stop":
        return stop_clipboard_monitor()
    elif action == "search":
        return search_clipboard(query)
    elif action == "history":
        return get_clipboard_history(count)
    elif action == "restore":
        return restore_clipboard_item(value if value else query)
    elif action == "clear":
        return clear_clipboard_history()
    else:
        return "Unknown clipboard manager action, sir."

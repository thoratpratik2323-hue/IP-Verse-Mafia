"""
habit_tracker.py — AI Daily Habit Tracker module for IP Prime assistant.

Allows adding, completing, checking, and generating streaks summaries for daily routines.
Saves data locally inside data/habits.json.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.habit_tracker")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
HABITS_FILE = DATA_DIR / "habits.json"

def _ensure_data_store():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not HABITS_FILE.exists():
            with open(HABITS_FILE, "w", encoding="utf-8") as f:
                json.dump({"habits": []}, f, indent=4)
    except Exception as e:
        logger.error("Failed to ensure habits data directory: %s", e)

def _load_habits() -> list[dict[str, Any]]:
    _ensure_data_store()
    try:
        if HABITS_FILE.exists():
            with open(HABITS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("habits", [])
    except Exception as e:
        logger.error("Error loading habits: %s", e)
    return []

def _save_habits(habits: list[dict[str, Any]]) -> bool:
    _ensure_data_store()
    try:
        with open(HABITS_FILE, "w", encoding="utf-8") as f:
            json.dump({"habits": habits}, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving habits: %s", e)
    return False

def add_habit(name: str, frequency: str = "daily") -> str:
    """Adds a new habit to the JSON habits list."""
    if not name:
        return "Habit name cannot be empty, sir."
        
    habits = _load_habits()
    name_clean = name.strip()
    
    # Check if duplicate exists
    for h in habits:
        if h.get("name", "").lower() == name_clean.lower():
            return f"Habit '{name_clean}' already exists in your trackers list, sir."

    new_habit = {
        "name": name_clean,
        "frequency": frequency.lower(),
        "streak": 0,
        "last_checked": "",
        "created_at": datetime.now().strftime("%Y-%m-%d")
    }
    
    habits.append(new_habit)
    if _save_habits(habits):
        return f"Successfully added habit '{name_clean}' ({frequency}) to your daily goals, sir!"
    return "Failed to save the new habit, sir."

def check_habit(name: str) -> str:
    """Marks a habit completed today and updates streak parameters."""
    if not name:
        return "Habit name cannot be empty, sir."
        
    habits = _load_habits()
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    found = False
    
    for h in habits:
        if h.get("name", "").lower() == name.lower().strip():
            found = True
            last_checked = h.get("last_checked", "")
            
            if last_checked == today_str:
                return f"Habit '{h['name']}' is already completed today, sir! Great job!"
                
            # Update streak
            if last_checked == yesterday_str:
                h["streak"] += 1
            elif not last_checked or last_checked < yesterday_str:
                # Reset streak to 1
                h["streak"] = 1
                
            h["last_checked"] = today_str
            break
            
    if not found:
        return f"Habit '{name}' was not found in your trackers list, sir."
        
    if _save_habits(habits):
        return f"Sabash sir! Habit marked done today. Streak is now: {h['streak']} days!"
    return "Failed to write habit updates to database, sir."

def get_habit_report() -> str:
    """Generates a formatted text summary of all habits."""
    habits = _load_habits()
    if not habits:
        return "You have not registered any habits in your track list yet, sir."
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    output = ["### [HABIT TRACKER] Daily Progress Summary:\n"]
    for idx, h in enumerate(habits, 1):
        name = h.get("name")
        freq = h.get("frequency", "daily").upper()
        streak = h.get("streak", 0)
        last_checked = h.get("last_checked", "")
        
        # Verify if streak is broken
        active_streak = streak
        if last_checked and last_checked < yesterday_str and last_checked != today_str:
            active_streak = 0
            
        status = "✅ Completed Today" if last_checked == today_str else "❌ Pending Today"
        output.append(f"{idx}. **{name}** ({freq}) | Streak: {active_streak} days | Status: {status}")
        
    return "\n".join(output) + "\n\nInhe complete kijiye, sir!"

def delete_habit(name: str) -> str:
    """Deletes a habit tracker from the database."""
    if not name:
        return "Habit name cannot be empty, sir."
        
    habits = _load_habits()
    initial_len = len(habits)
    habits = [h for h in habits if h.get("name", "").lower() != name.lower().strip()]
    
    if len(habits) < initial_len:
        if _save_habits(habits):
            return f"Successfully deleted habit '{name}' from trackers, sir."
        return "Deleted but failed to write to database, sir."
    return f"Habit '{name}' was not found in your tracker list, sir."

def show_unchecked_notification(player: Optional[Any] = None) -> str:
    """Returns a status summary of pending daily habits, used for 9 PM triggers."""
    habits = _load_habits()
    today_str = datetime.now().strftime("%Y-%m-%d")
    pending = [h.get("name") for h in habits if h.get("last_checked") != today_str]
    
    if not pending:
        return "Congratulations sir! All daily habits are successfully checked off for today!"
        
    names = ", ".join(pending)
    msg = f"Reminder: Pratik Sir, you still have unchecked habits today: {names}."
    if player and hasattr(player, "write_log"):
        player.write_log(f"🔔 HABIT ALERT: {msg}")
    return msg

def habit_tracker(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for habit_tracker action."""
    action = parameters.get("action", "report").lower().strip()
    name = parameters.get("name", "")
    frequency = parameters.get("frequency", "daily")
    
    if action == "add":
        return add_habit(name, frequency)
    elif action == "check":
        return check_habit(name)
    elif action == "report":
        return get_habit_report()
    elif action == "delete":
        return delete_habit(name)
    elif action == "evening_check":
        return show_unchecked_notification(player)
    else:
        return "Unknown habit tracker action, sir."

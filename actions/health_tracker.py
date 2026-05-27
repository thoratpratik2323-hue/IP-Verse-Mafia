"""
health_tracker.py — Health parameters tracking logger (water, meal, sleep) for IP Prime.

Maintains date-wise entries (daily consumption, calorie inputs, sleep durations)
inside data/health_data.json.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.health_tracker")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
HEALTH_FILE = DATA_DIR / "health_data.json"

def _ensure_data_store():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not HEALTH_FILE.exists():
            with open(HEALTH_FILE, "w", encoding="utf-8") as f:
                json.dump({"water_goal_ml": 3000, "history": {}}, f, indent=4)
    except Exception as e:
        logger.error("Failed to ensure health tracker directory: %s", e)

def _load_data() -> dict[str, Any]:
    _ensure_data_store()
    try:
        if HEALTH_FILE.exists():
            with open(HEALTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error("Error loading health data: %s", e)
    return {"water_goal_ml": 3000, "history": {}}

def _save_data(data: dict[str, Any]) -> bool:
    _ensure_data_store()
    try:
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving health data: %s", e)
    return False

def _get_today_entry(db: dict[str, Any]) -> dict[str, Any]:
    today = time.strftime("%Y-%m-%d")
    hist = db.get("history", {})
    if today not in hist:
        hist[today] = {
            "water_intake_ml": 0,
            "meals": [],
            "sleep_hours": 0.0,
            "calories": 0
        }
        db["history"] = hist
    return hist[today]

def log_water(amount_ml: int) -> str:
    """Logs water consumption in milliliters today."""
    if amount_ml <= 0:
        return "Amount must be a positive integer, sir."
        
    db = _load_data()
    today_entry = _get_today_entry(db)
    
    today_entry["water_intake_ml"] = today_entry.get("water_intake_ml", 0) + amount_ml
    goal = db.get("water_goal_ml", 3000)
    current = today_entry["water_intake_ml"]
    
    if _save_data(db):
        percent = (current / goal) * 100
        return f"Successfully logged {amount_ml}ml water, sir! Today's total is {current}ml / {goal}ml ({percent:.1f}% achieved)."
    return "Failed to save water log, sir."

def set_water_goal(goal_ml: int) -> str:
    """Configures daily water target goals."""
    if goal_ml <= 0:
        return "Water target goal must be greater than zero, sir."
        
    db = _load_data()
    db["water_goal_ml"] = goal_ml
    
    if _save_data(db):
        return f"Daily water goal successfully set to {goal_ml}ml, sir!"
    return "Failed to update target water parameters, sir."

def log_meal(meal_name: str, estimated_calories: int = 400) -> str:
    """Logs a food description and calorie count."""
    if not meal_name:
        return "Meal description is required, sir."
        
    db = _load_data()
    today_entry = _get_today_entry(db)
    
    today_entry["meals"] = today_entry.get("meals", []) or []
    today_entry["meals"].append({
        "time": time.strftime("%I:%M %p"),
        "name": meal_name,
        "calories": estimated_calories
    })
    
    today_entry["calories"] = today_entry.get("calories", 0) + estimated_calories
    
    if _save_data(db):
        return f"Logged meal '{meal_name}' ({estimated_calories} kcal) successfully, sir!"
    return "Failed to log meal, sir."

def log_sleep(hours: float) -> str:
    """Logs total hours of sleep recorded today."""
    if hours <= 0:
        return "Sleep duration must be positive, sir."
        
    db = _load_data()
    today_entry = _get_today_entry(db)
    today_entry["sleep_hours"] = hours
    
    if _save_data(db):
        return f"Sleep logged successfully: {hours} hours. Rest well, sir!"
    return "Failed to save sleep duration parameters, sir."

def get_daily_health_summary() -> str:
    """Compiles a complete diagnostic log of today's health metrics."""
    db = _load_data()
    today = time.strftime("%Y-%m-%d")
    today_entry = db.get("history", {}).get(today, {
        "water_intake_ml": 0, "meals": [], "sleep_hours": 0.0, "calories": 0
    })
    
    water = today_entry.get("water_intake_ml", 0)
    goal = db.get("water_goal_ml", 3000)
    sleep = today_entry.get("sleep_hours", 0.0)
    kcal = today_entry.get("calories", 0)
    meals = today_entry.get("meals", [])
    
    meals_list = ", ".join([m.get("name", "") for m in meals]) if meals else "No meals logged."
    
    return (
        f"### [HEALTH DIGEST] Status Report ({today}):\n"
        f"• **Water Consumption**: {water}ml / {goal}ml\n"
        f"• **Total Sleep**: {sleep} hours\n"
        f"• **Calories Consumed**: {kcal} kcal\n"
        f"• **Meals**: {meals_list}\n\n"
        "Stay active and healthy, sir!"
    )

def health_tracker(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for health_tracker action."""
    action = parameters.get("action", "summary").lower().strip()
    value = int(parameters.get("value", 250))
    goal = int(parameters.get("goal", 3000))
    meal = parameters.get("meal", "")
    calories = int(parameters.get("calories", 400))
    sleep_hours = float(parameters.get("sleep_hours", 8.0))
    
    if action == "log_water":
        return log_water(value)
    elif action == "set_goal":
        return set_water_goal(goal)
    elif action == "log_meal":
        return log_meal(meal, calories)
    elif action == "log_sleep":
        return log_sleep(sleep_hours)
    elif action == "summary":
        return get_daily_health_summary()
    else:
        return "Unknown health tracker action parameter, sir."

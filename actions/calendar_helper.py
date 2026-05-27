"""
calendar_helper.py — Manages calendars, appointment schedulers, and time management entries.

This is a standard action module for the IP Prime personal assistant suite.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# Setup database path
BASE_DIR = Path(__file__).resolve().parent.parent
EVENTS_PATH = BASE_DIR / "config" / "calendar_events.json"

def _load_events() -> dict:
    """Loads all calendar events from JSON file."""
    if not EVENTS_PATH.exists():
        EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
        
    try:
        with open(EVENTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_events(events: dict):
    """Saves calendar events to JSON file."""
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=4)

def execute_schedule_manager(action: str, title: str = None, date: str = None, time: str = None, event_id: str = None) -> str:
    """Manages events, reminders, and schedules (add, list, delete)."""
    action_clean = action.lower().strip()
    events = _load_events()
    
    if action_clean == "add":
        if not title:
            return "Error: Cannot add an event without a title."
            
        # Parse or default date/time
        now = datetime.now()
        if not date:
            date = now.strftime("%Y-%m-%d") # Default to today
        if not time:
            time = now.strftime("%H:%M")     # Default to now
            
        # Format validation
        try:
            datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return f"Error: Date format should be YYYY-MM-DD (got '{date}') and Time format should be HH:MM (got '{time}')."
            
        evt_id = str(uuid.uuid4())[:8]
        events[evt_id] = {
            "title": title,
            "date": date,
            "time": time,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        _save_events(events)
        return f"### 📅 Event Added Successfully!\n- **ID**: `{evt_id}`\n- **Title**: {title}\n- **Date**: {date}\n- **Time**: {time}"
        
    elif action_clean == "list":
        if not events:
            return "### 📅 Schedule Calendar\nNo events scheduled in your calendar currently."
            
        # Sort events by date and time
        sorted_events = []
        for eid, evt in events.items():
            sorted_events.append({
                "id": eid,
                "title": evt["title"],
                "date": evt["date"],
                "time": evt["time"]
            })
            
        try:
            sorted_events.sort(key=lambda x: datetime.strptime(f"{x['date']} {x['time']}", "%Y-%m-%d %H:%M"))
        except Exception:
            pass # fallback to default sorting
            
        table_rows = ["| Event ID | Date | Time | Event Description |", "| --- | --- | --- | --- |"]
        for evt in sorted_events:
            table_rows.append(f"| `{evt['id']}` | {evt['date']} | {evt['time']} | {evt['title']} |")
            
        return "### 📅 Scheduled Events Calendar\n\n" + "\n".join(table_rows)
        
    elif action_clean == "delete":
        if not event_id:
            return "Error: Please specify the `event_id` of the event you wish to delete."
            
        if event_id not in events:
            # Try case-insensitive matching
            found_id = None
            for eid in events:
                if eid.lower() == event_id.lower():
                    found_id = eid
                    break
            if not found_id:
                return f"Error: Event with ID `{event_id}` was not found in your schedule calendar."
            event_id = found_id
            
        deleted_evt = events.pop(event_id)
        _save_events(events)
        
        return f"### 📅 Event Deleted\nSuccessfully removed event **'{deleted_evt['title']}'** (ID: `{event_id}`) from your schedule calendar."
        
    else:
        return f"Error: Unknown schedule action '{action}'."

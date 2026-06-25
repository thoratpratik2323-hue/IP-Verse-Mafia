import json
from pathlib import Path
from datetime import datetime, timedelta

def _get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent

CALENDAR_PATH = _get_base_dir() / "memory" / "calendar.json"

def _load_calendar() -> list[dict]:
    if not CALENDAR_PATH.exists():
        return []
    try:
        return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_calendar(data: list[dict]):
    CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def calendar_tool(parameters: dict, player=None) -> str:
    """
    Local calendar action helper.
    Supports actions: 'list' and 'create'
    """
    action = parameters.get("action", "list").lower().strip()
    
    if action == "create":
        return create_event(parameters, player)
    else:
        return list_events(parameters, player)

def list_events(parameters: dict, player=None) -> str:
    date_str = parameters.get("date", "today").lower().strip()
    
    # Resolve relative dates
    target_date = datetime.now()
    if date_str == "tomorrow":
        target_date = datetime.now() + timedelta(days=1)
    elif date_str != "today":
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass # Keep today's date if parsing fails
            
    target_date_str = target_date.strftime("%Y-%m-%d")
    events = _load_calendar()
    
    day_events = []
    for ev in events:
        if ev.get("date") == target_date_str:
            day_events.append(ev)
            
    # Sort events by start time
    day_events.sort(key=lambda x: x.get("start_time", "00:00"))
    
    if not day_events:
        msg = f"Sir, you have no events scheduled for {target_date.strftime('%A, %B %d, %Y')}."
        if player:
            player.write_log(f"SATURDAY: {msg}")
        return msg
        
    lines = [f"Sir, here is your agenda for {target_date.strftime('%A, %b %d')}:"]
    for ev in day_events:
        lines.append(f"  - [{ev.get('start_time')}] {ev.get('title')} ({ev.get('description', 'No desc')})")
        
    response = "\n".join(lines)
    if player:
        player.write_log(response)
    return response

def create_event(parameters: dict, player=None) -> str:
    title = parameters.get("title", "").strip()
    date_str = parameters.get("date", "today").lower().strip()
    start_time = parameters.get("start_time", "12:00").strip()
    description = parameters.get("description", "").strip()

    if not title:
        return "Please specify a title for the event, sir."

    # Resolve date
    target_date = datetime.now()
    if date_str == "tomorrow":
        target_date = datetime.now() + timedelta(days=1)
    elif date_str != "today":
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
            
    target_date_str = target_date.strftime("%Y-%m-%d")
    events = _load_calendar()
    
    new_event = {
        "title": title,
        "date": target_date_str,
        "start_time": start_time,
        "description": description,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    events.append(new_event)
    _save_calendar(events)
    
    msg = f"Successfully scheduled '{title}' for {target_date.strftime('%B %d, %Y')} at {start_time}, sir."
    if player:
        player.write_log(f"SATURDAY: {msg}")
    return msg

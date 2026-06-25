import logging
import json
from pathlib import Path
from memory.encryption import encrypt_string, decrypt_string

BASE_DIR = Path(__file__).resolve().parent.parent
GOALS_PATH = BASE_DIR / "data" / "daily_goals.json"

def _load_goals() -> list[dict]:
    if not GOALS_PATH.exists():
        return []
    try:
        raw_text = GOALS_PATH.read_text(encoding="utf-8").strip()
        if not raw_text:
            return []
        if not (raw_text.startswith("{") or raw_text.startswith("[")):
            raw_text = decrypt_string(raw_text)
        data = json.loads(raw_text)
        if isinstance(data, list):
            return data
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return []

def _save_goals(goals: list) -> None:
    GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw_json = json.dumps(goals, indent=2, ensure_ascii=False)
        GOALS_PATH.write_text(encrypt_string(raw_json), encoding="utf-8")
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)

def goals_tracker(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list").lower().strip()
    goal_text = parameters.get("goal", "").strip()
    idx_str = parameters.get("index", "").strip()
    
    goals = _load_goals()
    
    if action in ("set", "add"):
        if not goal_text:
            return "Please specify the goal description to add, sir."
        goals.append({
            "text": goal_text,
            "completed": False
        })
        _save_goals(goals)
        return f"Added daily goal: '{goal_text}', sir."
        
    elif action in ("list", "check_in"):
        if not goals:
            return "No daily goals set for today, sir!"
            
        output = ["### [DAILY GOALS] Status Check:\n"]
        for i, g in enumerate(goals, 1):
            status = "✅ Done" if g["completed"] else "❌ Pending"
            output.append(f"{i}. {g['text']} — *{status}*")
            
        pending_count = sum(1 for g in goals if not g["completed"])
        if pending_count > 0:
            output.append(f"\nYou have {pending_count} pending goals left, sir. Keep pushing!")
        else:
            output.append("\nAwesome job, sir! All goals completed for today.")
        return "\n".join(output)
        
    elif action == "complete":
        if not idx_str:
            return "Please specify the goal index to mark complete, sir."
        try:
            idx = int(idx_str) - 1
            if 0 <= idx < len(goals):
                goals[idx]["completed"] = True
                _save_goals(goals)
                return f"Marked goal '{goals[idx]['text']}' as completed, sir! Well done."
            return f"Invalid index. I only found {len(goals)} goals, sir."
        except ValueError:
            return "Please provide a valid integer for the index, sir."
            
    else:
        return "Unknown goals tracker action."

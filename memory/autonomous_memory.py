import json
from datetime import datetime
from pathlib import Path
import sys

from memory.memory_manager import (
    load_memory, 
    update_memory,
    load_session_log
)

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
EPISODIC_MEMORY_PATH = BASE_DIR / "memory" / "episodic.json"
PROCEDURAL_MEMORY_PATH = BASE_DIR / "memory" / "procedural.json"

class AutonomousMemory:
    """
    4-Layer Memory System for 100% Autonomous AI.
    1. Short-term memory (Current conversation / Session)
    2. Long-term memory (User preferences, past notes)
    3. Episodic memory (What we did, step by step)
    4. Procedural memory (How to do things best)
    """

    def __init__(self):
        self._ensure_files()

    def _ensure_files(self):
        for path in [EPISODIC_MEMORY_PATH, PROCEDURAL_MEMORY_PATH]:
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("[]" if "episodic" in str(path) else "{}", encoding="utf-8")

    # ==========================================
    # 1. SHORT-TERM MEMORY
    # ==========================================
    def get_short_term_context(self) -> str:
        """Returns the current short-term session summary."""
        log = load_session_log()
        return log.get("summary", "")

    # ==========================================
    # 2. LONG-TERM MEMORY (Preferences)
    # ==========================================
    def learn_preference(self, preference_name: str, preference_value: str):
        """Learns and saves a user preference to long term memory."""
        update_memory({
            "preferences": {
                preference_name: {
                    "value": preference_value,
                    "updated": datetime.now().strftime("%Y-%m-%d")
                }
            }
        })
        print(f"[Memory] Learnt preference: {preference_name} = {preference_value}")

    def recall_preferences(self) -> dict:
        """Recalls all user preferences."""
        mem = load_memory()
        prefs = mem.get("preferences", {})
        return {k: v.get("value", v) if isinstance(v, dict) else v for k, v in prefs.items()}

    # ==========================================
    # 3. EPISODIC MEMORY (Events & Tasks)
    # ==========================================
    def remember_task(self, goal: str, plan: dict, result: str, success: bool):
        """
        Saves a completed or failed task into episodic memory.
        'Ye task pehle bhi aaya tha, tab ye kiya tha'
        """
        try:
            data = json.loads(EPISODIC_MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = []

        episode = {
            "timestamp": datetime.now().isoformat(),
            "goal": goal,
            "plan_steps": plan.get("steps", []),
            "result": result,
            "success": success
        }
        data.append(episode)

        # Keep last 100 episodes
        if len(data) > 100:
            data = data[-100:]

        EPISODIC_MEMORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[Memory] Episodic memory saved: '{goal}' (Success: {success})")

    def recall_past_experience(self, goal: str) -> list[dict]:
        """Recalls past experiences similar to the given goal."""
        try:
            data = json.loads(EPISODIC_MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []

        # Simple keyword matching for now (can be upgraded to embeddings)
        keywords = set(goal.lower().split())
        relevant = []
        for ep in data:
            ep_words = set(ep.get("goal", "").lower().split())
            if len(keywords.intersection(ep_words)) > 0:
                relevant.append(ep)
        
        # Sort by most recent
        return sorted(relevant, key=lambda x: x["timestamp"], reverse=True)[:3]

    # ==========================================
    # 4. PROCEDURAL MEMORY (How to do things)
    # ==========================================
    def learn_procedure(self, task_type: str, steps: list):
        """Saves a proven workflow for a specific task type."""
        try:
            data = json.loads(PROCEDURAL_MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}

        data[task_type] = {
            "steps": steps,
            "updated_at": datetime.now().isoformat()
        }

        PROCEDURAL_MEMORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[Memory] Procedural memory updated for: {task_type}")

    def recall_procedure(self, task_type: str) -> list:
        """'Ye kaam karne ka best tarika ye hai'"""
        try:
            data = json.loads(PROCEDURAL_MEMORY_PATH.read_text(encoding="utf-8"))
            return data.get(task_type, {}).get("steps", [])
        except Exception:
            return []

    def recall_all_procedures(self) -> dict:
        try:
            return json.loads(PROCEDURAL_MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}


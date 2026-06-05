"""
goal_generator.py — IP Prime Autonomous Goal Generator (Phase 3)

Prime observes your patterns and generates its OWN goals — no commands needed.
Examples:
  • 10 PM pe tum code karte ho → Prime suggests review / backup
  • Subah 9 AM → Daily digest email bheje
  • 3 AM → Auto-update check
  • Idle 30 min → Index workspace / cleanup memory
  • Monday → Weekly summary generate kare
"""

import json
import time
import threading
from datetime import datetime, date
from pathlib import Path

BASE_DIR        = Path(__file__).resolve().parent.parent
PATTERN_FILE    = BASE_DIR / "data" / "usage_patterns.json"
GOALS_LOG       = BASE_DIR / "logs" / "auto_goals.log"


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [GoalGen] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        try:
            print(line.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass
    GOALS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(GOALS_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_patterns() -> dict:
    if PATTERN_FILE.exists():
        try:
            with open(PATTERN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_patterns(patterns: dict):
    PATTERN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PATTERN_FILE, "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=2, ensure_ascii=False)


def record_activity(activity: str):
    """Call this whenever user does something so Prime learns patterns."""
    patterns = _load_patterns()
    now       = datetime.now()
    hour      = now.hour
    weekday   = now.strftime("%A")   # Monday, Tuesday ...

    key = f"{weekday}_{hour:02d}"
    if key not in patterns:
        patterns[key] = {}
    patterns[key][activity] = patterns[key].get(activity, 0) + 1
    _save_patterns(patterns)


def get_time_based_goals(core_engine=None) -> list[dict]:
    """
    Returns a list of autonomous goals based on time-of-day and day-of-week.
    Each goal is: {"goal": str, "priority": int, "reason": str}
    """
    now     = datetime.now()
    hour    = now.hour
    minute  = now.minute
    weekday = now.strftime("%A")
    goals   = []

    # ── Morning Goals (8-9 AM) ────────────────────────────────────────────────
    if hour == 8 and minute < 30:
        goals.append({
            "goal": "Generate and send the daily morning briefing email to Pratik Sir",
            "priority": 2,
            "reason": "Morning routine — daily digest at 8 AM"
        })
        goals.append({
            "goal": "Check all pending reminders and tasks for today",
            "priority": 2,
            "reason": "Start-of-day task review"
        })

    # ── Late Night Coding Hours (10 PM - 12 AM) ───────────────────────────────
    if 22 <= hour <= 23:
        goals.append({
            "goal": "Proactively index the coding projects workspace for semantic search",
            "priority": 3,
            "reason": "Pratik typically codes at night — keeping workspace indexed"
        })
        goals.append({
            "goal": "Check git status of all projects and suggest any uncommitted changes",
            "priority": 3,
            "reason": "Night coding session — ensure code is committed"
        })

    # ── Auto Update (3 AM) ────────────────────────────────────────────────────
    if hour == 3 and minute < 15:
        goals.append({
            "goal": "Run auto_update to check and apply latest IP Prime updates from GitHub",
            "priority": 1,
            "reason": "Nightly self-update check at 3 AM"
        })

    # ── Weekly Summary (Monday Morning) ──────────────────────────────────────
    if weekday == "Monday" and hour == 9 and minute < 30:
        goals.append({
            "goal": "Generate a weekly performance summary covering all tasks completed, memory entries, and system health",
            "priority": 2,
            "reason": "Weekly Monday morning summary"
        })

    # ── Memory Cleanup (Every Sunday Night) ──────────────────────────────────
    if weekday == "Sunday" and hour == 23:
        goals.append({
            "goal": "Run compact_memory to vacuum LanceDB and archive logs",
            "priority": 3,
            "reason": "Weekly memory maintenance"
        })

    # ── Idle Productivity Goals ────────────────────────────────────────────────
    # These are added by the idle detector, not this function

    return goals


def idle_goals(idle_minutes: int) -> list[dict]:
    """Goals to generate when user has been idle for `idle_minutes` minutes."""
    goals = []

    if idle_minutes >= 15:
        goals.append({
            "goal": "Run incremental semantic indexing of the workspace in background",
            "priority": 4,
            "reason": f"User idle for {idle_minutes} minutes — good time to index"
        })

    if idle_minutes >= 30:
        goals.append({
            "goal": "Run compact_memory to optimize search database during idle time",
            "priority": 4,
            "reason": f"User idle for {idle_minutes} minutes — memory maintenance"
        })

    if idle_minutes >= 60:
        goals.append({
            "goal": "Run full system health check and write a self-diagnostic report",
            "priority": 4,
            "reason": f"User idle for {idle_minutes} minutes — full audit"
        })

    return goals


class GoalGenerator:
    """
    Runs as a background thread.
    Every 15 minutes, checks time-based goals and submits them to the task queue.
    """
    def __init__(self, core_engine=None, speak=None):
        self.core    = core_engine
        self.speak   = speak
        self._thread = None
        self._stop   = threading.Event()
        self._submitted_today: set = set()

    def _submit_goal(self, goal_dict: dict):
        """Submits a goal to the autonomous task queue."""
        goal_key = f"{date.today()}::{goal_dict['goal'][:50]}"
        if goal_key in self._submitted_today:
            return   # Already submitted today, skip

        self._submitted_today.add(goal_key)
        _log(f"🎯 Auto-goal: {goal_dict['goal'][:80]}... (Priority {goal_dict['priority']})")

        if self.core and hasattr(self.core, "add_goal"):
            self.core.add_goal(
                goal_dict["goal"],
                context=f"[AUTO] {goal_dict['reason']}",
                priority=goal_dict.get("priority", 3)
            )
        else:
            # Try task queue directly
            try:
                from agent.task_queue import get_queue, TaskPriority
                p_map = {1: TaskPriority.HIGH, 2: TaskPriority.HIGH,
                         3: TaskPriority.NORMAL, 4: TaskPriority.LOW}
                priority = p_map.get(goal_dict.get("priority", 3), TaskPriority.NORMAL)
                speak_fn = self.speak or (lambda x: None)
                get_queue().submit(goal=goal_dict["goal"], priority=priority, speak=speak_fn)
            except Exception as e:
                _log(f"⚠️ Could not submit goal to queue: {e}")

    def _loop(self):
        _log("🧠 Autonomous Goal Generator started.")
        # Reset daily submissions at midnight
        current_day = date.today()

        while not self._stop.is_set():
            # Reset on new day
            if date.today() != current_day:
                self._submitted_today.clear()
                current_day = date.today()

            # Get and submit time-based goals
            goals = get_time_based_goals(self.core)
            for g in goals:
                self._submit_goal(g)

            self._stop.wait(timeout=60 * 15)   # Check every 15 minutes

        _log("🔴 Goal Generator stopped.")

    def start(self):
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="GoalGenerator"
        )
        self._thread.start()
        return self._thread

    def stop(self):
        self._stop.set()

    def submit_idle_goals(self, idle_minutes: int):
        """Called by proactive monitor when user is idle."""
        for g in idle_goals(idle_minutes):
            self._submit_goal(g)


# Singleton instance
_generator_instance: GoalGenerator | None = None

def get_goal_generator(core_engine=None, speak=None) -> GoalGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = GoalGenerator(core_engine, speak)
    return _generator_instance

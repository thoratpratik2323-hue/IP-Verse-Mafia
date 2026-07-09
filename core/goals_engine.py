"""
core/goals_engine.py — Active goals injector for IP Prime system prompt.
Loads goals from memory/goals.json and injects them into every session.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger("goals_engine")
GOALS_PATH = Path("memory/goals.json")

Status = Literal["active", "done", "paused"]


class GoalsEngine:
    """Manages Pratik's goals and injects them into the AI system prompt."""

    def __init__(self):
        self._goals: list[dict] = []
        self._load()

    def _load(self):
        GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if GOALS_PATH.exists():
            try:
                self._goals = json.loads(GOALS_PATH.read_text(encoding="utf-8"))
            except Exception:
                self._goals = []
        else:
            # Seed with example goals
            self._goals = [
                {"id": 1, "title": "Build IP Prime mobile companion app", "status": "active", "progress": 10},
                {"id": 2, "title": "Get internship / first job offer", "status": "active", "progress": 30},
                {"id": 3, "title": "Deploy REZ voice model online", "status": "active", "progress": 60},
            ]
            self._save()

    def _save(self):
        try:
            GOALS_PATH.write_text(json.dumps(self._goals, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"[Goals] Save failed: {e}")

    def add(self, title: str, progress: int = 0) -> dict:
        new_id = max((g["id"] for g in self._goals), default=0) + 1
        goal = {"id": new_id, "title": title, "status": "active",
                "progress": progress, "created": datetime.now().isoformat()}
        self._goals.append(goal)
        self._save()
        return goal

    def complete(self, goal_id: int) -> bool:
        for g in self._goals:
            if g["id"] == goal_id:
                g["status"] = "done"
                g["completed"] = datetime.now().isoformat()
                self._save()
                return True
        return False

    def update_progress(self, goal_id: int, progress: int) -> bool:
        for g in self._goals:
            if g["id"] == goal_id:
                g["progress"] = max(0, min(100, progress))
                self._save()
                return True
        return False

    def active_goals(self) -> list[dict]:
        return [g for g in self._goals if g.get("status") == "active"]

    def get_prompt_block(self) -> str:
        """Returns a formatted block to inject into the AI system prompt."""
        active = self.active_goals()
        if not active:
            return ""
        lines = [f"PRATIK'S ACTIVE GOALS (auto-injected — track progress, celebrate milestones):"]
        for g in active:
            bar = "█" * (g.get("progress", 0) // 10) + "░" * (10 - g.get("progress", 0) // 10)
            lines.append(f"  [{bar}] {g.get('progress', 0)}% — {g['title']}")
        return "\n".join(lines)


# Singleton
Goals = GoalsEngine()

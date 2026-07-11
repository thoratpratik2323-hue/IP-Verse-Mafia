from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ipprime.core.autonomy_engine")

# ── Paths ──────────────────────────────────────────────────────────────────
try:
    from actions.prime_utils import get_base_dir, get_api_key
    BASE_DIR = get_base_dir()
except Exception:
    # Fallback so this module never hard-crashes on import order issues
    BASE_DIR = Path(__file__).resolve().parent.parent
    def get_api_key():
        import os
        return os.environ.get("GEMINI_API_KEY", "")

MEMORY_DIR     = BASE_DIR / "memory"
CONFIG_DIR     = BASE_DIR / "config"
GOALS_FILE     = MEMORY_DIR / "autonomy_goals.json"
CONFIRM_FILE   = MEMORY_DIR / "autonomy_pending_confirmations.json"
LOG_FILE       = MEMORY_DIR / "autonomy_log.json"
POLICY_FILE    = CONFIG_DIR / "autonomy_policy.json"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# ── Default safety policy (used if config/autonomy_policy.json is missing) ──
DEFAULT_POLICY = {
    # Read-only / reversible / low-blast-radius tools. Auto-executed even in
    # "supervised" mode.
    "safe_tools": [
        "web_search", "web_search_quick", "weather_action", "system_monitor",
        "translate_text", "query_visual_timeline", "quick_briefing",
        "morning_briefing", "morning_briefer", "screen_explainer",
        "design_extractor", "live_code_reviewer", "email_summarizer",
        "clipboard_action", "task_planner", "reminder", "calendar_tool",
        "fetch_realtime_knowledge", "file_explorer"
    ],
    # Everything not explicitly listed as safe or forbidden defaults to this
    # tier — needs human approval before it runs autonomously.
    "default_tier": "CONFIRM",
    # Hard-blocked no matter what autonomy_level is set to. Editing these out
    # requires a deliberate code change, not a config toggle.
    "forbidden_tools": [
        "panic_wipe", "run_panic_wipe"
    ],
    # Defense in depth: if ANY proposed tool call's name or arguments contain
    # one of these (case-insensitive), it is blocked regardless of tool name.
    "forbidden_keywords": [
        "format c:", "rm -rf /", "rm -rf ~", "del /f /s /q", "factory_reset",
        "factory reset", "disable firewall", "disable antivirus",
        "disable_security", "wipe drive", "delete all", "shutdown -s -f",
        "diskpart", "drop database", "delete_all"
    ],
    # Max autonomous steps a single goal can take before it's force-stopped
    # (stops infinite loops if the model keeps proposing actions).
    "max_steps_per_goal": 8
}


def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to read %s: %s", path, e)
    return default


def _save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.error("Failed to write %s: %s", path, e)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── Safety Gate ──────────────────────────────────────────────────────────────
class SafetyGate:
    """Classifies a proposed (tool_name, args) pair into SAFE / CONFIRM / FORBIDDEN."""

    def __init__(self):
        self.policy = DEFAULT_POLICY.copy()
        if POLICY_FILE.exists():
            try:
                user_policy = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
                self.policy.update(user_policy)
            except Exception as e:
                logger.warning("Could not parse autonomy_policy.json, using defaults: %s", e)
        else:
            _save_json(POLICY_FILE, DEFAULT_POLICY)

    def classify(self, tool_name: str, args: dict) -> str:
        haystack = f"{tool_name} {json.dumps(args, ensure_ascii=False)}".lower()

        for kw in self.policy.get("forbidden_keywords", []):
            if kw.lower() in haystack:
                return "FORBIDDEN"

        if tool_name in self.policy.get("forbidden_tools", []):
            return "FORBIDDEN"

        if tool_name in self.policy.get("safe_tools", []):
            return "SAFE"

        return self.policy.get("default_tier", "CONFIRM")


# ── Lightweight stand-ins for player/speak so dispatch_tool() can run headless ──
class _SilentPlayer:
    """Minimal stand-in for the UI 'player' object that action modules expect.
    Forwards to a real session_mgr.ui if one is attached, else just logs."""

    def __init__(self, session_mgr=None):
        self.session_mgr = session_mgr

    def write_log(self, msg: str):
        logger.info(msg)
        ui = getattr(self.session_mgr, "ui", None) if self.session_mgr else None
        if ui and hasattr(ui, "write_log"):
            try:
                ui.write_log(f"[Autonomy] {msg}")
            except Exception:
                pass

    def write_thought(self, msg: str):
        self.write_log(msg)


def _silent_speak(text: str):
    # Autonomous background actions stay silent by default — they shouldn't
    # talk over the user unprompted. Logged instead of spoken.
    logger.info("[Autonomy speak-suppressed] %s", text)


# ── Autonomy Core ─────────────────────────────────────────────────────────────
class AutonomyCore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *a, **kw):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.gate = SafetyGate()
        self.session_mgr = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.interval = 90              # seconds between decision-loop ticks
        self.idle_required = True       # only act when the user isn't mid-conversation
        self.idle_threshold = 300       # seconds of silence considered "idle"
        self.autonomy_level = "supervised"   # off | supervised | trusted
        self._goals_lock = threading.Lock()
        self._confirm_lock = threading.Lock()

    # ── Lifecycle ────────────────────────────────────────────────────────────
    def start(self, session_mgr=None, interval=90, idle_required=True,
              idle_threshold=300, autonomy_level="supervised"):
        self.session_mgr = session_mgr
        self.interval = interval
        self.idle_required = idle_required
        self.idle_threshold = idle_threshold
        self.autonomy_level = autonomy_level
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Autonomy core started (level=%s, interval=%ss).",
                     autonomy_level, interval)

    def stop(self):
        self.running = False

    def set_autonomy_level(self, level: str):
        assert level in ("off", "supervised", "trusted"), "invalid autonomy level"
        self.autonomy_level = level
        self._log({"event": "level_changed", "level": level, "ts": _now()})

    # ── Goal queue ───────────────────────────────────────────────────────────
    def add_goal(self, description: str, priority: str = "normal", source: str = "user") -> str:
        goal_id = uuid.uuid4().hex[:10]
        with self._goals_lock:
            goals = _load_json(GOALS_FILE, [])
            goals.append({
                "id": goal_id,
                "description": description,
                "priority": priority,       # low | normal | high
                "source": source,           # user | self_proposed
                "status": "pending",        # pending | awaiting_confirmation | done | failed
                "steps_taken": 0,
                "history": [],
                "created_at": _now(),
                "updated_at": _now(),
            })
            _save_json(GOALS_FILE, goals)
        self._log({"event": "goal_added", "goal_id": goal_id, "description": description})
        return goal_id

    def list_goals(self, status: Optional[str] = None) -> list:
        goals = _load_json(GOALS_FILE, [])
        if status:
            return [g for g in goals if g["status"] == status]
        return goals

    def _update_goal(self, goal_id: str, **fields):
        with self._goals_lock:
            goals = _load_json(GOALS_FILE, [])
            for g in goals:
                if g["id"] == goal_id:
                    g.update(fields)
                    g["updated_at"] = _now()
                    break
            _save_json(GOALS_FILE, goals)

    def _next_pending_goal(self) -> Optional[dict]:
        goals = _load_json(GOALS_FILE, [])
        pending = [g for g in goals if g["status"] == "pending"]
        if not pending:
            return None
        order = {"high": 0, "normal": 1, "low": 2}
        pending.sort(key=lambda g: (order.get(g.get("priority", "normal"), 1), g["created_at"]))
        return pending[0]

    # ── Pending confirmations (CONFIRM-tier actions awaiting a human yes/no) ──
    def get_pending_confirmations(self) -> list:
        return _load_json(CONFIRM_FILE, [])

    def _queue_confirmation(self, goal_id: str, tool: str, args: dict, reasoning: str) -> str:
        conf_id = uuid.uuid4().hex[:10]
        with self._confirm_lock:
            confs = _load_json(CONFIRM_FILE, [])
            confs.append({
                "id": conf_id, "goal_id": goal_id, "tool": tool, "args": args,
                "reasoning": reasoning, "created_at": _now()
            })
            _save_json(CONFIRM_FILE, confs)
        self._update_goal(goal_id, status="awaiting_confirmation")
        self._notify_confirmation_needed(tool, reasoning)
        return conf_id

    def approve_action(self, confirmation_id: str) -> str:
        with self._confirm_lock:
            confs = _load_json(CONFIRM_FILE, [])
            match = next((c for c in confs if c["id"] == confirmation_id), None)
            if not match:
                return "Confirmation ID not found."
            confs = [c for c in confs if c["id"] != confirmation_id]
            _save_json(CONFIRM_FILE, confs)

        result = self._execute(match["tool"], match["args"])
        self._record_step(match["goal_id"], match["tool"], match["args"], "CONFIRM_APPROVED", result)
        self._update_goal(match["goal_id"], status="pending")  # resume loop next tick
        return f"Approved and executed '{match['tool']}': {result}"

    def reject_action(self, confirmation_id: str, reason: str = "") -> str:
        with self._confirm_lock:
            confs = _load_json(CONFIRM_FILE, [])
            match = next((c for c in confs if c["id"] == confirmation_id), None)
            if not match:
                return "Confirmation ID not found."
            confs = [c for c in confs if c["id"] != confirmation_id]
            _save_json(CONFIRM_FILE, confs)

        self._record_step(match["goal_id"], match["tool"], match["args"], "CONFIRM_REJECTED", reason)
        self._update_goal(match["goal_id"], status="failed")
        return "Rejected. Goal marked as failed."

    def _notify_confirmation_needed(self, tool: str, reasoning: str):
        msg = f"Approval needed for action '{tool}': {reasoning}"
        try:
            from os_shell.notification_center import push_notification
            push_notification("IP Prime — approval needed", msg)
        except Exception:
            logger.info("[Autonomy] %s", msg)
        if self.session_mgr and hasattr(self.session_mgr, "ui"):
            try:
                self.session_mgr.ui.write_log(f"[Autonomy] {msg}")
            except Exception:
                pass

    # ── Decision loop ────────────────────────────────────────────────────────
    def _run_loop(self):
        time.sleep(20)  # let the rest of the app finish booting first
        while self.running:
            try:
                if self.autonomy_level != "off":
                    if (not self.idle_required) or self._is_idle():
                        goal = self._next_pending_goal()
                        if goal:
                            self._process_goal(goal)
            except Exception as e:
                logger.error("Autonomy loop error: %s", e)
            time.sleep(self.interval)

    def _is_idle(self) -> bool:
        if not self.session_mgr:
            return True
        now = time.time()
        last_act = getattr(self.session_mgr, "_last_user_activity", now)
        tool_active = getattr(self.session_mgr, "_tool_executing", False)
        speaking = getattr(self.session_mgr, "_is_speaking", False)
        return (now - last_act > self.idle_threshold) and not tool_active and not speaking

    def _process_goal(self, goal: dict):
        if goal.get("steps_taken", 0) >= self.gate.policy.get("max_steps_per_goal", 8):
            self._update_goal(goal["id"], status="failed")
            self._log({"event": "goal_failed_step_limit", "goal_id": goal["id"]})
            return

        decision = self._decide_next_step(goal)
        tool = decision.get("tool")
        args = decision.get("args", {}) or {}
        reasoning = decision.get("reasoning", "")

        if not tool or decision.get("done"):
            self._update_goal(goal["id"], status="done")
            self._log({"event": "goal_completed", "goal_id": goal["id"], "reasoning": reasoning})
            return

        tier = self.gate.classify(tool, args)

        if tier == "FORBIDDEN":
            self._record_step(goal["id"], tool, args, "BLOCKED", "Blocked by safety policy")
            self._update_goal(goal["id"], status="failed")
            self._log({"event": "action_blocked", "goal_id": goal["id"], "tool": tool})
            return

        if tier == "SAFE" or (tier == "CONFIRM" and self.autonomy_level == "trusted"):
            result = self._execute(tool, args)
            self._record_step(goal["id"], tool, args, "EXECUTED", result)
            steps = goal.get("steps_taken", 0) + 1
            self._update_goal(goal["id"], status="pending", steps_taken=steps)
            return

        # tier == CONFIRM and we're in supervised mode -> ask the human
        self._queue_confirmation(goal["id"], tool, args, reasoning)
        self._log({"event": "confirmation_requested", "goal_id": goal["id"], "tool": tool})

    def _decide_next_step(self, goal: dict) -> dict:
        """Asks Gemini which single tool call (if any) makes progress on this goal."""
        client = self._gemini_client()
        if not client:
            return {"tool": None, "done": True, "reasoning": "No API key configured."}

        try:
            from core.tool_registry import TOOL_DECLARATIONS
            catalog = "\n".join(
                f"- {t['name']}: {t.get('description', '')[:140]}" for t in TOOL_DECLARATIONS
            )
        except Exception:
            catalog = "(tool catalog unavailable)"

        history = goal.get("history", [])[-5:]
        prompt = f"""You are the autonomous planning core of IP Prime, Pratik Thorat's personal AI assistant.

Goal: "{goal['description']}"
Steps already taken on this goal: {json.dumps(history, ensure_ascii=False)}

Available tools (name: description):
{catalog}

Decide the single next concrete tool call to make progress on this goal, or
decide the goal is already complete / cannot be completed safely.

Return ONLY raw JSON with these exact keys:
{{"tool": "<tool_name or null>", "args": {{}}, "reasoning": "<one short sentence>", "done": false}}

Set "done": true and "tool": null once the goal is finished or should stop.
Be conservative — only propose actions clearly necessary for this goal."""

        try:
            from google.genai import types
            from actions.model_switcher import get_preferred_model
            model_name = get_preferred_model("fast")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text.strip())
            return data
        except Exception as e:
            logger.warning("Decision step failed for goal %s: %s", goal["id"], e)
            return {"tool": None, "done": True, "reasoning": f"Planning failed: {e}"}

    def _gemini_client(self):
        try:
            from google import genai
            api_key = get_api_key()
            if api_key:
                return genai.Client(api_key=api_key)
        except Exception as e:
            logger.debug("Gemini client init failed: %s", e)
        return None

    # ── Execution ────────────────────────────────────────────────────────────
    def _execute(self, tool: str, args: dict) -> str:
        try:
            from core.tool_dispatcher import dispatch_tool
        except Exception as e:
            return f"dispatch_tool unavailable: {e}"

        player = _SilentPlayer(self.session_mgr)

        async def _run():
            loop = asyncio.get_running_loop()
            return await dispatch_tool(tool, args, player, _silent_speak, loop)

        try:
            return asyncio.run(_run())
        except Exception as e:
            return f"Execution error: {e}"

    # ── Logging ──────────────────────────────────────────────────────────────
    def _record_step(self, goal_id: str, tool: str, args: dict, outcome: str, result: str):
        with self._goals_lock:
            goals = _load_json(GOALS_FILE, [])
            for g in goals:
                if g["id"] == goal_id:
                    g.setdefault("history", []).append({
                        "tool": tool, "args": args, "outcome": outcome,
                        "result": str(result)[:300], "ts": _now()
                    })
                    break
            _save_json(GOALS_FILE, goals)
        self._log({"event": "step", "goal_id": goal_id, "tool": tool, "outcome": outcome})

    def _log(self, entry: dict):
        entry["ts"] = entry.get("ts", _now())
        log = _load_json(LOG_FILE, [])
        log.append(entry)
        _save_json(LOG_FILE, log[-200:])


# Module-level singleton — import this everywhere
autonomy_core = AutonomyCore()


# ── Voice/chat-callable wrapper (register in tool_registry + tool_dispatcher) ──
def autonomy_engine(parameters: dict, player=None) -> str:
    """Dispatcher-style entrypoint so this can be wired in as a normal tool too.
    action: add_goal | list_goals | pending_confirmations | approve | reject | set_level
    """
    action = parameters.get("action", "list_goals")

    if action == "add_goal":
        desc = parameters.get("description", "")
        if not desc:
            return "Please provide 'description', sir."
        priority = parameters.get("priority", "normal")
        goal_id = autonomy_core.add_goal(desc, priority=priority)
        return f"Goal queued, sir. ID: {goal_id}"

    elif action == "list_goals":
        status = parameters.get("status")
        goals = autonomy_core.list_goals(status)
        if not goals:
            return "No goals in the queue, sir."
        lines = [f"[{g['status']}] {g['id']}: {g['description']}" for g in goals]
        return "\n".join(lines)

    elif action == "pending_confirmations":
        confs = autonomy_core.get_pending_confirmations()
        if not confs:
            return "Nothing awaiting your approval, sir."
        lines = [f"{c['id']}: {c['tool']} — {c['reasoning']}" for c in confs]
        return "\n".join(lines)

    elif action == "approve":
        conf_id = parameters.get("confirmation_id", "")
        return autonomy_core.approve_action(conf_id)

    elif action == "reject":
        conf_id = parameters.get("confirmation_id", "")
        reason = parameters.get("reason", "")
        return autonomy_core.reject_action(conf_id, reason)

    elif action == "set_level":
        level = parameters.get("level", "supervised")
        autonomy_core.set_autonomy_level(level)
        return f"Autonomy level set to '{level}', sir."

    return f"Unknown autonomy_engine action: '{action}', sir."

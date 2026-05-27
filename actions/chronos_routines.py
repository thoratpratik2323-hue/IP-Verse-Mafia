"""
chronos_routines.py — Time-tracking analytics and automated productivity routine scheduler.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/chronos_routines.py
import json
import time
import threading
from pathlib import Path
from datetime import datetime

def _get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()

class ChronosRoutines:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._running = False
        self._thread = None
        self._player = None
        self._last_checked_minute = ""
        
    @classmethod
    def instance(cls) -> "ChronosRoutines":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
            
    def start(self, player=None) -> str:
        if self._running:
            return "Chronos-AI scheduler is already running."
        self._player = player
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, name="ChronosAI-Scheduler", daemon=True)
        self._thread.start()
        print("[Chronos-AI] ⏰ Scheduler engine started.")
        return "Chronos-AI routines engine started successfully."
        
    def stop(self) -> str:
        self._running = False
        print("[Chronos-AI] 🛑 Scheduler engine stopped.")
        return "Chronos-AI routines engine stopped."
        
    def load_routines(self) -> dict:
        routines_file = BASE_DIR / "config" / "routines.json"
        default_routines = {
            "morning_brief": {"enabled": True, "time": "08:00", "actions": ["briefing", "weather", "broadcast"]},
            "workspace_check": {"enabled": True, "time": "18:00", "actions": ["compile", "broadcast"]}
        }
        if not routines_file.exists():
            return default_routines
        try:
            return json.loads(routines_file.read_text(encoding="utf-8"))
        except Exception:
            return default_routines
            
    def _scheduler_loop(self):
        while self._running:
            try:
                now_str = datetime.now().strftime("%H:%M")
                if now_str != self._last_checked_minute:
                    self._last_checked_minute = now_str
                    routines = self.load_routines()
                    
                    for name, routine in routines.items():
                        if routine.get("enabled", False) and routine.get("time", "") == now_str:
                            actions = routine.get("actions", [])
                            print(f"[Chronos-AI] 🔔 Triggering routine: '{name}' with actions: {actions}")
                            threading.Thread(target=self.execute_routine, args=(name, actions), daemon=True).start()
            except Exception as e:
                print(f"[Chronos-AI Error] {e}")
            time.sleep(10)
            
    def execute_routine(self, name: str, actions: list[str]):
        print(f"[Chronos-AI] Executing {name}...")
        report_parts = []
        
        # 1. Weather Bulletin
        if "weather" in actions:
            try:
                from actions.weather_report import weather_action
                weather_res = weather_action({})
                report_parts.append(f"Weather Update:\n{weather_res}")
            except Exception:
                report_parts.append("Weather: Service temporarily unavailable.")
                
        # 2. Workspace Compile Check
        if "compile" in actions:
            try:
                report_parts.append("Workspace Check: Initiating py_compile check...")
                import glob
                import py_compile
                python_files = glob.glob(str(BASE_DIR / "*.py")) + glob.glob(str(BASE_DIR / "actions" / "*.py"))
                errors = []
                for f in python_files[:15]: # check up to 15 key files
                    try:
                        py_compile.compile(f, doraise=True)
                    except Exception as err:
                        errors.append(Path(f).name + f" ({err})")
                if errors:
                    report_parts.append(f"Workspace Status: ⚠️ Syntax errors found in: {', '.join(errors)}")
                else:
                    report_parts.append("Workspace Status: ✅ All core files compiled with zero syntax errors!")
            except Exception as e:
                report_parts.append(f"Workspace Status: compilation scan check failed: {e}")
                
        # 3. Morning Briefing / News Summary
        if "briefing" in actions:
            # Generate a gorgeous sweet briefing context
            brief = (
                f"Namaste Pratik Sir! Main IP Prime bol raha hoon. Aaj {datetime.now().strftime('%A, %B %d')} hai. "
                "Aaj ka din bilkul smooth aur productive hone wala hai. Aapke workspace check ready hain, "
                "aur main poori tarah se online hoon. Boliye, aaj kya coding aur project tasks start karein?"
            )
            report_parts.append(f"Voice Briefing:\n{brief}")
            # Speak it out loud!
            if self._player and hasattr(self._player, "speak"):
                self._player.speak(
                    f"[SYSTEM_EVENT] Greet your creator Pratik Sir with this sweet morning brief in Hinglish: {brief}"
                )
                
        # 4. Broadcast Notification
        if "broadcast" in actions or len(report_parts) > 0:
            try:
                from actions.broadcast_center import broadcast_notification
                title = f"Chronos-AI: {name.replace('_', ' ').title()}"
                body = "\n\n".join(report_parts)
                broadcast_notification(title, body)
            except Exception as e:
                print(f"[Chronos-AI Broadcast Error] {e}")
                
        print(f"[Chronos-AI] Completed routine execution for: '{name}'")

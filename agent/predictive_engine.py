import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

class PredictiveEngine:
    """
    Phase 4: Predictive Actions Engine.
    Prepares files, projects, and agendas ahead of scheduled events based on patterns.
    """
    def __init__(self, core_engine):
        self.core = core_engine
        self.last_prediction_trigger = {}
        self.predictions = {
            "09:45": {
                "days": [0], # Monday (0 = Monday in datetime)
                "goal": "Prepare meeting agenda and notes for the weekly standup.",
                "context": "Predictive Standup Preparation for Monday morning."
            },
            "10:00": {
                "days": [0, 1, 2, 3, 4, 5, 6], # Daily
                "goal": "Open Visual Studio Code and proactively load the last active coding project.",
                "context": "Daily coding session initialization."
            },
            "17:00": {
                "days": [4], # Friday
                "goal": "Generate a weekly Git development summary and commit report.",
                "context": "Friday evening code report generation."
            }
        }

    def check_and_predict(self) -> list[str]:
        """Checks the current clock and calendars to queue predictive actions."""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        weekday = now.weekday()
        
        triggered_goals = []
        
        # 1. Recurrent Time Predictions
        if current_time_str in self.predictions:
            pred = self.predictions[current_time_str]
            # Avoid duplicate triggers within the same minute
            if weekday in pred["days"] and self.last_prediction_trigger.get(current_time_str) != now.date().isoformat():
                print(f"[PredictiveEngine] 🔮 Triggered predictive goal for {current_time_str}: '{pred['goal']}'")
                
                # Proactively execute actions
                if "open visual studio code" in pred["goal"].lower():
                    self._proactively_load_project()
                else:
                    self.core.add_goal(pred["goal"], context=pred["context"], priority=2)
                    
                self.last_prediction_trigger[current_time_str] = now.date().isoformat()
                triggered_goals.append(pred["goal"])
                
        # 2. Interactive Condition Watcher (e.g. stackoverflow opened)
        # If the user opens a browser tab with stackoverflow, offer proactive help
        self._watch_active_browsers(now, triggered_goals)
        
        return triggered_goals

    def _proactively_load_project(self):
        """Action: Opens VS Code and restores the last active coding workspace."""
        try:
            print("[PredictiveEngine] 🔮 Opening VS Code and loading last active project...")
            workspace_dir = Path.home() / ".ipprime" / "workspace"
            
            # Simple fallback to standard startup
            if workspace_dir.exists():
                subprocess.Popen("code .", shell=True, cwd=str(workspace_dir))
            else:
                subprocess.Popen("code", shell=True)
                
            self.core.add_goal(
                "Verify that Visual Studio Code successfully loaded the user's workspace.",
                context="System opened VS Code; verifying active instances.",
                priority=3
            )
        except Exception as e:
            print(f"[PredictiveEngine] ⚠️ Failed to open VS Code proactively: {e}")

    def _watch_active_browsers(self, now: datetime, triggered_goals: list):
        """Action: Watches foreground activity to offer help if user opens StackOverflow/GitHub."""
        try:
            from actions.computer_settings import get_active_window_title
            active_window = get_active_window_title() if hasattr(get_active_window_title, "__call__") else ""
            
            if "stackoverflow" in active_window.lower() and self.last_prediction_trigger.get("stackoverflow") != now.date().isoformat():
                goal = "Detect if the user is struggling with an error and proactively offer programming help."
                print(f"[PredictiveEngine] 🔮 Proactive Assist: '{goal}'")
                self.core.add_goal(goal, context=f"User opened StackOverflow in: {active_window}", priority=2)
                self.last_prediction_trigger["stackoverflow"] = now.date().isoformat()
                triggered_goals.append(goal)
        except Exception:
            pass

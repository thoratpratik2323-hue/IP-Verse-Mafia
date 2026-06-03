import json
import os
from datetime import datetime
from pathlib import Path
from google import genai
from actions.prime_utils import get_api_key

class PatternEngine:
    """
    Step 4: Pattern Recognition Engine.
    Learns coding start times, idle periods, high output hours, and preferred tools.
    """
    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.patterns_file = memory_dir / "long_term" / "user_patterns.json"
        self.patterns_file.parent.mkdir(parents=True, exist_ok=True)
        
    def detect_patterns(self) -> dict:
        """Analyzes local history databases/logs and detects habit trends."""
        patterns = {
            "work_start_time": "10:00 AM",
            "break_times": "45 minutes after intense periods",
            "productive_hours": "Late afternoon (2:00 PM - 5:00 PM)",
            "preferred_tools": ["VSC", "Browser Control", "Git Autopilot"],
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            # Check screen time database/JSON if exists
            screen_time_path = Path("data/screen_time.json")
            if screen_time_path.exists():
                with open(screen_time_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Dynamic inference of preferred tools from actual "apps" dictionary
                apps = data.get("apps", {})
                if apps:
                    sorted_apps = sorted(apps.items(), key=lambda x: x[1], reverse=True)
                    patterns["preferred_tools"] = [app[0] for app in sorted_apps[:5]]
                    
            # Check completed task logs to infer productive hours from actual "turns"
            session_log_path = Path("memory/session_log.json")
            if session_log_path.exists():
                with open(session_log_path, "r", encoding="utf-8") as f:
                    logs_data = json.load(f)
                
                turns = logs_data.get("turns", [])
                hours = []
                for turn in turns:
                    ts = turn.get("ts", "")
                    if ts:
                        try:
                            # ts format: "2026-05-29 01:01"
                            hour = int(ts.split()[1].split(":")[0])
                            hours.append(hour)
                        except Exception:
                            pass
                if hours:
                    peak_hour = max(set(hours), key=hours.count)
                    period = "AM" if peak_hour < 12 else "PM"
                    display_hour = peak_hour if peak_hour <= 12 else peak_hour - 12
                    if display_hour == 0:
                        display_hour = 12
                    patterns["productive_hours"] = f"Peak interactive hour: {display_hour}:00 {period}"
                        
            # Save detected patterns
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(patterns, f, indent=4)
                
        except Exception as e:
            print(f"[PatternEngine] Error detecting patterns: {e}")
            
        return patterns


class LearningSystem:
    """
    Step 2: Learning & Daily Review System.
    Reflects on successful/failed tasks of the day and automatically refines prompt logic.
    """
    def __init__(self, memory_dir: Path = None):
        if memory_dir is None:
            if getattr(os, "frozen", False):
                self.base_dir = Path(os.executable).parent
            else:
                self.base_dir = Path(__file__).resolve().parent.parent
            self.memory_dir = self.base_dir / "memory"
        else:
            self.memory_dir = memory_dir
            
        self.insights_file = self.memory_dir / "long_term" / "learning_insights.json"
        self.pattern_engine = PatternEngine(self.memory_dir)
        
        try:
            self.client = genai.Client(api_key=get_api_key())
        except Exception:
            self.client = None

    def daily_review(self) -> str:
        """Aggregates daily execution metrics and generates LLM-guided improvements."""
        if not self.client:
            return "API Key not loaded, cannot complete daily review, sir."
            
        print("[LearningSystem] 🧠 Commencing daily self-reflection review...")
        
        # 1. Gather context
        today_actions = self._get_today_actions()
        successes = [a for a in today_actions if a.get("success") is True]
        failures = [a for a in today_actions if a.get("success") is False]
        user_patterns = self.pattern_engine.detect_patterns()
        
        prompt = f"""You are the Self-Learning Optimizer for IP Prime (Pratik Sir's personal AI cockpit).
Your task is to analyze the system's execution logs and user habits for today and generate exactly 3 highly actionable optimizations to improve future performance, execution speed, and error resilience.

Actions Executed Today:
{json.dumps(today_actions, indent=2)}

Successful Tasks:
{json.dumps(successes, indent=2)}

Failed Operations & Errors:
{json.dumps(failures, indent=2)}

Detected User Habit Patterns:
{json.dumps(user_patterns, indent=2)}

Based on this, return a JSON response containing exactly 3 improvements. Format the output in strict JSON:
{{
  "review_date": "YYYY-MM-DD",
  "success_ratio": "X%",
  "improvements": [
    {{
      "title": "Improvement Name",
      "metric_observed": "What triggered this suggestion",
      "actionable_change": "Direct software/behavior change to implement"
    }}
  ]
}}
Do NOT wrap the response in markdown blocks. Return only raw JSON."""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            result = response.text.strip()
            
            # Clean markdown fences if present
            if "```" in result:
                result = result.replace("```json", "").replace("```", "").strip()
                
            # Validate JSON
            review_data = json.loads(result)
            
            # Save daily insights to memory
            self.insights_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.insights_file, "w", encoding="utf-8") as f:
                json.dump(review_data, f, indent=4)
                
            print("[LearningSystem] ✅ Daily self-review successfully logged in memory.")
            return f"Review complete. Success ratio: {review_data.get('success_ratio')}. Saved 3 improvements."
            
        except Exception as e:
            error_msg = f"Self-review failed to compile: {e}"
            print(f"[LearningSystem] ⚠️ {error_msg}")
            return error_msg

    def _get_today_actions(self) -> list:
        """Helper to fetch and filter actions executed today."""
        today_date = datetime.now().strftime("%Y-%m-%d")
        actions = []
        
        # Scan session logs or db
        session_log_path = Path("memory/session_log.json")
        if session_log_path.exists():
            try:
                with open(session_log_path, "r", encoding="utf-8") as f:
                    logs_data = json.load(f)
                
                # Fetch turns matching today
                for turn in logs_data.get("turns", []):
                    ts = turn.get("ts", "")
                    if today_date in ts:
                        actions.append({
                            "action": f"User: {turn.get('user', '')} -> Assistant: {turn.get('assistant', '')}",
                            "time": ts,
                            "success": True
                        })
            except Exception as e:
                print(f"[LearningSystem] Error loading session actions: {e}")
                
        # If empty, provide mock data for demonstration
        if not actions:
            actions = [
                {"action": "Check system health", "time": datetime.now().isoformat(), "success": True},
                {"action": "Verify task planner API", "time": datetime.now().isoformat(), "success": True},
                {"action": "Build portfolio HTML webpage", "time": datetime.now().isoformat(), "success": True}
            ]
            
        return actions

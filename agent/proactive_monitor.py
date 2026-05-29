import time
import os
import threading
import json
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

class ProactiveMonitor:
    """
    Background monitor that perceives the environment (time, system, files, schedule)
    and proactively injects tasks into the Autonomous Core.
    """
    def __init__(self, core_engine):
        self.core = core_engine
        self.running = False
        self.last_check_time = time.time()
        self.work_start_time = time.time()
        self.last_briefing_date = None
        self.last_health_alert = 0
        self.last_email_check = 0
        self.last_code_check = 0
        
        # Phase 4 Advanced Agents
        from agent.predictive_engine import PredictiveEngine
        from agent.vision_loop import VisionLoop
        self.predictive_engine = PredictiveEngine(self.core)
        self.vision_loop = VisionLoop(self.core)
        
    def start(self):
        """Starts the proactive monitoring in a background thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True, name="ProactiveMonitor")
        self.thread.start()
        print("[ProactiveMonitor] 👁️ Proactive Intelligence loop started.")
        
    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2)
            
    def _monitor_loop(self):
        """The background loop executing all proactive agents periodically."""
        while self.running:
            try:
                self._check_for_proactive_actions()
            except Exception as e:
                print(f"[ProactiveMonitor] ⚠️ Error in monitor loop: {e}")
                
            # Check every 60 seconds to keep CPU/RAM usage minimal
            time.sleep(60)
            
    def _check_for_proactive_actions(self):
        """Runs the monitoring pipelines for all autonomous proactive agents."""
        current_time = time.time()
        
        # 1. Work Fatigue Monitor (4-hour continuous check)
        work_duration_hours = (current_time - self.work_start_time) / 3600
        if work_duration_hours > 4.0:
            print("[ProactiveMonitor] 👁️ Work Fatigue: Detected continuous work for >4 hours.")
            self.core.add_goal(
                "Suggest the user to take a break and play some relaxing lo-fi music.",
                context="System logs indicate the user has been working continuously for 4+ hours.",
                priority=1
            )
            self.work_start_time = current_time
            
        # 2. System Health Watcher Agent (CPU/RAM Check)
        self._watch_system_health(current_time)
        
        # 3. Calendar & Deadlines Agent (Upcoming task thresholds)
        self._check_upcoming_tasks(current_time)
        
        # 4. Email Watcher Agent (summarizing new incoming emails)
        self._watch_incoming_emails(current_time)
        
        # 5. Code Monitor Agent (self-healing for crash logs)
        self._watch_code_crashes(current_time)
        
        # 6. News/Daily Briefing Agent (Morning digest trigger)
        self._check_morning_briefing()
        
        # 7. Predictive Actions Agent (Phase 4)
        try:
            self.predictive_engine.check_and_predict()
        except Exception as e:
            print(f"[ProactiveMonitor] Predictive Agent error: {e}")
            
        # 8. Computer Vision Loop Agent (Phase 4)
        try:
            self.vision_loop.proactive_screen_watch()
        except Exception as e:
            print(f"[ProactiveMonitor] Vision Agent error: {e}")

    def _watch_system_health(self, current_time: float):
        """Agent 1: Monitors RAM/CPU and proactively clears memory if high."""
        if not psutil:
            return
        # Restrict check to once every 5 minutes to prevent high CPU utilization
        if current_time - self.last_health_alert < 300:
            return
            
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            if cpu > 90.0 or ram > 90.0:
                if not self.core.goal_exists("Recommend resource optimization"):
                    print(f"[ProactiveMonitor] 👁️ System Alert: CPU={cpu}%, RAM={ram}% detected.")
                    self.core.add_goal(
                        "Recommend resource optimization and suggest closing high-memory application instances.",
                        context=f"Proactive CPU alert at {cpu}% usage and memory load at {ram}%.",
                        priority=1
                    )
                    self.last_health_alert = current_time
        except Exception as e:
            print(f"[ProactiveMonitor] Health Watcher Error: {e}")

    def _check_upcoming_tasks(self, current_time: float):
        """Agent 2: Tracks task priority lists and signals approaching deadlines."""
        tasks_file = Path.home() / ".ipprime" / "tasks.json"
        if not tasks_file.exists():
            return
            
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            tasks = data.get("tasks", [])
            for task in tasks:
                if task.get("status") == "pending" and task.get("deadline"):
                    deadline_str = task.get("deadline")
                    # Check if deadline falls within next 1 hour
                    # Simple heuristic: alert if task is high priority and flagged as pending
                    if task.get("priority") == 1:
                        goal_name = f"Send an urgent desktop briefing reminder for the task: '{task.get('name')}'"
                        if not self.core.goal_exists(goal_name):
                            print(f"[ProactiveMonitor] 👁️ High-Priority Task approaching: '{task.get('name')}'")
                            self.core.add_goal(
                                goal_name,
                                context=f"Task deadline approaching. Task details: {task}",
                                priority=3
                            )
        except Exception as e:
            print(f"[ProactiveMonitor] Deadline Agent Error: {e}")

    def _watch_incoming_emails(self, current_time: float):
        """Agent 3: Checks user's mailbox files for unread messages and summarizes them."""
        # Check every 60 seconds
        if current_time - self.last_email_check < 60:
            return
        self.last_email_check = current_time
        
        email_dir = Path.home() / ".ipprime" / "inbox"
        email_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            emails = list(email_dir.glob("*.json"))
            for email_path in emails:
                with open(email_path, "r", encoding="utf-8") as f:
                    email_data = json.load(f)
                
                if email_data.get("status") == "unread":
                    sender = email_data.get("sender", "Unknown")
                    subject = email_data.get("subject", "No Subject")
                    goal_name = f"Summarize the new email '{subject}' from '{sender}' and present options to reply."
                    if not self.core.goal_exists(goal_name):
                        print(f"[ProactiveMonitor] 👁️ Unread Email: '{subject}' from '{sender}'")
                        
                        self.core.add_goal(
                            goal_name,
                            context=f"New email payload read from {email_path.name}: {email_data}",
                            priority=2
                        )
                    
                    # Mark email as read to prevent duplicate triggers
                    email_data["status"] = "read"
                    with open(email_path, "w", encoding="utf-8") as f:
                        json.dump(email_data, f, indent=4)
        except Exception as e:
            print(f"[ProactiveMonitor] Email Watcher Error: {e}")

    def _watch_code_crashes(self, current_time: float):
        """Agent 4: Scans running project workspace for python log crashes and auto-heals."""
        if current_time - self.last_code_check < 45:
            return
        self.last_code_check = current_time
        
        # Watch the designated code outputs directory
        code_dir = Path.home() / ".ipprime" / "workspace"
        if not code_dir.exists():
            return
            
        try:
            logs = list(code_dir.glob("*.log"))
            for log_path in logs:
                # Check logs updated in the last 60 seconds
                if os.path.getmtime(log_path) > (current_time - 60):
                    content = log_path.read_text(encoding="utf-8", errors="ignore")
                    if "Traceback" in content or "ZeroDivisionError" in content or "IndentationError" in content or "SyntaxError" in content:
                        goal_name = f"Analyze and self-heal the python file associated with the crash log: {log_path.name}"
                        if not self.core.goal_exists(goal_name):
                            print(f"[ProactiveMonitor] 👁️ Crash detected in logs: {log_path.name}")
                            self.core.add_goal(
                                goal_name,
                                context=f"Crash detected. Log content preview:\n{content[-500:]}",
                                priority=3
                            )
        except Exception as e:
            print(f"[ProactiveMonitor] Code Watcher Error: {e}")

    def _check_morning_briefing(self):
        """Agent 5: Prepares a daily forecast and pending review briefing every morning."""
        from datetime import datetime
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        
        # Trigger briefing once per day between 8:00 AM and 10:00 AM
        if 8 <= now.hour <= 10 and self.last_briefing_date != today_date:
            goal_name = "Generate a premium morning overview containing weather forecast, schedule breakdown, and active alerts."
            if not self.core.goal_exists(goal_name):
                print("[ProactiveMonitor] 👁️ Morning Briefing Triggered.")
                self.core.add_goal(
                    goal_name,
                    context=f"Daily initialization briefing for {today_date}.",
                    priority=2
                )
                self.last_briefing_date = today_date


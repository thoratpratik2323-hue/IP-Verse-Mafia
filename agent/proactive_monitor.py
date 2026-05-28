import time
import threading
import json
from pathlib import Path

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
        
    def start(self):
        """Starts the proactive monitoring in a background thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("[ProactiveMonitor] 👁️ Proactive Intelligence loop started.")
        
    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2)
            
    def _monitor_loop(self):
        """The actual background loop."""
        while self.running:
            try:
                self._check_for_proactive_actions()
            except Exception as e:
                print(f"[ProactiveMonitor] ⚠️ Error in monitor loop: {e}")
                
            # Sleep for 5 minutes before checking again
            # For demonstration, sleeping 10 seconds
            time.sleep(10)
            
    def _check_for_proactive_actions(self):
        """Analyzes environment and injects goals into core if necessary."""
        current_time = time.time()
        
        # Example 1: Work fatigue check (e.g. 4 hours without break)
        work_duration_hours = (current_time - self.work_start_time) / 3600
        if work_duration_hours > 4.0:
            print("[ProactiveMonitor] 👁️ Detected continuous work for >4 hours.")
            self.core.add_goal("Suggest the user to take a break and play some relaxing lo-fi music.", context="User has been working for 4 hours straight.", priority=1)
            # Reset timer after suggesting
            self.work_start_time = current_time
            
        # Example 2: Check upcoming tasks from ~/.ipprime/tasks.json
        self._check_upcoming_tasks()
        
        # Example 3: System Health Check (pseudo implementation)
        # If CPU is consistently > 95%, suggest closing apps
        # (Could use psutil here)

    def _check_upcoming_tasks(self):
        """Reads the user's tasks and proactively acts on them."""
        tasks_file = Path.home() / ".ipprime" / "tasks.json"
        if not tasks_file.exists():
            return
            
        try:
            with open(tasks_file, "r") as f:
                data = json.load(f)
                
            tasks = data.get("tasks", [])
            for task in tasks:
                if task.get("status") == "pending" and task.get("deadline"):
                    # Check if deadline is approaching (e.g., today)
                    # For demonstration, we just proactively suggest checking it
                    # Real implementation would parse ISO date and compare.
                    pass
        except Exception:
            pass

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
        
        # Proactive alerts cooldown timers to avoid spamming
        self.last_code_suggestion = 0
        self.last_cpu_alert = 0
        self.last_mem_alert = 0
        self.last_key_alert = 0
        
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
                
            # Sleep for 15 seconds before checking again (responsive context checking)
            time.sleep(15)
            
    def _check_for_proactive_actions(self):
        """Analyzes environment and injects goals into core if necessary."""
        current_time = time.time()
        
        # 1. Work fatigue check (e.g. 4 hours without break)
        work_duration_hours = (current_time - self.work_start_time) / 3600
        if work_duration_hours > 4.0:
            print("[ProactiveMonitor] 👁️ Detected continuous work for >4 hours.")
            self.core.add_goal("Suggest the user to take a break and play some relaxing lo-fi music.", context="User has been working for 4 hours straight.", priority=1)
            # Reset timer after suggesting
            self.work_start_time = current_time
            
        # 2. Check upcoming tasks from ~/.ipprime/tasks.json
        self._check_upcoming_tasks()
        
        # 3. System Resource Health Watchdog (CPU & Memory)
        self._check_system_resources(current_time)
        
        # 4. Active Window Tracker (Context Awareness)
        self._check_active_workspace(current_time)
        
        # 5. API Key and Configuration Sentinel
        self._check_configuration_sentinel(current_time)

    def _check_system_resources(self, current_time):
        """Monitors system performance metrics and acts on high resource usage."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            
            if cpu_percent > 90.0:
                if current_time - self.last_cpu_alert > 1800:  # 30 mins cooldown
                    self.last_cpu_alert = current_time
                    self.core.add_goal(
                        f"Alert the user about high CPU usage ({cpu_percent}%) and suggest closing background apps.",
                        context="System resources are critically low due to high CPU load.",
                        priority=1
                    )
            if mem_percent > 92.0:
                if current_time - self.last_mem_alert > 1800:
                    self.last_mem_alert = current_time
                    self.core.add_goal(
                        f"Alert the user about high Memory usage ({mem_percent}%) and suggest system cleanup.",
                        context="System virtual memory is almost exhausted.",
                        priority=1
                    )
        except Exception as e:
            print(f"[ProactiveMonitor] System health check failed: {e}")

    def _check_active_workspace(self, current_time):
        """Perceives the active desktop application window and suggests workflow boosters."""
        try:
            import pygetwindow as gw
            active_win = gw.getActiveWindow()
            if active_win and active_win.title:
                title = active_win.title.lower()
                
                # Dynamic context assessment for coding environments
                if "visual studio code" in title or "vscode" in title or ".py" in title or "pycharm" in title:
                    if current_time - self.last_code_suggestion > 3600:  # 1 hour cooldown
                        self.last_code_suggestion = current_time
                        self.core.add_goal(
                            "Proactively suggest running code review or checking for potential bugs on the active VS Code workspace.",
                            context="User is currently active on Visual Studio Code or editing a script.",
                            priority=3
                        )
        except Exception as e:
            # Silent fallback if pygetwindow fails or is unsupported
            pass

    def _check_configuration_sentinel(self, current_time):
        """Verifies integrity of local keys config to ensure AI services remain functional."""
        try:
            config_file = Path("config/api_keys.json")
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                
                gemini_key = cfg.get("GEMINI_API_KEY", "")
                if not gemini_key or "YOUR_" in gemini_key or len(gemini_key) < 10:
                    if current_time - self.last_key_alert > 7200:  # 2 hours cooldown
                        self.last_key_alert = current_time
                        self.core.add_goal(
                            "Remind the user to configure their GEMINI_API_KEY in the setup panel to restore full AI capabilities.",
                            context="API key configuration is missing or invalid.",
                            priority=1
                        )
        except Exception as e:
            print(f"[ProactiveMonitor] Config sentinel check failed: {e}")

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
                    # Real implementation would parse ISO date and compare.
                    pass
        except Exception:
            pass

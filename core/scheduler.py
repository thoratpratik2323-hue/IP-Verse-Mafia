import time
import threading
from pathlib import Path
from datetime import datetime

class SaturdayScheduler:
    def __init__(self):
        self.stop_event = threading.Event()
        self.tasks = {}
        self._thread = None
        
        # Register default actions
        self.register_task(
            name="git_backup_check",
            task_type="interval",
            value=3600,  # every hour
            action=self._action_git_backup,
            max_retries=1
        )
        self.register_task(
            name="daily_weather_brief",
            task_type="time",
            value="08:00",  # every morning at 08:00 AM
            action=self._action_weather_brief,
            max_retries=2
        )

    def register_task(self, name: str, task_type: str, value, action, max_retries: int = 0):
        """
        Register a background task.
        - task_type: 'interval' (value: seconds) or 'time' (value: 'HH:MM')
        """
        self.tasks[name] = {
            "type": task_type,
            "value": value,
            "last_run": 0 if task_type == "interval" else "",
            "action": action,
            "status": "pending",
            "retry_count": 0,
            "max_retries": max_retries
        }
        self.log(f"Registered background task '{name}' ({task_type}: {value}, max_retries: {max_retries})")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SaturdayScheduler")
        self._thread.start()
        self.log("Background scheduler started successfully.")

    def stop(self):
        self.stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.log("Background scheduler stopped.")

    def log(self, message: str):
        try:
            import ui
            ui_inst = ui.get_ui()
            if ui_inst:
                ui_inst._win._log_sig.emit(f"SYS [Scheduler]: {message}")
                return
            print(f"[Scheduler] {message}")
        except Exception:
            print(f"[Scheduler] {message}")

    def get_task_status(self) -> dict:
        """Returns the health and status of all registered tasks."""
        status_report = {}
        for name, t in self.tasks.items():
            status_report[name] = {
                "type": t["type"],
                "value": t["value"],
                "last_run": t["last_run"],
                "status": t["status"],
                "retry_count": t["retry_count"],
                "max_retries": t["max_retries"]
            }
        return status_report

    def _loop(self):
        while not self.stop_event.is_set():
            now = time.time()
            now_dt = datetime.now()
            today_date_str = now_dt.strftime("%Y-%m-%d")

            for name, t in list(self.tasks.items()):
                try:
                    if t["type"] == "interval":
                        if now - t["last_run"] >= t["value"]:
                            # Prevent running on startup if last_run is 0, initialize it instead
                            if t["last_run"] == 0:
                                t["last_run"] = now
                                continue
                            t["last_run"] = now
                            self.log(f"Triggering interval task: {name}")
                            threading.Thread(target=self._run_task, args=(name, t), daemon=True).start()
                            
                    elif t["type"] == "time":
                        try:
                            target_h, target_m = map(int, t["value"].split(":"))
                            # Trigger only if current hour and minute match target hour and minute, and last run wasn't today
                            if now_dt.hour == target_h and now_dt.minute == target_m and t["last_run"] != today_date_str:
                                t["last_run"] = today_date_str
                                self.log(f"Triggering scheduled time task: {name}")
                                threading.Thread(target=self._run_task, args=(name, t), daemon=True).start()
                        except ValueError:
                            self.log(f"Skipped task '{name}': invalid time format '{t['value']}'")
                except Exception as e:
                    self.log(f"Error checking task '{name}': {e}")
            
            # Check every 10 seconds to keep resource usage very low
            time.sleep(10)

    def _run_task(self, name: str, task: dict):
        """Wrapper to execute task action and handle errors/retries."""
        try:
            task["action"]()
            task["status"] = "success"
            task["retry_count"] = 0
            self.log(f"Task '{name}' completed successfully.")
        except Exception as e:
            task["status"] = "failed"
            task["retry_count"] += 1
            max_ret = task.get("max_retries", 0)
            self.log(f"Task '{name}' failed (attempt {task['retry_count']}/{max_ret + 1}): {e}")
            
            if task["retry_count"] <= max_ret:
                self.log(f"Scheduling retry for task '{name}' in 10s...")
                # Schedule retry after 10s using a daemon Timer
                def retry_timer_callback():
                    threading.Thread(target=self._run_task, args=(name, task), daemon=True).start()
                threading.Timer(10.0, retry_timer_callback).start()

    def _action_git_backup(self):
        """Automatically check and backup SaturdayProjects to Git if actions.github is ready."""
        try:
            self.log("Checking project repositories for auto-backup...")
            from actions.github import auto_backup_projects
            report = auto_backup_projects()
            self.log(f"Auto-backup complete: {report}")
        except ImportError as ie:
            self.log(f"Auto-backup skipped (actions.github module not available): {ie}")
        except Exception as e:
            self.log(f"Auto-backup failed: {e}")
            raise e

    def _action_weather_brief(self):
        """Fetch weather report and log to console."""
        try:
            self.log("Fetching scheduled weather report...")
            from actions.weather_report import weather_action
            report = weather_action(parameters={"city": "my location"})
            self.log(f"Weather report brief: {report}")
        except Exception as e:
            self.log(f"Weather briefing failed: {e}")
            raise e

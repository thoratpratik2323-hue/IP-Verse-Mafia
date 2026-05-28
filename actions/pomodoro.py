import time
import threading
from pathlib import Path
from typing import Optional, Any
from actions.screen_time import get_active_window_app

class PomodoroTimer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(PomodoroTimer, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.duration_seconds = 25 * 60
        self.remaining_seconds = self.duration_seconds
        self.is_running = False
        self.timer_thread = None
        self.player = None
        self.on_tick_callback = None
        self.on_complete_callback = None
        self.distraction_blacklist = [
            "youtube", "netflix", "facebook", "twitter", "instagram", "reddit",
            "discord", "steam", "riotclient", "epicgames", "valorant", "gta5"
        ]
        self._stop_signal = False

    def start(self, duration_minutes: int = 25, player: Optional[Any] = None, on_tick=None, on_complete=None):
        self.duration_seconds = duration_minutes * 60
        self.remaining_seconds = self.duration_seconds
        self.player = player
        self.on_tick_callback = on_tick
        self.on_complete_callback = on_complete
        
        if self.is_running:
            return "Pomodoro timer is already running, sir!"
            
        self.is_running = True
        self._stop_signal = False
        self.timer_thread = threading.Thread(target=self._run_timer, daemon=True, name="PomodoroTimerThread")
        self.timer_thread.start()
        
        if self.player and hasattr(self.player, "write_log"):
            self.player.write_log(f"🍅 POMODORO: Focus session started for {duration_minutes} minutes.")
            
        return f"Focus session of {duration_minutes} minutes started successfully, sir! Fodna hai aaj!"

    def stop(self):
        if not self.is_running:
            return "No active focus session running, sir."
            
        self._stop_signal = True
        self.is_running = False
        if self.player and hasattr(self.player, "write_log"):
            self.player.write_log("🍅 POMODORO: Focus session stopped by user.")
        return "Focus session stopped, sir."

    def _run_timer(self):
        distraction_check_counter = 0
        
        while self.remaining_seconds > 0 and not self._stop_signal:
            time.sleep(1)
            self.remaining_seconds -= 1
            
            if self.on_tick_callback:
                try:
                    self.on_tick_callback(self.remaining_seconds)
                except Exception:
                    pass
            
            # Check for distractions every 10 seconds
            distraction_check_counter += 1
            if distraction_check_counter >= 10:
                distraction_check_counter = 0
                self._check_distraction()
                
        self.is_running = False
        
        if not self._stop_signal:
            if self.on_complete_callback:
                try:
                    self.on_complete_callback()
                except Exception:
                    pass
            if self.player and hasattr(self.player, "write_log"):
                self.player.write_log("🍅 POMODORO: Focus session completed! Take a break, sir.")
            if self.player and hasattr(self.player, "_win") and hasattr(self.player._win, "ip_ray") and self.player._win.ip_ray:
                self.player._win.ip_ray.speak("Congratulations Pratik Sir, you completed your Pomodoro session! Work is done, take a break bhai!")

    def _check_distraction(self):
        try:
            current_app = get_active_window_app()
            if current_app in self.distraction_blacklist:
                msg = f"Alert: Pratik Sir, you are in Focus Mode! Avoid distractions from '{current_app}', sir."
                if self.player and hasattr(self.player, "write_log"):
                    self.player.write_log(f"⚠️ DISTRACTION DETECTED: '{current_app}' accessed during Pomodoro!")
                if self.player and hasattr(self.player, "_win") and hasattr(self.player._win, "ip_ray") and self.player._win.ip_ray:
                    self.player._win.ip_ray.speak(f"Bhai, focus mode chal raha hai! {current_app} band kijiye or coding pe dhyan dijiye!")
        except Exception:
            pass

def pomodoro(parameters: dict, player=None) -> str:
    """Dispatcher for Pomodoro actions."""
    action = parameters.get("action", "start").lower().strip()
    duration = int(parameters.get("duration", 25))
    timer = PomodoroTimer()
    
    if action == "start":
        return timer.start(duration, player)
    elif action == "stop":
        return timer.stop()
    elif action == "status":
        if timer.is_running:
            mins = timer.remaining_seconds // 60
            secs = timer.remaining_seconds % 60
            return f"Pomodoro active. {mins:02d}:{secs:02d} remaining, sir."
        return "Pomodoro is idle, sir."
    else:
        return "Unknown Pomodoro action, sir."

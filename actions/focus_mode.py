import logging
import os
import sys
import time
import threading

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
BLOCKED_SITES = ["youtube.com", "www.youtube.com", "twitter.com", "x.com", "facebook.com", "reddit.com", "instagram.com"]

_active_pomodoro_thread = None
_stop_pomodoro_event = threading.Event()

def block_sites() -> bool:
    try:
        if not os.path.exists(HOSTS_PATH):
            return False
        with open(HOSTS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "# SATURDAY FOCUS MODE" in content:
            return True
            
        block_text = "\n# SATURDAY FOCUS MODE BLOCKED WEBSITES\n"
        for site in BLOCKED_SITES:
            block_text += f"127.0.0.1 {site}\n"
        block_text += "# END SATURDAY FOCUS MODE BLOCKED WEBSITES\n"
        
        with open(HOSTS_PATH, "a", encoding="utf-8") as f:
            f.write(block_text)
        return True
    except PermissionError:
        return False
    except Exception:
        return False

def unblock_sites() -> bool:
    try:
        if not os.path.exists(HOSTS_PATH):
            return False
        with open(HOSTS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        skip = False
        for line in lines:
            if "# SATURDAY FOCUS MODE BLOCKED WEBSITES" in line:
                skip = True
                continue
            if "# END SATURDAY FOCUS MODE BLOCKED WEBSITES" in line:
                skip = False
                continue
            if not skip:
                new_lines.append(line)
                
        with open(HOSTS_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except PermissionError:
        return False
    except Exception:
        return False

def pomodoro_worker(duration_mins: int, player):
    speak_message(f"Sir, Focus Mode session of {duration_mins} minutes starts now. Let's get to work!")
    
    start_time = time.time()
    total_secs = duration_mins * 60
    
    halfway_spoken = False
    five_min_left_spoken = False
    
    while not _stop_pomodoro_event.is_set():
        elapsed = time.time() - start_time
        if elapsed >= total_secs:
            break
            
        # Halfway check
        if elapsed >= total_secs / 2 and not halfway_spoken:
            speak_message("Sir, you are halfway through your focus session. Stay focused.")
            halfway_spoken = True
            
        # 5 mins check
        if total_secs - elapsed <= 300 and not five_min_left_spoken and total_secs > 300:
            speak_message("Sir, only five minutes remaining in this session.")
            five_min_left_spoken = True
            
        time.sleep(2)
        
    if not _stop_pomodoro_event.is_set():
        unblock_sites()
        speak_message("Great job, sir! Your focus session is complete. Take a short break.")
        
def speak_message(msg: str):
    try:
        import main
        sat = main.get_saturday()
        if sat:
            sat.speak(msg)
        else:
            print(f"[FocusMode] {msg}")
    except Exception:
        print(f"[FocusMode] {msg}")

def focus_mode(parameters: dict, player=None) -> str:
    global _active_pomodoro_thread, _stop_pomodoro_event
    action = parameters.get("action", "start").lower().strip()
    duration = int(parameters.get("duration_mins", 25))
    
    if action == "start":
        if _active_pomodoro_thread and _active_pomodoro_thread.is_alive():
            return "Sir, a focus session is already active."
            
        blocked = block_sites()
        warn_msg = ""
        if not blocked:
            warn_msg = " (Note: Hosts file block failed. Please run Saturday as Administrator to block websites.)"
            
        _stop_pomodoro_event.clear()
        _active_pomodoro_thread = threading.Thread(target=pomodoro_worker, args=(duration, player), daemon=True)
        _active_pomodoro_thread.start()
        
        return f"Focus Mode activated for {duration} minutes, sir.{warn_msg}"
        
    elif action == "stop":
        if not (_active_pomodoro_thread and _active_pomodoro_thread.is_alive()):
            unblock_sites()
            return "No active focus session found, but cleared website blocks."
            
        _stop_pomodoro_event.set()
        try:
            _active_pomodoro_thread.join(timeout=1)
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
        unblock_sites()
        return "Focus Mode stopped, sir. Unblocked websites."
        
    elif action == "status":
        if _active_pomodoro_thread and _active_pomodoro_thread.is_alive():
            return "Focus Mode is currently active, sir."
        return "Focus Mode is inactive."
        
    else:
        return "Unknown focus mode action."

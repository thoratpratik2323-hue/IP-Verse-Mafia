import logging
import main
import datetime

def speak_reminder_action(message: str):
    sat = main.get_saturday()
    if sat:
        sat.speak(f"Sir, reminder: {message}")
    else:
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast("Saturday Reminder", message, duration=10)
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)

def scheduled_task(parameters: dict, player=None) -> str:
    time_str = parameters.get("time", "").strip()      # HH:MM format
    interval_val = parameters.get("interval")           # integer seconds
    message = parameters.get("message", "Reminder").strip()
    
    scheduler = main.get_scheduler()
    if not scheduler:
        return "System scheduler is not active, sir."
        
    task_name = f"spoken_reminder_{int(datetime.datetime.now().timestamp())}"
    action_cb = lambda: speak_reminder_action(message)
    
    if time_str:
        try:
            # Validate HH:MM format
            datetime.datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return "Invalid time format. Please use HH:MM format (24-hour clock), sir."
            
        scheduler.register_task(
            name=task_name,
            task_type="time",
            value=time_str,
            action=action_cb,
            max_retries=1
        )
        return f"Spoken reminder for '{message}' scheduled successfully at {time_str}, sir."
    elif interval_val:
        try:
            seconds = int(interval_val)
            scheduler.register_task(
                name=task_name,
                task_type="interval",
                value=seconds,
                action=action_cb,
                max_retries=1
            )
            return f"Spoken reminder for '{message}' scheduled to repeat every {seconds} seconds, sir."
        except ValueError:
            return "Please provide a valid integer for interval seconds, sir."
    else:
        return "I need a specific time (HH:MM) or interval to schedule the reminder, sir."

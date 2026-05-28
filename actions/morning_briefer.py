"""
morning_briefer.py — Aggregates weather, news, system stats, and pending task updates.

This is a standard action module for the IP Prime personal assistant suite.
"""

import sys
import re
import urllib.request
import subprocess
from datetime import datetime
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
BRIEFING_DIR = Path.home() / ".ipprime"
LOG_FILE = BRIEFING_DIR / "briefing_log.txt"
RUNNER_SCRIPT = BRIEFING_DIR / "morning_briefer_runner.py"

def generate_briefing(player=None) -> str:
    """Generates the full dynamic morning briefing in Hinglish."""
    # 1. Day & Time Greeting
    now = datetime.now()
    days_hindi = {
        "Monday": "Monday (Somvaar)",
        "Tuesday": "Tuesday (Mangalvaar)",
        "Wednesday": "Wednesday (Budhvaar)",
        "Thursday": "Thursday (Guruvaar)",
        "Friday": "Friday (Shukravaar)",
        "Saturday": "Saturday (Shanivaar)",
        "Sunday": "Sunday (Ravivaar)"
    }
    day_name = now.strftime("%A")
    day_str = days_hindi.get(day_name, day_name)
    date_str = now.strftime("%d %B %Y, %I:%M %p")
    
    greeting = f"Good morning Pratik Sir! Aaj {day_str} hai, aur time ho raha hai {date_str}, sir.\n\n"
    
    # 2. Live Weather from wttr.in
    weather_info = "Weather details pull nahi ho paye, sir."
    try:
        req = urllib.request.Request(
            "http://wttr.in/?format=3",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            weather_info = response.read().decode("utf-8").strip()
            # Clean wttr.in output slightly (remove extra spaces/symbols if any)
            weather_info = f"Mausam update: {weather_info}"
    except Exception as e:
        weather_info = f"Weather lookup failed: {e}"

    # 3. System Metrics via psutil
    sys_metrics = "System metrics read nahi ho paye, sir."
    try:
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        battery = "No battery info"
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                battery = f"{bat.percent}% {'(Charging)' if bat.power_plugged else '(Discharging)'}"
        sys_metrics = f"CPU Usage: {cpu}% | RAM Usage: {ram}% | Battery: {battery}"
    except Exception as e:
        sys_metrics = f"System metrics failed: {e}"

    # 4. Pending & Overdue Tasks from task_planner
    tasks_summary = "Planner summary pull karne mein issue hua, sir."
    overdue_warning = ""
    try:
        from actions.task_planner import _load_tasks, get_overdue_tasks
        all_tasks = _load_tasks()
        pending_count = sum(1 for t in all_tasks if t.get("status") == "pending")
        overdue_list = get_overdue_tasks()
        
        tasks_summary = f"Aapke planner mein total {pending_count} pending tasks hain, sir."
        try:
            from actions.study_planner import get_today_study_task
            study_task = get_today_study_task()
            if study_task:
                tasks_summary += f"\n[STUDY PLAN] {study_task}"
        except Exception:
            pass
        if overdue_list:
            overdue_warning = f"[WARNING] Aapke {len(overdue_list)} tasks overdue chal rahe hain! Inhe jaldi dekhiye, sir.\n"
    except Exception as e:
        tasks_summary = f"Task planning count failed: {e}"

    # 5. Top 3 news headlines from Google News technology feed
    news_summary = "News feed fetch nahi ho payi, sir."
    try:
        feed_url = "https://news.google.com/rss/search?q=technology&hl=en-IN&gl=IN"
        req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read().decode("utf-8")
            
            # Simple, robust XML regex-based title extraction
            titles = re.findall(r"<item>\s*<title>(.*?)</title>", xml_data, re.DOTALL)
            if titles:
                # Clean html entities if any (like &amp;, &quot;)
                cleaned_titles = []
                for t in titles[:3]:
                    t_clean = t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
                    # Google news titles usually have " - Source" at the end, clean it up for brevity
                    t_clean = re.sub(r"\s*-\s*[^-$]+$", "", t_clean)
                    cleaned_titles.append(t_clean)
                
                news_summary = "Tech News Headlines:\n" + "\n".join([f"  {idx}. {title}" for idx, title in enumerate(cleaned_titles, 1)])
            else:
                news_summary = "Google News feed parse nahi ho payi, sir."
    except Exception as e:
        news_summary = f"News fetch error: {e}"

    # 6. Motivational Closing in Hinglish
    quotes = [
        "Chaliye sir, aaj ka din shandaar banate hain. Aur yaad rakhiye, code runs on coffee and passion!",
        "Every single line of code is a step closer to greatness. Aaj fodna hai, sir!",
        "Chhota chhota progress hi bada success banata hai. Let's make today count, sir!",
        "Consistency is key. Aap smart ho aur aap kuch bhi kar sakte ho. All the best for today, sir!"
    ]
    # Simple hash of the current day of the year to pick a quote of the day
    quote_of_day = quotes[now.timetuple().tm_yday % len(quotes)]

    # Assemble Briefing
    briefing = (
        f"{greeting}"
        f"[WEATHER] {weather_info}\n"
        f"[SYSTEM] System Health: {sys_metrics}\n"
        f"[TASKS] Task Planner: {tasks_summary}\n"
        f"{overdue_warning}"
        f"\n[NEWS] {news_summary}\n\n"
        f"[MOTIVATION] Motivation: \"{quote_of_day}\"\n\n"
        "Have a great day, sir!"
    )
    return briefing

def _create_runner_script():
    """Generates the morning briefer standalone runner python file."""
    BRIEFING_DIR.mkdir(parents=True, exist_ok=True)
    
    script_content = f"""# Headless scheduled runner for IP Prime Morning Briefing
import sys
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.append(r"{BASE_DIR}")

from actions.morning_briefer import generate_briefing

briefing_dir = Path(r"{BRIEFING_DIR}")
log_file = briefing_dir / "briefing_log.txt"

# Generate briefing
brief = generate_briefing()

# Log to file
timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
with open(log_file, "a", encoding="utf-8") as f:
    f.write(f"\\n=== Morning Briefing Log [{{timestamp}}] ===\\n")
    f.write(brief)
    f.write("\\n==========================================\\n")

# Show notification (Plyer with Native PowerShell fallback)
notification_shown = False
try:
    from plyer import notification
    notification.notify(
        title="Good Morning Pratik Sir!",
        message="Aapka morning brief ready hai, sir! Log file update kar di gayi hai.",
        timeout=10
    )
    notification_shown = True
except Exception:
    pass

if not notification_shown:
    try:
        import subprocess
        ps_cmd = (
            '[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); '
            '$objNotifyIcon = New-Object System.Windows.Forms.NotifyIcon; '
            '$objNotifyIcon.Icon = [System.Drawing.SystemIcons]::Information; '
            '$objNotifyIcon.BalloonTipIcon = "Info"; '
            '$objNotifyIcon.BalloonTipTitle = "Good Morning Pratik Sir!"; '
            '$objNotifyIcon.BalloonTipText = "Aapka morning brief ready hai, sir! Log file check karein."; '
            '$objNotifyIcon.Visible = $True; '
            '$objNotifyIcon.ShowBalloonTip(10000)'
        )
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    except Exception:
        pass
"""
    try:
        with open(RUNNER_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script_content)
        return True
    except Exception as e:
        print(f"[MorningBriefer] Failed to write runner script: {e}")
        return False

def schedule_briefing(hour: int = 8, minute: int = 0) -> str:
    """Schedules a daily briefing using Windows Task Scheduler (schtasks)."""
    # 1. Ensure runner script is built
    if not _create_runner_script():
        return "Failed to create briefing runner script, sir."
        
    task_name = "IPPrime_MorningBriefing"
    py_exec = sys.executable
    
    # 2. Cancel existing schedule if any to prevent duplicates
    cancel_briefing_schedule()
    
    # 3. Create scheduled task (daily at specified time)
    time_str = f"{hour:02d}:{minute:02d}"
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'"{py_exec}" "{RUNNER_SCRIPT}"',
        "/sc", "daily",
        "/st", time_str,
        "/f"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return f"Morning briefing scheduled daily at {time_str} successfully, sir! Windows Task Scheduler mein '{task_name}' task set kar diya hai."
        else:
            return f"Failed to schedule briefing: {result.stderr.strip()}, sir."
    except Exception as e:
        return f"Scheduler error: {e}, sir."

def cancel_briefing_schedule() -> str:
    """Removes the scheduled daily briefing from Windows Task Scheduler."""
    task_name = "IPPrime_MorningBriefing"
    cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return f"Scheduled morning briefing task '{task_name}' successfully removed, sir."
        else:
            # If the task doesn't exist, it's already deleted/not scheduled
            if "not found" in result.stderr.lower() or "nahi mila" in result.stderr.lower() or result.returncode == 1:
                return "Koi scheduled morning briefing task active nahi tha, sir."
            return f"Failed to cancel schedule: {result.stderr.strip()}, sir."
    except Exception as e:
        return f"Scheduler error: {e}, sir."

def morning_briefer(parameters: dict, player=None) -> str:
    """Dispatcher for morning briefing actions."""
    action = parameters.get("action", "briefing").lower().strip()
    hour = int(parameters.get("hour", 8))
    minute = int(parameters.get("minute", 0))
    
    if action == "briefing":
        return generate_briefing(player)
    elif action == "schedule":
        return schedule_briefing(hour, minute)
    elif action == "cancel":
        return cancel_briefing_schedule()
    else:
        return f"Unknown action '{action}' for Morning Briefer, sir."

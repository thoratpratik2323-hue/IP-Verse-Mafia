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
    """Generates the full dynamic morning briefing in Hinglish with randomized styles, themes, and fun dev quotes."""
    import random
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
    
    # Randomly select a briefing style to keep it exciting!
    styles = ["jarvis", "buddy", "roast", "coach"]
    selected_style = random.choice(styles)
    
    # 1. Day & Time Greeting based on Style
    if selected_style == "jarvis":
        greetings = [
            f"A very pleasant morning, Pratik Sir. The date is {date_str} and the day is {day_str}. Systems are primed for your command, sir.\n\n",
            f"Good morning, Pratik Sir. Chronos is ticking at {date_str} on this fine {day_str}. Ready to analyze some code, sir?\n\n"
        ]
    elif selected_style == "buddy":
        greetings = [
            f"Arey good morning Pratik bro! Aaj toh mast {day_str} hai, aur time dekh lo—{date_str} ho chuka hai. Kya plans hain aaj ke?\n\n",
            f"Ram Ram Pratik bhai! 🌟 Aaj {day_str} hai, clock pe {date_str} baj rahe hain. Aaj kuch naya aur toofani karte hain!\n\n",
            f"Suno bhai Pratik, good morning! Aaj {day_str} ki shuruaat ho gayi hai, date hai {date_str}. Let's rock it today, bro!\n\n"
        ]
    elif selected_style == "roast":
        greetings = [
            f"Oh ho, good morning Pratik Sir! 🥱 Time ho raha hai {date_str} on a lazy {day_str}. CPU is ready to do the heavy lifting while you decide when to wake up properly, bro!\n\n",
            f"Arey, uth gaye Pratik bhai? Good morning! Clock pe {date_str} ho gaye hain iss pyare {day_str} ko. Chalo, check karte hain kitna productivity hone wala hai aaj!\n\n"
        ]
    else:  # coach
        greetings = [
            f"Rise and shine, Pratik Sir! 🔥 It's {day_str}, clocking in at {date_str}. No excuses today, only execution. Let's conquer the goals, sir!\n\n",
            f"Good morning, champ! Today is {day_str} ({date_str}). Another 24 hours to write clean code, solve problems, and build amazing things. Let's go, Pratik!\n\n"
        ]
    greeting = random.choice(greetings)

    # 2. Live Weather from wttr.in for Ukkalgaon
    weather_info = "Weather details pull nahi ho paye, sir."
    try:
        req = urllib.request.Request(
            "http://wttr.in/Ukkalgaon?format=3",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            weather_info = response.read().decode("utf-8").strip()
            # Style the weather introduction
            if selected_style == "jarvis":
                intro = f"Meteo-sensors for Ukkalgaon report: {weather_info}"
            elif selected_style == "buddy":
                intro = f"Ukkalgaon ka mausam ekdum shandar lag raha hai: {weather_info}"
            elif selected_style == "roast":
                intro = f"Ukkalgaon ka live weather check kiya. wttr.in bol raha hai: {weather_info}. Perfect temperature to skip running and write some code, bro!"
            else:  # coach
                intro = f"Environmental status at Ukkalgaon: {weather_info}. Great day to push your limits!"
            weather_info = intro
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
        
        # Style the metrics description
        if selected_style == "jarvis":
            sys_metrics = f"CPU Load at {cpu}% | RAM Utilization: {ram}% | Power State: {battery}."
        elif selected_style == "buddy":
            sys_metrics = f"Apna system damdar chal raha hai—CPU sirf {cpu}% pe chill kar raha hai, RAM: {ram}%, aur battery: {battery} hai, bro."
        elif selected_style == "roast":
            if cpu < 15:
                cpu_roast = f"CPU sits idle at {cpu}% because someone is still reading logs instead of compiling! 😂"
            else:
                cpu_roast = f"CPU is working harder than us at {cpu}%! 🔥"
            sys_metrics = f"{cpu_roast} RAM occupancy: {ram}%, Power level: {battery}."
        else: # coach
            sys_metrics = f"Hardware Vitals -> Engine Efficiency (CPU): {cpu}% | Memory Reserve (RAM): {ram}% | Power Reserve: {battery}."
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
        
        if selected_style == "jarvis":
            tasks_summary = f"There are currently {pending_count} pending tasks recorded in the kernel."
            if overdue_list:
                overdue_warning = f"\n[ALERT] Sir, {len(overdue_list)} items have exceeded their scheduled deadlines. Immediate review is advised."
        elif selected_style == "buddy":
            tasks_summary = f"Bhai, planner mein total {pending_count} pending tasks bache hue hain abhi."
            if overdue_list:
                overdue_warning = f"\n[DEKH LO BRO] Hamaare {len(overdue_list)} tasks overdue chal rahe hain! Inhe pehle niptaate hain na?"
        elif selected_style == "roast":
            tasks_summary = f"Planner states {pending_count} items are pending. No pressure, but they won't code themselves!"
            if overdue_list:
                overdue_warning = f"\n[OOF] {len(overdue_list)} tasks are overdue! Lagta hai backlog badhta ja raha hai, Pratik bro! 😜"
        else: # coach
            tasks_summary = f"Task planner status: {pending_count} active objectives remaining in queue."
            if overdue_list:
                overdue_warning = f"\n[WARNING] Critical Alert: {len(overdue_list)} objectives are overdue! Prioritize and eliminate these targets immediately, Pratik!"
                
        try:
            from actions.study_planner import get_today_study_task
            study_task = get_today_study_task()
            if study_task:
                tasks_summary += f"\n[STUDY PLAN] {study_task}"
        except Exception:
            pass
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
                cleaned_titles = []
                for t in titles[:3]:
                    t_clean = t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
                    t_clean = re.sub(r"\s*-\s*[^-$]+$", "", t_clean)
                    cleaned_titles.append(t_clean)
                
                if selected_style == "jarvis":
                    header = "Intel Core Feed (Tech Updates):\n"
                elif selected_style == "buddy":
                    header = "Internet par ye chal raha hai, tech world ke updates:\n"
                elif selected_style == "roast":
                    header = "Latest buzz in tech (so you can pretend to be working):\n"
                else: # coach
                    header = "Industry Reconnaissance (Tech News):\n"
                
                news_summary = header + "\n".join([f"  {idx}. {title}" for idx, title in enumerate(cleaned_titles, 1)])
            else:
                news_summary = "Google News feed parse nahi ho payi, sir."
    except Exception as e:
        news_summary = f"News fetch error: {e}"

    # 6. Dynamic Side-Quests and Quotes
    buddy_quotes = [
        "Chaliye sir, aaj ka din shandaar banate hain. Aur yaad rakhiye, code runs on coffee and passion!",
        "Every single line of code is a step closer to greatness. Aaj fodna hai, sir!",
        "Chhota chhota progress hi bada success banata hai. Let's make today count, sir!",
        "Consistency is key. Aap smart ho aur aap kuch bhi kar sakte ho. All the best for today, sir!",
        "Code likhna ek kala hai, aur aap uske shandaar kalakaar ho, bro! 🎨"
    ]
    jarvis_quotes = [
        "A quiet keyboard generates the loudest progress, sir. Let us optimize the day.",
        "Precision in coding ensures longevity in software architectures. Ready when you are, sir.",
        "Great ideas are only limited by computational bandwidth and human perseverance. Let's excel.",
        "System diagnostics are fully clean. The platform is ready for your architectural creations, sir."
    ]
    roast_quotes = [
        "Remember: It's not a bug, it's an undocumented feature! 🐛 Let's go write some bugs!",
        "Coding is 10% writing code and 90% understanding why those 10% didn't work. Good luck today!",
        "If at first you don't succeed, call it version 1.0! Let's get shipping, Pratik bro!",
        "Don't worry if it doesn't work right. If everything did, you'd be out of a job!"
    ]
    coach_quotes = [
        "Your only competition is the person you were yesterday. Push the limits today!",
        "Success is built daily, not overnight. Write that test, refactor that module, hit that goal!",
        "Greatness requires consistency. Stay focused, stay driven, and make today count!",
        "Do not wish for fewer problems; wish for more skills. Let's level up today!"
    ]
    
    # Pick a quote based on style
    if selected_style == "jarvis":
        quote_of_day = random.choice(jarvis_quotes)
    elif selected_style == "buddy":
        quote_of_day = random.choice(buddy_quotes)
    elif selected_style == "roast":
        quote_of_day = random.choice(roast_quotes)
    else:
        quote_of_day = random.choice(coach_quotes)
        
    # Generate a random fun developer "Side Quest" (Challenge of the Day)
    side_quests = [
        "Aaj code mein try/except block lagaye bina run mat karna! 😉",
        "Aaj kam se kam 15 minutes screen break zaroori hai! 🚶‍♂️",
        "Challenge: Rename at least 2 generic variable names in your active project to highly descriptive ones!",
        "Challenge: Drink at least 3 litres of water today while building amazing tech!",
        "Challenge: Commit your pending code with an extremely clear, descriptive commit message!",
        "Aaj ek function ko at least 15% optimize karne ki koshish karna, bro!",
        "Challenge: Teach me a new custom command today to level up my skills!"
    ]
    daily_quest = random.choice(side_quests)
    
    # Style styling format
    style_names = {
        "jarvis": "🤵 [Jarvis Protocol Active]",
        "buddy": "😎 [Desi Buddy Mode Active]",
        "roast": "🔥 [Sarcastic Dev Mode Active]",
        "coach": "🏋️ [Motivational Coach Active]"
    }
    style_label = style_names.get(selected_style, "🤖 [Morning Briefing]")
    
    # Assemble Briefing
    briefing = (
        f"{style_label}\n\n"
        f"{greeting}"
        f"[WEATHER] {weather_info}\n"
        f"[SYSTEM] Hardware Vitals: {sys_metrics}\n"
        f"[TASKS] Tasks Status: {tasks_summary}\n"
        f"{overdue_warning}\n"
        f"[NEWS] {news_summary}\n\n"
        f"[SIDE-QUEST] 🎯 Daily Challenge: \"{daily_quest}\"\n\n"
        f"[WORDS OF WISDOM] \"{quote_of_day}\"\n\n"
        "Have an absolute blast today, sir!"
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

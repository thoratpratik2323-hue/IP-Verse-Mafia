"""
predictive_workspace.py — Analyzes schedule and project directories to proactively stage tools, apps, and files.
"""

import os
import json
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
EVENTS_PATH = BASE_DIR / "config" / "calendar_events.json"
PROJECTS_ROOT = Path(r"C:\Users\thora\.gemini\antigravity\scratch\IP Prime\CODING PROJECTS")

def get_recent_projects() -> list[str]:
    """Finds the most recently modified folders in CODING PROJECTS."""
    projects_dir = PROJECTS_ROOT / "projects"
    if not projects_dir.exists():
        return []
    try:
        subdirs = [d for d in projects_dir.iterdir() if d.is_dir()]
        subdirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return [d.name for d in subdirs[:5]]
    except Exception:
        return []

def get_upcoming_events() -> list[dict]:
    """Reads calendar events and returns those occurring today or scheduled."""
    if not EVENTS_PATH.exists():
        return []
    try:
        with open(EVENTS_PATH, "r", encoding="utf-8") as f:
            events = json.load(f)
        event_list = []
        for eid, evt in events.items():
            event_list.append(evt)
        # Sort by date/time
        event_list.sort(key=lambda x: x.get("date", "") + " " + x.get("time", ""))
        return event_list
    except Exception:
        return []

def stage_predictive_workspace(player=None) -> str:
    """
    Main logic: Analyzes calendar and files, determines the most likely active
    context, and triggers window staging.
    """
    if player:
        player.write_log("SYS: Predictive Workspace Analyzer active...")

    events = get_upcoming_events()
    projects = get_recent_projects()

    now_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Determine target theme / context based on schedule & recent projects
    target_layout = "dev" # default
    reason = "No upcoming calendar events; defaulting to general development workspace."
    target_project = None

    if projects:
        target_project = projects[0]
        reason = f"Based on recent work in project folder '{target_project}'."

    # Search for today's calendar events to override layout
    for evt in events:
        if evt.get("date") == now_str:
            title = evt.get("title", "").lower()
            if "design" in title or "figma" in title or "ui" in title:
                target_layout = "design"
                reason = f"Upcoming event today: '{evt.get('title')}' (Design layout scheduled)."
                break
            elif "chill" in title or "relax" in title or "music" in title or "youtube" in title:
                target_layout = "chill"
                reason = f"Upcoming event today: '{evt.get('title')}' (Relaxation layout scheduled)."
                break
            elif "code" in title or "dev" in title or "refactor" in title or "build" in title:
                target_layout = "dev"
                reason = f"Upcoming event today: '{evt.get('title')}' (Development layout scheduled)."
                break

    report = [
        "### 🧠 Predictive Workspace Staging",
        f"**Active Workspace Context:** `{target_layout.upper()}`",
        f"**Reasoning**: {reason}",
    ]

    if target_project:
        report.append(f"**Proactively Staging Project:** `{target_project}`")

    # 2. Trigger smart workspace execution in background
    from actions.computer_settings import smart_workspace
    
    # Run the window layout staging
    msg = smart_workspace(layout=target_layout, player=player)
    report.append(f"**Action Executed**: {msg}")

    # If there's a specific folder, open it in explorer or VS Code
    if target_project and target_layout == "dev":
        proj_path = PROJECTS_ROOT / "projects" / target_project
        if proj_path.exists():
            def open_project():
                try:
                    time.sleep(1.0)
                    # Open file explorer in project
                    subprocess.Popen(["explorer", str(proj_path)])
                    # Open VS Code in project (if 'code' command is available)
                    subprocess.Popen(["code", str(proj_path)], shell=True)
                except Exception:
                    pass
            threading.Thread(target=open_project, daemon=True).start()
            report.append(f"- Proactively opening folder: `{proj_path}` in File Explorer & VS Code.")

    return "\n".join(report)

def predictive_workspace(parameters: dict, player=None) -> str:
    """Entry point wrapper for the predictive workspace feature."""
    return stage_predictive_workspace(player=player)

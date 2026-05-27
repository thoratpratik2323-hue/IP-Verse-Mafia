import os
import json
import uuid
from datetime import datetime
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"
TASKS_DIR = Path.home() / ".ipprime"
TASKS_FILE = TASKS_DIR / "tasks.json"

def _ensure_tasks_file():
    """Creates the tasks directory and JSON file if they do not exist."""
    try:
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        if not TASKS_FILE.exists():
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump({"tasks": []}, f, indent=4)
    except Exception as e:
        print(f"[TaskPlanner] Error ensuring tasks directory: {e}")

def _load_tasks() -> list:
    """Loads all tasks from tasks.json."""
    _ensure_tasks_file()
    try:
        if TASKS_FILE.exists():
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("tasks", [])
    except Exception as e:
        print(f"[TaskPlanner] Error loading tasks: {e}")
    return []

def _save_tasks(tasks: list) -> bool:
    """Saves tasks to tasks.json."""
    _ensure_tasks_file()
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump({"tasks": tasks}, f, indent=4)
        return True
    except Exception as e:
        print(f"[TaskPlanner] Error saving tasks: {e}")
    return False

def add_task(title: str, description: str = "", deadline: str = "", priority: str = "medium") -> str:
    """Adds a new task to the task list."""
    if not title:
        return "Task title cannot be empty, sir."
        
    tasks = _load_tasks()
    task_id = str(uuid.uuid4())[:8]
    
    new_task = {
        "id": task_id,
        "title": title,
        "description": description,
        "deadline": deadline,  # YYYY-MM-DD
        "priority": priority.lower(),
        "status": "pending",
        "created": datetime.now().isoformat(),
        "subtasks": []
    }
    
    tasks.append(new_task)
    if _save_tasks(tasks):
        return f"Task '{title}' has been successfully added to your list, sir."
    return "Failed to save the task, sir."

def list_tasks(filter_status: str = "all") -> str:
    """Lists tasks based on the status filter (all, pending, done, overdue)."""
    tasks = _load_tasks()
    if not tasks:
        return "Aapka task list bilkul empty hai, sir."
        
    now_str = datetime.now().strftime("%Y-%m-%d")
    filtered = []
    
    for t in tasks:
        status = t.get("status", "pending")
        deadline = t.get("deadline", "")
        
        # Check overdue status dynamically
        is_overdue = False
        if status == "pending" and deadline:
            try:
                if deadline < now_str:
                    is_overdue = True
            except Exception:
                pass
                
        if filter_status == "all":
            filtered.append((t, is_overdue))
        elif filter_status == "pending" and status == "pending" and not is_overdue:
            filtered.append((t, False))
        elif filter_status == "done" and status == "done":
            filtered.append((t, False))
        elif filter_status == "overdue" and is_overdue:
            filtered.append((t, True))

    if not filtered:
        return f"No tasks found matching the filter '{filter_status}', sir."
        
    output = [f"### [PLANNER] Pratik Sir's Task List ({filter_status.capitalize()})\n"]
    for idx, (t, is_overdue) in enumerate(filtered, 1):
        t_id = t.get("id")
        title = t.get("title")
        desc = t.get("description", "")
        prio = t.get("priority", "medium").upper()
        deadline = t.get("deadline", "No Deadline")
        status = t.get("status", "pending")
        
        status_symbol = "[PENDING]" if status == "pending" else "[DONE]"
        if is_overdue:
            status_symbol = "[OVERDUE]"
            
        desc_line = f"  - *Desc*: {desc}\n" if desc else ""
        output.append(
            f"**{idx}. [{t_id}] {title}**\n"
            f"  - *Status*: {status_symbol} | *Priority*: {prio} | *Deadline*: {deadline}\n"
            f"{desc_line}"
        )
        
    return "\n".join(output) + "\n\nAll clear for now, sir."

def complete_task(task_id_or_title: str) -> str:
    """Marks a task as completed."""
    tasks = _load_tasks()
    found = False
    task_title = ""
    
    for t in tasks:
        if t.get("id") == task_id_or_title or t.get("title").lower() == task_id_or_title.lower():
            t["status"] = "done"
            task_title = t.get("title")
            found = True
            break
            
    if found:
        if _save_tasks(tasks):
            return f"Task '{task_title}' marked as completed! Sabash sir!"
        return "Marked as done but failed to save, sir."
    return f"Task '{task_id_or_title}' nahi mila, sir."

def delete_task(task_id_or_title: str) -> str:
    """Deletes a task from the list."""
    tasks = _load_tasks()
    initial_len = len(tasks)
    
    # Filter out the task
    tasks = [t for t in tasks if t.get("id") != task_id_or_title and t.get("title").lower() != task_id_or_title.lower()]
    
    if len(tasks) < initial_len:
        if _save_tasks(tasks):
            return f"Task successfully deleted from your planner, sir."
        return "Deleted from list but failed to save, sir."
    return f"Task '{task_id_or_title}' nahi mila, sir."

def get_overdue_tasks() -> list:
    """Returns a raw list of overdue task dicts."""
    tasks = _load_tasks()
    now_str = datetime.now().strftime("%Y-%m-%d")
    overdue = []
    
    for t in tasks:
        if t.get("status") == "pending" and t.get("deadline"):
            try:
                if t.get("deadline") < now_str:
                    overdue.append(t)
            except Exception:
                pass
    return overdue

def voice_plan_tasks(goal: str) -> str:
    """Breaks down a complex goal using Gemini and adds all subtasks to the planner."""
    if not goal:
        return "Goal specification empty hai, sir."
        
    gemini_key = None
    try:
        if API_KEYS_PATH.exists():
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                gemini_key = cfg.get("gemini_api_key")
    except Exception as e:
        print(f"[TaskPlanner] Error loading API key: {e}")
        
    if not gemini_key:
        return "Gemini API key is not configured, cannot break down this goal, sir."
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        prompt = (
            f"You are a master planner AI. Take the following high-level goal of Pratik Sir: '{goal}'. "
            "Break it down into an actionable step-by-step checklist of subtasks (exactly 3 to 6 steps). "
            "Return the response in strict JSON format matching this schema:\n"
            "{\n"
            "  \"plan_title\": \"Short clear title for the overall goal\",\n"
            "  \"tasks\": [\n"
            "    {\n"
            "      \"title\": \"Step title\",\n"
            "      \"description\": \"1-sentence instruction for this step\",\n"
            "      \"priority\": \"high/medium/low\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Return only the raw JSON. No markdown backticks, no comments."
        )
        
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        # Clean response text
        res_text = response.text.strip()
        if "```" in res_text:
            # Strip markdown fences if any
            res_text = res_text.replace("```json", "").replace("```", "").strip()
            
        plan_data = json.loads(res_text)
        plan_title = plan_data.get("plan_title", "Custom AI Plan")
        created_tasks = plan_data.get("tasks", [])
        
        if not created_tasks:
            return "Gemini plan empty return kiya, sir."
            
        tasks = _load_tasks()
        added_titles = []
        
        # Add all plan tasks to local tasks list
        for t_spec in created_tasks:
            task_id = str(uuid.uuid4())[:8]
            new_task = {
                "id": task_id,
                "title": f"[{plan_title}] {t_spec.get('title')}",
                "description": t_spec.get("description", ""),
                "deadline": datetime.now().strftime("%Y-%m-%d"), # Default deadline is today
                "priority": t_spec.get("priority", "medium").lower(),
                "status": "pending",
                "created": datetime.now().isoformat(),
                "subtasks": []
            }
            tasks.append(new_task)
            added_titles.append(new_task["title"])
            
        if _save_tasks(tasks):
            subtasks_summary = "\n".join([f"- {title}" for title in added_titles])
            return (
                f"### [AI] AI Task Planner: '{plan_title}'\n"
                f"Pratik Sir, I broke down your goal into {len(added_titles)} subtasks and added them to your planner:\n\n"
                f"{subtasks_summary}\n\n"
                "Everything has been successfully queued up, sir!"
            )
        else:
            return "Failed to save the generated subtasks to tasks database, sir."
            
    except Exception as e:
        return f"Error breaking down your goal with Gemini: {e}, sir."

def task_planner(parameters: dict, player=None) -> str:
    """Main dispatcher for the task_planner action."""
    action = parameters.get("action", "list").lower().strip()
    title = parameters.get("title", "")
    description = parameters.get("description", "")
    deadline = parameters.get("deadline", "")
    priority = parameters.get("priority", "medium")
    goal = parameters.get("goal", "")
    task_id = parameters.get("task_id", title) # fallback to title if ID not provided
    
    if action == "add":
        return add_task(title, description, deadline, priority)
    elif action == "list":
        filter_status = parameters.get("filter_status", "all")
        return list_tasks(filter_status)
    elif action == "complete":
        return complete_task(task_id)
    elif action == "delete":
        return delete_task(task_id)
    elif action == "plan":
        return voice_plan_tasks(goal)
    elif action == "overdue":
        overdue = get_overdue_tasks()
        if not overdue:
            return "Koi bhi task overdue nahi hai! Bahut badiya, sir."
        output = ["### [ALERT] Overdue Tasks List:\n"]
        for idx, t in enumerate(overdue, 1):
            output.append(f"{idx}. **[{t.get('id')}] {t.get('title')}** (Deadline: {t.get('deadline')})")
        return "\n".join(output) + "\n\nInhe jaldi khatam kijiye, sir!"
    else:
        return f"Unknown action '{action}' for Task Planner, sir."

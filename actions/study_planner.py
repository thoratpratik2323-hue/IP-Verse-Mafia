import json
import time
from pathlib import Path
from typing import Optional, Any
from google import genai

PLAN_FILE = Path("c:/Users/thora/Documents/SecondBrain/study_plan.json")

def generate_study_plan(topics: str, exam_date: str, player: Optional[Any] = None) -> str:
    """Uses Gemini to split list of topics into a day-by-day plan up to the target exam date."""
    if not topics or not exam_date:
        return "Topics and exam date are required, sir."
        
    try:
        from main import _get_api_key
        client = genai.Client(api_key=_get_api_key())
        
        prompt = (
            f"You are a study planning assistant. Create a day-by-day study schedule. "
            f"Start from today ({time.strftime('%Y-%m-%d')}) and end on the exam date ({exam_date}).\n\n"
            f"Topics to cover:\n{topics}\n\n"
            f"Format the output strictly as a JSON object with this format:\n"
            f"{{\n"
            f"  \"exam_date\": \"{exam_date}\",\n"
            f"  \"schedule\": [\n"
            f"    {{\"date\": \"YYYY-MM-DD\", \"topic\": \"Topic name\", \"task\": \"Specific chapter/task to read\", \"completed\": false}}\n"
            f"  ]\n"
            f"}}\n"
            f"Return ONLY valid raw JSON content. Do not enclose it in markdown blocks."
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        # Clean response text in case it is enclosed in markdown
        cleaned_json = response.text.strip()
        if cleaned_json.startswith("```json"):
            cleaned_json = cleaned_json[7:]
        if cleaned_json.endswith("```"):
            cleaned_json = cleaned_json[:-3]
        cleaned_json = cleaned_json.strip()
        
        # Verify JSON validity
        plan_data = json.loads(cleaned_json)
        
        # Save to SecondBrain
        PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
        PLAN_FILE.write_text(json.dumps(plan_data, indent=4), encoding="utf-8")
        
        if player and hasattr(player, "write_log"):
            player.write_log("📅 STUDYPLAN: New study plan generated and saved successfully!")
            
        return "Study plan generated successfully, bhai!"
    except Exception as e:
        print(f"[StudyPlanner] Error generating plan: {e}")
        return f"Study plan generation failed: {e}"

def load_study_plan() -> Optional[dict]:
    try:
        if PLAN_FILE.exists():
            return json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None

def save_study_plan(data: dict) -> bool:
    try:
        PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
        PLAN_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        return True
    except Exception:
        return False

def get_today_study_task() -> str:
    """Returns today's study task description for the daily briefing."""
    plan = load_study_plan()
    if not plan:
        return ""
        
    today = time.strftime("%Y-%m-%d")
    for day in plan.get("schedule", []):
        if day.get("date") == today:
            status = "completed" if day.get("completed") else "pending"
            return f"Bhai, aaj study plan me aapka topic hai: '{day.get('topic')}' -> Task: {day.get('task')} ({status})."
            
    return ""

def study_planner(parameters: dict, player=None) -> str:
    """Dispatcher for Study Planner action."""
    action = parameters.get("action", "load").lower().strip()
    topics = parameters.get("topics", "")
    exam_date = parameters.get("exam_date", "")
    
    if action == "generate":
        return generate_study_plan(topics, exam_date, player)
    else:
        plan = load_study_plan()
        if plan:
            return f"Study plan loaded. Target exam date: {plan.get('exam_date')}."
        return "No study plan found, sir."

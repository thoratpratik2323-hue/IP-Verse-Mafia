import logging
import json
from pathlib import Path
from google import genai
from memory.encryption import encrypt_string, decrypt_string

BASE_DIR = Path(__file__).resolve().parent.parent
STUDY_PATH = BASE_DIR / "data" / "study_progress.json"

def _load_study() -> dict:
    if not STUDY_PATH.exists():
        return {}
    try:
        raw = STUDY_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        if not (raw.startswith("{") or raw.startswith("[")):
            raw = decrypt_string(raw)
        return json.loads(raw)
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return {}

def _save_study(data: dict):
    STUDY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw_json = json.dumps(data, indent=2, ensure_ascii=False)
        STUDY_PATH.write_text(encrypt_string(raw_json), encoding="utf-8")
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)

def study_mode(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status").lower().strip()
    topic = parameters.get("topic", "").strip()
    ans = parameters.get("user_answer", "").strip()
    
    progress = _load_study()
    
    try:
        from main import _get_api_key
        client = genai.Client(api_key=_get_api_key())
    except Exception:
        return "I need a Gemini API key to generate study materials, sir."
        
    if action == "start":
        if not topic:
            return "Please tell me what topic you want to learn, sir."
            
        prompt = (
            f"Generate a single beginner-friendly multiple-choice question to test basic knowledge of '{topic}'. "
            "Return only the question and 4 numbered options. Do not output the answer yet."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        q_text = response.text.strip()
        
        progress[topic] = {
            "current_question": q_text,
            "score": 0,
            "total_questions": 1,
            "active": True
        }
        progress["active_topic"] = topic
        _save_study(progress)
        
        return (
            f"### 📚 [STUDY MODE] Learning: {topic}\n"
            f"I have initialized a study session for you. Here is your first quiz question:\n\n"
            f"{q_text}"
        )
        
    elif action == "answer":
        active_topic = progress.get("active_topic")
        if not active_topic or not progress.get(active_topic, {}).get("active"):
            return "No active study session is running, sir. Say 'start study mode on X' to begin."
            
        sess = progress[active_topic]
        current_q = sess["current_question"]
        
        prompt = (
            f"You asked the question:\n{current_q}\n\n"
            f"The user answered:\n{ans}\n\n"
            "Evaluate if this answer is correct. Explain why briefly in warm Hinglish. "
            "Then, generate the NEXT beginner-friendly multiple-choice question on this topic. "
            "If they answered correctly, start by saying 'CORRECT'. If incorrect, say 'INCORRECT'."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        result_text = response.text.strip()
        is_correct = result_text.startswith("CORRECT")
        
        if is_correct:
            sess["score"] += 1
        sess["total_questions"] += 1
        
        # Extract next question if generated
        parts = result_text.split("Next question:")
        if len(parts) > 1:
            sess["current_question"] = parts[-1].strip()
        else:
            parts_alt = result_text.split("NEXT question:")
            if len(parts_alt) > 1:
                sess["current_question"] = parts_alt[-1].strip()
            else:
                sess["current_question"] = result_text
                
        _save_study(progress)
        
        eval_label = "✅ CORRECT!" if is_correct else "❌ INCORRECT"
        return (
            f"### 📝 [STUDY MODE] Topic: {active_topic}\n"
            f"Evaluation: **{eval_label}**\n\n"
            f"{result_text}\n\n"
            f"Current Score: {sess['score']}/{sess['total_questions'] - 1}"
        )
        
    elif action == "status":
        active_topic = progress.get("active_topic")
        if not active_topic:
            return "No active study sessions found, sir."
        sess = progress[active_topic]
        status = "Active" if sess.get("active") else "Completed"
        return (
            f"### 📊 [STUDY PROGRESS] Topic: {active_topic} ({status})\n"
            f"- Score: {sess['score']}/{sess['total_questions'] - 1}\n"
            f"- Current Question: {sess['current_question']}"
        )
        
    else:
        return "Unknown study mode action, sir."

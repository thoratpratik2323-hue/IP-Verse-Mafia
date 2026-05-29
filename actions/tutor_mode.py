"""
tutor_mode.py — Spaced repetition Leitner tutoring engine for IP Prime.

Allows registering learning topics, quizzing progress, and tracking review intervals.
Saves details inside data/tutor_data.json.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.tutor_mode")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TUTOR_FILE = DATA_DIR / "tutor_data.json"

BOX_INTERVALS = {
    1: 1,   # Review daily
    2: 3,   # Review every 3 days
    3: 7,   # Review every 7 days
    4: 14,  # Review every 14 days
    5: 30   # Review every 30 days
}

def _ensure_tutor_store():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not TUTOR_FILE.exists():
            with open(TUTOR_FILE, "w", encoding="utf-8") as f:
                json.dump({"topics": [], "quizzes_taken": 0}, f, indent=4)
    except Exception as e:
        logger.error("Failed to ensure tutor data directory: %s", e)

def _load_tutor_data() -> dict[str, Any]:
    _ensure_tutor_store()
    try:
        if TUTOR_FILE.exists():
            with open(TUTOR_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error("Error loading tutor data: %s", e)
    return {"topics": [], "quizzes_taken": 0}

def _save_tutor_data(data: dict[str, Any]) -> bool:
    _ensure_tutor_store()
    try:
        with open(TUTOR_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving tutor data: %s", e)
    return False

def add_topic(name: str, quiz_question: str = "", quiz_answer: str = "") -> str:
    """Adds a new learning topic with a default review card."""
    if not name:
        return "Topic name cannot be empty, sir."
        
    data = _load_tutor_data()
    topics = data.get("topics", [])
    name_clean = name.strip()

    # Check for duplicates
    for t in topics:
        if t.get("name", "").lower() == name_clean.lower():
            return f"Topic '{name_clean}' already exists in your tutoring library, sir."

    new_topic = {
        "name": name_clean,
        "box": 1,
        "next_review": datetime.now().strftime("%Y-%m-%d"),
        "q": quiz_question or f"What is the core definition of {name_clean}?",
        "a": quiz_answer or "A concept to review and understand.",
        "created_at": datetime.now().strftime("%Y-%m-%d")
    }
    
    topics.append(new_topic)
    data["topics"] = topics
    if _save_tutor_data(data):
        return f"Successfully added topic '{name_clean}' to spaced repetition study deck box 1, sir!"
    return "Failed to save the new topic, sir."

def start_learning_session(topic_name: str) -> str:
    """Activates tutoring text for a specific topic using dynamically generated AI guides."""
    from actions.prime_utils import UnifiedModelClient
    
    ai_guide = ""
    try:
        client = UnifiedModelClient(category="coding")
        prompt = f"""You are the Premium spaced repetition Leitner tutoring engine for IP Prime.
Produce a high-value, beautifully structured learning guide for Pratik Sir on the topic: '{topic_name}'.
Your guide should:
1. Explain the topic's core concept clearly.
2. Provide a 3-point critical breakdown of must-know elements.
3. Keep the tone premium, direct, and use a friendly Hinglish style where appropriate.

Use standard clean markdown. Keep it concise (150-250 words total)."""
        response = client.models.generate_content(model=None, contents=prompt)
        ai_guide = response.text.strip()
    except Exception as e:
        logger.warning("Failed to generate dynamic AI tutor guide: %s. Using fallback stub.", e)

    if not ai_guide:
        ai_guide = (
            f"Pratik Sir, standard analysis suggests {topic_name} is highly important. "
            "Let's review the fundamental elements today. Make sure to commit details to memory."
        )

    return (
        f"### [TUTOR] Learning Session: {topic_name}\n"
        f"{ai_guide}\n\n"
        "*(Type 'quiz me' or ask me to check your knowledge whenever you feel ready, sir)*"
    )

def quiz_me(topic_name: Optional[str] = None) -> str:
    """Retrieves an active quiz card for a pending topic."""
    data = _load_tutor_data()
    topics = data.get("topics", [])
    if not topics:
        return "Aapka study deck empty hai, sir! Please add a topic first."

    today_str = datetime.now().strftime("%Y-%m-%d")
    selected_topic = None

    if topic_name:
        # Match user preference
        for t in topics:
            if t.get("name", "").lower() == topic_name.lower().strip():
                selected_topic = t
                break
    else:
        # Pick the most overdue review topic
        for t in topics:
            if t.get("next_review", "") <= today_str:
                selected_topic = t
                break
        # Fallback to any random card if none due today
        if not selected_topic and topics:
            selected_topic = topics[0]

    if not selected_topic:
        return "Excellent sir! All learning topics are fully reviewed for today."

    return (
        f"### [QUIZ DECK] Topic: {selected_topic['name']}\n"
        f"**Question**: {selected_topic.get('q')}\n\n"
        "Try to answer out loud or in text, then tell me if you got it right or wrong!"
    )

def process_quiz_outcome(topic_name: str, correct: bool) -> str:
    """Updates spaced repetition box index depending on correct/incorrect results."""
    data = _load_tutor_data()
    topics = data.get("topics", [])
    found = False
    
    for t in topics:
        if t.get("name", "").lower() == topic_name.lower().strip():
            found = True
            current_box = t.get("box", 1)
            
            if correct:
                # Move to next Leitner Box
                next_box = min(current_box + 1, 5)
            else:
                # Fallback to Box 1
                next_box = 1
                
            t["box"] = next_box
            days_to_add = BOX_INTERVALS[next_box]
            next_date = (datetime.now() + timedelta(days=days_to_add)).strftime("%Y-%m-%d")
            t["next_review"] = next_date
            break
            
    if not found:
        return f"Topic '{topic_name}' was not found in your study deck, sir."

    data["topics"] = topics
    data["quizzes_taken"] = data.get("quizzes_taken", 0) + 1
    
    if _save_tutor_data(data):
        box_msg = f"Promoted to Box {next_box}" if correct else "Demoted back to Box 1"
        return f"Progress saved, sir! {box_msg}. Next review scheduled for: {next_date}."
    return "Failed to save the quiz progress result, sir."

def get_progress_report() -> str:
    """Compiles learning efficiency index report."""
    data = _load_tutor_data()
    topics = data.get("topics", [])
    if not topics:
        return "No active topics in spaced repetition learning stack, sir."

    today_str = datetime.now().strftime("%Y-%m-%d")
    due_count = sum(1 for t in topics if t.get("next_review", "") <= today_str)
    
    output = [
        "### [LEARNING CORE] Tutor Progress Report:\n",
        f"• Total active topics: {len(topics)}",
        f"• Total quizzes taken: {data.get('quizzes_taken', 0)}",
        f"• Topics due for review today: {due_count}\n",
        "**Library Breakdown**:"
    ]
    
    for t in topics:
        output.append(
            f"- **{t['name']}**: Box {t.get('box')} | Next Review: {t.get('next_review')}"
        )
        
    return "\n".join(output) + "\n\nHappy learning, sir!"

def check_review_reminders(player: Optional[Any] = None) -> str:
    """Returns reminder trigger text if review topics are overdue."""
    data = _load_tutor_data()
    topics = data.get("topics", [])
    today_str = datetime.now().strftime("%Y-%m-%d")
    due = [t.get("name") for t in topics if t.get("next_review", "") <= today_str]
    
    if not due:
        return ""
        
    msg = f"Study Alert: Pratik Sir, you have {len(due)} topics due for review: {', '.join(due)}."
    if player and hasattr(player, "write_log"):
        player.write_log(f"📚 STUDY REMINDER: {len(due)} topics due today!")
    return msg

def tutor_mode(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for tutor_mode action."""
    action = parameters.get("action", "report").lower().strip()
    topic = parameters.get("topic", "")
    q = parameters.get("question", "")
    a = parameters.get("answer", "")
    correct = parameters.get("correct", "true").lower() == "true"
    
    if action == "add":
        return add_topic(topic, q, a)
    elif action == "start":
        return start_learning_session(topic)
    elif action == "quiz":
        return quiz_me(topic if topic else None)
    elif action == "outcome":
        return process_quiz_outcome(topic, correct)
    elif action == "report":
        return get_progress_report()
    elif action == "reminder":
        return check_review_reminders(player)
    else:
        return "Unknown tutoring module action, sir."

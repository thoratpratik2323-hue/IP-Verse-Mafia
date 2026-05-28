"""
actions/cyber_tutor.py — Cybersecurity Education & Tutor Module.

Provides comprehensive educational support for networking, Linux, web security,
cryptography, and defensive systems without active target testing mechanisms.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("ip_prime.cyber_tutor")

# File paths
TOPICS_FILE = Path(__file__).resolve().parent.parent / "data" / "cyber_topics.json"
PROGRESS_FILE = Path(__file__).resolve().parent.parent / "data" / "cyber_progress.json"

ROADMAPS = {
    "beginner": {
        "name": "Beginner \u2192 CEH Path",
        "description": "Ideal for newcomers. Focuses on networking, Linux fundamentals, and general security terminology.",
        "milestones": ["Networking Basics", "Linux Fundamentals for Security Professionals", "Security+ concepts"]
    },
    "web_pentesting": {
        "name": "Web Pentesting \u2192 OSCP Web Path",
        "description": "Focuses on identifying and remediating critical web vulnerabilities (OWASP Top 10).",
        "milestones": ["Web Security & OWASP Top 10", "Burp Suite theory", "PortSwigger Web Security Academy"]
    },
    "ctf_player": {
        "name": "CTF Player \u2192 TryHackMe / HackTheBox Path",
        "description": "Action-oriented learning through capture-the-flag practice challenges.",
        "milestones": ["Cryptography Foundations", "Steganography theoretical concepts", "Basic string decoders"]
    },
    "bug_bounty": {
        "name": "Bug Bounty Hunter \u2192 HackerOne Path",
        "description": "Focuses on secure target scoping, vulnerability reporting, and responsible disclosure.",
        "milestones": ["Bug Bounty & Vulnerability Disclosure", "OWASP Top 10", "Report drafting"]
    },
    "blue_team": {
        "name": "Blue Team / Defensive \u2192 SOC Analyst Path",
        "description": "Defensive path focusing on logs analysis, correlation rules, and threat detection.",
        "milestones": ["Defensive Security & Blue Team Operations", "IDS/IPS rules", "Log analysis workflows"]
    }
}

def _load_topics() -> dict[str, Any]:
    """Loads cybersecurity topics and quizzes from the JSON catalog."""
    if not TOPICS_FILE.exists():
        logger.error("Topics catalog file not found at %s", TOPICS_FILE)
        return {"topics": {}, "quizzes": []}
    try:
        return json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to parse topics catalog: %s", e)
        return {"topics": {}, "quizzes": []}

def _load_progress() -> dict[str, Any]:
    """Loads user learning progress logs."""
    if not PROGRESS_FILE.exists():
        return {"topics_completed": [], "quiz_scores": {}, "current_roadmap": "None"}
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to parse progress file: %s", e)
        return {"topics_completed": [], "quiz_scores": {}, "current_roadmap": "None"}

def _save_progress(progress: dict[str, Any]) -> None:
    """Saves user progress state back to disk."""
    try:
        PROGRESS_FILE.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error("Failed to save progress data: %s", e)

def teach_topic(topic_id: str, player: Any = None) -> str:
    """
    Retrieves full explanation text for a target topic and records progress.
    """
    catalog = _load_topics()
    topics = catalog.get("topics", {})
    if topic_id not in topics:
        available = ", ".join(topics.keys())
        return f"Topic '{topic_id}' not found. Available topics: {available}."
    
    topic = topics[topic_id]
    progress = _load_progress()
    
    # Update progress completion
    if topic_id not in progress.setdefault("topics_completed", []):
        progress["topics_completed"].append(topic_id)
        _save_progress(progress)
    
    response = (
        f"\ud83d\udcca **TOPIC:** {topic['title']}\n"
        f"\ud83d\udcd8 **Roadmap:** {topic.get('roadmap', 'General')}\n\n"
        f"{topic['content']}\n\n"
        f"\u2705 *Topic marked as reviewed! You can now test your knowledge using a quiz.*"
    )
    return response

def get_topic_list(player: Any = None) -> str:
    """
    Lists all security educational topics and completion status.
    """
    catalog = _load_topics()
    topics = catalog.get("topics", {})
    progress = _load_progress()
    completed = progress.get("topics_completed", [])
    
    if not topics:
        return "No educational topics catalog found."
    
    lines = ["\ud83d\udcd6 **Cybersecurity Educational Library:**\n"]
    for tid, info in topics.items():
        status = "\u2705 Reviewed" if tid in completed else "\u23f3 Unreviewed"
        lines.append(f"- **{info['title']}** (`{tid}`): {info['description']} [{status}]")
        
    return "\n".join(lines)

def get_learning_roadmap(roadmap_path: str = "", player: Any = None) -> str:
    """
    Exposes learning roadmaps for CEH, OSCP, SOC analysts, and bounty hunters.
    """
    progress = _load_progress()
    
    if not roadmap_path:
        lines = [
            "\ud83d\uddfa\ufe0f **Cybersecurity Learning Roadmaps:**\n",
            "Choose a roadmap using 'roadmap_path':",
            "- `beginner` \u2192 CEH Path",
            "- `web_pentesting` \u2192 OSCP Web Path",
            "- `ctf_player` \u2192 TryHackMe / HTB Path",
            "- `bug_bounty` \u2192 HackerOne Path",
            "- `blue_team` \u2192 SOC Analyst Path\n",
            f"Your current path: **{progress.get('current_roadmap', 'None')}**"
        ]
        return "\n".join(lines)
    
    path_key = roadmap_path.lower().strip()
    if path_key not in ROADMAPS:
        return f"Unknown roadmap path '{roadmap_path}'. Choose from: {', '.join(ROADMAPS.keys())}."
    
    roadmap = ROADMAPS[path_key]
    progress["current_roadmap"] = roadmap["name"]
    _save_progress(progress)
    
    milestones = "\n".join(f"{i+1}. {m}" for i, m in enumerate(roadmap["milestones"]))
    return (
        f"\ud83d\uddfa\ufe0f **Roadmap Set:** {roadmap['name']}\n"
        f"**Description:** {roadmap['description']}\n\n"
        f"\ud83d\udcc8 **Key Milestones:**\n{milestones}\n\n"
        f"\u2705 *Your active path has been updated in your profile.*"
    )

def quiz_cyber(quiz_id: str = "", user_answer: str = "", player: Any = None) -> str:
    """
    Presents a multiple-choice security question or validates a user's answer.
    """
    catalog = _load_topics()
    quizzes = catalog.get("quizzes", [])
    if not quizzes:
        return "No cybersecurity quizzes loaded."
    
    # If no specific quiz requested, fetch a random unanswered or default one
    if not quiz_id:
        progress = _load_progress()
        scores = progress.get("quiz_scores", {})
        
        # Pick first quiz that isn't answered correctly, otherwise return the first quiz
        selected = quizzes[0]
        for q in quizzes:
            if q["id"] not in scores:
                selected = q
                break
        
        options_text = "\n".join(f"  - {opt}" for opt in selected["options"])
        return (
            f"\u2753 **QUIZ QUESTION** (ID: `{selected['id']}`)\n"
            f"Topic: {selected['topic'].upper()}\n\n"
            f"**{selected['question']}**\n\n"
            f"Options:\n{options_text}\n\n"
            f"*Answer using: quiz_cyber(quiz_id='{selected['id']}', user_answer='[your answer]')*"
        )
        
    # Answer validation
    selected_quiz = None
    for q in quizzes:
        if q["id"] == quiz_id:
            selected_quiz = q
            break
            
    if not selected_quiz:
        return f"Quiz question with ID '{quiz_id}' not found."
    
    if not user_answer:
        options_text = "\n".join(f"  - {opt}" for opt in selected_quiz["options"])
        return (
            f"\u2753 **QUIZ QUESTION** (ID: `{selected_quiz['id']}`)\n\n"
            f"**{selected_quiz['question']}**\n\n"
            f"Options:\n{options_text}"
        )
    
    progress = _load_progress()
    correct_ans = selected_quiz["answer"]
    is_correct = user_answer.strip().lower() == correct_ans.strip().lower()
    
    # Fuzzy match matching options
    if not is_correct:
        # Check if user matches exact option value
        for opt in selected_quiz["options"]:
            if opt.strip().lower() == user_answer.strip().lower() and opt.strip().lower() == correct_ans.strip().lower():
                is_correct = True
                break
                
    if is_correct:
        progress.setdefault("quiz_scores", {})[quiz_id] = "Correct"
        _save_progress(progress)
        return "\ud83c\udf89 **Correct!** Great job! You have mastered this concept."
    else:
        return f"\u274c **Incorrect.** The correct answer was: **{correct_ans}**. Keep learning and try again!"

def cyber_tutor(parameters: dict[str, Any], player: Any = None) -> str:
    """
    Main orchestrator/dispatcher for cybersecurity tutor.
    """
    action = parameters.get("action", "list").lower().strip()
    if action == "teach":
        topic_id = parameters.get("topic_id", "")
        return teach_topic(topic_id, player)
    elif action == "list":
        return get_topic_list(player)
    elif action == "roadmap":
        path = parameters.get("roadmap_path", "")
        return get_learning_roadmap(path, player)
    elif action == "quiz":
        qid = parameters.get("quiz_id", "")
        ans = parameters.get("user_answer", "")
        return quiz_cyber(qid, ans, player)
    else:
        return f"Unknown cyber_tutor action '{action}'."

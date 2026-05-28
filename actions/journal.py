"""
journal.py — AI Vocal Daily Journaling and mood analytics engine for IP Prime.

Allows adding daily vocal/text entries, tagging contents, querying logs, and mapping
mood trends over time. Saves logs to data/journal.json.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.journal")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JOURNAL_FILE = DATA_DIR / "journal.json"

def _ensure_journal_store():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not JOURNAL_FILE.exists():
            with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
                json.dump({"entries": []}, f, indent=4)
    except Exception as e:
        logger.error("Failed to ensure journal directory: %s", e)

def _load_journal() -> list[dict[str, Any]]:
    _ensure_journal_store()
    try:
        if JOURNAL_FILE.exists():
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("entries", [])
    except Exception as e:
        logger.error("Error loading journal: %s", e)
    return []

def _save_journal(entries: list[dict[str, Any]]) -> bool:
    _ensure_journal_store()
    try:
        with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump({"entries": entries}, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving journal: %s", e)
    return False

def add_journal_entry(text: str, mood_tag: str = "neutral", tags: Optional[list[str]] = None) -> str:
    """Creates a new journal entry with date and tags."""
    if not text:
        return "Journal text content cannot be empty, sir."
        
    entries = _load_journal()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    new_entry = {
        "date": today_str,
        "timestamp": datetime.now().strftime("%I:%M %p"),
        "text": text.strip(),
        "mood": mood_tag.lower().strip(),
        "tags": tags or ["general"]
    }
    
    entries.append(new_entry)
    if _save_journal(entries):
        return f"Successfully added today's journal entry under mood '{mood_tag}', sir! I have secured your thoughts."
    return "Failed to save the journal entry, sir."

def read_journal(date_str: Optional[str] = None) -> str:
    """Reads journal entries matching a target date (default: today)."""
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    entries = _load_journal()
    
    matches = [e for e in entries if e.get("date") == target_date]
    if not matches:
        return f"Aapka target date '{target_date}' ka koi journal entry nahi mila, sir."
        
    output = [f"### [JOURNAL] Thoughts from {target_date}:\n"]
    for idx, e in enumerate(matches, 1):
        output.append(
            f"**Entry {idx}** ({e['timestamp']}) | Mood: {e['mood'].upper()}\n"
            f"  - \"{e['text']}\"\n"
            f"  - *Tags*: {', '.join(e['tags'])}\n"
        )
    return "\n".join(output)

def search_journal(query: str) -> str:
    """Searches past journal entries for keyword matches."""
    if not query:
        return "Search query cannot be empty, sir."
        
    entries = _load_journal()
    matches = [e for e in entries if query.lower() in e.get("text", "").lower()]
    
    if not matches:
        return f"Aapke past journal logs mein query '{query}' se matching kuch nahi mila, sir."

    output = [f"### [JOURNAL SEARCH] Matches for '{query}':\n"]
    for idx, e in enumerate(matches[:5], 1):
        output.append(
            f"{idx}. **{e['date']}** ({e['timestamp']}) | Mood: {e['mood'].upper()}\n"
            f"   - \"{e['text']}\""
        )
    return "\n".join(output)

def get_mood_trends() -> str:
    """Calculates distribution statistics of past recorded moods."""
    entries = _load_journal()
    if not entries:
        return "No entries logged in your journal to map mood trends, sir."
        
    mood_counts = {}
    for e in entries:
        m = e.get("mood", "neutral")
        mood_counts[m] = mood_counts.get(m, 0) + 1
        
    total = len(entries)
    output = ["### [MOOD TRENDS] Weekly Emotional Distribution:\n"]
    for mood, cnt in mood_counts.items():
        percentage = (cnt / total) * 100
        bar = "█" * int(percentage // 10)
        output.append(f"• **{mood.upper()}**: {percentage:.1f}% ({cnt} days) {bar}")
        
    return "\n".join(output) + "\n\nKeep tracking to see long-term trends, sir!"

def get_weekly_summary() -> str:
    """Compiles a summary of recurring themes and highlights using AI."""
    entries = _load_journal()
    if not entries:
        return "No journal entries registered to compile weekly summaries, sir."

    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [e for e in entries if e.get("date", "") >= seven_days_ago]
    
    if not recent:
        return "You have not logged any journal entries in the last 7 days, sir."

    outline = "\n".join([f"- [{e['date']}] Mood: {e['mood']} | {e['text']}" for e in recent])
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = (
                f"You are a wellness coach AI. Summarize the following journal entries of Pratik Sir "
                f"from the past week:\n\n{outline}\n\n"
                "Please generate a short, encouraging summary of: 1) Weekly Highlights, 2) Core themes / topics mentioned, "
                "3) A motivational advice line in Hinglish. Keep it warm and concise."
            )
            res = model.generate_content(prompt)
            return f"### [WEEKLY JOURNAL REVIEW]\n\n{res.text.strip()}\n\nAll secure sir!"
        except Exception as e:
            logger.error("Failed compiling weekly journal summary via Gemini: %s", e)

    # Basic fallback summary
    return (
        f"### [WEEKLY JOURNAL REVIEW (Simulated)]:\n"
        f"Pratik Sir, you logged {len(recent)} entries in the last 7 days. "
        "Core highlights: Focused, productive, and balanced. "
        "Advice: Aapka week kafi productive aur direct raha hai. Keep up the high focus, sir!"
    )

def journal(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for journal action."""
    action = parameters.get("action", "read").lower().strip()
    text = parameters.get("text", "")
    mood = parameters.get("mood", "neutral")
    date_str = parameters.get("date")
    query = parameters.get("query", "")
    
    if action == "add":
        tags_raw = parameters.get("tags", "general")
        tags = [t.strip() for t in tags_raw.split(",")] if tags_raw else ["general"]
        return add_journal_entry(text, mood, tags)
    elif action == "read":
        return read_journal(date_str)
    elif action == "search":
        return search_journal(query)
    elif action == "trends":
        return get_mood_trends()
    elif action == "summary":
        return get_weekly_summary()
    else:
        return "Unknown journal action parameter, sir."

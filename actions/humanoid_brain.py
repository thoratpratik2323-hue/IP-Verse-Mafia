"""
humanoid_brain.py — Coordinates context queues and active assistant conversational memories.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/humanoid_brain.py
import json
from datetime import datetime
from pathlib import Path
import sys

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
MOOD_HISTORY_PATH = BASE_DIR / "memory" / "long_term" / "mood_history.json"

MOOD_LEXICON = {
    "happy": ["khush", "happy", "awesome", "great", "maza", "mazza", "mazandar", "brilliant", "mast", "party", "badiya", "superb", "excited"],
    "tired": ["thaka", "tired", "sleepy", "exhausted", "lazy", "bore", "slow", "headache", "pain", "stiff", "stress", "heavy"],
    "sad": ["sad", "down", "upset", "udaas", "bad", "roop", "rula", "hurt", "lonely", "miss", "gussa", "angry", "annoyed"],
    "energetic": ["energy", "charge", "code", "run", "fast", "lets go", "chalo", "jaldi", "building", "hype", "ready", "active"]
}

HUMANOID_FILLERS = {
    "happy": [
        "Arey waah Sir! 😍 ",
        "Kya baat hai Sir, sunkar dil khush ho gaya! ",
        "Arey brilliant! Mast mood hai aaj toh. ",
        "Wah Sir! Chalo is khushi mein kaam aur badhiya karte hain. "
    ],
    "tired": [
        "Hmm, lagta hai thoda thak gaye hain Sir. Aaram se kijiye. ☕ ",
        "Oh ho, stress mat lijiye Sir. Main background tasks handle kar leta hoon. ",
        "Take it easy Sir. Thoda paani pi lijiye, baaki main hoon na yahan. ",
        "Arey Sir, thoda break le lo, screen se thodi der door ho jao. "
    ],
    "sad": [
        "Hmm, main samajh sakta hoon Sir. Koi baat nahi, sab theek ho jayega. 🫂 ",
        "Oh, sorry to hear that Sir. Tension mat lijiye, chalo milkar isko solve karte hain. ",
        "Arey Sir, bilkul udaas mat hoiye. Main hamesha aapke saath hoon. ",
        "Udaas mat hoiye Sir. Chalo thoda chill karte hain. "
    ],
    "energetic": [
        "Chalo chalo Sir, full power! Let's code it. ⚡ ",
        "Arey bilkul Sir! Full flow mein hain aaj toh aap, chaliye machate hain! ",
        "Supercharged! Bilkul ready hoon main bhi Sir. ",
        "Yes! Let's do it immediately Sir. "
    ],
    "neutral": [
        "Bilkul Sir! ",
        "Acha, toh dekhiye Sir... ",
        "Haan Sir, ho jayega. ",
        "Dekho Sir, "
    ]
}

def track_user_mood(user_input: str) -> dict:
    """Classifies user mood based on keywords, updates history, and returns current state."""
    text = (user_input or "").lower().strip()
    detected_mood = "neutral"
    
    # Simple, fast keyword matching
    for mood, keywords in MOOD_LEXICON.items():
        if any(kw in text for kw in keywords):
            detected_mood = mood
            break
            
    # Load and save mood history
    MOOD_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if MOOD_HISTORY_PATH.exists():
        try:
            history = json.loads(MOOD_HISTORY_PATH.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = []
        except Exception:
            pass
            
    history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "input": user_input[:200],
        "mood": detected_mood
    })
    
    # Keep last 50 entries
    history = history[-50:]
    
    try:
        MOOD_HISTORY_PATH.write_text(json.dumps(history, indent=4, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[HumanoidBrain] Mood log save failed: {e}")
        
    return {
        "current_mood": detected_mood,
        "history_count": len(history),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

def get_rolling_mood() -> str:
    """Determines current dominant mood from recent logs."""
    if not MOOD_HISTORY_PATH.exists():
        return "neutral"
    try:
        history = json.loads(MOOD_HISTORY_PATH.read_text(encoding="utf-8"))
        if not history:
            return "neutral"
        recent = history[-5:] # check last 5 entries
        moods = [h.get("mood", "neutral") for h in recent]
        # Get most common mood (excluding neutral if others exist)
        non_neutrals = [m for m in moods if m != "neutral"]
        if non_neutrals:
            return max(set(non_neutrals), key=non_neutrals.count)
        return "neutral"
    except Exception:
        return "neutral"

def inject_humanoid_fillers(text: str) -> str:
    """Prepends natural conversational fillers based on rolling mood."""
    mood = get_rolling_mood()
    fillers = HUMANOID_FILLERS.get(mood, HUMANOID_FILLERS["neutral"])
    
    # Select filler based on message length / hash to keep it deterministic but varied
    import hashlib
    h_idx = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % len(fillers)
    filler = fillers[h_idx]
    
    # Avoid double-prepending fillers if already present
    if any(text.startswith(f.strip()[:10]) for f in fillers):
        return text
        
    return filler + text

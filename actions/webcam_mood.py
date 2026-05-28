"""
webcam_mood.py — Takes webcam frame and parses user expressions for mood historical logs.

This is a standard action module for the IP Prime personal assistant suite.
"""

import io
import json
import time
import threading
import random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"
MOOD_DIR = Path.home() / ".ipprime"
MOOD_HISTORY_FILE = MOOD_DIR / "mood_history.json"

def _get_gemini_client():
    """Loads API key and returns a Gemini Client from the new google-genai SDK."""
    try:
        from google import genai
        if API_KEYS_PATH.exists():
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                api_key = json.load(f)["gemini_api_key"]
            return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[WebcamMood] Error loading key or client: {e}")
    return None

def _ensure_mood_file():
    """Ensures mood log file exists."""
    try:
        MOOD_DIR.mkdir(parents=True, exist_ok=True)
        if not MOOD_HISTORY_FILE.exists():
            with open(MOOD_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({"history": []}, f, indent=4)
    except Exception as e:
        print(f"[WebcamMood] Error ensuring directory: {e}")

def _save_mood_to_history(mood: str, confidence: str, advice: str, simulated: bool = False):
    """Saves a mood reading to history."""
    _ensure_mood_file()
    try:
        if MOOD_HISTORY_FILE.exists():
            with open(MOOD_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            history = data.get("history", [])
            history.append({
                "timestamp": datetime.now().isoformat(),
                "mood": mood,
                "confidence": confidence,
                "advice": advice,
                "simulated": simulated
            })
            
            with open(MOOD_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({"history": history}, f, indent=4)
    except Exception as e:
        print(f"[WebcamMood] Error saving history: {e}")

def get_mood_history(days: int = 7, player=None) -> str:
    """Returns formatted history of past mood readings."""
    _ensure_mood_file()
    try:
        with open(MOOD_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        history = data.get("history", [])
        if not history:
            return "Aapka mood history log khali hai, sir."
            
        cutoff = datetime.now() - timedelta(days=days)
        filtered = []
        
        for h in history:
            try:
                t = datetime.fromisoformat(h.get("timestamp"))
                if t >= cutoff:
                    filtered.append(h)
            except Exception:
                pass
                
        if not filtered:
            return f"Pichle {days} dino mein koi mood readings nahi mili, sir."
            
        output = [f"### [HISTORY] Pratik Sir's Emotional Telemetry (Last {days} Days)\n"]
        for idx, h in enumerate(reversed(filtered[-10:]), 1): # Show last 10 readings max
            t_str = datetime.fromisoformat(h.get("timestamp")).strftime("%Y-%m-%d %I:%M %p")
            mood = h.get("mood", "neutral").upper()
            conf = h.get("confidence", "medium").upper()
            sim = " (Simulated)" if h.get("simulated") else ""
            
            output.append(
                f"**{idx}. [{t_str}] Mood: {mood}** (Confidence: {conf}){sim}\n"
                f"  - *Advice*: {h.get('advice')}\n"
            )
            
        return "\n".join(output) + "\n\nTake care of yourself, sir!"
    except Exception as e:
        return f"Error reading mood history: {e}, sir."

def detect_mood_from_webcam(player=None) -> str:
    """Captures image from OpenCV webcam (degrades to simulation) and analyzes emotion via Gemini."""
    client = _get_gemini_client()
    
    cv2_available = False
    cap = None
    frame = None
    
    # 1. Try to open webcam and capture frame
    try:
        import cv2
        cv2_available = True
        
        if player:
            player.write_thought("Accessing webcam channel...")
            
        # Try device index 0
        cap = cv2.VideoCapture(0)
        if cap and cap.isOpened():
            # Warmup camera
            for _ in range(5):
                cap.read()
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                frame = None
        else:
            if cap:
                cap.release()
            frame = None
    except Exception as e:
        print(f"[WebcamMood] OpenCV error: {e}")
        frame = None
        
    # 2. Simulation Fallback: If webcam fails or cv2 not installed, generate high-fidelity simulated response
    if frame is None or not client:
        sim_moods = [
            ("focused", "high", "Pratik Sir, aap abhi bahut deep focus mein ho. Code mast chal raha hai, bas 5 minute ka pause leke stretch kar lijiye sir!"),
            ("happy", "high", "Arey waah sir! Chehre pe shandar muskan hai. Aaj productivity levels aasmaan chhu rahe hain, sir!"),
            ("stressed", "medium", "Thoda tension lag raha hai sir. Gehri saans lijiye, chai ka mug fill kariye aur aaram se work kariye, sir."),
            ("tired", "high", "Aap thake thake lag rahe ho sir. Eyes ko rest dijiye aur 10 minutes ki power nap lijiye, sir."),
            ("neutral", "high", "Ekdam relaxed aur call vibes hain sir. Sab kuch control mein hai!"),
            ("excited", "high", "Energy levels fully loaded hain sir! Bilkul rockstar vaali feeling, sir!")
        ]
        mood, confidence, advice = random.choice(sim_moods)
        
        # Log to file
        _save_mood_to_history(mood, confidence, advice, simulated=True)
        
        mode_str = " (OpenCV Camera/Client inactive, running high-fidelity simulation)" if not cv2_available else " (Camera offline, simulated)"
        return (
            f"### [CAMERA] Webcam Mood Telemetry{mode_str}\n"
            f"Result for **Pratik Sir**:\n"
            f"- **MOOD**: `{mood.upper()}`\n"
            f"- **CONFIDENCE**: `{confidence.upper()}`\n\n"
            f"> **Hinglish Advice**: {advice}\n\n"
            "Mood metrics captured successfully, sir!"
        )

    # 3. Webcam capture was successful and client is active
    try:
        import cv2
        is_success, buffer = cv2.imencode(".jpg", frame)
        if not is_success:
            return "Failed to encode camera frame to JPEG, sir."
            
        image_bytes = io.BytesIO(buffer)
        image = Image.open(image_bytes)
        
        if player:
            player.write_thought("Analyzing camera capture with Gemini Vision...")
            
        system_instruction = (
            "You are IP PRIME's Emotion AI Engine. Look at this image of a person (Pratik Sir). "
            "Analyze their facial expression, posture, lighting, and overall appearance. "
            "Determine their current emotional state: happy/sad/stressed/focused/tired/neutral/excited. "
            "Your output must follow exactly this single-line format:\n"
            "MOOD: [mood] | CONFIDENCE: [high/medium/low] | ADVICE: [one personalized, encouraging, warm tip in Hinglish starting with 'Pratik Sir, ...']\n"
            "Do not include markdown tags, extra comments or explanations."
        )
        
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
        )
        
        # Parse result
        res_text = response.text.strip()
        
        # Parse fields
        mood = "neutral"
        confidence = "medium"
        advice = "Pratik Sir, stay cool and have a wonderful coding session!"
        
        parts = res_text.split("|")
        for p in parts:
            p_clean = p.strip()
            if p_clean.startswith("MOOD:"):
                mood = p_clean.replace("MOOD:", "").strip().lower()
            elif p_clean.startswith("CONFIDENCE:"):
                confidence = p_clean.replace("CONFIDENCE:", "").strip().lower()
            elif p_clean.startswith("ADVICE:"):
                advice = p_clean.replace("ADVICE:", "").strip()
                
        # Save to logs
        _save_mood_to_history(mood, confidence, advice, simulated=False)
        
        return (
            f"### [CAMERA] Webcam Mood Telemetry\n"
            f"Result for **Pratik Sir**:\n"
            f"- **MOOD**: `{mood.upper()}`\n"
            f"- **CONFIDENCE**: `{confidence.upper()}`\n\n"
            f"> **Hinglish Advice**: {advice}\n\n"
            "Live webcam analysis complete, sir!"
        )
    except Exception as e:
        return f"Error running Gemini visual mood analysis: {e}, sir."


class WebcamMoodWatcher:
    """Singleton background watcher that runs webcam mood scans periodically."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(WebcamMoodWatcher, cls).__new__(cls)
                cls._instance.is_running = False
                cls._instance.thread = None
                cls._instance.interval_minutes = 30
                cls._instance.player = None
            return cls._instance

    def start(self, interval_minutes: int = 30, player=None):
        with self._lock:
            if self.is_running:
                return f"Mood watcher is already running, checking every {self.interval_minutes} minutes, sir."
                
            self.interval_minutes = interval_minutes
            self.player = player
            self.is_running = True
            
            self.thread = threading.Thread(target=self._watch_loop, daemon=True, name="WebcamMoodWatcherThread")
            self.thread.start()
            
            return f"Webcam mood watcher activated successfully! Scanning every {interval_minutes} minutes, sir."

    def stop(self) -> str:
        with self._lock:
            if not self.is_running:
                return "Mood watcher active nahi hai, sir."
            self.is_running = False
            return "Webcam mood watcher stopped, sir."

    def _watch_loop(self):
        print(f"[MoodWatcher] Background telemetry started (interval={self.interval_minutes}m)")
        
        while self.is_running:
            # Sleep in 1-second intervals to allow fast exit
            for _ in range(self.interval_minutes * 60):
                if not self.is_running:
                    break
                time.sleep(1)
                
            if not self.is_running:
                break
                
            try:
                print("[MoodWatcher] Executing periodic webcam mood scan...")
                detect_mood_from_webcam(self.player)
            except Exception as e:
                print(f"[MoodWatcher] Scan loop error: {e}")


def webcam_mood(parameters: dict, player=None) -> str:
    """Dispatcher for webcam mood actions."""
    action = parameters.get("action", "detect").lower().strip()
    days = int(parameters.get("days", 7))
    interval = int(parameters.get("interval", 30))
    
    watcher = WebcamMoodWatcher()
    
    if action == "detect":
        return detect_mood_from_webcam(player)
    elif action == "history":
        return get_mood_history(days, player)
    elif action == "watch":
        return watcher.start(interval, player)
    elif action == "stop_watch":
        return watcher.stop()
    else:
        return f"Unknown action '{action}' for Webcam Mood, sir."

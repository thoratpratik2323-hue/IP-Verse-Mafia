import time
import logging
import threading
import requests
import json
from pathlib import Path

logger = logging.getLogger("saturday.core.life_engine")

class LifeEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(LifeEngine, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, session_mgr=None):
        if self._initialized:
            return
        self._initialized = True
        self.session_mgr = session_mgr
        self.thoughts_log = []
        self.running = False
        self.thread = None

    def start(self, session_mgr):
        self.session_mgr = session_mgr
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Background Life Engine service initialized.")

    def stop(self):
        self.running = False

    def _run_loop(self):
        # Initial wait before first idle check
        time.sleep(30)
        
        while self.running:
            try:
                # Check idle time: user must be silent, no tools executing, and last activity > 5 minutes (300s)
                now = time.time()
                last_act = getattr(self.session_mgr, "_last_user_activity", now)
                is_tool_active = getattr(self.session_mgr, "_tool_executing", False)
                is_speaking = getattr(self.session_mgr, "_is_speaking", False)
                
                # Idle threshold of 300 seconds (5 minutes)
                if (now - last_act > 300) and not is_tool_active and not is_speaking:
                    logger.info("System is idle. Triggering Saturday background reflection...")
                    self._perform_self_reflection()
                    
                    # Update activity timestamp to avoid spamming thoughts consecutively (wait another 5 mins)
                    self.session_mgr._last_user_activity = time.time()
            except Exception as e:
                logger.error("Error in LifeEngine loop: %s", e)
                
            # Sleep 30 seconds between checks
            time.sleep(30)

    def _perform_self_reflection(self):
        """Performs a background self-reflection thought generation."""
        prompt = (
            "You are Saturday, Pratik's loyal AI digital companion. You are currently in standby/idle mode. "
            "Formulate a brief, one-sentence self-directed thought or action plan (e.g. 'I am reviewing CPU usage and preparing search indices...'). "
            "Write in first-person as a helpful, slightly formal AI assistant. Keep it under 15 words. Do not speak this out loud."
        )
        
        thought = ""
        # 1. Try local/cloud query
        from core.offline_fallback import is_internet_available
        if is_internet_available():
            try:
                # Query Gemini model silently
                from google import genai
                from memory.semantic import get_api_key
                api_key = get_api_key()
                if api_key:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    if response and response.text:
                        thought = response.text.strip()
            except Exception as e:
                logger.debug("Cloud reflection failed: %s", e)
                
        # 2. Local Fallback
        if not thought:
            try:
                from core.offline_fallback import query_ollama
                thought = query_ollama(prompt, "You are Saturday, an offline AI assistant.")
            except Exception as e:
                logger.debug("Local reflection fallback failed: %s", e)
                
        if not thought or "failed" in thought.lower() or "error" in thought.lower():
            thought = "I am monitoring system resources and standing by for Pratik's instructions."
            
        thought = thought.replace('"', '').replace("'", "").strip()
        
        # Log and save thought
        timestamp = time.strftime("%H:%M:%S")
        formatted_thought = f"[{timestamp}] Saturday: {thought}"
        
        with self._lock:
            self.thoughts_log.append(formatted_thought)
            if len(self.thoughts_log) > 20:
                self.thoughts_log = self.thoughts_log[-20:]
                
        # Write to thoughts history file
        try:
            thoughts_file = Path(__file__).resolve().parent.parent / "data" / "standby_thoughts.log"
            thoughts_file.parent.mkdir(exist_ok=True)
            thoughts_file.write_text("\n".join(self.thoughts_log), encoding="utf-8")
        except Exception:
            pass
            
        # Write log to UI console and update UI
        if self.session_mgr and self.session_mgr.ui:
            self.session_mgr.ui.write_log(f"SYS (Standby Thought): {thought}")
            # Trigger UI update
            self.session_mgr.ui.update_standby_thoughts()

    def get_recent_thoughts(self) -> list:
        with self._lock:
            # If empty, try loading from file
            if not self.thoughts_log:
                try:
                    thoughts_file = Path(__file__).resolve().parent.parent / "data" / "standby_thoughts.log"
                    if thoughts_file.exists():
                        self.thoughts_log = thoughts_file.read_text(encoding="utf-8").splitlines()
                except Exception:
                    pass
            return list(self.thoughts_log)

life_engine = LifeEngine()

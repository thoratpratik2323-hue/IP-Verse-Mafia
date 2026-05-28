"""
live_code_reviewer.py — Reviews code files for performance, security, and logical bugs.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"
REVIEWS_DIR = Path.home() / ".ipprime"
REVIEWS_LOG = REVIEWS_DIR / "code_reviews.log"

def _get_gemini_client():
    """Loads API key and returns a Gemini Client from the new google-genai SDK."""
    try:
        from google import genai
        if API_KEYS_PATH.exists():
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                api_key = json.load(f)["gemini_api_key"]
            return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[CodeReviewer] Error loading key or client: {e}")
    return None

def _find_recently_modified_file() -> str | None:
    """Finds the most recently modified source file (.py, .js, .ts, .cpp, .html, .css) in the project."""
    extensions = {".py", ".js", ".ts", ".cpp", ".html", ".css", ".json"}
    recent_file = None
    recent_mtime = 0
    
    # We walk the project directory, skipping common folders
    for root, dirs, files in os.walk(str(BASE_DIR)):
        # Skip node_modules, virtualenvs, cache folders
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "env", "dist", "build", "memory"}]
        
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in extensions:
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime > recent_mtime:
                        recent_mtime = mtime
                        recent_file = str(file_path)
                except Exception:
                    pass
    return recent_file

def review_code_snippet(code: str, language: str = 'python', player=None) -> str:
    """Sends a code snippet to Gemini for comprehensive code review."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API key not configured properly, sir."
        
    if not code:
        return "Code snippet empty hai, sir."
        
    try:
        if player:
            player.write_thought(f"Analyzing {language} code snippet with Gemini...")
            
        system_instruction = (
            "You are a strict, senior staff software engineer and application security expert. "
            "You will be provided with a source code file or snippet. Review it thoroughly and return a structured assessment. "
            "Your output must follow exactly this layout:\n"
            "### [REVIEW] CODE REVIEW SUMMARY\n\n"
            "#### 1. BUGS & CRITICAL ERRORS\n"
            "- List any bugs, logic errors, syntax mistakes, or potential crash points. If none, write 'No critical bugs found.'\n\n"
            "#### 2. PERFORMANCE & EFFICIENCY\n"
            "- Suggest computational improvements, memory optimizations, or cleaner algorithmic steps.\n\n"
            "#### 3. SECURITY & COMPLIANCE\n"
            "- Point out secrets/keys exposure, SQLi, XSS, insecure storage, or bad practices.\n\n"
            "#### 4. REFACTORING & STYLE SUGGESTIONS\n"
            "- Focus on clean code, naming conventions, readability, or modern syntax standard shortcuts.\n\n"
            "#### 5. OVERALL GRADE\n"
            "- Provide a clear overall code quality grade from 'A+' (Flawless) to 'F' (Needs a total rewrite).\n\n"
            "Make all notes concise and extremely helpful. Write in a helpful, direct tone addressed to Pratik Sir."
        )
        
        prompt = f"Please review this {language} code snippet, sir:\n\n```\n{code}\n```"
        
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        
        return response.text
        
    except Exception as e:
        return f"Error reviewing code snippet: {e}, sir."

def review_current_file(file_path: str = '', player=None) -> str:
    """Finds a target file and performs a comprehensive review of its contents."""
    target = file_path
    if not target:
        target = _find_recently_modified_file()
        
    if not target or not os.path.exists(target):
        return "Aapka target source file nahi mila, sir. Please pass a valid path or modify a file first."
        
    try:
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            
        filename = Path(target).name
        ext = Path(target).suffix[1:]
        
        if player:
            player.write_thought(f"Reviewing active file '{filename}'...")
            
        review_result = review_code_snippet(code, language=ext, player=player)
        
        # Extract overall grade
        import re
        grade_match = re.search(r"GRADE:\s*\*?([A-F][+-]?)", review_result, re.I)
        grade = grade_match.group(1).strip() if grade_match else "B"
        
        # Semantic memory vector indexing for code reviews
        try:
            from actions.semantic_store import index_code_review
            index_code_review(file_path=target, review_content=review_result, grade=grade)
        except Exception as sem_err:
            print(f"[Code Reviewer] LanceDB indexing skipped: {sem_err}")
            
        header = f"### [REVIEW] Live Code Review for: `{filename}`\n"
        header += f"- **Full Path**: `{target}`\n"
        header += f"- **Analyzed at**: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n\n"
        
        return header + review_result
        
    except Exception as e:
        return f"Error reading or reviewing file '{target}': {e}, sir."


class LiveCodeReviewWatcher:
    """Singleton background watcher that monitors a target file and logs reviews on modification."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(LiveCodeReviewWatcher, cls).__new__(cls)
                cls._instance.is_running = False
                cls._instance.thread = None
                cls._instance.target_path = None
                cls._instance.last_mtime = 0
                cls._instance.interval = 30
                cls._instance.player = None
            return cls._instance

    def start(self, file_path: str, interval: int = 30, player=None):
        with self._lock:
            if self.is_running:
                if self.target_path == file_path:
                    return f"Already watching '{Path(file_path).name}' for changes, sir."
                else:
                    self.stop()
                    
            if not os.path.exists(file_path):
                return f"Target file '{file_path}' does not exist, sir."
                
            self.target_path = file_path
            self.interval = interval
            self.player = player
            self.last_mtime = os.path.getmtime(file_path)
            self.is_running = True
            
            self.thread = threading.Thread(target=self._watch_loop, daemon=True, name="CodeReviewWatcherThread")
            self.thread.start()
            
            return f"Started watching '{Path(file_path).name}' (checking every {interval}s). I will automatically log reviews on save, sir!"

    def stop(self) -> str:
        with self._lock:
            if not self.is_running:
                return "No file watcher is currently active, sir."
            self.is_running = False
            filename = Path(self.target_path).name if self.target_path else "file"
            return f"Stopped watching '{filename}', sir."

    def _watch_loop(self):
        filename = Path(self.target_path).name
        print(f"[Watcher] Started background watcher for {filename}")
        
        while self.is_running:
            time.sleep(self.interval)
            
            # Check if thread was stopped during sleep
            if not self.is_running:
                break
                
            try:
                if os.path.exists(self.target_path):
                    current_mtime = os.path.getmtime(self.target_path)
                    if current_mtime > self.last_mtime:
                        self.last_mtime = current_mtime
                        print(f"[Watcher] File change detected on '{filename}'. Executing auto review...")
                        
                        if self.player:
                            self.player.write_thought(f"[WATCHER] File Watcher: '{filename}' has been modified. Reviewing now...")
                            
                        # Run review
                        review = review_current_file(self.target_path, player=self.player)
                        
                        # Log to file
                        REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
                        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
                        with open(REVIEWS_LOG, "a", encoding="utf-8") as lf:
                            lf.write("\n=========================================\n")
                            lf.write(f"AUTO REVIEW FOR '{filename}' [{timestamp}]\n")
                            lf.write("=========================================\n")
                            lf.write(review)
                            lf.write("\n=========================================\n")
                            
                        if self.player:
                            self.player.write_log(f"Auto code review complete for {filename}. Saved to log.")
            except Exception as e:
                print(f"[Watcher] Error in watch loop: {e}")


def live_code_reviewer(parameters: dict, player=None) -> str:
    """Dispatcher for code reviewer action."""
    action = parameters.get("action", "review_file").lower().strip()
    file_path = parameters.get("file_path", "")
    code = parameters.get("code", "")
    language = parameters.get("language", "python").lower().strip()
    interval = int(parameters.get("interval", 30))
    
    watcher = LiveCodeReviewWatcher()
    
    if action == "review_file":
        return review_current_file(file_path, player)
    elif action == "review_snippet":
        return review_code_snippet(code, language, player)
    elif action == "watch":
        target = file_path
        if not target:
            target = _find_recently_modified_file()
        if not target:
            return "No recently modified source file found to watch, sir."
        return watcher.start(target, interval, player)
    elif action == "stop_watch":
        return watcher.stop()
    else:
        return f"Unknown action '{action}' for Live Code Reviewer, sir."

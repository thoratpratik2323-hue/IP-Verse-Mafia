"""
actions/file_classifier.py — Background watcher that auto-classifies study materials and downloads.

This is a premium action module for the IP Prime personal assistant suite.
"""

import time
import shutil
import threading
from pathlib import Path

class FileClassifierThread(threading.Thread):
    """Background watcher thread that monitors Downloads and auto-organizes study materials."""
    def __init__(self, check_interval_seconds: int = 15):
        super().__init__(name="FileClassifierThread", daemon=True)
        self.check_interval_seconds = check_interval_seconds
        self._stop_event = threading.Event()
        self.downloads_dir = Path.home() / "Downloads"
        self.second_brain_dir = Path.home() / "Documents" / "SecondBrain"
        
    def stop(self):
        self._stop_event.set()
        
    def run(self):
        print("[FileClassifier] 📁 Background downloads file classifier online.")
        # Ensure target directories exist
        if not self.downloads_dir.exists():
            try:
                self.downloads_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
                
        while not self._stop_event.is_set():
            try:
                if self.downloads_dir.exists() and self.second_brain_dir.exists():
                    self._classify_downloads()
            except Exception as e:
                print(f"[FileClassifier] ⚠️ File classification cycle failed: {e}")
                
            # Wait for next interval or stop signal
            if self._stop_event.wait(timeout=self.check_interval_seconds):
                break
                
    def _classify_downloads(self):
        # Category subfolders
        study_dir = self.second_brain_dir / "00 Notes"
        code_dir = self.second_brain_dir / "03 Projects"
        archive_dir = self.second_brain_dir / "00 Notes"
        
        # Extensions mapping
        study_exts = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".txt"}
        code_exts = {".py", ".js", ".ts", ".html", ".css", ".json", ".c", ".cpp", ".java"}
        
        # Scan downloads folder
        for item in self.downloads_dir.iterdir():
            if self._stop_event.is_set():
                return
                
            if item.is_file():
                suffix = item.suffix.lower()
                dest_folder = None
                
                # Check extension to decide destination
                if suffix in study_exts:
                    dest_folder = study_dir
                elif suffix in code_exts:
                    dest_folder = code_dir
                elif suffix in {".zip", ".rar", ".7z", ".png", ".jpg", ".jpeg"}:
                    # Only archive if it looks like a study resource or project asset
                    if any(kw in item.name.lower() for kw in ("study", "notes", "lecture", "book", "prime", "code", "learn")):
                        dest_folder = archive_dir
                
                if dest_folder:
                    try:
                        dest_folder.mkdir(parents=True, exist_ok=True)
                        dest_path = dest_folder / item.name
                        
                        # Prevent overwriting by appending a timestamp if filename exists
                        if dest_path.exists():
                            timestamp = int(time.time())
                            dest_path = dest_folder / f"{item.stem}_{timestamp}{suffix}"
                            
                        # Move file safely
                        shutil.move(str(item), str(dest_path))
                        print(f"[FileClassifier] ✓ Auto-organized: '{item.name}' -> SecondBrain/{dest_folder.name}/")
                        
                        # Auto-check habits
                        try:
                            from actions.habits_engine import check_study_habit, check_coding_habit
                            if dest_folder == study_dir:
                                check_study_habit()
                            elif dest_folder == code_dir:
                                check_coding_habit()
                        except Exception as hab_e:
                            print(f"[FileClassifier] Habits update error: {hab_e}")
                        
                        # Dynamic log to PyQt6 system status if UI is running
                        try:
                            pass
                            # Safely write to UI console if possible
                        except Exception:
                            pass
                    except Exception as err:
                        print(f"[FileClassifier] Failed to move '{item.name}': {err}")

# Helper function to start the thread
_classifier_thread = None

def start_classifier():
    global _classifier_thread
    if _classifier_thread is None:
        _classifier_thread = FileClassifierThread()
        _classifier_thread.start()

def stop_classifier():
    global _classifier_thread
    if _classifier_thread is not None:
        _classifier_thread.stop()
        _classifier_thread = None

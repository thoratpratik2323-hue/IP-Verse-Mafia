import time
import shutil
import threading
from pathlib import Path

class DownloadsClassifier:
    def __init__(self):
        self.stop_event = threading.Event()
        self._thread = None
        self.poll_interval = 120  # Poll every 2 minutes

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DownloadsClassifier")
        self._thread.start()
        self.log("Background Downloads Folder Classifier started.")

    def stop(self):
        self.stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.log("Background Downloads Folder Classifier stopped.")

    def log(self, message: str):
        try:
            import ui
            ui_inst = ui.get_ui()
            if ui_inst:
                ui_inst._win._log_sig.emit(f"SYS [Classifier]: {message}")
                return
            print(f"[Classifier] {message}")
        except Exception:
            print(f"[Classifier] {message}")

    def _loop(self):
        # Give system time to settle on startup
        time.sleep(10)
        downloads_dir = Path.home() / "Downloads"
        
        while not self.stop_event.is_set():
            if downloads_dir.exists():
                try:
                    self._classify_folder(downloads_dir)
                except Exception as e:
                    self.log(f"Classifier error: {e}")
            
            # Wait for poll_interval, but wake up instantly if stopped
            self.stop_event.wait(self.poll_interval)

    def _classify_folder(self, downloads_dir: Path):
        # Retrieve configurable output root directory name
        from config import get_config
        dest_name = get_config().get("downloads_classifier_output_dir", "sat output")
        sat_output_dir = downloads_dir / dest_name
        
        # Extension mappings
        mapping = {
            # Study Materials
            ".pdf": "StudyMaterials",
            ".docx": "StudyMaterials",
            ".pptx": "StudyMaterials",
            ".xlsx": "StudyMaterials",
            ".txt": "StudyMaterials",
            ".epub": "StudyMaterials",
            
            # Projects
            ".py": "SaturdayProjects",
            ".js": "SaturdayProjects",
            ".html": "SaturdayProjects",
            ".css": "SaturdayProjects",
            ".sh": "SaturdayProjects",
            ".bat": "SaturdayProjects",
            ".md": "SaturdayProjects",
            ".json": "SaturdayProjects",
            ".csv": "SaturdayProjects",
            
            # Archives
            ".zip": "Archives",
            ".rar": "Archives",
            ".7z": "Archives",
            ".tar": "Archives",
            ".gz": "Archives"
        }

        classified_count = 0
        skipped_count = 0

        # Scan ONLY top-level items in Downloads to avoid modifying user-organized subfolders
        for f in downloads_dir.iterdir():
            if self.stop_event.is_set():
                break
            # Skip folders entirely to only process top-level files
            if not f.is_file():
                continue
                
            suffix = f.suffix.lower()
            if suffix in mapping:
                category = mapping[suffix]
                dest_dir = sat_output_dir / category
                
                try:
                    # Skip recently modified files (likely still downloading)
                    if time.time() - f.stat().st_mtime < 2:
                        skipped_count += 1
                        continue
                    
                    # Ensure file is not locked or partially downloaded
                    # If file size changes or we cannot open it in append/write mode due to browser lock, wait
                    initial_size = f.stat().st_size
                    time.sleep(0.5)
                    if f.stat().st_size != initial_size:
                        skipped_count += 1
                        continue # File size is still changing
                        
                    try:
                        # Attempt to open the file in append mode to check for write locks (especially on Windows)
                        with open(f, "ab") as lock_fp:
                            pass
                    except OSError:
                        # File is locked by another process (e.g. browser downloading)
                        skipped_count += 1
                        continue
                        
                    # Create destination directory if needed
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Target path
                    dest_path = dest_dir / f.name
                    # Resolve conflict by appending counter
                    if dest_path.exists():
                        counter = 1
                        while True:
                            candidate = dest_dir / f"{f.stem}_{counter}{suffix}"
                            if not candidate.exists():
                                dest_path = candidate
                                break
                            counter += 1
                            
                    # Move the file
                    shutil.move(str(f), str(dest_path))
                    self.log(f"Moved and classified '{f.name}' -> '{category}/{dest_path.name}'")
                    classified_count += 1
                except Exception as e:
                    self.log(f"Skipped '{f.name}': {e}")
                    skipped_count += 1

        if classified_count > 0 or skipped_count > 0:
            self.log(f"Folder classification complete. Classified: {classified_count}, Skipped: {skipped_count}.")

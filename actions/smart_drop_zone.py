import time
import shutil
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".pptx"],
    "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".sh"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Installers": [".exe", ".msi", ".dmg", ".pkg", ".apk"],
    "Audio": [".mp3", ".wav", ".flac", ".aac"],
    "Video": [".mp4", ".mkv", ".avi", ".mov"]
}

class DropZoneHandler(FileSystemEventHandler):
    def __init__(self, downloads_dir):
        self.downloads_dir = Path(downloads_dir)
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        # Process asynchronously so we don't block the observer
        threading.Thread(target=self.delayed_sort, args=(file_path,), daemon=True).start()
        
    def delayed_sort(self, file_path):
        # Wait a bit to ensure the file finishes downloading
        time.sleep(2)
        
        # Skip temporary files
        if file_path.suffix.lower() in [".crdownload", ".tmp", ".download", ".part"]:
            return
            
        if not file_path.exists():
            return
            
        self.sort_file(file_path)
        
    def sort_file(self, file_path):
        ext = file_path.suffix.lower()
        target_folder = "Other"
        
        for category, extensions in CATEGORIES.items():
            if ext in extensions:
                target_folder = category
                break
                
        # We only auto-sort recognized files to avoid aggressive moving
        if target_folder == "Other":
            return
            
        dest_dir = self.downloads_dir / target_folder
        dest_dir.mkdir(exist_ok=True)
        
        # Handle duplicates
        dest_path = dest_dir / file_path.name
        counter = 1
        while dest_path.exists():
            dest_path = dest_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1
        
        try:
            shutil.move(str(file_path), str(dest_path))
            print(f"[Smart Drop Zone] Moved '{file_path.name}' -> {target_folder}/")
        except Exception as e:
            print(f"[Smart Drop Zone] Error moving '{file_path.name}': {e}")

def start_smart_drop_zone():
    downloads_dir = Path.home() / "Downloads"
    if not downloads_dir.exists():
        print("[Smart Drop Zone] Downloads directory not found.")
        return
        
    event_handler = DropZoneHandler(downloads_dir)
    observer = Observer()
    observer.schedule(event_handler, str(downloads_dir), recursive=False)
    observer.start()
    print(f"[Smart Drop Zone] Actively watching '{downloads_dir}' for autonomous sorting.")
    
    # Keep thread alive to allow watchdog to run
    try:
        while True:
            time.sleep(1)
    except Exception:
        observer.stop()
    observer.join()

def run_in_background():
    """Starts the drop zone watcher safely in a background thread."""
    thread = threading.Thread(target=start_smart_drop_zone, daemon=True, name="DropZoneThread")
    thread.start()

import os
import shutil
import time
from pathlib import Path
from PyQt6.QtCore import QThread

class WorkspaceCleanerDaemon(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.workspace_root = Path(r"D:\primes output")
        
    def run(self):
        print("[Cleaner Daemon] Active and monitoring D:\\primes output")
        while self.running:
            # Check every 15 seconds
            for _ in range(15):
                if not self.running:
                    return
                time.sleep(1)
                
            try:
                self.clean_workspace()
            except Exception as e:
                print(f"[Cleaner Daemon] Error during scan: {e}")

    def stop(self):
        self.running = False
        
    def is_file_locked(self, filepath) -> bool:
        """Checks if a file is currently locked/being written by another process."""
        try:
            # Try to rename to the same name; if it's locked by another process on Windows, this fails.
            if os.path.exists(filepath):
                with open(filepath, 'a'):
                    pass
                return False
        except IOError:
            return True
        return False

    def clean_workspace(self):
        if not self.workspace_root.exists() or not self.workspace_root.is_dir():
            return
            
        # Extension mappings
        mappings = {
            # Code scripts
            ".py": "code",
            ".js": "code",
            ".cpp": "code",
            ".h": "code",
            ".java": "code",
            ".css": "code",
            ".html": "code",
            ".sh": "code",
            ".bat": "code",
            # Archives
            ".zip": "archives",
            ".rar": "archives",
            ".tar": "archives",
            ".gz": "archives",
            ".7z": "archives",
            # Exports/Images
            ".png": "exports",
            ".jpg": "exports",
            ".jpeg": "exports",
            ".gif": "exports",
            ".svg": "exports",
            # Documents
            ".pdf": "docs",
            ".docx": "docs",
            ".xlsx": "docs",
            ".pptx": "docs",
            ".txt": "docs",
            ".md": "docs",
            ".json": "docs"
        }
        
        # Excluded files
        excluded_files = {"ip_prime_ipc.json"}
        
        for item in os.listdir(self.workspace_root):
            item_path = self.workspace_root / item
            
            # Only clean files at the root level of the workspace
            if item_path.is_file():
                if item.lower() in excluded_files:
                    continue
                    
                ext = item_path.suffix.lower()
                folder_name = mappings.get(ext)
                
                if folder_name:
                    dest_dir = self.workspace_root / folder_name
                    dest_path = dest_dir / item
                    
                    # Skip if currently locked or active
                    if self.is_file_locked(item_path):
                        continue
                        
                    try:
                        os.makedirs(dest_dir, exist_ok=True)
                        shutil.move(str(item_path), str(dest_path))
                        print(f"[Cleaner Daemon] Moved {item} -> {folder_name}/")
                    except Exception as e:
                        print(f"[Cleaner Daemon] Failed to move {item}: {e}")

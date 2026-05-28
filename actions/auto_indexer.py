"""
auto_indexer.py — Programmatic workspace parser that indexes all target directories and project catalogs.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/auto_indexer.py
import os
import time
import threading
from pathlib import Path
from actions.semantic_store import _get_gemini_client, index_file, init_db
from actions.obsidian_helper import get_obsidian_vault_path
from actions.prime_utils import get_base_dir

BASE_DIR = get_base_dir()

class AutoIndexerThread(threading.Thread):
    """Background daemon thread that periodically indexes local files and Obsidian notes incrementally."""
    def __init__(self, interval_seconds: int = 300):
        super().__init__(name="AutoIndexerThread", daemon=True)
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        
    def stop(self):
        self._stop_event.set()
        
    def run(self):
        print("[AutoIndexer] 🧠 Background incremental semantic indexer online.")
        # Brief warmup delay to avoid freezing main thread on startup
        time.sleep(15)
        
        while not self._stop_event.is_set():
            try:
                self._index_all_workspaces()
            except Exception as e:
                print(f"[AutoIndexer] ⚠️ Indexing iteration failed: {e}")
                
            # Wait for next interval or stop signal
            if self._stop_event.wait(timeout=self.interval_seconds):
                break
                
    def _index_all_workspaces(self):
        print("[AutoIndexer] Starting background RAG sync...")
        init_db()
        try:
            client = _get_gemini_client()
        except Exception as e:
            print(f"[AutoIndexer] Authentication failed (skipping RAG sync): {e}")
            return

        ignored_folders = {".git", "__pycache__", ".venv", "node_modules", "build", "dist", "assets", ".obsidian", ".trash", ".claude", ".codex", ".do", ".fly", ".husky", "awesome_repos"}
        allowed_extensions = {".py", ".txt", ".md", ".json", ".html", ".css", ".js", ".ts"}

        indexed_count = 0
        total_files = 0

        # 1. Index configured Obsidian Vault
        vault_path_str = get_obsidian_vault_path()
        paths_to_index = []
        if vault_path_str:
            vault_path = Path(vault_path_str).resolve()
            if vault_path.exists() and vault_path.is_dir():
                paths_to_index.append(vault_path)

        # 2. Index active IP Given Workspace
        try:
            from prime_platform.ip_given_workspace import get_ip_given_root
            ip_given = get_ip_given_root()
        except Exception:
            ip_given = Path("C:/Users/thora/Downloads/IP Given")

        if ip_given.exists() and ip_given.is_dir():
            paths_to_index.append(ip_given)
        else:
            # Fallback to home/Desktop projects
            projects_dir = Path.home() / "Desktop" / "IPRayProjects"
            if projects_dir.exists() and projects_dir.is_dir():
                paths_to_index.append(projects_dir)
        
        # Add current directory for self-indexing
        paths_to_index.append(BASE_DIR)

        for folder_path in paths_to_index:
            for root, dirs, files in os.walk(folder_path):
                # Prune ignored folders
                dirs[:] = [d for d in dirs if d not in ignored_folders]
                
                for file in files:
                    if self._stop_event.is_set():
                        return
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in allowed_extensions:
                        total_files += 1
                        try:
                            # index_file is naturally incremental and returns True ONLY when file was modified/indexed
                            if index_file(client, file_path):
                                indexed_count += 1
                                print(f"[AutoIndexer] Sync: {file_path.name}")
                                # Gentle delay between embeds to avoid rate limits
                                time.sleep(0.5)
                        except Exception:
                            pass

        if indexed_count > 0:
            print(f"[AutoIndexer] ✓ RAG sync finished. Newly indexed: {indexed_count} files (Total scanned: {total_files}).")
        else:
            print("[AutoIndexer] ✓ RAG sync finished. No modified files detected.")

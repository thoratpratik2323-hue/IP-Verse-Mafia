import os
import io
import time
import sqlite3
import threading
import logging
import mss
import PIL.Image
from pathlib import Path
from google import genai
from google.genai import types

logger = logging.getLogger("saturday.visual_timeline")

class VisualTimeline:
    def __init__(self, interval_seconds: int = 300):
        self.interval = interval_seconds
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        self.base_dir = Path(__file__).resolve().parent.parent
        self.db_path = self.base_dir / "memory" / "visual_timeline.db"
        self.shots_dir = self.base_dir / "memory" / "screenshots"
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                with conn:
                    c = conn.cursor()
                    c.execute("""
                        CREATE TABLE IF NOT EXISTS timeline (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            screenshot_path TEXT,
                            summary TEXT
                        )
                    """)
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to initialize visual timeline database: %s", e)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="VisualTimelineThread")
        self._thread.start()
        logger.info("Visual Timeline background thread started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("Visual Timeline background thread stopped.")

    def _get_api_key(self) -> str:
        api_config = self.base_dir / "config" / "api_keys.json"
        if api_config.exists():
            try:
                import json
                return json.loads(api_config.read_text(encoding="utf-8"))["gemini_api_key"]
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
        return ""

    def _cleanup_old_screenshots(self):
        """Clean up database rows and files older than 7 days, and enforce a max of 2000 rows."""
        seven_days_ago = time.time() - (7 * 24 * 3600)
        
        # 1. Clean up files from shots_dir older than 7 days
        try:
            for f in self.shots_dir.iterdir():
                if f.is_file() and f.suffix.lower() == ".png":
                    if f.stat().st_mtime < seven_days_ago:
                        try:
                            f.unlink()
                            logger.info("Deleted expired screenshot file: %s", f.name)
                        except Exception as fe:
                            logger.error("Failed to delete expired file %s: %s", f.name, fe)
        except Exception as e:
            logger.error("Failed to list screenshot files for cleanup: %s", e)
            
        # 2. Clean up database records older than 7 days
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                with conn:
                    conn.execute("DELETE FROM timeline WHERE datetime(timestamp) < datetime('now', '-7 days')")
            finally:
                conn.close()
            logger.info("Cleaned up expired database records older than 7 days.")
        except Exception as e:
            logger.error("Failed to clean up database records: %s", e)

        # 3. Enforce a max_db_entries cap of 2000 rows, pruning oldest first
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                with conn:
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM timeline")
                    count = c.fetchone()[0]
                    if count > 2000:
                        excess = count - 2000
                        # Select oldest records first
                        c.execute("SELECT id, screenshot_path FROM timeline ORDER BY timestamp ASC LIMIT ?", (excess,))
                        to_delete = c.fetchall()
                        for record_id, filepath in to_delete:
                            if filepath:
                                try:
                                    p = Path(filepath)
                                    if p.exists():
                                        p.unlink()
                                except Exception as _exc:  # noqa: BLE001
                                    logging.debug("[%s] Suppressed: %s", __name__, _exc)
                            c.execute("DELETE FROM timeline WHERE id = ?", (record_id,))
            finally:
                conn.close()
            logger.info("Pruned database entries to maintain the 2000 limit.")
        except Exception as e:
            logger.error("Failed to prune database: %s", e)

    def query_timeline(self, start_dt: str, end_dt: str) -> list[tuple[str, str, str]]:
        """
        Retrieve visual timeline records within a timestamp range.
        Timestamps should be in 'YYYY-MM-DD HH:MM:SS' format.
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                c = conn.cursor()
                c.execute(
                    "SELECT timestamp, screenshot_path, summary FROM timeline "
                    "WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?) "
                    "ORDER BY timestamp DESC",
                    (start_dt, end_dt)
                )
                return c.fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to query timeline by range: %s", e)
            return []

    def _loop(self):
        # Give system time to settle
        self._stop_event.wait(60)
        while not self._stop_event.is_set():
            try:
                self._cleanup_old_screenshots()
                self._capture_and_index()
            except Exception as e:
                logger.error("Error in visual timeline capture: %s", e)
                
            self._stop_event.wait(self.interval)

    def _capture_and_index(self):
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("No API key available for Visual Timeline summary.")
            return

        # Cross-platform Wayland screenshot grab using mss
        with mss.MSS() as sct:
            mon = sct.monitors[1] if len(sct.monitors) >= 2 else sct.monitors[0]
            shot = sct.grab(mon)
            img = PIL.Image.frombytes("RGB", shot.size, shot.rgb)
            
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"
        shot_path = self.shots_dir / filename
        img.save(str(shot_path), format="PNG")

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        # Retrieve standardized Gemini API Version
        try:
            from config import GEMINI_API_VERSION
            api_ver = GEMINI_API_VERSION
        except Exception:
            api_ver = "v1beta"

        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": api_ver}
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                "You are an AI visual timeline memory logger. Briefly describe what is currently happening on the user's screen. Mention the application open and the task. Keep it to 1 sentence, simple and direct."
            ]
        )
        
        summary = response.text.strip()
        
        conn = sqlite3.connect(str(self.db_path))
        try:
            with conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO timeline (screenshot_path, summary) VALUES (?, ?)",
                    (str(shot_path), summary)
                )
        finally:
            conn.close()

        import ui
        ui_inst = ui.get_ui()
        if ui_inst:
            ui_inst.show_custom_alert(
                "Visual Memory Saved",
                f"Saturday captured a screen snapshot:\n\n{summary}",
                "info"
            )
            ui_inst.write_log(f"SYS: Captured screen snapshot. Summary: {summary}")

import logging
import time
import threading
import ctypes
import os
import sys
from pathlib import Path
import mss
import mss.tools
import PIL.Image
import io

AUDITOR_NAME = "Saturday's Proactive Screen Crash Auditor"

# Cached dependencies to avoid circular imports and repeated lookups
_ui_module = None
_main_module = None
_genai_module = None
_types_module = None
_config_module = None

def _load_dependencies():
    global _ui_module, _main_module, _genai_module, _types_module, _config_module
    if _ui_module is None:
        try:
            import ui
            _ui_module = ui
        except ImportError:
            pass
    if _main_module is None:
        try:
            import main
            _main_module = main
        except ImportError:
            pass
    if _genai_module is None:
        try:
            from google import genai
            _genai_module = genai
        except ImportError:
            pass
    if _types_module is None:
        try:
            from google.genai import types
            _types_module = types
        except ImportError:
            pass
    if _config_module is None:
        try:
            import config
            _config_module = config
        except ImportError:
            pass

def get_active_window_title() -> str:
    """Returns the title of the active foreground window on Windows."""
    if sys.platform != "win32":
        return ""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0:
            return ""
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return ""

def capture_screenshot() -> bytes:
    """Capture screen and return compressed JPEG bytes."""
    try:
        with mss.MSS() as sct:
            mon = sct.monitors[1] if len(sct.monitors) >= 2 else sct.monitors[0]
            shot = sct.grab(mon)
            img = PIL.Image.frombytes("RGB", shot.size, shot.rgb)
            img.thumbnail([640, 360], PIL.Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=55)
            return buf.getvalue()
    except Exception as e:
        print(f"[CrashAuditor] ⚠️ Screen capture failed: {e}")
        return b""

class ScreenCrashAuditor:
    def __init__(self):
        self.stop_event = threading.Event()
        self._thread = None
        self.last_alert_time = 0
        self.alert_cooldown = 180  # Cooldown between speaking screen alerts (3 mins)
        _load_dependencies()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="CrashAuditor")
        self._thread.start()
        self.log(f"{AUDITOR_NAME} started.")

    def stop(self):
        self.stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.log(f"{AUDITOR_NAME} stopped.")

    def log(self, message: str):
        try:
            _load_dependencies()
            if _ui_module:
                ui_inst = _ui_module.get_ui()
                if ui_inst:
                    ui_inst._win._log_sig.emit(f"SYS [Auditor]: {message}")
                    return
            print(f"[CrashAuditor] {message}")
        except Exception:
            print(f"[CrashAuditor] {message}")

    def _loop(self):
        if sys.platform != "win32":
            self.log("Auditor is non-operational on non-Windows platforms.")
            return

        # Allow system to boot fully
        time.sleep(15)
        
        while not self.stop_event.is_set():
            try:
                raw_title = get_active_window_title()
                title = raw_title.lower()
                is_dev = any(w in title for w in ["visual studio code", "vscode", "code", "cmd", "powershell", "terminal", "bash", "pycharm", "eclipse"])
                
                # We check active windows. Developer window audit cooldown is 3 minutes (180s).
                # To keep CPU overhead low, we poll title every 15s.
                if is_dev:
                    now = time.time()
                    if now - self.last_alert_time >= self.alert_cooldown:
                        self.log(f"Auditing active developer window: '{raw_title}'")
                        self.last_alert_time = now
                        self._audit_screen()
            except Exception as e:
                self.log(f"Loop error: {e}")
            
            # Poll every 15 seconds
            time.sleep(15)

    def _audit_screen(self):
        image_bytes = capture_screenshot()
        if not image_bytes:
            return
        # Run audit in a separate daemon thread to avoid blocking the main polling loop
        threading.Thread(target=self._audit_screen_worker, args=(image_bytes,), daemon=True).start()

    def _audit_screen_worker(self, image_bytes):
        try:
            _load_dependencies()
            if not _config_module or not _genai_module or not _types_module:
                return

            cfg = _config_module.get_config()
            api_key = cfg.get("gemini_api_key", "")
            if not api_key:
                return

            model = cfg.get("crash_auditor_model", "gemini-2.5-flash")
            api_ver = getattr(_config_module, "GEMINI_API_VERSION", "v1beta")
            
            client = _genai_module.Client(
                api_key=api_key,
                http_options={"api_version": api_ver}
            )
            image_part = _types_module.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            
            prompt = (
                f"You are {AUDITOR_NAME}. "
                "Look at this screenshot of a developer environment. "
                "Determine if there is an active compiler error, exception traceback, runtime crash, command error, or failed test displayed on screen. "
                "If there is NO active error or crash, reply ONLY 'NO_ERROR'. "
                "If there IS an error or crash, reply in maximum 2 clear sentences describing the error and how to fix it."
            )

            response = client.models.generate_content(
                model=model,
                contents=[image_part, prompt]
            )
            
            result_text = response.text.strip()
            
            if "NO_ERROR" not in result_text:
                self.log(f"⚠️ DETECTED ERROR ON SCREEN: {result_text}")
                
                # Speak out loud
                if _main_module:
                    sat = _main_module.get_saturday()
                    if sat:
                        sat.speak(f"Heads up sir, I noticed an error on your screen: {result_text}")
        except Exception as e:
            self.log(f"Failed to audit screen: {e}")

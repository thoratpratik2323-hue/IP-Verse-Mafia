import threading
import time
import logging

logger = logging.getLogger("saturday.vision_guard")

class VisionGuard:
    def __init__(self, interval_seconds: int = None):
        if interval_seconds is None:
            try:
                from config import get_config
                interval_seconds = get_config().get("vision_guard_interval", 1200)
            except Exception:
                interval_seconds = 1200
                
        self.interval = interval_seconds
        self._thread = None
        self._stop_event = threading.Event()
        self._last_alert_time = 0.0
        self._snooze_until = 0.0
        self._lock = threading.Lock()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        with self._lock:
            self._last_alert_time = time.time()
            self._snooze_until = 0.0
        self._thread = threading.Thread(target=self._loop, daemon=True, name="VisionGuardThread")
        self._thread.start()
        logger.info("Vision Guard background thread started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("Vision Guard background thread stopped.")

    def _loop(self):
        # Give system time to settle on startup
        self._stop_event.wait(15.0)
        
        while not self._stop_event.is_set():
            with self._lock:
                now = time.time()
                # If snoozed, wait until snooze expires, otherwise wait until next alert interval
                target = self._snooze_until if self._snooze_until > now else self._last_alert_time + self.interval
                remaining = target - now
                
            if remaining <= 0:
                self._trigger_alert()
                with self._lock:
                    self._last_alert_time = time.time()
                    self._snooze_until = 0.0  # Reset snooze
                continue
                
            # Wait for remaining time or 10s (whichever is smaller) to respond quickly to stops
            self._stop_event.wait(min(10.0, remaining))

    def snooze(self, minutes: int = 20):
        with self._lock:
            self._snooze_until = time.time() + (minutes * 60)
        logger.info("Vision Guard alerts snoozed for %d minutes.", minutes)

    def _trigger_alert(self):
        try:
            import ui
            ui_inst = ui.get_ui()
            
            enabled = True
            voice_enabled = False
            
            if ui_inst and ui_inst._win:
                enabled = getattr(ui_inst._win, "_vg_enabled", True)
                voice_enabled = getattr(ui_inst._win, "_vg_voice_enabled", False)
                
            if not enabled:
                logger.info("Vision Guard alert skipped: disabled in UI settings.")
                return

            if ui_inst and ui_inst._win:
                if hasattr(ui_inst._win, "_vision_guard_sig"):
                    ui_inst._win._vision_guard_sig.emit()
            
            if voice_enabled:
                import main
                sat = main.get_saturday()
                if sat and hasattr(sat, "speak"):
                    # Speak in Devanagari script for natural TTS synthesis
                    sat.speak("प्रतीक सर, आपने 20 मिनट काम कर लिया है। कृपया 20 फीट दूर किसी वस्तु को 20 सेकंड के लिए देखें ताकि आँखों को आराम मिल सके।")
        except Exception as e:
            logger.error("Failed to trigger Vision Guard alert: %s", e)

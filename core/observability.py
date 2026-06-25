import time
import json
import logging
from threading import Lock

logger = logging.getLogger("saturday.core.observability")

class ThoughtTracker:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(ThoughtTracker, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.lock = Lock()
        self.current_thoughts = []
        self.active_thought = None
        self.start_time = 0.0

    def clear(self):
        with self.lock:
            self.current_thoughts = []
            self.active_thought = None
            self.start_time = time.time()

    def start_thought(self, label: str):
        with self.lock:
            self.active_thought = {
                "step": label,
                "start_time": time.time(),
                "elapsed_ms": 0,
                "status": "Running..."
            }
            self.current_thoughts.append(self.active_thought)

    def add_step(self, description: str):
        with self.lock:
            if self.active_thought:
                self.active_thought["status"] = description
                self.active_thought["elapsed_ms"] = int((time.time() - self.active_thought["start_time"]) * 1000)

    def end_thought(self, status: str = "Done"):
        with self.lock:
            if self.active_thought:
                self.active_thought["status"] = status
                self.active_thought["elapsed_ms"] = int((time.time() - self.active_thought["start_time"]) * 1000)
                self.active_thought = None

    def get_thoughts(self) -> list:
        with self.lock:
            return list(self.current_thoughts)

    def get_summary_text(self) -> str:
        with self.lock:
            lines = []
            for t in self.current_thoughts:
                ms = t["elapsed_ms"]
                status = t["status"]
                lines.append(f"• {t['step']} ({ms}ms) -> {status}")
            return "\n".join(lines)

    def save_to_file(self):
        try:
            from pathlib import Path
            log_path = Path(__file__).resolve().parent.parent / "data" / "reasoning_trace.json"
            log_path.parent.mkdir(exist_ok=True)
            with self.lock:
                log_path.write_text(json.dumps(self.current_thoughts, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to save thought trace: %s", e)

thought_tracker = ThoughtTracker()

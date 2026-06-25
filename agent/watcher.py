import threading
import time
import datetime

class ProactiveWatcher:
    def __init__(self, speak_func):
        self.speak = speak_func
        self.reminders = []
        self.running = False

    def add_reminder(self, message: str, at_time: str):
        # at_time format: "HH:MM"
        self.reminders.append({"msg": message, "time": at_time, "done": False})

    def start(self):
        self.running = True
        t = threading.Thread(target=self._loop, daemon=True, name="SaturdayProactiveWatcher")
        t.start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            now = datetime.datetime.now().strftime("%H:%M")
            for r in self.reminders:
                if r["time"] == now and not r["done"]:
                    self.speak(r["msg"])
                    r["done"] = True
            time.sleep(30)  # check every 30 seconds

"""
wake_word.py — Listen loop checking audio frequencies for assistant wake words.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/wake_word.py
import time
import threading
import speech_recognition as sr

class WakeWordSpotterThread(threading.Thread):
    """Background thread that listens for trigger words when the assistant is muted."""
    def __init__(self, on_wake_callback, ui=None):
        super().__init__(name="WakeWordSpotterThread", daemon=True)
        self.on_wake_callback = on_wake_callback
        self.ui = ui
        self._stop_event = threading.Event()
        self._running = False
        
        # Keywords list
        self.keywords = ["prime", "ip prime", "buddy", "bro", "yoo", "okay boss", "suno", "wake up"]
        
    def stop(self):
        self._stop_event.set()
        self._running = False
        
    def pause_listening(self):
        if self._running:
            print("[WakeWord] Paused spotter (mic in use by Live Stream).")
            self._running = False
            
    def resume_listening(self):
        if not self._running and not self._stop_event.is_set():
            print("[WakeWord] Resumed spotter (waiting for trigger...).")
            self._running = True

    def run(self):
        print("[WakeWord] Always-on Wake Word spotter initialized.")
        r = sr.Recognizer()
        r.energy_threshold = 1200  # adjust sensitivity
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.5
        
        # Calibrate once at startup to save massive CPU cycles in loop!
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.8)
        except Exception as e:
            print(f"[WakeWord] Ambient noise calibration failed at startup: {e}")
        
        # Start in listening state
        self._running = True
        
        while not self._stop_event.is_set():
            if not self._running:
                time.sleep(0.5)
                continue
                
            try:
                with sr.Microphone() as source:
                    if not self._running or self._stop_event.is_set():
                        continue
                        
                    print("[WakeWord] Listening for trigger phrase...")
                    # Listen with 0.8s timeout to quickly release the mic lock when paused
                    audio = r.listen(source, timeout=0.8, phrase_time_limit=2.0)
                    
                if not self._running or self._stop_event.is_set():
                    continue
                    
                # Spot check via Sphinx (offline) or Google Recognizer (fast fallback)
                # We use Google Recognizer which is incredibly fast and requires no complex local models
                try:
                    text = r.recognize_google(audio, language="en-US").lower().strip()
                    print(f"[WakeWord] Heard: \"{text}\"")
                    
                    if any(kw in text for kw in self.keywords):
                        print(f"[WakeWord] Keyword spotted in: \"{text}\"!")
                        if self.on_wake_callback:
                            self.on_wake_callback()
                            # Pause self temporarily to let live stream take over
                            self.pause_listening()
                except sr.UnknownValueError:
                    pass  # normal, could not understand quiet sounds
                except sr.RequestError:
                    pass  # connection issue, fallback quietly
                    
            except sr.WaitTimeoutError:
                pass  # normal timeout, loop back
            except Exception:
                # Catch generic errors (like mic occupied) and back off gracefully
                time.sleep(2.0)

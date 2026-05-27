"""Hand motion & gesture control (Jarvis-GUI style) via webcam."""
from __future__ import annotations

import json
import threading
import time

from prime_platform.config import BASE_DIR, load_prime_config, save_prime_config

_STATE_PATH = BASE_DIR / "memory" / "gesture_state.json"
_lock = threading.Lock()
_service: "GestureService | None" = None


class GestureService:
  """Background webcam gesture detector. Uses MediaPipe Hands when available, else motion zones."""

  GESTURES = (
      "open_palm",    # 4+ fingers — wake / unmute
      "fist",         # mute
      "point_up",     # index only — focus listen
      "swipe_left",   # volume down
      "swipe_right",  # volume up
      "pinch",        # left click
      "wave",         # motion burst — ping log
  )

  def __init__(self):
      self._running = False
      self._thread: threading.Thread | None = None
      self._player = None
      self._last_gesture = ""
      self._last_gesture_t = 0.0
      self._cooldown = 1.2
      self._prev_wrist_x: float | None = None
      self._motion_history: list[float] = []

  def start(self, player=None, camera_index: int = 0) -> str:
      if self._running:
          return "Gesture control is already running."
      self._player = player
      self._running = True
      self._thread = threading.Thread(
          target=self._loop,
          args=(camera_index,),
          daemon=True,
          name="IPPrime-Gesture",
      )
      self._thread.start()
      self._save_state(running=True)
      self._log("Gesture control started — show open palm to wake, fist to mute.")
      return (
          "Gesture control ONLINE.\n"
          "  Open palm (4+ fingers) → wake / listening\n"
          "  Fist → mute\n"
          "  Point up → focus mode ping\n"
          "  Swipe L/R → volume down/up\n"
          "  Pinch → mouse click\n"
          "Install mediapipe for best accuracy: pip install mediapipe"
      )

  def stop(self) -> str:
      self._running = False
      self._save_state(running=False)
      self._log("Gesture control stopped.")
      return "Gesture control stopped."

  def status(self) -> str:
      cfg = load_prime_config().get("gesture_control", {})
      mp = _mediapipe_available()
      lines = [
          "═══ GESTURE CONTROL ═══",
          f"  Running: {self._running}",
          f"  MediaPipe hands: {'yes' if mp else 'no (using motion fallback)'}",
          f"  Camera index: {cfg.get('camera_index', 0)}",
          f"  Cooldown: {cfg.get('cooldown_sec', 1.2)}s",
          f"  Last gesture: {self._last_gesture or 'none'}",
      ]
      return "\n".join(lines)

  def _log(self, msg: str) -> None:
      try:
          if self._player and hasattr(self._player, "write_log"):
              self._player.write_log(f"GESTURE: {msg}")
      except Exception:
          pass
      print(f"[Gesture] {msg}")

  def _save_state(self, running: bool) -> None:
      try:
          _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
          _STATE_PATH.write_text(
              json.dumps({"running": running, "ts": time.time()}, indent=2),
              encoding="utf-8",
          )
      except Exception:
          pass

  def _emit(self, gesture: str) -> None:
      now = time.time()
      if gesture == self._last_gesture and now - self._last_gesture_t < self._cooldown:
          return
      self._last_gesture = gesture
      self._last_gesture_t = now
      self._log(f"Detected → {gesture}")
      try:
          self._handle_gesture(gesture)
      except Exception as e:
          self._log(f"Handler error: {e}")

  def _handle_gesture(self, gesture: str) -> None:
      win = getattr(self._player, "_win", None) if self._player else None
      ip = getattr(win, "ip_ray", None) if win else None

      if gesture == "open_palm":
          if self._player is not None:
              self._player.muted = False
          if ip:
              ip._wake_active = True
              ip._wake_timer = time.time()
          if win:
              win._state_sig.emit("LISTENING")

      elif gesture == "fist":
          if self._player is not None:
              self._player.muted = True
          elif win:
              win._muted = True
              win.hud.muted = True
              win._state_sig.emit("MUTED")

      elif gesture == "point_up":
          if win:
              win._state_sig.emit("LISTENING")
          self._log("Listen mode — say Prime")

      elif gesture in ("swipe_left", "swipe_right"):
          from actions.computer_settings import computer_settings
          delta = "down" if gesture == "swipe_left" else "up"
          computer_settings(
              parameters={"action": "volume", "description": f"volume {delta}", "value": delta},
              player=self._player,
          )

      elif gesture == "pinch":
          try:
              import pyautogui
              pyautogui.click()
          except Exception:
              pass

      elif gesture == "wave":
          self._log("Wave detected — IP Prime ready.")

  def _loop(self, camera_index: int) -> None:
      try:
          import cv2
      except ImportError:
          self._running = False
          self._log("opencv-python required: pip install opencv-python")
          return

      cfg = load_prime_config().get("gesture_control", {})
      self._cooldown = float(cfg.get("cooldown_sec", 1.2))
      use_mp = _mediapipe_available() and cfg.get("use_mediapipe", True)

      cap = cv2.VideoCapture(camera_index)
      if not cap.isOpened():
          self._running = False
          self._log(f"Cannot open camera {camera_index}")
          return

      hands = _HandTracker() if use_mp else None
      bg = cv2.createBackgroundSubtractorMOG2(history=120, varThreshold=40)

      while self._running:
          ok, frame = cap.read()
          if not ok:
              time.sleep(0.05)
              continue
          frame = cv2.flip(frame, 1)
          h, w = frame.shape[:2]

          if hands:
              g = hands.classify(frame)
              if g:
                  self._emit(g)
          else:
              gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
              fg = bg.apply(gray)
              motion = cv2.countNonZero(fg) / float(w * h)
              self._motion_history.append(motion)
              if len(self._motion_history) > 8:
                  self._motion_history.pop(0)
              if motion > 0.08 and sum(self._motion_history) > 0.35:
                  self._emit("wave")
                  self._motion_history.clear()
              # Wrist proxy: center of motion blob
              M = cv2.moments(fg)
              if M["m00"] > 5000:
                  cx = M["m10"] / M["m00"]
                  if self._prev_wrist_x is not None:
                      dx = cx - self._prev_wrist_x
                      if abs(dx) > w * 0.12:
                          self._emit("swipe_right" if dx > 0 else "swipe_left")
                  self._prev_wrist_x = cx

          time.sleep(0.03)

      cap.release()

  @classmethod
  def instance(cls) -> "GestureService":
      global _service
      if _service is None:
          _service = cls()
      return _service


class _HandTracker:
  def __init__(self):
      import mediapipe as mp
      self._hands = mp.solutions.hands.Hands(
          static_image_mode=False,
          max_num_hands=1,
          min_detection_confidence=0.6,
          min_tracking_confidence=0.5,
      )

  def classify(self, frame) -> str | None:
      import cv2
      rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
      res = self._hands.process(rgb)
      if not res.multi_hand_landmarks:
          return None
      lm = res.multi_hand_landmarks[0].landmark
      tips = [4, 8, 12, 16, 20]
      pip = [3, 6, 10, 14, 18]
      extended = []
      for tip, pip_i in zip(tips, pip):
          extended.append(lm[tip].y < lm[pip_i].y)
      count = sum(extended[1:])  # exclude thumb for simplicity
      thumb_ext = extended[0]
      # Pinch: thumb tip near index tip
      dx = lm[4].x - lm[8].x
      dy = lm[4].y - lm[8].y
      if (dx * dx + dy * dy) ** 0.5 < 0.05:
          return "pinch"
      if count >= 4:
          return "open_palm"
      if count == 0 and not thumb_ext:
          return "fist"
      if count == 1 and extended[1]:
          return "point_up"
      return None


def _mediapipe_available() -> bool:
  try:
      import importlib.util
      return importlib.util.find_spec("mediapipe") is not None
  except Exception:
      return False


def gesture_control(action: str = "status", player=None, camera_index: int | None = None) -> str:
  svc = GestureService.instance()
  action = (action or "status").lower()
  if action in ("start", "on", "enable"):
      idx = camera_index
      if idx is None:
          idx = int(load_prime_config().get("gesture_control", {}).get("camera_index", 0))
      return svc.start(player=player, camera_index=idx)
  if action in ("stop", "off", "disable"):
      return svc.stop()
  return svc.status()


def configure_gesture(use_mediapipe: bool | None = None, cooldown_sec: float | None = None, camera_index: int | None = None) -> str:
  cfg = load_prime_config()
  gc = cfg.setdefault("gesture_control", {
      "enabled": False,
      "use_mediapipe": True,
      "cooldown_sec": 1.2,
      "camera_index": 0,
  })
  if use_mediapipe is not None:
      gc["use_mediapipe"] = bool(use_mediapipe)
  if cooldown_sec is not None:
      gc["cooldown_sec"] = float(cooldown_sec)
  if camera_index is not None:
      gc["camera_index"] = int(camera_index)
  save_prime_config(cfg)
  return GestureService.instance().status()

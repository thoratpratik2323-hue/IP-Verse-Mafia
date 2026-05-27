"""
screen_overlay.py — Glassmorphic PyQT overlay displaying active speaking hud notifications.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/screen_overlay.py
import sys
import io
import re
import json
import asyncio
import threading
import time
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QMouseEvent

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    from PIL import Image
    _PIL = True
except ImportError:
    _PIL = False

from google import genai
from google.genai import types as gtypes

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _base_dir()

def _get_api_key() -> str:
    cfg_path = BASE_DIR / "config" / "api_keys.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            return cfg.get("vision_api_key") or cfg.get("coding_api_key") or cfg.get("gemini_api_key", "")
        except Exception:
            pass
    return ""

def _capture_screen() -> bytes:
    if not _MSS:
        raise RuntimeError("mss is not installed.")
    with mss.mss() as sct:
        monitors = sct.monitors
        target = monitors[1] if len(monitors) > 1 else monitors[0]
        shot = sct.grab(target)
        png = mss.tools.to_png(shot.rgb, shot.size)
        return png

class HighlightOverlay(QWidget):
    """Pulsing neon-colored concentric rings centered around a coordinate (x, y)"""
    def __init__(self, x: int, y: int, duration: float = 3.0, color_name: str = "cyan", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        
        self.target_x = x
        self.target_y = y
        self.color_name = color_name.lower().strip()
        self.duration = duration
        
        self.win_size = 300
        self.setGeometry(
            int(x - self.win_size / 2),
            int(y - self.win_size / 2),
            self.win_size,
            self.win_size
        )
        
        self.tick = 0
        self.max_ticks = int(duration * 60) # ~60 FPS
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)
        self.timer.start(16)
        
    def _step(self):
        self.tick += 1
        if self.tick >= self.max_ticks:
            self.timer.stop()
            self.close()
        self.update()
        
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = self.width() / 2, self.height() / 2
        
        c_map = {
            "cyan": QColor(6, 182, 212),
            "red": QColor(239, 68, 68),
            "green": QColor(16, 185, 129),
            "purple": QColor(139, 92, 246),
            "blue": QColor(59, 130, 246),
            "gold": QColor(253, 224, 71)
        }
        base_color = c_map.get(self.color_name, QColor(6, 182, 212))
        
        progress = self.tick / self.max_ticks
        pulse_val = (self.tick % 50) / 50.0
        
        # Concentric rings
        for i in range(3):
            scale = (pulse_val + i * 0.33) % 1.0
            r = 18 + scale * 90
            opacity = int(230 * (1.0 - scale) * (1.0 - progress))
            
            pen_c = QColor(base_color)
            pen_c.setAlpha(opacity)
            
            p.setPen(QPen(pen_c, 2.5 - scale, Qt.PenStyle.SolidLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)
            
        # Target crosshair ticks
        cross_c = QColor(base_color)
        cross_c.setAlpha(int(255 * (1.0 - progress)))
        p.setPen(QPen(cross_c, 2))
        
        p.drawLine(int(cx - 15), int(cy), int(cx - 6), int(cy))
        p.drawLine(int(cx + 6), int(cy), int(cx + 15), int(cy))
        p.drawLine(int(cx), int(cy - 15), int(cx), int(cy - 6))
        p.drawLine(int(cx), int(cy + 6), int(cx), int(cy + 15))


class TranslationCardOverlay(QWidget):
    """Frosted glass overlay mask spanning full screen that draws dynamic translation overlay blocks."""
    def __init__(self, items: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        
        self.items = items # list of dicts with: {"text": str, "translation": str, "x": int, "y": int, "w": int, "h": int}
        
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        W, H = self.width(), self.height()
        
        # 1. Dark frosted semi-transparent backdrop
        p.setBrush(QBrush(QColor(3, 7, 18, 160)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, W, H)
        
        # 2. Render each translation card in-place over coordinates
        for idx, item in enumerate(self.items):
            x, y = item["x"], item["y"]
            w, h = item["w"], item["h"]
            orig = item["text"]
            trans = item["translation"]
            
            # Card bounds
            card_w = max(180, w + 30)
            card_h = max(70, h + 30)
            card_x = max(10, min(W - card_w - 10, x - 15))
            card_y = max(10, min(H - card_h - 10, y - 15))
            
            # Frosted glass background
            grad = QLinearGradient(card_x, card_y, card_x + card_w, card_y + card_h)
            grad.setColorAt(0.0, QColor(15, 23, 42, 230))
            grad.setColorAt(1.0, QColor(30, 41, 59, 210))
            
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(6, 182, 212, 130), 1.2)) # Cyan border highlight
            p.drawRoundedRect(QRectF(card_x, card_y, card_w, card_h), 8.0, 8.0)
            
            # Text layout
            p.setFont(QFont("Segoe UI Semibold", 8))
            p.setPen(QColor(148, 163, 184)) # Slate muted for original
            orig_truncated = orig[:30] + ("..." if len(orig) > 30 else "")
            p.drawText(QRectF(card_x + 10, card_y + 8, card_w - 20, 18), Qt.AlignmentFlag.AlignLeft, f"Orig: {orig_truncated}")
            
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.setPen(QColor(248, 250, 252)) # Crisp white for translation
            p.drawText(QRectF(card_x + 10, card_y + 26, card_w - 20, card_h - 32), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.TextWordWrap, trans)
            
        # 3. Help Pill at Top Center
        pill_w = 400
        pill_h = 32
        pill_x = (W - pill_w) / 2
        pill_y = 20
        p.setBrush(QBrush(QColor(15, 23, 42, 240)))
        p.setPen(QPen(QColor(139, 92, 246, 180), 1.5)) # Neon purple border
        p.drawRoundedRect(QRectF(pill_x, pill_y, pill_w, pill_h), 16.0, 16.0)
        
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(248, 250, 252))
        p.drawText(QRectF(pill_x, pill_y, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter, "✨ TRANSLATION HUD  ·  CLICK ANYWHERE TO CLOSE")

    def mousePressEvent(self, _: QMouseEvent):
        # Dismiss on click
        self.close()


def pulse_overlay(x: int, y: int, duration: float = 3.0, color: str = "cyan") -> str:
    """Trigger a pulsing concentric highlight at the given coordinate on the main thread."""
    try:
        app = QApplication.instance()
        if not app:
            return "Application not running."
        # Create and show overlay safely on UI thread
        def _trigger():
            widget = HighlightOverlay(x, y, duration, color)
            # Store a reference in the app object to prevent garbage collection
            if not hasattr(app, "_active_overlays"):
                app._active_overlays = []
            app._active_overlays.append(widget)
            widget.show()
            # Clean up reference when closed
            widget.destroyed.connect(lambda: app._active_overlays.remove(widget) if widget in app._active_overlays else None)
            
        QTimer.singleShot(0, _trigger)
        return f"Highlight triggered at ({x}, {y})"
    except Exception as e:
        return f"Error triggering highlight: {e}"


def run_ocr_translation_in_background(target_lang: str = "English", callback_signal=None) -> str:
    """Takes a screenshot, calls Gemini Vision to get translated blocks and coordinates, and returns items."""
    api_key = _get_api_key()
    if not api_key:
        return "Gemini API key not found in configurations, sir."
        
    try:
        png_bytes = _capture_screen()
        # Resize image for fast transmission
        if _PIL:
            img = Image.open(io.BytesIO(png_bytes))
            phys_w, phys_h = img.width, img.height
            # Downscale if extremely large
            if phys_w > 1920:
                img = img.resize((1920, int(phys_h * (1920 / phys_w))), Image.Resampling.BILINEAR)
                phys_w, phys_h = img.width, img.height
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                png_bytes = buf.getvalue()
        else:
            phys_w, phys_h = 1920, 1080 # fallback logical bounds
            
        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Locate all visible text blocks on the screen that are NOT in {target_lang}. "
            f"Translate them to {target_lang}. "
            f"For each text block, you MUST return its bounding box coordinates relative to the screen dimensions: "
            f"left, top, width, height in physical pixel scale (where the full image dimensions are exactly {phys_w}x{phys_h} pixels).\n"
            f"Return ONLY valid JSON in a list format, like this (no markdown, no triple backticks):\n"
            f'[\n'
            f'  {{"text": "Bonjour", "translation": "Hello", "x": 100, "y": 200, "w": 80, "h": 30}}\n'
            f']'
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                gtypes.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                prompt,
            ],
        )
        
        text = (response.text or "").strip()
        # Clean markdown wrappers if any
        text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
        text = re.sub(r"\r?\n?```\s*$", "", text)
        text = text.strip()
        
        items = json.loads(text)
        if not isinstance(items, list):
            items = [items]
            
        print(f"[TranslationHUD] Extracted {len(items)} text blocks successfully.")
        
        if callback_signal:
            callback_signal.emit(items)
            
        return f"Successfully translated {len(items)} text blocks to {target_lang}."
        
    except Exception as e:
        print(f"[TranslationHUD] OCR Grounding failure: {e}")
        return f"OCR Translation failed: {e}"

"""
screen_translator.py — Capture screen region, OCR translate using Gemini, and show floating glassmorphic overlay.

Standard action module for the IP Prime suite (Phase 4).
"""

import io
import json
import logging
from pathlib import Path
from PIL import Image

from PyQt6.QtCore import Qt, QRect, QSize, QPoint, QBuffer, QIODevice, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QFont, QCursor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QRubberBand, QDialog, QVBoxLayout, 
    QHBoxLayout, QTextBrowser, QPushButton, QLabel
)

logger = logging.getLogger("ip_prime.screen_translator")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "api_keys.json"

def _get_gemini_client():
    try:
        from core.session import _get_api_key
        from google import genai
        key = _get_api_key()
        if not key:
            # Fallback direct read
            if CONFIG_FILE.exists():
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                key = data.get("gemini_api_key", "")
        if key:
            return genai.Client(api_key=key)
    except Exception as e:
        logger.error("Failed to get Gemini client: %s", e)
    return None

class SnippingWidget(QWidget):
    def __init__(self, pixmap, callback):
        super().__init__()
        self.pixmap = pixmap
        self.callback = callback
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.origin = None
        self.rubberband = None

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw base screen grab
        painter.drawPixmap(0, 0, self.pixmap)
        # Draw dim dark overlay
        painter.fillRect(self.rect(), QColor(10, 15, 30, 110))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.position().toPoint()
            if not self.rubberband:
                self.rubberband = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self.rubberband.setGeometry(QRect(self.origin, QSize()))
            self.rubberband.show()

    def mouseMoveEvent(self, event):
        if self.origin and self.rubberband:
            self.rubberband.setGeometry(QRect(self.origin, event.position().toPoint()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.origin:
            self.rubberband.hide()
            rect = QRect(self.origin, event.position().toPoint()).normalized()
            self.close()
            if rect.width() > 8 and rect.height() > 8:
                cropped = self.pixmap.copy(rect)
                self.callback(cropped, rect)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

class TranslationOverlay(QDialog):
    def __init__(self, text, rect, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(420, 260)
        
        # Position overlay near the selected area, bounded inside screen
        screen_geom = QApplication.primaryScreen().geometry()
        x = rect.x() + (rect.width() - 420) // 2
        y = rect.y() + rect.height() + 15
        
        # Keep inside bounds
        x = max(20, min(x, screen_geom.width() - 440))
        if y + 260 > screen_geom.height():
            y = max(20, rect.y() - 275)
            
        self.move(x, y)
        self.init_ui(text)

        # Allow dragging the dialog
        self._drag_pos = QPoint()

    def init_ui(self, text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 15)
        layout.setSpacing(10)

        # Glassmorphic container frame
        self.container = QWidget(self)
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background: rgba(15, 23, 42, 0.94);
                border: 1.5px solid rgba(6, 182, 212, 0.45);
                border-radius: 18px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(12)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_lbl = QLabel("🌐 LIVE TRANSLATION HUD", self.container)
        title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #06B6D4; letter-spacing: 0.5px; background: transparent;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        close_btn = QPushButton("✕", self.container)
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: none;
                border-radius: 13px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #EF4444;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        container_layout.addLayout(header_layout)

        # Text display
        self.text_browser = QTextBrowser(self.container)
        self.text_browser.setFont(QFont("Segoe UI", 9))
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background: rgba(30, 41, 59, 0.45);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.text_browser.setMarkdown(text)
        container_layout.addWidget(self.text_browser)

        layout.addWidget(self.container)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

class TranslatorManager(QObject):
    translation_ready = pyqtSignal(str, QRect)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def trigger_snip(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.error_occurred.emit("Screen capture failed — no screen detected.")
            return

        # Take screen snapshot
        pixmap = screen.grabWindow(0)
        
        # Show snip overlay widget
        self.snip_widget = SnippingWidget(pixmap, self.on_region_selected)
        self.snip_widget.show()

    def on_region_selected(self, pixmap, rect):
        # Run OCR + Gemini in background thread
        import threading
        threading.Thread(target=self._run_gemini_ocr, args=(pixmap, rect), daemon=True).start()

    def _run_gemini_ocr(self, pixmap, rect):
        try:
            client = _get_gemini_client()
            if not client:
                self.error_occurred.emit("Gemini client key missing or invalid in config.")
                return

            # Save Pixmap to PIL Image via memory buffer
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            pixmap.save(buffer, "PNG")
            
            pil_img = Image.open(io.BytesIO(buffer.data().data()))

            # Call Gemini Live / standard endpoint for multimodal analysis
            prompt = (
                "Translate and OCR the content of this image region.\n"
                "Provide the OCR parsed original text, then translate it to both English and Hinglish buddy conversational tone.\n"
                "Format beautifully in markdown style like this:\n"
                "**Original Text:** ...\n\n"
                "**English Translation:** ...\n\n"
                "**Hinglish / Buddy Note:** ..."
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[pil_img, prompt]
            )

            result = response.text or "No text could be extracted or translated."
            self.translation_ready.emit(result, rect)

        except Exception as e:
            logger.error("Gemini OCR screen translation failed: %s", e)
            self.error_occurred.emit(f"OCR Translation failed: {e}")

# Global instance manager to coordinate HUD overlays
_manager_instance = None

def start_screen_translation(ui=None):
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = TranslatorManager()
        
        def handle_success(text, rect):
            # Spawn beautiful floating overlay dialog
            parent_win = getattr(ui, "_win", None) if ui else None
            overlay = TranslationOverlay(text, rect, parent_win)
            overlay.show()
            if ui and hasattr(ui, "write_log"):
                ui.write_log("✨ Live Translation HUD displayed successfully.")

        def handle_error(err):
            if ui and hasattr(ui, "write_log"):
                ui.write_log(f"❌ Screen Translation error: {err}")
                
            ip_ray = getattr(ui, "ip_ray", None) or getattr(getattr(ui, "_win", None), "ip_ray", None)
            if ip_ray and hasattr(ip_ray, "speak"):
                ip_ray.speak("Sorry sir, screen translation me error aaya.")

        _manager_instance.translation_ready.connect(handle_success)
        _manager_instance.error_occurred.connect(handle_error)

    if ui and hasattr(ui, "write_log"):
        ui.write_log("⚡ Snipping Tool active. Drag mouse across screen region to translate.")
        
    ip_ray = getattr(ui, "ip_ray", None) or getattr(getattr(ui, "_win", None), "ip_ray", None)
    if ip_ray and hasattr(ip_ray, "speak"):
        ip_ray.speak("Scanning screen, please select the region you want to translate, bhai.")

    _manager_instance.trigger_snip()

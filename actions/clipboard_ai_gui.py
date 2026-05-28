import sys
import threading
import pyperclip
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from google import genai

class ClipboardAIPanel(QDialog):
    explanation_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(450, 350)
        self.explanation_ready.connect(self._on_explanation_ready)
        self._init_ui()

    def _init_ui(self):
        container = QWidget(self)
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container {
                background: rgba(15, 23, 42, 0.95);
                border: 2px solid rgba(16, 185, 129, 0.4);
                border-radius: 18px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Title block
        title_lay = QHBoxLayout()
        title_lbl = QLabel("CLIPBOARD AI ASSISTANT 📋")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #10B981; letter-spacing: 0.5px; background: transparent;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.3);
                border: 1px solid #EF4444;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        title_lay.addWidget(title_lbl)
        title_lay.addStretch()
        title_lay.addWidget(close_btn)
        layout.addLayout(title_lay)

        # Content area
        self.text_area = QTextBrowser()
        self.text_area.setStyleSheet("""
            QTextBrowser {
                background: rgba(5, 5, 10, 0.6);
                border: 1px solid rgba(16, 185, 129, 0.15);
                border-radius: 10px;
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                line-height: 1.4;
                padding: 8px;
            }
        """)
        self.text_area.setHtml("<i style='color:#94A3B8;'>Fetching explanation... Please wait, bhai!</i>")
        layout.addWidget(self.text_area)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def trigger_explanation(self):
        clip_content = pyperclip.paste()
        if not clip_content or clip_content.isspace():
            self.text_area.setHtml("<span style='color:#EF4444;'>Clipboard empty hai, sir! Kuch text copy kijiye pehle.</span>")
            return
        
        self.text_area.setHtml("<i style='color:#10B981;'>Clipboard content analyze ho raha hai...</i>")
        threading.Thread(target=self._fetch_explanation_bg, args=(clip_content,), daemon=True).start()

    def _fetch_explanation_bg(self, content):
        try:
            # We must use gemini-2.5-flash for the SDK
            # Since embedding quota is hit, the standard Live or Text generation works
            # Let's import the api key getter
            from main import _get_api_key
            client = genai.Client(api_key=_get_api_key())
            
            prompt = (
                f"Explain the following clipboard text/code in brief, friendly Hinglish. "
                f"Be concise and clear. Highlight key details.\n\nClipboard content:\n{content}"
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            self.explanation_ready.emit(response.text)
        except Exception as e:
            self.explanation_ready.emit(f"AI explaining failed: {e}")

    def _on_explanation_ready(self, text):
        # format simple markdown or newline to html
        formatted = text.replace("\n", "<br>")
        self.text_area.setHtml(f"<div style='font-family:sans-serif;'>{formatted}</div>")
        
        # also notify / speak if possible
        parent = self.parent()
        if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
            parent.ip_ray.speak("Clipboard content explain kar diya hai, bhai!")

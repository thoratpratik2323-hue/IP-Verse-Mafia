import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from actions.morning_briefer import generate_briefing

class BriefingPanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(500, 600)
        self._init_ui()

    def _init_ui(self):
        # Main glassmorphic container
        container = QWidget(self)
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container {
                background: rgba(10, 15, 30, 0.92);
                border: 2px solid rgba(245, 158, 11, 0.4);
                border-radius: 18px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title block
        title_lay = QHBoxLayout()
        title_lbl = QLabel("DAILY BRIEFING 🌅")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #F59E0B; letter-spacing: 1px; background: transparent;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 15px;
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
                border: 1px solid rgba(245, 158, 11, 0.15);
                border-radius: 10px;
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                line-height: 1.5;
                padding: 10px;
            }
        """)
        layout.addWidget(self.text_area)

        # Speak Button
        speak_btn = QPushButton("🗣 SPEAK BRIEFING")
        speak_btn.setFixedHeight(40)
        speak_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        speak_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        speak_btn.setStyleSheet("""
            QPushButton {
                background: rgba(245, 158, 11, 0.15);
                color: #F59E0B;
                border: 1px solid rgba(245, 158, 11, 0.4);
                border-radius: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: rgba(245, 158, 11, 0.3);
                border: 1px solid #F59E0B;
            }
        """)
        speak_btn.clicked.connect(self._speak_briefing)
        layout.addWidget(speak_btn)

        # Full layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def refresh(self):
        try:
            brief = generate_briefing(self.parent())
            self.text_area.setHtml(self._format_briefing_html(brief))
        except Exception as e:
            self.text_area.setText(f"Briefing load error: {e}")

    def _format_briefing_html(self, text: str) -> str:
        # Format text to HTML beautifully
        html = text.replace("\n", "<br>")
        html = html.replace("[WEATHER]", "<strong style='color:#38BDF8;'>[WEATHER]</strong>")
        html = html.replace("[SYSTEM]", "<strong style='color:#A855F7;'>[SYSTEM]</strong>")
        html = html.replace("[TASKS]", "<strong style='color:#10B981;'>[TASKS]</strong>")
        html = html.replace("[WARNING]", "<strong style='color:#EF4444;'>[WARNING]</strong>")
        html = html.replace("[NEWS]", "<strong style='color:#F59E0B;'>[NEWS]</strong>")
        html = html.replace("[MOTIVATION]", "<strong style='color:#EC4899;'>[MOTIVATION]</strong>")
        return f"<div style='font-family:sans-serif;'>{html}</div>"

    def _speak_briefing(self):
        parent = self.parent()
        if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
            try:
                # get briefing plain text
                brief = generate_briefing(parent)
                parent.ip_ray.speak(brief)
            except Exception as e:
                pass
        self.close()

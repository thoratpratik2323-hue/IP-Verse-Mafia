import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QTextBrowser, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from actions.dsa_helper import get_dsa_hints

class DSAPanel(QDialog):
    hints_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(500, 520)
        self.hints_ready.connect(self._on_hints_ready)
        self._init_ui()

    def _init_ui(self):
        container = QWidget(self)
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container {
                background: rgba(15, 23, 42, 0.95);
                border: 2px solid rgba(139, 92, 246, 0.4);
                border-radius: 18px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Title block
        title_lay = QHBoxLayout()
        title_lbl = QLabel("DSA AI MENTOR 💡")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #8B5CF6; letter-spacing: 0.5px; background: transparent;")
        
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

        # Input Area Label
        input_lbl = QLabel("Paste your LeetCode / DSA problem statement:")
        input_lbl.setFont(QFont("Segoe UI", 9))
        input_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        layout.addWidget(input_lbl)

        # Problem Input QTextEdit
        self.problem_input = QTextEdit()
        self.problem_input.setPlaceholderText("Paste problem text here, bhai...")
        self.problem_input.setStyleSheet("""
            QTextEdit {
                background: rgba(5, 5, 10, 0.6);
                border: 1px solid rgba(139, 92, 246, 0.25);
                border-radius: 8px;
                color: #F1F5F9;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                padding: 6px;
            }
        """)
        self.problem_input.setMaximumHeight(100)
        layout.addWidget(self.problem_input)

        # Get Hints Button
        get_btn = QPushButton("GET PROGRESSIVE HINTS")
        get_btn.setFixedHeight(36)
        get_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        get_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        get_btn.setStyleSheet("""
            QPushButton {
                background: rgba(139, 92, 246, 0.15);
                color: #8B5CF6;
                border: 1px solid rgba(139, 92, 246, 0.4);
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: rgba(139, 92, 246, 0.3);
                border: 1px solid #8B5CF6;
            }
        """)
        get_btn.clicked.connect(self._get_hints)
        layout.addWidget(get_btn)

        # Results Browser
        self.results_browser = QTextBrowser()
        self.results_browser.setStyleSheet("""
            QTextBrowser {
                background: rgba(5, 5, 10, 0.6);
                border: 1px solid rgba(139, 92, 246, 0.15);
                border-radius: 10px;
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                line-height: 1.4;
                padding: 10px;
            }
        """)
        self.results_browser.setHtml("<i style='color:#64748B;'>Progressive hints will appear here. No code solutions will be shared.</i>")
        layout.addWidget(self.results_browser)

        # Full layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def _get_hints(self):
        problem = self.problem_input.toPlainText()
        if not problem or problem.isspace():
            self.results_browser.setHtml("<span style='color:#EF4444;'>Pehle problem paste karo, bhai!</span>")
            return
            
        self.results_browser.setHtml("<i style='color:#8B5CF6;'>Analyzing problem and preparing mentoring hints...</i>")
        threading.Thread(target=get_dsa_hints, args=(problem, self.hints_ready.emit), daemon=True).start()

    def _on_hints_ready(self, text):
        formatted = text.replace("\n", "<br>")
        formatted = formatted.replace("Hint 1", "<strong style='color:#8B5CF6;'>Hint 1</strong>")
        formatted = formatted.replace("Hint 2", "<strong style='color:#A78BFA;'>Hint 2</strong>")
        formatted = formatted.replace("Hint 3", "<strong style='color:#C084FC;'>Hint 3</strong>")
        
        self.results_browser.setHtml(f"<div style='font-family:sans-serif;'>{formatted}</div>")
        
        parent = self.parent()
        if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
            parent.ip_ray.speak("Problem check kar li hai bhai, hints ready hain!")

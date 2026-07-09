"""
os_shell/widgets/clipboard_monitor.py — Clipboard AI Monitor.
Polls clipboard every 1.5s. When new text is copied, shows a toast
with AI options: Summarize / Translate / Explain.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QApplication, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont


class ClipboardToast(QWidget):
    """Small toast popup when new text is copied."""
    action_requested = pyqtSignal(str, str)   # (action, text)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 100)
        self._current_text = ""
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self._card = QWidget(self)
        self._card.setGeometry(0, 0, 300, 100)
        self._card.setStyleSheet("""
            QWidget {
                background: rgba(10, 18, 35, 0.95);
                border: 1px solid rgba(6, 182, 212, 0.4);
                border-radius: 14px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(6, 182, 212, 90))
        shadow.setOffset(0, 4)
        self._card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        lbl = QLabel("📋 New text copied — AI can help:")
        lbl.setFont(QFont("Outfit", 9))
        lbl.setStyleSheet("color: rgba(6,182,212,0.85); background: transparent; border: none;")
        header.addWidget(lbl)
        header.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("QPushButton { background:transparent; border:none; color:rgba(255,255,255,0.4); font-size:10px; }"
                                "QPushButton:hover { color:#f87171; }")
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for label, action in [("✨ Summarize", "summarize"), ("🌐 Translate", "translate"), ("💡 Explain", "explain")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Outfit", 9))
            btn.setFixedHeight(26)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(6,182,212,0.15);
                    border: 1px solid rgba(6,182,212,0.3);
                    border-radius: 7px;
                    color: #06b6d4;
                    padding: 0 8px;
                }
                QPushButton:hover { background: rgba(6,182,212,0.28); }
            """)
            btn.clicked.connect(lambda checked, a=action: self._on_action(a))
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

    def _on_action(self, action: str):
        self.hide()
        self.action_requested.emit(action, self._current_text)

    def show_for(self, text: str, parent_rect):
        self._current_text = text
        if parent_rect:
            x = parent_rect.width() - self.width() - 20
            y = parent_rect.height() - self.height() - 60
            self.move(x, y)
        self.show()
        self.raise_()
        self._auto_hide_timer.start(6000)   # Auto-hide after 6 seconds


class ClipboardMonitor:
    """Polls the clipboard and shows toast on new content."""

    def __init__(self, parent_widget, on_action_callback):
        self._parent = parent_widget
        self._on_action = on_action_callback
        self._last_text = ""
        self._toast = ClipboardToast(parent_widget)
        self._toast.action_requested.connect(self._handle_action)

        self._timer = QTimer()
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self._check_clipboard)
        self._timer.start()

    def _check_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text().strip()
        if text and text != self._last_text and len(text) > 10:
            self._last_text = text
            rect = self._parent.rect() if self._parent else None
            self._toast.show_for(text[:500], rect)

    def _handle_action(self, action: str, text: str):
        prompt_map = {
            "summarize": f"Summarize this in 2-3 sentences:\n\n{text}",
            "translate":  f"Translate this to Hindi:\n\n{text}",
            "explain":    f"Explain this clearly and simply:\n\n{text}",
        }
        prompt = prompt_map.get(action, text)
        if self._on_action:
            self._on_action(prompt)

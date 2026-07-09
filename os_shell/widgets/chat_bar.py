"""
os_shell/widgets/chat_bar.py — Floating Chat Input Bar for IP Prime OS.
Beautiful frosted-glass command input at the bottom of the screen.
Shows AI response bubbles, thinking indicator, and history preview.
"""

from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton,
    QLabel, QScrollArea, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont, QKeyEvent


class _ThinkingDot(QLabel):
    """Animated '...' thinking indicator."""
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFont(QFont("Outfit", 13))
        self.setStyleSheet("color: #06b6d4; background: transparent;")
        self._dots = 0
        self._timer = QTimer(self)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._dots = 0
        self.show()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._dots = (self._dots + 1) % 4
        self.setText("⚡ Prime thinking" + "." * self._dots)


class _MessageBubble(QFrame):
    """Single chat message bubble."""

    def __init__(self, text: str, role: str = "user", parent=None):
        super().__init__(parent)
        is_user = role == "user"
        color   = "rgba(6,182,212,0.15)"  if is_user else "rgba(139,92,246,0.12)"
        border  = "rgba(6,182,212,0.4)"   if is_user else "rgba(139,92,246,0.35)"
        align   = Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft

        self.setStyleSheet(f"""
            QFrame {{
                background: {color};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        prefix = "You" if is_user else "⚡ Prime"
        prefix_lbl = QLabel(prefix)
        prefix_lbl.setFont(QFont("Outfit", 8, QFont.Weight.Bold))
        prefix_lbl.setStyleSheet(
            f"color: {'#06b6d4' if is_user else '#a78bfa'}; background: transparent;"
        )
        prefix_lbl.setAlignment(align)

        msg_lbl = QLabel(text[:300] + ("…" if len(text) > 300 else ""))
        msg_lbl.setFont(QFont("Outfit", 10))
        msg_lbl.setStyleSheet("color: rgba(255,255,255,0.85); background: transparent;")
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(align)

        layout.addWidget(prefix_lbl)
        layout.addWidget(msg_lbl)


class FloatingChatBar(QWidget):
    """
    Frosted-glass floating chat bar anchored to the bottom of the screen.
    Features:
      - Text input with send button
      - Last 4 message bubbles (history preview)
      - Animated thinking indicator
      - Keyboard shortcut: Enter to send, Shift+Enter for newline
    """
    message_sent = pyqtSignal(str)   # Emitted when user sends a message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._history: list[dict] = []   # {role, text}
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Container
        self._container = QWidget()
        self._container.setStyleSheet("""
            QWidget {
                background: rgba(8, 14, 30, 0.92);
                border: 1px solid rgba(6, 182, 212, 0.30);
                border-bottom: none;
                border-radius: 18px 18px 0 0;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(6, 182, 212, 70))
        shadow.setOffset(0, -8)
        self._container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(self._container)
        c_layout.setContentsMargins(16, 14, 16, 16)
        c_layout.setSpacing(10)

        # Thinking dot
        self._thinking = _ThinkingDot(self._container)
        self._thinking.hide()
        c_layout.addWidget(self._thinking)

        # Message history scroll area
        self._history_scroll = QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setMaximumHeight(160)
        self._history_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        self._history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._history_scroll.hide()   # Hidden until first message

        self._history_widget = QWidget()
        self._history_layout = QVBoxLayout(self._history_widget)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(6)
        self._history_layout.addStretch()
        self._history_scroll.setWidget(self._history_widget)
        c_layout.addWidget(self._history_scroll)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self._input = QLineEdit()
        self._input.setPlaceholderText("💬  Kuch bolo ya likho Pratik…  (Enter to send)")
        self._input.setFont(QFont("Outfit", 12))
        self._input.setFixedHeight(44)
        self._input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(6,182,212,0.35);
                border-radius: 12px;
                color: #f8fafc;
                padding: 0 16px;
                selection-background-color: rgba(6,182,212,0.3);
            }
            QLineEdit:focus {
                border-color: rgba(6,182,212,0.75);
                background: rgba(255,255,255,0.10);
            }
        """)
        self._input.returnPressed.connect(self._send)

        send_btn = QPushButton("⚡")
        send_btn.setFixedSize(44, 44)
        send_btn.setFont(QFont("Segoe UI Emoji", 14))
        send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(6,182,212,0.85), stop:1 rgba(139,92,246,0.85));
                border: none;
                border-radius: 12px;
                color: #ffffff;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(6,182,212,1.0), stop:1 rgba(139,92,246,1.0));
            }
            QPushButton:pressed { opacity: 0.8; }
        """)
        send_btn.clicked.connect(self._send)

        input_row.addWidget(self._input, 1)
        input_row.addWidget(send_btn)
        c_layout.addLayout(input_row)

        # Hint row
        hint_row = QHBoxLayout()
        hint_lbl = QLabel("Press  ? for hotkeys  ·  Ctrl+Space for Command Palette  ·  Ctrl+F for Search")
        hint_lbl.setFont(QFont("JetBrains Mono", 8))
        hint_lbl.setStyleSheet("color: rgba(255,255,255,0.20); background: transparent;")
        hint_row.addWidget(hint_lbl)
        hint_row.addStretch()
        c_layout.addLayout(hint_row)

        outer.addWidget(self._container)

    def _send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._add_bubble(text, "user")
        self.message_sent.emit(text)

    def _add_bubble(self, text: str, role: str):
        self._history.append({"role": role, "text": text})
        bubble = _MessageBubble(text, role, self._history_widget)
        # Insert before the stretch
        self._history_layout.insertWidget(self._history_layout.count() - 1, bubble)
        # Keep only last 4 bubbles visible
        if self._history_layout.count() - 1 > 4:
            item = self._history_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._history_scroll.show()
        QTimer.singleShot(50, lambda: self._history_scroll.verticalScrollBar().setValue(
            self._history_scroll.verticalScrollBar().maximum()
        ))

    def show_thinking(self):
        """Show animated 'thinking…' indicator."""
        self._thinking.start()

    def show_response(self, text: str):
        """Called when AI responds — hide thinking, show response bubble."""
        self._thinking.stop()
        self._add_bubble(text, "ai")

    def focus_input(self):
        self._input.setFocus()
        self._input.selectAll()

    def anchor_to_bottom(self, parent_width: int, parent_height: int):
        """Reposition to bottom edge of parent."""
        w = min(parent_width - 60, 900)
        x = (parent_width - w) // 2
        self.setGeometry(x, parent_height - self.height(), w, self.height())

    def show_bar(self):
        self.show()
        self.raise_()
        self.focus_input()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_bar()

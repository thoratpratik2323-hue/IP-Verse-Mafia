"""
os_shell/widgets/notification_center.py — macOS-style Notification Center.
Right-side slide-in panel showing system alerts, events, and reminders.
Ctrl+Shift+A to toggle.
"""

import datetime
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont


class _NotifCard(QWidget):
    """Single notification card."""
    def __init__(self, icon: str, title: str, body: str, time_str: str = "",
                 color: str = "#06b6d4", on_dismiss=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet(f"""
            QWidget {{
                background: rgba(15, 23, 42, 0.80);
                border-left: 3px solid {color};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Outfit", 20))
        icon_lbl.setFixedWidth(32)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Outfit", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f8fafc; background: transparent; border: none;")
        body_lbl = QLabel(body)
        body_lbl.setFont(QFont("Outfit", 10))
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet("color: rgba(255,255,255,0.6); background: transparent; border: none;")
        text_col.addWidget(title_lbl)
        text_col.addWidget(body_lbl)
        layout.addLayout(text_col)

        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        time_lbl = QLabel(time_str)
        time_lbl.setFont(QFont("JetBrains Mono", 8))
        time_lbl.setStyleSheet("color: rgba(255,255,255,0.35); background: transparent; border: none;")
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(time_lbl)

        if on_dismiss:
            dismiss_btn = QPushButton("✕")
            dismiss_btn.setFixedSize(20, 20)
            dismiss_btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; color: rgba(255,255,255,0.4); font-size: 11px; }
                QPushButton:hover { color: #f87171; }
            """)
            dismiss_btn.clicked.connect(lambda: on_dismiss(self))
            right_col.addWidget(dismiss_btn)

        right_col.addStretch()
        layout.addLayout(right_col)


class NotificationCenter(QWidget):
    """Slide-in notification panel from the right side."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._visible = False
        self._notifs: list[_NotifCard] = []

        self._setup_ui()
        self._seed_defaults()
        self.hide()

    def _setup_ui(self):
        self.setFixedWidth(340)
        self.setStyleSheet("background: transparent;")

        self._panel = QWidget(self)
        self._panel.setStyleSheet("""
            QWidget {
                background: rgba(8, 14, 28, 0.96);
                border-left: 1px solid rgba(6, 182, 212, 0.25);
                border-top: 1px solid rgba(6, 182, 212, 0.15);
                border-bottom-left-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(-4, 0)
        self._panel.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self._panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet("background: rgba(6, 182, 212, 0.08); border: none;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 10, 16, 10)

        title = QLabel("🔔 Notifications")
        title.setFont(QFont("Outfit", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #f8fafc; background: transparent; border: none;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.setFont(QFont("Outfit", 10))
        clear_btn.setStyleSheet("""
            QPushButton { background: rgba(6,182,212,0.15); border: 1px solid rgba(6,182,212,0.3);
                border-radius: 8px; color: #06b6d4; padding: 4px 10px; }
            QPushButton:hover { background: rgba(6,182,212,0.28); }
        """)
        clear_btn.clicked.connect(self.clear_all)
        h_layout.addWidget(clear_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: rgba(255,255,255,0.5); font-size: 14px; }
            QPushButton:hover { color: #f87171; }
        """)
        close_btn.clicked.connect(self.toggle)
        h_layout.addWidget(close_btn)
        outer.addWidget(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(8)
        self._content_layout.addStretch()

        scroll.setWidget(self._content)
        outer.addWidget(scroll)

        self._empty_lbl = QLabel("No new notifications 🎉")
        self._empty_lbl.setFont(QFont("Outfit", 11))
        self._empty_lbl.setStyleSheet("color: rgba(255,255,255,0.3); background: transparent; border: none;")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty_lbl)

        panel_layout = QVBoxLayout(self)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self._panel)

    def _seed_defaults(self):
        now = datetime.datetime.now().strftime("%H:%M")
        self.add_notification("🤖", "IP Prime Ready", "All systems operational. Say 'Hey Prime' to start.", now, "#06b6d4")
        self.add_notification("🧠", "Memory Loaded", "8-layer brain memory initialized successfully.", now, "#8b5cf6")

    def add_notification(self, icon: str, title: str, body: str,
                         time_str: str = "", color: str = "#06b6d4"):
        if not time_str:
            time_str = datetime.datetime.now().strftime("%H:%M")
        card = _NotifCard(icon, title, body, time_str, color,
                          on_dismiss=self._dismiss_card, parent=self._content)
        self._notifs.append(card)
        # Insert before the stretch
        count = self._content_layout.count()
        self._content_layout.insertWidget(count - 1, card)
        self._update_empty_state()

    def _dismiss_card(self, card: _NotifCard):
        self._content_layout.removeWidget(card)
        card.deleteLater()
        if card in self._notifs:
            self._notifs.remove(card)
        self._update_empty_state()

    def clear_all(self):
        for card in list(self._notifs):
            self._content_layout.removeWidget(card)
            card.deleteLater()
        self._notifs.clear()
        self._update_empty_state()

    def _update_empty_state(self):
        self._empty_lbl.setVisible(len(self._notifs) == 0)

    def toggle(self):
        if self._visible:
            self.hide()
            self._visible = False
        else:
            if self.parent():
                p = self.parent()
                self.setGeometry(p.width() - 340, 0, 340, p.height())
                self._panel.setGeometry(0, 0, 340, p.height())
            self.show()
            self.raise_()
            self._visible = True

    def open(self):
        if not self._visible:
            self.toggle()

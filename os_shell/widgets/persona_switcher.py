"""
os_shell/widgets/persona_switcher.py — Persona Switcher pill widget.
Compact floating pill (top-right corner) — click to cycle: Dev / Hacker / REZ / Normal.
Ctrl+Shift+P to cycle through personas.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont


PERSONAS = [
    {"name": "Dev",    "icon": "🧑‍💻", "color": "#06b6d4", "border": "rgba(6,182,212,0.5)",  "cmd": "normal mode"},
    {"name": "Hacker", "icon": "👾", "color": "#10b981", "border": "rgba(16,185,129,0.5)", "cmd": "hacker mode"},
    {"name": "REZ",    "icon": "💜", "color": "#a855f7", "border": "rgba(168,85,247,0.5)", "cmd": "be rez"},
    {"name": "Focus",  "icon": "🎯", "color": "#f59e0b", "border": "rgba(245,158,11,0.5)", "cmd": "focus start"},
]


class PersonaSwitcher(QWidget):
    """Compact floating pill widget for switching AI personas."""
    persona_changed = pyqtSignal(str)   # emits the command string

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(38)
        self._current_idx = 0
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._pill = QWidget(self)
        self._pill.setStyleSheet(f"""
            QWidget {{
                background: rgba(10, 18, 35, 0.90);
                border: 1px solid {PERSONAS[0]['border']};
                border-radius: 19px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(6, 182, 212, 80))
        shadow.setOffset(0, 2)
        self._pill.setGraphicsEffect(shadow)

        pill_layout = QHBoxLayout(self._pill)
        pill_layout.setContentsMargins(12, 0, 12, 0)
        pill_layout.setSpacing(8)

        self._icon_lbl = QLabel(PERSONAS[0]["icon"])
        self._icon_lbl.setFont(QFont("Outfit", 14))
        self._icon_lbl.setStyleSheet("background: transparent; border: none;")
        pill_layout.addWidget(self._icon_lbl)

        self._name_lbl = QLabel(PERSONAS[0]["name"])
        self._name_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        self._name_lbl.setStyleSheet(f"color: {PERSONAS[0]['color']}; background: transparent; border: none;")
        pill_layout.addWidget(self._name_lbl)

        next_btn = QPushButton("›")
        next_btn.setFixedSize(22, 22)
        next_btn.setFont(QFont("Outfit", 14))
        next_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
                border-radius: 11px; color: white; }
            QPushButton:hover { background: rgba(255,255,255,0.18); }
        """)
        next_btn.clicked.connect(self.next_persona)
        pill_layout.addWidget(next_btn)

        layout.addWidget(self._pill)
        self.setFixedWidth(self._pill.sizeHint().width() + 10)

    def _refresh_ui(self):
        p = PERSONAS[self._current_idx]
        self._icon_lbl.setText(p["icon"])
        self._name_lbl.setText(p["name"])
        self._name_lbl.setStyleSheet(f"color: {p['color']}; background: transparent; border: none;")
        self._pill.setStyleSheet(f"""
            QWidget {{
                background: rgba(10, 18, 35, 0.90);
                border: 1px solid {p['border']};
                border-radius: 19px;
            }}
        """)

    def next_persona(self):
        self._current_idx = (self._current_idx + 1) % len(PERSONAS)
        self._refresh_ui()
        self.persona_changed.emit(PERSONAS[self._current_idx]["cmd"])

    def show_widget(self, parent_width: int):
        if parent_width:
            self.move(parent_width - self.width() - 20, 8)
        self.show()
        self.raise_()

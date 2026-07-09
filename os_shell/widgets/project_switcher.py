"""
os_shell/widgets/project_switcher.py — Project Context Switcher.
Lets Pratik switch between named project workspaces, each with its own
memory context, recent files list, and active task set.
Ctrl+Shift+W to open.
"""

import json
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont

PROJECTS_PATH = Path("memory/projects.json")

_DEFAULT_PROJECTS = [
    {"id": "ip_prime", "name": "IP Prime OS", "emoji": "🤖", "color": "#06b6d4", "active": True},
    {"id": "portfolio", "name": "Portfolio Website", "emoji": "🌐", "color": "#8b5cf6", "active": False},
    {"id": "college", "name": "College Assignments", "emoji": "📚", "color": "#f59e0b", "active": False},
]


def _load_projects() -> list[dict]:
    PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PROJECTS_PATH.exists():
        try:
            return json.loads(PROJECTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    PROJECTS_PATH.write_text(json.dumps(_DEFAULT_PROJECTS, indent=2))
    return _DEFAULT_PROJECTS


def _save_projects(projects: list[dict]):
    try:
        PROJECTS_PATH.write_text(json.dumps(projects, indent=2))
    except Exception:
        pass


class ProjectCard(QFrame):
    """Card for a single project in the switcher."""
    clicked = pyqtSignal(dict)

    def __init__(self, project: dict, is_active: bool, parent=None):
        super().__init__(parent)
        self._project = project
        color = project.get("color", "#06b6d4")
        border = f"2px solid {color}" if is_active else "1px solid rgba(255,255,255,0.10)"
        bg = f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.12)" if is_active else "rgba(255,255,255,0.04)"

        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: {border};
                border-radius: 10px;
            }}
            QFrame:hover {{
                background: rgba(255,255,255,0.08);
                border: 1px solid {color}80;
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        emoji = QLabel(project.get("emoji", "📁"))
        emoji.setFont(QFont("Segoe UI Emoji", 18))
        emoji.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(emoji)

        text_col = QVBoxLayout()
        name = QLabel(project.get("name", "Project"))
        name.setFont(QFont("Outfit", 11, QFont.Weight.Medium))
        name.setStyleSheet(f"color: {'#ffffff' if is_active else 'rgba(255,255,255,0.7)'}; background: transparent; border: none;")
        text_col.addWidget(name)

        if is_active:
            active_badge = QLabel("● ACTIVE")
            active_badge.setFont(QFont("JetBrains Mono", 8))
            active_badge.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            text_col.addWidget(active_badge)

        layout.addLayout(text_col, 1)

    def mousePressEvent(self, event):
        self.clicked.emit(self._project)


class ProjectSwitcherWidget(QWidget):
    """Overlay for switching between project workspaces."""
    project_switched = pyqtSignal(str, str)   # (project_id, project_name)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._projects = _load_projects()
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget(self)
        self._container.setFixedWidth(380)
        self._container.setStyleSheet("""
            QWidget {
                background: rgba(10, 18, 35, 0.97);
                border: 1px solid rgba(139, 92, 246, 0.4);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(139, 92, 246, 100))
        shadow.setOffset(0, 8)
        self._container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(self._container)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("🗂️ Project Switcher")
        title.setFont(QFont("Outfit", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #8b5cf6; background: transparent; border: none;")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; color:rgba(255,255,255,0.3); font-size:11px; }"
            "QPushButton:hover { color:#f87171; }"
        )
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        c_layout.addLayout(hdr)

        # New project input
        new_row = QHBoxLayout()
        self._new_input = QLineEdit()
        self._new_input.setPlaceholderText("➕ New project name…")
        self._new_input.setFont(QFont("Outfit", 10))
        self._new_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(139,92,246,0.3);
                border-radius: 8px;
                color: #f8fafc;
                padding: 6px 10px;
            }
            QLineEdit:focus { border-color: rgba(139,92,246,0.7); }
        """)
        self._new_input.returnPressed.connect(self._add_project)
        new_row.addWidget(self._new_input)
        add_btn = QPushButton("Add")
        add_btn.setFont(QFont("Outfit", 9))
        add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(139,92,246,0.25);
                border: 1px solid rgba(139,92,246,0.5);
                border-radius: 8px;
                color: #c4b5fd;
                padding: 6px 12px;
            }
            QPushButton:hover { background: rgba(139,92,246,0.4); }
        """)
        add_btn.clicked.connect(self._add_project)
        new_row.addWidget(add_btn)
        c_layout.addLayout(new_row)

        # Project list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMaximumHeight(300)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._scroll.setWidget(self._list_widget)
        c_layout.addWidget(self._scroll)

        hint = QLabel("Ctrl+Shift+W to open | Click project to switch")
        hint.setFont(QFont("JetBrains Mono", 8))
        hint.setStyleSheet("color: rgba(255,255,255,0.25); background: transparent; border: none;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(hint)

        outer.addStretch()
        outer.addWidget(self._container, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()

        self._rebuild_list()

    def _rebuild_list(self):
        for i in reversed(range(self._list_layout.count())):
            w = self._list_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        active_id = next((p["id"] for p in self._projects if p.get("active")), None)
        for p in self._projects:
            card = ProjectCard(p, p["id"] == active_id, self._list_widget)
            card.clicked.connect(self._switch_project)
            self._list_layout.addWidget(card)

    def _switch_project(self, project: dict):
        for p in self._projects:
            p["active"] = (p["id"] == project["id"])
        _save_projects(self._projects)
        self._rebuild_list()
        self.project_switched.emit(project["id"], project["name"])
        self.hide()

    def _add_project(self):
        name = self._new_input.text().strip()
        if not name:
            return
        import uuid
        emojis = ["🚀", "⚡", "🎯", "🌟", "🔥", "💎", "🎨"]
        colors = ["#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]
        idx = len(self._projects) % len(emojis)
        new_p = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "emoji": emojis[idx],
            "color": colors[idx % len(colors)],
            "active": False
        }
        self._projects.append(new_p)
        _save_projects(self._projects)
        self._new_input.clear()
        self._rebuild_list()

    def open(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self._new_input.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

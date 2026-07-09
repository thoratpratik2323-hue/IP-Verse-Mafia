"""
os_shell/widgets/sticky_notes.py — Sticky Notes on Desktop.
Draggable colored notes on the desktop, auto-saved to data/sticky_notes.json.
Ctrl+Shift+N to create a new note.
"""

import json
from pathlib import Path
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont

NOTES_FILE = Path("data/sticky_notes.json")

NOTE_COLORS = [
    {"bg": "rgba(253, 230, 138, 0.92)", "border": "rgba(217, 170, 20, 0.6)",  "text": "#1e1b00", "name": "yellow"},
    {"bg": "rgba(167, 243, 208, 0.92)", "border": "rgba(16, 185, 129, 0.6)",  "text": "#022c22", "name": "green"},
    {"bg": "rgba(196, 181, 253, 0.92)", "border": "rgba(139, 92, 246, 0.6)",  "text": "#1e1042", "name": "purple"},
    {"bg": "rgba(147, 197, 253, 0.92)", "border": "rgba(59, 130, 246, 0.6)",  "text": "#0c1a3e", "name": "blue"},
    {"bg": "rgba(253, 164, 175, 0.92)", "border": "rgba(244, 63, 94, 0.6)",   "text": "#3b0a14", "name": "pink"},
]


def _load_notes():
    NOTES_FILE.parent.mkdir(exist_ok=True)
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_notes(notes_data):
    NOTES_FILE.parent.mkdir(exist_ok=True)
    NOTES_FILE.write_text(json.dumps(notes_data, indent=2, ensure_ascii=False), encoding="utf-8")


class StickyNote(QWidget):
    """A single draggable sticky note widget."""

    def __init__(self, note_id: int, text: str = "", color_idx: int = 0,
                 x: int = 100, y: int = 100, parent=None, on_close=None, on_change=None):
        super().__init__(parent)
        self.note_id = note_id
        self._color_idx = color_idx % len(NOTE_COLORS)
        self._on_close = on_close
        self._on_change = on_change
        self._drag_pos = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(220, 200)
        self.move(x, y)

        self._setup_ui(text)
        self.show()

    def _setup_ui(self, text: str):
        c = NOTE_COLORS[self._color_idx]

        self._card = QWidget(self)
        self._card.setGeometry(0, 0, 220, 200)
        self._card.setStyleSheet(f"""
            QWidget {{
                background: {c['bg']};
                border: 1.5px solid {c['border']};
                border-radius: 12px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 4)
        self._card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        drag_label = QLabel("📌 Note")
        drag_label.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        drag_label.setStyleSheet(f"color: {c['text']}; background: transparent; border: none;")
        header.addWidget(drag_label)
        header.addStretch()

        # Color cycle button
        color_btn = QPushButton("🎨")
        color_btn.setFixedSize(22, 22)
        color_btn.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 13px; }"
                                "QPushButton:hover { background: rgba(0,0,0,0.1); border-radius: 4px; }")
        color_btn.clicked.connect(self._cycle_color)
        header.addWidget(color_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 11px; color: rgba(0,0,0,0.5); }"
                                "QPushButton:hover { color: red; background: rgba(0,0,0,0.1); border-radius: 4px; }")
        close_btn.clicked.connect(self._close_note)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Text area
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("Write your note here…")
        self._text_edit.setFont(QFont("Outfit", 11))
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {c['text']};
            }}
        """)
        self._text_edit.setText(text)
        self._text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._text_edit)

    def _cycle_color(self):
        self._color_idx = (self._color_idx + 1) % len(NOTE_COLORS)
        # Rebuild UI with new color
        text = self._text_edit.toPlainText()
        for child in self.children():
            if isinstance(child, QWidget):
                child.deleteLater()
        self._setup_ui(text)
        if self._on_change:
            self._on_change()

    def _on_text_changed(self):
        if self._on_change:
            self._on_change()

    def _close_note(self):
        if self._on_close:
            self._on_close(self.note_id)
        self.hide()
        self.deleteLater()

    def get_data(self):
        return {
            "id": self.note_id,
            "text": self._text_edit.toPlainText(),
            "color_idx": self._color_idx,
            "x": self.x(),
            "y": self.y(),
        }

    # ── Drag ─────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        if self._on_change:
            self._on_change()


class StickyNotesManager:
    """Manages all sticky notes — create, save, load, close."""

    def __init__(self, parent_widget):
        self._parent = parent_widget
        self._notes: list[StickyNote] = []
        self._next_id = 0
        self._load()

    def _load(self):
        data = _load_notes()
        for item in data:
            self._add_note(
                text=item.get("text", ""),
                color_idx=item.get("color_idx", 0),
                x=item.get("x", 120),
                y=item.get("y", 120),
                note_id=item.get("id", self._next_id),
            )
            self._next_id = max(self._next_id, item.get("id", 0) + 1)

    def _add_note(self, text="", color_idx=0, x=120, y=120, note_id=None):
        if note_id is None:
            note_id = self._next_id
            self._next_id += 1
        note = StickyNote(
            note_id=note_id,
            text=text,
            color_idx=color_idx,
            x=x,
            y=y,
            parent=self._parent,
            on_close=self._on_note_closed,
            on_change=self._save,
        )
        self._notes.append(note)
        return note

    def new_note(self):
        """Create a new empty sticky note."""
        import random
        x = random.randint(200, 900)
        y = random.randint(150, 500)
        color_idx = self._next_id % len(NOTE_COLORS)
        note = self._add_note(text="", color_idx=color_idx, x=x, y=y)
        note.raise_()
        self._save()

    def _on_note_closed(self, note_id: int):
        self._notes = [n for n in self._notes if n.note_id != note_id]
        self._save()

    def _save(self):
        data = [n.get_data() for n in self._notes if n.isVisible()]
        _save_notes(data)

"""
os_shell/widgets/global_search.py — Spotlight-style Global Search.
Searches files on disk (Desktop/Downloads), memory/notes, running windows.
Ctrl+F to open.
"""

import os
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont, QKeyEvent


class GlobalSearchWidget(QWidget):
    """Spotlight-style global search overlay."""
    file_triggered = pyqtSignal(str)   # emits path string to open
    command_triggered = pyqtSignal(str) # emits cmd to run

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setStyleSheet("background: rgba(0,0,0,0);")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget(self)
        self._container.setFixedWidth(640)
        self._container.setStyleSheet("""
            QWidget {
                background: rgba(10, 18, 35, 0.95);
                border: 1px solid rgba(6, 182, 212, 0.4);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(6, 182, 212, 100))
        shadow.setOffset(0, 8)
        self._container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(10)

        # Header
        hdr = QLabel("🔍 Spotlight Global Search")
        hdr.setFont(QFont("Outfit", 11, QFont.Weight.Medium))
        hdr.setStyleSheet("color: rgba(6, 182, 212, 0.8); background: transparent; border: none;")
        container_layout.addWidget(hdr)

        # Search line
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search files, memories, commands…")
        self._search.setFont(QFont("Outfit", 14))
        self._search.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(6, 182, 212, 0.45);
                border-radius: 10px;
                color: #f8fafc;
                padding: 10px 14px;
            }
            QLineEdit:focus {
                border-color: rgba(6, 182, 212, 0.8);
                background: rgba(255, 255, 255, 0.10);
            }
        """)
        self._search.textChanged.connect(self._do_search)
        container_layout.addWidget(self._search)

        # Results
        self._list = QListWidget()
        self._list.setFont(QFont("Outfit", 12))
        self._list.setMaximumHeight(350)
        self._list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                color: #f8fafc;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background: rgba(6, 182, 212, 0.22);
                color: #ffffff;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.08);
            }
        """)
        self._list.itemActivated.connect(self._execute_item)
        container_layout.addWidget(self._list)

        # Help footer
        hint = QLabel("↑↓ Navigate   ↵ Open / Run   Esc Close")
        hint.setFont(QFont("JetBrains Mono", 9))
        hint.setStyleSheet("color: rgba(255,255,255,0.35); background: transparent; border: none;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint)

        outer.addStretch()
        outer.addWidget(self._container, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()

    def _do_search(self, text: str):
        self._list.clear()
        q = text.lower().strip()
        if not q or len(q) < 2:
            return

        # 1. Search Files in Desktop/Downloads/Workspace
        home = Path.home()
        paths = [home / "Desktop", home / "Downloads", Path(".")]
        results = []
        for base in paths:
            if base.exists():
                try:
                    for root, dirs, files in os.walk(base):
                        # Limit depth to keep it fast
                        if root.count(os.sep) - str(base).count(os.sep) > 1:
                            continue
                        for f in files:
                            if q in f.lower():
                                fp = os.path.join(root, f)
                                results.append(("📄 file", f, fp))
                                if len(results) >= 20:
                                    break
                except Exception:
                    pass
            if len(results) >= 20:
                break

        # 2. Search Commands
        commands = [
            ("Start Voice Listening", "voice start"),
            ("Stop Voice Listening", "voice stop"),
            ("Check System Telemetry", "open sysdash"),
            ("Trigger Autopilot Coder", "open autopilot"),
            ("Clean/Organize Desktop", "organize files"),
            ("Open Password Vault", "open vault"),
        ]
        for name, cmd in commands:
            if q in name.lower() or q in cmd.lower():
                results.append(("⚡ command", name, cmd))

        # Add to list widget
        for typ, display, val in results:
            it = QListWidgetItem(f"[{typ.upper()}]  {display}")
            it.setData(Qt.ItemDataRole.UserRole, (typ, val))
            self._list.addItem(it)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _execute_item(self, item):
        typ, val = item.data(Qt.ItemDataRole.UserRole)
        self.hide()
        if typ == "file":
            self.file_triggered.emit(val)
        elif typ == "command":
            self.command_triggered.emit(val)

    def open(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
        self._search.clear()
        self._list.clear()
        self.show()
        self.raise_()
        self._search.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.hide()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            cur = self._list.currentItem()
            if cur:
                self._execute_item(cur)
        elif key == Qt.Key.Key_Down:
            row = self._list.currentRow()
            self._list.setCurrentRow(min(row + 1, self._list.count() - 1))
        elif key == Qt.Key.Key_Up:
            row = self._list.currentRow()
            self._list.setCurrentRow(max(row - 1, 0))
        else:
            super().keyPressEvent(event)

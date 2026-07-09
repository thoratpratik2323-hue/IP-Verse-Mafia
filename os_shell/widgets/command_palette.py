"""
os_shell/widgets/command_palette.py — VS Code-style Command Palette overlay.
Ctrl+Space to open. Type to fuzzy-search actions. Arrow keys + Enter to run.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont, QKeyEvent


PALETTE_COMMANDS = [
    ("🎙️ Start Listening",         "voice start"),
    ("🔇 Stop Listening",           "voice stop"),
    ("📸 Screen Snapshot + AI",     "screen snapshot"),
    ("🧠 Open Mind Graph",          "open graph"),
    ("💻 Open Swarm Console",       "open swarm"),
    ("📁 Open File Explorer",       "open files"),
    ("⚙️ Open Config",              "open config"),
    ("🤖 Toggle Autopilot Coder",   "open autopilot"),
    ("🎨 Open NainiPix Studio",     "open nainipix"),
    ("🐍 Open CobraAI Web",         "open cobra_web"),
    ("🎛️ Open RAVX Web",            "open ravx_web"),
    ("⚡ Open XBLT Web",            "open xblt_web"),
    ("📊 SysDash Telemetry",        "open sysdash"),
    ("🔮 Toggle Launchpad",         "launchpad"),
    ("⏱️ Start Focus Timer",        "focus start"),
    ("⏹️ Stop Focus Timer",         "focus stop"),
    ("📌 New Sticky Note",          "sticky new"),
    ("🔔 Notification Center",      "notifications"),
    ("🔍 Global Search",            "search"),
    ("🌙 Night Theme",              "theme dark"),
    ("☀️ Light Theme",              "theme light"),
    ("🟣 Neon Theme",              "theme neon"),
    ("💜 REZ Mode",                 "be rez"),
    ("👾 Hacker Mode",              "hacker mode"),
    ("🤖 Normal Mode",              "normal mode"),
    ("📋 Clipboard AI",             "clipboard ai"),
    ("🗄️ Password Vault",           "open vault"),
    ("🎮 Game Mode Toggle",         "game mode"),
    ("🌐 Network Monitor",          "network monitor"),
    ("🗂️ Organize Files",           "organize files"),
    ("📅 Daily Digest",             "daily digest"),
    ("❌ Close Palette",            "__close__"),
]


class CommandPalette(QWidget):
    """Glassmorphic full-screen command palette with fuzzy search."""
    command_selected = pyqtSignal(str)   # emits the command string

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._commands = PALETTE_COMMANDS
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        # Full-screen dimmed backdrop
        self.setStyleSheet("background: rgba(0, 0, 0, 0);")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Center container
        self._container = QWidget(self)
        self._container.setFixedWidth(620)
        self._container.setStyleSheet("""
            QWidget {
                background: rgba(10, 18, 35, 0.96);
                border: 1px solid rgba(6, 182, 212, 0.35);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(48)
        shadow.setColor(QColor(6, 182, 212, 120))
        shadow.setOffset(0, 8)
        self._container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(10)

        # Header label
        header = QLabel("⚡ Command Palette")
        header.setFont(QFont("Outfit", 11, QFont.Weight.Medium))
        header.setStyleSheet("color: rgba(6, 182, 212, 0.8); background: transparent; border: none;")
        container_layout.addWidget(header)

        # Search box
        self._search = QLineEdit()
        self._search.setPlaceholderText("Type to search commands…")
        self._search.setFont(QFont("Outfit", 14))
        self._search.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(6, 182, 212, 0.4);
                border-radius: 10px;
                color: #f8fafc;
                padding: 10px 14px;
            }
            QLineEdit:focus {
                border-color: rgba(6, 182, 212, 0.8);
                background: rgba(255, 255, 255, 0.10);
            }
        """)
        self._search.textChanged.connect(self._filter)
        container_layout.addWidget(self._search)

        # Results list
        self._list = QListWidget()
        self._list.setFont(QFont("Outfit", 12))
        self._list.setMaximumHeight(380)
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
                border: none;
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

        # Footer hint
        hint = QLabel("↑↓ Navigate   ↵ Run   Esc Close")
        hint.setFont(QFont("JetBrains Mono", 9))
        hint.setStyleSheet("color: rgba(255,255,255,0.35); background: transparent; border: none;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint)

        outer.addStretch()
        outer.addWidget(self._container, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()

        self._populate(self._commands)

    def _populate(self, items):
        self._list.clear()
        for label, cmd in items:
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, cmd)
            self._list.addItem(it)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _filter(self, text):
        q = text.lower()
        if not q:
            self._populate(self._commands)
            return
        filtered = [(lbl, cmd) for lbl, cmd in self._commands if q in lbl.lower() or q in cmd.lower()]
        self._populate(filtered)

    def _execute_item(self, item):
        cmd = item.data(Qt.ItemDataRole.UserRole)
        self.hide()
        if cmd != "__close__":
            self.command_selected.emit(cmd)

    def open(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
        self._search.clear()
        self._filter("")
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

"""
os_shell/widgets/hotkey_cheatsheet.py — Hotkey Reference Overlay.
Press ? to show / hide. Full-screen frosted overlay listing all shortcuts.
"""

from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont, QKeyEvent


_HOTKEYS = [
    # (Category, Key, Description)
    ("AI & Chat",    "Enter",           "Send message to IP Prime"),
    ("AI & Chat",    "Ctrl + Space",    "Open Command Palette"),
    ("AI & Chat",    "Ctrl + F",        "Global Search"),
    ("AI & Chat",    "F12",             "Screenshot + AI Analysis"),
    ("Widgets",      "Ctrl + Shift + N","New Sticky Note"),
    ("Widgets",      "Ctrl + Shift + A","Notification Center"),
    ("Widgets",      "Ctrl + Shift + F","Focus Timer"),
    ("Widgets",      "Ctrl + Shift + P","Cycle AI Persona"),
    ("Widgets",      "Ctrl + Shift + V","Password Vault"),
    ("Widgets",      "Ctrl + Shift + J","Task Queue HUD"),
    ("Widgets",      "Ctrl + Shift + W","Project Switcher"),
    ("System",       "Ctrl + Shift + S","Sleep Mode"),
    ("System",       "Ctrl + Shift + G","Game Mode"),
    ("System",       "F9",              "Toggle Game Mode"),
    ("System",       "?",               "Show / Hide this cheatsheet"),
]


class HotkeyCheatsheet(QWidget):
    """Full-screen translucent hotkey reference overlay. Press ? to toggle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self._build_ui()
        self.hide()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Semi-transparent backdrop (click anywhere to dismiss)
        self.setStyleSheet("background: rgba(2, 6, 23, 0.88);")

        # Card
        card = QFrame()
        card.setFixedSize(780, 560)
        card.setStyleSheet("""
            QFrame {
                background: rgba(10, 18, 40, 0.97);
                border: 1px solid rgba(6, 182, 212, 0.40);
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(6, 182, 212, 90))
        shadow.setOffset(0, 0)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("⌨️  IP Prime — Keyboard Shortcuts")
        title.setFont(QFont("Outfit", 17, QFont.Weight.Bold))
        title.setStyleSheet("""
            color: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #06b6d4, stop:1 #8b5cf6);
            background: transparent;
        """)
        close_hint = QLabel("Press  ?  or  Esc  to close")
        close_hint.setFont(QFont("JetBrains Mono", 9))
        close_hint.setStyleSheet("color: rgba(255,255,255,0.30); background: transparent;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_hint)
        card_layout.addLayout(header)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background: rgba(6,182,212,0.20); max-height: 1px;")
        card_layout.addWidget(div)

        # Grid of shortcuts (2 columns)
        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        _cat_color   = "rgba(6,182,212,0.80)"
        _key_bg      = "rgba(255,255,255,0.06)"
        _key_border  = "rgba(255,255,255,0.12)"
        _desc_color  = "rgba(255,255,255,0.70)"

        row = 0
        prev_cat = ""
        col_offset = 0
        half = (len(_HOTKEYS) + 1) // 2

        for idx, (cat, key, desc) in enumerate(_HOTKEYS):
            col_offset = 0 if idx < half else 2

            if cat != prev_cat and col_offset == 0:
                cat_lbl = QLabel(f"  {cat.upper()}")
                cat_lbl.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
                cat_lbl.setStyleSheet(
                    f"color: {_cat_color}; background: rgba(6,182,212,0.07);"
                    "border-radius: 4px; padding: 2px 6px;"
                )
                grid.addWidget(cat_lbl, row, col_offset, 1, 2)
                row += 1
                prev_cat = cat

            key_lbl = QLabel(key)
            key_lbl.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
            key_lbl.setStyleSheet(f"""
                color: #e2e8f0;
                background: {_key_bg};
                border: 1px solid {_key_border};
                border-radius: 5px;
                padding: 3px 10px;
            """)
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            desc_lbl = QLabel(f"  {desc}")
            desc_lbl.setFont(QFont("Outfit", 10))
            desc_lbl.setStyleSheet(f"color: {_desc_color}; background: transparent;")

            grid.addWidget(key_lbl,  row, col_offset)
            grid.addWidget(desc_lbl, row, col_offset + 1)
            row += 1

            if idx == half - 1:
                row = 0
                prev_cat = ""

        card_layout.addLayout(grid)
        card_layout.addStretch()

        # Footer
        footer_lbl = QLabel("All shortcuts work anywhere on the desktop — no need to click first.")
        footer_lbl.setFont(QFont("Outfit", 9))
        footer_lbl.setStyleSheet("color: rgba(255,255,255,0.20); background: transparent;")
        footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(footer_lbl)

        root.addWidget(card)

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            if self.parent():
                self.setGeometry(0, 0, self.parent().width(), self.parent().height())
            self.show()
            self.raise_()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Question):
            self.hide()
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.hide()

"""
os_shell_windows/embedded_browser.py
======================================
SATURDAY's own browser screen. When SaturdayOS Mode is on and you ask
SATURDAY to open YouTube, WhatsApp Web, search something, etc. — it opens
HERE, inside SATURDAY's own window, instead of launching a real
Chrome/Edge window on top of it (which would break the "this is its own
OS" illusion).

Requires: PyQt6-WebEngine
    pip install PyQt6-WebEngine --break-system-packages   (Linux)
    pip install PyQt6-WebEngine                            (Windows)

If PyQt6-WebEngine isn't installed yet, this panel shows a friendly
placeholder instead of crashing — browser_bridge.py keeps using the
panel either way, you just won't see real pages until you install it.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    _WEBENGINE_OK = True
except ImportError:
    _WEBENGINE_OK = False

BG     = "#00060a"
PANEL  = "#010d14"
BORDER = "#0d3347"
PRI    = "#00d4ff"
TEXT   = "#8ffcff"
WHITE  = "#d8f8ff"


class EmbeddedBrowserPanel(QWidget):
    """A minimal-chrome browser surface living INSIDE the SATURDAY window.
    Call .navigate(url) to load a page; the close button (or on_close
    callback) dismisses it and returns to the orb console."""

    def __init__(self, on_close=None, parent=None):
        super().__init__(parent)
        self._on_close = on_close
        self.setStyleSheet(f"background: {BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- minimal top chrome: back / current url / close ---
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet(f"background: {PANEL}; border-bottom: 1px solid {BORDER};")
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(10, 4, 10, 4)
        bar_l.setSpacing(8)

        self._back_btn = QPushButton("◀")
        self._back_btn.setFixedWidth(32)
        self._back_btn.setStyleSheet(self._btn_style())
        bar_l.addWidget(self._back_btn)

        self._url_lbl = QLabel("saturday://home")
        self._url_lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        bar_l.addWidget(self._url_lbl, 1)

        close_btn = QPushButton("✕  Back to SATURDAY")
        close_btn.setStyleSheet(self._btn_style())
        close_btn.clicked.connect(self._close_clicked)
        bar_l.addWidget(close_btn)

        root.addWidget(bar)

        # --- the actual web surface ---
        if _WEBENGINE_OK:
            self._view = QWebEngineView()
            self._back_btn.clicked.connect(self._view.back)
            root.addWidget(self._view, 1)
        else:
            self._view = None
            placeholder = QLabel(
                "PyQt6-WebEngine is not installed yet.\n\n"
                "Run:   pip install PyQt6-WebEngine\n\n"
                "to enable SATURDAY's embedded browser screen."
            )
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"color: {WHITE}; font-size: 14px; background: {BG};")
            root.addWidget(placeholder, 1)

    @staticmethod
    def _btn_style() -> str:
        return f"""
            QPushButton {{ color: {PRI}; background: {PANEL}; border: 1px solid {BORDER};
                           border-radius: 4px; padding: 4px 10px; font-size: 12px; }}
            QPushButton:hover {{ color: {WHITE}; border-color: {PRI}; }}
        """

    def navigate(self, url: str) -> None:
        self._url_lbl.setText(url)
        if self._view is not None:
            self._view.setUrl(QUrl(url))

    def _close_clicked(self) -> None:
        if self._on_close:
            self._on_close()

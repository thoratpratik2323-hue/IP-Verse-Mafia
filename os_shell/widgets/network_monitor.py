"""
os_shell/widgets/network_monitor.py — Network Monitor HUD.
Small floating widget showing live upload/download speed and WiFi info.
"""

import psutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont


def _bytes_to_str(b: float) -> str:
    if b >= 1_000_000:
        return f"{b/1_000_000:.1f} MB/s"
    elif b >= 1_000:
        return f"{b/1_000:.1f} KB/s"
    return f"{b:.0f} B/s"


class NetworkMonitorHUD(QWidget):
    """Compact floating network stats HUD."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(180, 110)
        self._drag_pos = None
        self._last_sent = 0
        self._last_recv = 0

        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start()
        self._update_stats()
        self.hide()

    def _setup_ui(self):
        self._card = QWidget(self)
        self._card.setGeometry(0, 0, 180, 110)
        self._card.setStyleSheet("""
            QWidget {
                background: rgba(10, 18, 35, 0.92);
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 14px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(16, 185, 129, 80))
        shadow.setOffset(0, 3)
        self._card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("📡 Network")
        title.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #10b981; background: transparent; border: none;")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("QPushButton { background:transparent; border:none; color:rgba(255,255,255,0.4); font-size:10px; } QPushButton:hover { color:#f87171; }")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # Stats
        self._up_lbl = QLabel("▲ 0 B/s")
        self._down_lbl = QLabel("▼ 0 B/s")
        self._wifi_lbl = QLabel("🌐 Checking…")

        for lbl in [self._up_lbl, self._down_lbl, self._wifi_lbl]:
            lbl.setFont(QFont("JetBrains Mono", 9))
            lbl.setStyleSheet("color: rgba(255,255,255,0.75); background: transparent; border: none;")
            layout.addWidget(lbl)

    def _update_stats(self):
        try:
            net = psutil.net_io_counters()
            sent = net.bytes_sent
            recv = net.bytes_recv
            if self._last_sent and self._last_recv:
                up = (sent - self._last_sent) / 1.5
                down = (recv - self._last_recv) / 1.5
                self._up_lbl.setText(f"▲ {_bytes_to_str(up)}")
                self._down_lbl.setText(f"▼ {_bytes_to_str(down)}")
            self._last_sent = sent
            self._last_recv = recv

            # Try to get WiFi SSID
            try:
                import subprocess
                result = subprocess.run(
                    ["netsh", "wlan", "show", "interfaces"],
                    capture_output=True, text=True, timeout=2
                )
                for line in result.stdout.splitlines():
                    if "SSID" in line and "BSSID" not in line:
                        ssid = line.split(":", 1)[-1].strip()
                        self._wifi_lbl.setText(f"📶 {ssid[:18]}")
                        break
            except Exception:
                self._wifi_lbl.setText("🌐 Connected")
        except Exception:
            self._up_lbl.setText("▲ --")
            self._down_lbl.setText("▼ --")

    def show_widget(self, x: int = 20, y: int = 60):
        self.move(x, y)
        self.show()
        self.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

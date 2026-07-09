"""
os_shell/widgets/network_monitor.py — Network Monitor HUD (non-blocking).
psutil stats on main thread (fast), WiFi SSID in QThread (slow subprocess isolated).
"""

import psutil
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont


def _bytes_to_str(b: float) -> str:
    if b >= 1_000_000:
        return f"{b/1_000_000:.1f} MB/s"
    elif b >= 1_000:
        return f"{b/1_000:.1f} KB/s"
    return f"{b:.0f} B/s"


class _WifiWorker(QThread):
    """Background thread: fetches WiFi SSID once every 30 seconds."""
    ssid_ready = pyqtSignal(str)

    def run(self):
        try:
            import subprocess
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=3,
                creationflags=0x08000000  # CREATE_NO_WINDOW on Windows
            )
            for line in result.stdout.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    ssid = line.split(":", 1)[-1].strip()
                    if ssid:
                        self.ssid_ready.emit(f"📶 {ssid[:20]}")
                        return
            self.ssid_ready.emit("🌐 Connected")
        except Exception:
            self.ssid_ready.emit("🌐 Connected")


class NetworkMonitorHUD(QWidget):
    """Compact floating network stats HUD — zero main-thread blocking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(180, 110)
        self._drag_pos = None
        self._last_sent = 0
        self._last_recv = 0
        self._ssid_cache = "🌐 Checking…"
        self._wifi_worker = None

        self._setup_ui()

        # Stats update — 3 seconds (safe for main thread, psutil is fast)
        self._timer = QTimer(self)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start()

        # WiFi SSID — update every 30s in background thread
        self._wifi_timer = QTimer(self)
        self._wifi_timer.setInterval(30_000)
        self._wifi_timer.timeout.connect(self._fetch_wifi)
        self._wifi_timer.start()
        # Fetch once after 2s delay (not at startup to avoid blocking)
        QTimer.singleShot(2000, self._fetch_wifi)

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
        close_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; color:rgba(255,255,255,0.4); font-size:10px; }"
            "QPushButton:hover { color:#f87171; }"
        )
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        self._up_lbl = QLabel("▲ 0 B/s")
        self._down_lbl = QLabel("▼ 0 B/s")
        self._wifi_lbl = QLabel("🌐 …")

        for lbl in [self._up_lbl, self._down_lbl, self._wifi_lbl]:
            lbl.setFont(QFont("JetBrains Mono", 9))
            lbl.setStyleSheet("color: rgba(255,255,255,0.75); background: transparent; border: none;")
            layout.addWidget(lbl)

    def _update_stats(self):
        """Called every 3s on main thread — psutil is non-blocking."""
        try:
            net = psutil.net_io_counters()
            sent = net.bytes_sent
            recv = net.bytes_recv
            if self._last_sent and self._last_recv:
                up = (sent - self._last_sent) / 3.0
                down = (recv - self._last_recv) / 3.0
                self._up_lbl.setText(f"▲ {_bytes_to_str(up)}")
                self._down_lbl.setText(f"▼ {_bytes_to_str(down)}")
            self._last_sent = sent
            self._last_recv = recv
            self._wifi_lbl.setText(self._ssid_cache)
        except Exception:
            self._up_lbl.setText("▲ --")
            self._down_lbl.setText("▼ --")

    def _fetch_wifi(self):
        """Launch background thread to get SSID — never blocks UI."""
        if self._wifi_worker and self._wifi_worker.isRunning():
            return  # Previous fetch still in progress, skip
        self._wifi_worker = _WifiWorker()
        self._wifi_worker.ssid_ready.connect(self._on_ssid)
        self._wifi_worker.start()

    def _on_ssid(self, ssid: str):
        self._ssid_cache = ssid
        self._wifi_lbl.setText(ssid)

    def show_widget(self, x: int = 20, y: int = 60):
        self.move(x, y)
        self.show()
        self.raise_()

    def showEvent(self, event):
        """Resume timers only when widget becomes visible."""
        super().showEvent(event)
        self._timer.start()
        self._wifi_timer.start()
        self._fetch_wifi()        # Get SSID immediately on show
        self._update_stats()

    def hideEvent(self, event):
        """Pause timers when widget is hidden — zero CPU overhead."""
        super().hideEvent(event)
        self._timer.stop()
        self._wifi_timer.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


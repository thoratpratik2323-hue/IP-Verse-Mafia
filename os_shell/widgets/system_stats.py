import psutil
import platform
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
)
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QBrush, QLinearGradient


class _MiniBar(QProgressBar):
    """Slim gradient progress bar."""
    def __init__(self, color_start="#27C8F5", color_end="#8B5CF6", parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setFixedHeight(6)
        self.setTextVisible(False)
        self.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255,255,255,0.07);
                border: none; border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {color_start}, stop:1 {color_end});
                border-radius: 3px;
            }}
        """)


class SystemStatsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatsWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(11)

        # ── Header ──────────────────────────────
        hdr = QLabel("SYSTEM STATUS", self)
        hdr.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        hdr.setStyleSheet("color: #27C8F5; letter-spacing: 2px; background: transparent;")
        layout.addWidget(hdr)

        self._divider(layout)

        # ── Rows ────────────────────────────────
        self.cpu_val   = QLabel("0%", self)
        self.ram_val   = QLabel("0%", self)
        self.disk_val  = QLabel("0%", self)
        self.net_val   = QLabel("↑0  ↓0 KB/s", self)
        self.temp_val  = QLabel("—", self)

        self.cpu_bar  = _MiniBar("#27C8F5", "#8B5CF6",  self)
        self.ram_bar  = _MiniBar("#F59E0B", "#EF4444",  self)
        self.disk_bar = _MiniBar("#10B981", "#27C8F5",  self)

        for icon, label, val_lbl, bar in [
            ("⚡", "CPU",  self.cpu_val,  self.cpu_bar),
            ("🧠", "RAM",  self.ram_val,  self.ram_bar),
            ("💾", "DISK", self.disk_val, self.disk_bar),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            ico = QLabel(icon, self)
            ico.setFont(QFont("Segoe UI Emoji", 12))
            ico.setStyleSheet("background: transparent;")
            ico.setFixedWidth(20)
            row.addWidget(ico)
            lbl = QLabel(label, self)
            lbl.setFont(QFont("Outfit", 10))
            lbl.setStyleSheet("color: rgba(200,215,230,0.75); background: transparent; min-width: 36px;")
            row.addWidget(lbl)
            row.addStretch()
            val_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
            val_lbl.setStyleSheet("color: #E8EEF8; background: transparent;")
            row.addWidget(val_lbl)
            layout.addLayout(row)
            layout.addWidget(bar)

        self._divider(layout)

        # ── Network row ─────────────────────────
        net_row = QHBoxLayout()
        net_ico = QLabel("🌐", self)
        net_ico.setFont(QFont("Segoe UI Emoji", 12))
        net_ico.setStyleSheet("background: transparent;")
        net_row.addWidget(net_ico)
        net_lbl = QLabel("Network", self)
        net_lbl.setFont(QFont("Outfit", 10))
        net_lbl.setStyleSheet("color: rgba(200,215,230,0.75); background: transparent;")
        net_row.addWidget(net_lbl)
        net_row.addStretch()
        self.net_val.setFont(QFont("Outfit", 9))
        self.net_val.setStyleSheet("color: #10B981; background: transparent;")
        net_row.addWidget(self.net_val)
        layout.addLayout(net_row)

        # ── OS info ─────────────────────────────
        os_row = QHBoxLayout()
        os_ico = QLabel("🖥", self)
        os_ico.setFont(QFont("Segoe UI Emoji", 12))
        os_ico.setStyleSheet("background: transparent;")
        os_row.addWidget(os_ico)
        os_name = platform.node() or "IP Prime Host"
        os_lbl = QLabel(os_name[:18], self)
        os_lbl.setFont(QFont("Outfit", 9))
        os_lbl.setStyleSheet("color: rgba(160,180,200,0.6); background: transparent;")
        os_row.addWidget(os_lbl)
        os_row.addStretch()
        layout.addLayout(os_row)

        # ── Timer ───────────────────────────────
        self._prev_net = psutil.net_io_counters()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)
        self.update_stats()

    def _divider(self, layout):
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(255,255,255,0.07); margin: 2px 0;")
        layout.addWidget(line)

    def update_stats(self):
        cpu  = int(psutil.cpu_percent())
        ram  = int(psutil.virtual_memory().percent)
        try:
            disk = int(psutil.disk_usage("C:\\").percent)
        except Exception:
            disk = int(psutil.disk_usage("/").percent)

        self.cpu_bar.setValue(cpu)
        self.ram_bar.setValue(ram)
        self.disk_bar.setValue(disk)

        self.cpu_val.setText(f"{cpu}%")
        self.ram_val.setText(f"{ram}%")
        self.disk_val.setText(f"{disk}%")

        # Network delta
        try:
            cur = psutil.net_io_counters()
            up  = max(0, (cur.bytes_sent - self._prev_net.bytes_sent) // 2048)
            dn  = max(0, (cur.bytes_recv - self._prev_net.bytes_recv) // 2048)
            self.net_val.setText(f"↑{up} ↓{dn} KB/s")
            self._prev_net = cur
        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        painter.fillPath(path, QColor(8, 14, 30, 210))
        from PyQt6.QtGui import QPen
        painter.setPen(QPen(QColor(39, 200, 245, 35), 1))
        painter.drawPath(path)

"""
os_shell/widgets/cyber_radar_hud.py — Cyber Threat Intelligence Radar HUD.
Rotating sci-fi network radar scanner displaying security telemetry.
"""
from __future__ import annotations
import math
import random
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QConicalGradient

class CyberRadarHUD(QWidget):
    """
    Floating security radar widget showing rotating sweep line, active firewall ports,
    and a threat index indicator.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 180)
        
        self.angle = 0.0
        self.threat_index = 0.01
        self.alert_blink = False
        self.tick_counter = 0
        
        # Telemetry Labels
        self.header_lbl = QLabel("SECURE RADAR SYSTEM", self)
        self.header_lbl.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        self.header_lbl.setStyleSheet("color: #10b981; background: transparent; letter-spacing: 1px;")
        self.header_lbl.move(18, 15)
        
        self.stats_lbl = QLabel(self)
        self.stats_lbl.setFont(QFont("Outfit", 8))
        self.stats_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        self.stats_lbl.setGeometry(130, 45, 160, 120)
        self.stats_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # 60 fps Timer for radar rotation & blinking indicators
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)
        
        self.update_stats()

    def _tick(self):
        # Rotate sweep line
        self.angle += 1.5
        if self.angle >= 360.0:
            self.angle -= 360.0
            
        self.tick_counter += 1
        # Blink alerts every 500ms
        if self.tick_counter % 30 == 0:
            self.alert_blink = not self.alert_blink
            
        # Randomly fluctuate threat level slightly for cyber aesthetic feel
        if self.tick_counter % 120 == 0:
            self.threat_index = max(0.00, min(1.00, self.threat_index + random.choice([-0.005, 0.005])))
            self.update_stats()
            
        self.update()

    def update_stats(self):
        txt = (
            f"SYSTEM INDEX: SAFE\n"
            f"THREAT RATIO: {self.threat_index * 100:.2f}%\n"
            f"FIREWALL: ACTIVE\n\n"
            f"PORT 80 (HTTP)   [ OK ]\n"
            f"PORT 443 (HTTPS) [ OK ]\n"
            f"PORT 8765 (WS)   [ OK ]"
        )
        self.stats_lbl.setText(txt)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Background Panel Card
        p.setPen(QPen(QColor(255, 255, 255, 20), 1.2))
        p.setBrush(QBrush(QColor(15, 23, 42, 170)))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 12.0, 12.0)
        
        # 2. Draw Radar Circle Scanner
        cx, cy = 65, 105
        R = 50
        
        # Concentric circles
        p.setPen(QPen(QColor(16, 185, 129, 30), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R, R)
        p.drawEllipse(QPointF(cx, cy), R * 0.7, R * 0.7)
        p.drawEllipse(QPointF(cx, cy), R * 0.4, R * 0.4)
        
        # Crosshair lines
        p.drawLine(QPointF(cx - R, cy), QPointF(cx + R, cy))
        p.drawLine(QPointF(cx, cy - R), QPointF(cx, cy + R))
        
        # Conical Sweep Gradient
        p.save()
        p.translate(cx, cy)
        p.rotate(-self.angle)
        
        sweep = QConicalGradient(QPointF(0, 0), 0)
        sweep.setColorAt(0.0, QColor(16, 185, 129, 100)) # Glowing neon green edge
        sweep.setColorAt(0.1, QColor(16, 185, 129, 20))
        sweep.setColorAt(0.5, QColor(16, 185, 129, 0)) # Faded tail
        sweep.setColorAt(1.0, QColor(16, 185, 129, 100))
        
        p.setBrush(QBrush(sweep))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-R, -R, R * 2, R * 2))
        p.restore()
        
        # 3. Blinking Red Threat indicator on top right
        alert_x, alert_y = 270, 18
        p.setPen(Qt.PenStyle.NoPen)
        if self.alert_blink:
            p.setBrush(QBrush(QColor(16, 185, 129))) # Safe green heartbeat pulse
        else:
            p.setBrush(QBrush(QColor(16, 185, 129, 50)))
        p.drawEllipse(QRectF(alert_x, alert_y, 8, 8))

import math
import random
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QPointF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QConicalGradient,
    QPen, QBrush, QFont, QPainterPath
)

# ─── States ───────────────────────────────────
IDLE       = "idle"
LISTENING  = "listening"
PROCESSING = "processing"
SPEAKING   = "speaking"


class AIOrb(QWidget):
    """
    Central animated AI Orb.
    Click  → trigger assistant / toggle listening
    States → idle | listening | processing | speaking
    """
    orb_clicked = pyqtSignal()

    SIZE = 130          # orb diameter

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE + 60, self.SIZE + 60)  # room for glow ring
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.state     = IDLE
        self._angle    = 0.0          # spin angle for ring
        self._pulse    = 0.0          # idle pulse phase
        self._wave     = [0.0] * 32   # audio waveform bars
        self._glow_r   = 0.0          # current glow radius offset

        self._tick = QTimer(self)
        self._tick.timeout.connect(self._animate)
        self._tick.start(30)          # ~33 FPS

    # ── Public API ─────────────────────────────
    def set_state(self, state: str):
        if self.state != state:
            self.state = state

    # ── Animation tick ─────────────────────────
    def _animate(self):
        self._pulse += 0.04
        self._angle  = (self._angle + 1.8) % 360

        if self.state == LISTENING:
            # Organic wave bars
            for i in range(len(self._wave)):
                self._wave[i] = abs(math.sin(self._pulse * 2 + i * 0.4)) * 0.8 + random.random() * 0.2
            self._glow_r = 10 + 6 * abs(math.sin(self._pulse))
        elif self.state == PROCESSING:
            self._glow_r = 14 + 4 * abs(math.sin(self._pulse * 3))
        elif self.state == SPEAKING:
            for i in range(len(self._wave)):
                self._wave[i] = abs(math.sin(self._pulse * 3 + i * 0.6)) * random.uniform(0.4, 1.0)
            self._glow_r = 8 + 8 * abs(math.sin(self._pulse * 2))
        else:
            self._glow_r = 4 + 3 * abs(math.sin(self._pulse * 0.5))

        self.update()

    # ── Mouse click ────────────────────────────
    def mousePressEvent(self, event):
        self.orb_clicked.emit()

    # ── Paint ──────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width()  // 2
        cy = self.height() // 2
        r  = self.SIZE // 2

        # ── Outer ambient glow ────────────────
        glow_color = self._state_color(alpha=0)
        glow_color2 = self._state_color(alpha=55 + int(self._glow_r * 2))
        glow_r = r + 20 + self._glow_r
        grd = QRadialGradient(cx, cy, glow_r)
        grd.setColorAt(0.0, self._state_color(alpha=40 + int(self._glow_r * 1.5)))
        grd.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grd))
        painter.drawEllipse(int(cx - glow_r), int(cy - glow_r),
                            int(glow_r * 2), int(glow_r * 2))

        # ── Spinning arc ring ─────────────────
        if self.state in (PROCESSING, LISTENING, SPEAKING):
            ring_r = r + 8
            arc_pen = QPen(self._state_color(alpha=200), 2.5)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            span = 280 if self.state == PROCESSING else 200
            painter.drawArc(
                int(cx - ring_r), int(cy - ring_r),
                int(ring_r * 2),  int(ring_r * 2),
                int(self._angle * 16), int(span * 16)
            )
            # counter arc
            arc_pen2 = QPen(self._accent_color(alpha=120), 1.5)
            painter.setPen(arc_pen2)
            painter.drawArc(
                int(cx - ring_r), int(cy - ring_r),
                int(ring_r * 2),  int(ring_r * 2),
                int((-self._angle * 0.7 + 90) * 16), int(120 * 16)
            )

        # ── Orb body ─────────────────────────
        body_grad = QRadialGradient(cx - r * 0.25, cy - r * 0.25, r * 1.1)
        body_grad.setColorAt(0.0, self._state_color(alpha=255).lighter(130))
        body_grad.setColorAt(0.5, self._state_color(alpha=220))
        body_grad.setColorAt(1.0, QColor(4, 8, 20, 240))
        painter.setBrush(QBrush(body_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # ── Inner highlight gloss ─────────────
        gloss = QRadialGradient(cx - r * 0.3, cy - r * 0.4, r * 0.55)
        gloss.setColorAt(0.0, QColor(255, 255, 255, 70))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(gloss))
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # ── Waveform bars (listening / speaking) ─
        if self.state in (LISTENING, SPEAKING):
            n = 18
            bar_w = 3
            gap = 4
            total = n * (bar_w + gap) - gap
            start_x = cx - total // 2
            max_bar = r * 0.55
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(n):
                h = int(max_bar * self._wave[i % len(self._wave)])
                x = start_x + i * (bar_w + gap)
                bar_col = self._state_color(alpha=180)
                painter.setBrush(QBrush(bar_col))
                painter.drawRoundedRect(x, cy - h // 2, bar_w, max(4, h), 1, 1)

        # ── Processing dots spinner ───────────
        if self.state == PROCESSING:
            dot_r = r * 0.65
            n_dots = 8
            for i in range(n_dots):
                a = math.radians(self._angle + i * (360 / n_dots))
                dx = cx + dot_r * math.cos(a)
                dy = cy + dot_r * math.sin(a)
                fade = int(220 * (i / n_dots))
                dc = self._state_color(alpha=fade)
                painter.setBrush(QBrush(dc))
                painter.drawEllipse(QPointF(dx, dy), 3, 3)

        # ── State label ───────────────────────
        painter.setPen(QPen(QColor(255, 255, 255, 200)))
        font = QFont("Outfit", 9, QFont.Weight.Medium)
        painter.setFont(font)
        lbl = {
            IDLE:       "PRIME",
            LISTENING:  "LISTENING",
            PROCESSING: "THINKING",
            SPEAKING:   "SPEAKING",
        }.get(self.state, "PRIME")
        painter.drawText(0, cy + r - 4, self.width(), 24,
                         Qt.AlignmentFlag.AlignHCenter, lbl)

    # ── Color helpers ─────────────────────────
    def _state_color(self, alpha=255) -> QColor:
        colors = {
            IDLE:       (39,  200, 245),
            LISTENING:  (0,   255, 120),
            PROCESSING: (245, 158,  11),
            SPEAKING:   (139,  92, 246),
        }
        r, g, b = colors.get(self.state, (39, 200, 245))
        return QColor(r, g, b, alpha)

    def _accent_color(self, alpha=255) -> QColor:
        r, g, b = (139, 92, 246)
        return QColor(r, g, b, alpha)

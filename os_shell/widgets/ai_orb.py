import math
import random
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient,
    QPen, QBrush, QFont, QPainterPath
)

# ─── States ───────────────────────────────────
IDLE       = "idle"
LISTENING  = "listening"
PROCESSING = "processing"
SPEAKING   = "speaking"


class AIOrb(QWidget):
    """
    Premium Animated AI Orb with a beautiful Circular Soundwave / Visualizer.
    Design: Glassmorphism center sphere, overlapping translucent liquid energy blobs,
    and a radial glowing neon circular visualizer ring.
    """
    orb_clicked = pyqtSignal()

    SIZE = 140  # Orb diameter

    def __init__(self, parent=None):
        super().__init__(parent)
        # Give ample room (300x300) for the 140px orb + circular visualizer waves extending outward
        self.setFixedSize(300, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.state = IDLE
        self._angle = 0.0          # Spin angle for rotation effects
        self._pulse = 0.0          # Time/breathing phase variable
        
        # Audio bands for the circular visualizer
        self._num_bands = 64
        self._bands = [0.0] * self._num_bands
        self._target_bands = [0.0] * self._num_bands
        
        # Animation loop (approx 50 FPS for buttery smooth motion)
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._animate)
        self._tick.start(20)

    # ── Public API ─────────────────────────────
    def set_state(self, state: str):
        if self.state != state:
            self.state = state

    # ── Animation Tick ─────────────────────────
    def _animate(self):
        self._pulse += 0.05
        # Dynamic spin speed based on state
        spin_speed = 3.0 if self.state == PROCESSING else (1.5 if self.state == LISTENING else 0.8)
        self._angle = (self._angle + spin_speed) % 360

        # Update targets and smooth bands
        for i in range(self._num_bands):
            if self.state == LISTENING:
                # Active audio spectrum visualization
                freq_mod = math.sin(self._pulse * 1.5 + i * 0.25)
                noise = random.uniform(0.1, 0.4) if i % 3 == 0 else random.uniform(0.0, 0.15)
                target = abs(freq_mod) * 0.75 + noise
            elif self.state == SPEAKING:
                # Vocal pattern representation
                vocal_envelope = math.sin(self._pulse * 2.0 + i * 0.15) * math.cos(self._pulse * 0.5 + i * 0.08)
                target = max(0.0, vocal_envelope * 0.9 + random.uniform(-0.1, 0.2))
            elif self.state == PROCESSING:
                # Pulsing corona/flare activity
                target = 0.35 + 0.15 * math.sin(self._pulse * 4.0 + i * 0.4)
            else:
                # Calm, breathing idle waves
                target = 0.12 + 0.08 * math.sin(self._pulse * 0.8 + i * 0.2)
            
            # Smooth interpolation (ease-out filter)
            self._bands[i] += (target - self._bands[i]) * 0.25

        self.update()

    # ── Mouse click ────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.orb_clicked.emit()

    # ── Paint ──────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r_base = self.SIZE / 2.0

        # Dynamic state colors
        core_color = self._get_state_color(1.0)
        glow_color = self._get_state_color(0.3)
        accent_color = self._get_accent_color()

        # ── 1. Circular Liquid Blobs (Siri-style glass energy layer) ──
        self._draw_liquid_blobs(painter, cx, cy, r_base)

        # ── 2. Circular Soundwave Visualizer (Neon Radial Bars) ──
        self._draw_circular_visualizer(painter, cx, cy, r_base, core_color, accent_color)

        # ── 3. Outer Sphere Ring ──
        ring_pen = QPen(QColor(255, 255, 255, 30), 1.5)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r_base + 3, r_base + 3)

        # ── 4. Main Glassmorphic Orb Body ──
        orb_grad = QRadialGradient(cx - r_base * 0.2, cy - r_base * 0.2, r_base)
        orb_grad.setColorAt(0.0, QColor(255, 255, 255, 35))
        orb_grad.setColorAt(0.4, QColor(core_color.red(), core_color.green(), core_color.blue(), 60))
        orb_grad.setColorAt(0.92, QColor(10, 16, 32, 230))
        orb_grad.setColorAt(1.0, QColor(4, 6, 12, 255))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(orb_grad))
        painter.drawEllipse(QPointF(cx, cy), r_base, r_base)

        # ── 5. Inner Pulsing Core ──
        core_r = r_base * (0.65 + 0.05 * math.sin(self._pulse * 1.5))
        core_grad = QRadialGradient(cx, cy, core_r)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 220))
        core_grad.setColorAt(0.2, QColor(core_color.red(), core_color.green(), core_color.blue(), 230))
        core_grad.setColorAt(0.65, QColor(core_color.red() // 2, core_color.green() // 2, core_color.blue() // 2, 100))
        core_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # ── 6. Futuristic Lens Flare / Highlights ──
        highlight = QRadialGradient(cx - r_base * 0.35, cy - r_base * 0.35, r_base * 0.5)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 80))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(highlight))
        painter.drawEllipse(QPointF(cx - r_base * 0.1, cy - r_base * 0.1), r_base * 0.9, r_base * 0.9)

        # ── 7. Text Status Indicator ──
        status_text = {
            IDLE: "PRIME OS",
            LISTENING: "LISTENING",
            PROCESSING: "THINKING",
            SPEAKING: "SPEAKING"
        }.get(self.state, "PRIME OS")

        painter.setPen(QPen(QColor(255, 255, 255, 210)))
        font = QFont("Outfit", 9, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        painter.setFont(font)
        
        # Center status text inside the lower half of the orb
        painter.drawText(int(cx - r_base), int(cy + r_base * 0.35), int(r_base * 2), 25,
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, status_text)

    # ── Render Helper: Siri-Style Blobs ────────────────────────────────
    def _draw_liquid_blobs(self, painter, cx, cy, r_base):
        # We draw 3 layers of translucent morphing shapes
        num_points = 72
        layers = [
            # (multiplier, speed_offset, color, scale_range)
            (0.18, 0.0, self._get_state_color(0.18), 1.05),
            (0.12, 2.1, self._get_accent_color(0.15), 1.15),
            (0.15, 4.2, self._get_state_color(0.12), 0.95)
        ]

        painter.setPen(Qt.PenStyle.NoPen)

        for i, (amp, phase_off, col, base_scale) in enumerate(layers):
            path = QPainterPath()
            first_point = None

            for pt in range(num_points):
                angle_deg = pt * (360.0 / num_points)
                rad = math.radians(angle_deg)
                
                # Morphing equation using multi-octave sine/cosine
                wave = math.sin(rad * 3.0 + self._pulse * 1.2 + phase_off) * \
                       math.cos(rad * 2.0 - self._pulse * 0.8 + phase_off)
                
                curr_r = r_base * (base_scale + amp * wave)
                x = cx + curr_r * math.cos(rad)
                y = cy + curr_r * math.sin(rad)

                if pt == 0:
                    path.moveTo(x, y)
                    first_point = QPointF(x, y)
                else:
                    path.lineTo(x, y)

            if first_point:
                path.lineTo(first_point)
            
            path.closeSubpath()
            painter.setBrush(QBrush(col))
            painter.drawPath(path)

    # ── Render Helper: Circular Visualizer ────────────────────────────
    def _draw_circular_visualizer(self, painter, cx, cy, r_base, primary_color, accent_color):
        base_r = r_base + 6.0
        max_height = 42.0

        for i in range(self._num_bands):
            # Dynamic angle with steady rotation
            angle_deg = i * (360.0 / self._num_bands) + self._angle
            rad = math.radians(angle_deg)
            
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            # Get amplitude for this frequency band
            amp = self._bands[i]
            
            # Start/End points of the radial bar
            start_x = cx + base_r * cos_a
            start_y = cy + base_r * sin_a
            end_x = cx + (base_r + amp * max_height) * cos_a
            end_y = cy + (base_r + amp * max_height) * sin_a

            # Gradient for the radial visualizer bar
            grad = QLinearGradient(start_x, start_y, end_x, end_y)
            grad.setColorAt(0.0, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 230))
            grad.setColorAt(0.7, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 180))
            grad.setColorAt(1.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))

            # Dynamic bar width based on visualizer activity
            bar_width = 2.0 + amp * 2.0
            pen = QPen(QBrush(grad), bar_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            
            painter.setPen(pen)
            painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))

    # ── State Color Palettes ──────────────────────────────────────────
    def _get_state_color(self, opacity=1.0) -> QColor:
        # Curated glowing modern palettes (neon & cyber themed)
        alpha = int(opacity * 255)
        colors = {
            IDLE:       (0, 191, 255),    # Deep neon cyan
            LISTENING:  (0, 245, 120),    # Emerald cyber green
            PROCESSING: (255, 191, 0),    # Solar bright yellow/amber
            SPEAKING:   (186, 85, 211),   # Orchid voice violet
        }
        r, g, b = colors.get(self.state, (0, 191, 255))
        return QColor(r, g, b, alpha)

    def _get_accent_color(self, opacity=1.0) -> QColor:
        alpha = int(opacity * 255)
        # Complimentary cyber gradients
        accents = {
            IDLE:       (138, 43, 226),   # Cyber purple accent
            LISTENING:  (0, 255, 235),    # Cyan/Aqua accent
            PROCESSING: (255, 80, 0),     # Cyberpunk red-orange
            SPEAKING:   (255, 0, 128),    # Intense hot pink
        }
        r, g, b = accents.get(self.state, (138, 43, 226))
        return QColor(r, g, b, alpha)

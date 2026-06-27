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
    Ultra-Premium Sparkling Cosmic AI Orb.
    Features:
      - Siri-style overlapping morphing liquid energy blobs
      - Radial circular audio visualizer ring
      - Orbiting 4-point glowing star sparkles (magic stardust escaping the core)
      - Inner shimmering quantum particles floating within the glass sphere
      - Slow-rotating multi-layered central lens flare star shimmer
      - Glassmorphic outer crust with HSL tailored state color styling
    """
    orb_clicked = pyqtSignal()

    SIZE = 145  # Orb diameter

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.state = IDLE
        self._angle = 0.0          # Core spin angle
        self._pulse = 0.0          # Shimmer/pulse phase

        # Audio frequency bands
        self._num_bands = 64
        self._bands = [0.0] * self._num_bands
        
        # Spawn stardust/sparkle particles
        self._particles = []
        self._init_particles()

        # Animation timer (approx 60 FPS for buttery smooth rendering)
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._animate)
        self._tick.start(16)

    def _init_particles(self):
        # Create 45 unique sparkles with various orbits, speeds, and sizes
        for i in range(45):
            self._particles.append({
                "angle": random.uniform(0, 360),
                "distance": random.uniform(20, 125),   # Distance from core center
                "speed": random.uniform(0.4, 1.4) * (1 if random.random() > 0.4 else -1),
                "size": random.uniform(1.2, 4.0),
                "is_star": random.random() > 0.6,      # 40% are 4-point diamond stars
                "blink_speed": random.uniform(0.04, 0.12),
                "blink_phase": random.uniform(0, 2 * math.pi),
                "color_shift": random.uniform(0.0, 1.0)
            })

    # ── Public API ─────────────────────────────
    def set_state(self, state: str):
        state = state.lower().strip()
        if state == "muted":
            state = IDLE
        if self.state != state:
            self.state = state

    # ── Animation Update ────────────────────────
    def _animate(self):
        self._pulse += 0.06
        # Core rotation speed based on state
        spin_speed = 3.5 if self.state == PROCESSING else (1.8 if self.state == LISTENING else 0.8)
        self._angle = (self._angle + spin_speed) % 360

        # Update audio bands/peaks smoothly
        for i in range(self._num_bands):
            if self.state == LISTENING:
                target = abs(math.sin(self._pulse * 1.5 + i * 0.25)) * 0.75 + random.uniform(0.0, 0.2)
            elif self.state == SPEAKING:
                target = max(0.0, math.sin(self._pulse * 2.0 + i * 0.15) * math.cos(self._pulse * 0.5 + i * 0.08) * 0.9 + random.uniform(-0.1, 0.2))
            elif self.state == PROCESSING:
                target = 0.3 + 0.15 * math.sin(self._pulse * 4.0 + i * 0.45)
            else:
                target = 0.1 + 0.06 * math.sin(self._pulse * 0.8 + i * 0.2)
            
            # Standard easing interpolation
            self._bands[i] += (target - self._bands[i]) * 0.25

        # Update sparkles/particles
        for p in self._particles:
            speed_mult = 2.8 if self.state == PROCESSING else (1.8 if self.state == LISTENING or self.state == SPEAKING else 1.0)
            p["angle"] = (p["angle"] + p["speed"] * speed_mult) % 360
            p["blink_phase"] += p["blink_speed"]

        self.update()

    # ── Mouse click ────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.orb_clicked.emit()

    # ── Paint Event ────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r_base = self.SIZE / 2.0

        primary_color = self._get_state_color(1.0)
        accent_color = self._get_accent_color(1.0)

        # ── 1. Background Siri-Style Liquid Energy Blobs ──
        self._draw_liquid_blobs(painter, cx, cy, r_base)

        # ── 2. Radial Circular Audio Visualizer Ring ──
        self._draw_circular_visualizer(painter, cx, cy, r_base, primary_color, accent_color)

        # ── 3. Draw Outer Orbiting Sparkles (Magic Stardust) ──
        self._draw_particles(painter, cx, cy, r_base, primary_color, accent_color, inside=False)

        # ── 4. Main Glassmorphic Outer Crust Sphere ──
        orb_grad = QRadialGradient(cx - r_base * 0.2, cy - r_base * 0.2, r_base)
        orb_grad.setColorAt(0.0, QColor(255, 255, 255, 45))
        orb_grad.setColorAt(0.4, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 50))
        orb_grad.setColorAt(0.9, QColor(8, 12, 28, 220))
        orb_grad.setColorAt(1.0, QColor(4, 6, 12, 255))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(orb_grad))
        painter.drawEllipse(QPointF(cx, cy), r_base, r_base)

        # Draw a subtle thin white edge highlight
        highlight_pen = QPen(QColor(255, 255, 255, 40), 1.0)
        painter.setPen(highlight_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r_base, r_base)

        # ── 5. Draw Inner Sparkling Particles (Floating inside the sphere) ──
        self._draw_particles(painter, cx, cy, r_base, primary_color, accent_color, inside=True)

        # ── 6. Rotating Center Star Shimmer (Lens Flare Effect) ──
        self._draw_center_shimmer(painter, cx, cy, primary_color, accent_color)

        # ── 7. Core Pulsing Glow ──
        core_r = r_base * (0.50 + 0.04 * math.sin(self._pulse * 2.0))
        core_grad = QRadialGradient(cx, cy, core_r)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        core_grad.setColorAt(0.25, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 230))
        core_grad.setColorAt(0.7, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 90))
        core_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # ── 8. Status Text ──
        status_text = {
            IDLE: "PRIME OS",
            LISTENING: "LISTENING",
            PROCESSING: "THINKING",
            SPEAKING: "SPEAKING"
        }.get(self.state, "PRIME OS")

        painter.setPen(QPen(QColor(255, 255, 255, 210)))
        font = QFont("Outfit", 9, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.8)
        painter.setFont(font)
        painter.drawText(int(cx - r_base), int(cy + r_base * 0.40), int(r_base * 2), 25,
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, status_text)

    # ── Render Helper: Siri-Style Blobs ────────────────────────────────
    def _draw_liquid_blobs(self, painter, cx, cy, r_base):
        num_points = 64
        layers = [
            (0.18, 0.0, self._get_state_color(0.14), 1.05),
            (0.14, 2.0, self._get_accent_color(0.12), 1.12),
            (0.16, 4.0, self._get_state_color(0.10), 0.96)
        ]
        painter.setPen(Qt.PenStyle.NoPen)
        for amp, phase_off, col, base_scale in layers:
            path = QPainterPath()
            first_point = None
            for pt in range(num_points):
                angle_deg = pt * (360.0 / num_points)
                rad = math.radians(angle_deg)
                wave = math.sin(rad * 3.0 + self._pulse * 1.4 + phase_off) * \
                       math.cos(rad * 2.0 - self._pulse * 0.9 + phase_off)
                
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
            angle_deg = i * (360.0 / self._num_bands) + self._angle * 0.5
            rad = math.radians(angle_deg)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            amp = self._bands[i]

            start_x = cx + base_r * cos_a
            start_y = cy + base_r * sin_a
            end_x = cx + (base_r + amp * max_height) * cos_a
            end_y = cy + (base_r + amp * max_height) * sin_a

            grad = QLinearGradient(start_x, start_y, end_x, end_y)
            grad.setColorAt(0.0, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 230))
            grad.setColorAt(0.7, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 180))
            grad.setColorAt(1.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))

            bar_width = 1.8 + amp * 2.2
            pen = QPen(QBrush(grad), bar_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))

            # Draw a tiny sparkling star dot at the tip of highly active visualizer bars!
            if amp > 0.45:
                sparkle_size = 2.0 + (amp * 2.5)
                sparkle_color = QColor(255, 255, 255, int(200 * amp))
                self._draw_star_shape(painter, end_x, end_y, sparkle_size, sparkle_color)

    # ── Render Helper: Sparkles & Particles ───────────────────────────
    def _draw_particles(self, painter, cx, cy, r_base, primary_color, accent_color, inside=True):
        # Draw particles depending on whether they are inside or outside the main glass orb
        for p in self._particles:
            dist = p["distance"]
            is_currently_inside = dist < (r_base - 10.0)

            # Filter particles based on placement request
            if inside != is_currently_inside:
                continue

            rad = math.radians(p["angle"])
            
            # Dynamic radius with wave ripple modulation when listening/speaking
            curr_dist = dist
            if not inside and self.state in (LISTENING, SPEAKING):
                avg_audio = sum(self._bands) / len(self._bands)
                curr_dist += avg_audio * 30.0 * math.sin(p["angle"] + self._pulse)

            x = cx + curr_dist * math.cos(rad)
            y = cy + curr_dist * math.sin(rad)

            # Blinking opacity
            blink = abs(math.sin(p["blink_phase"]))
            alpha = int(p["alpha"] * blink)
            if alpha < 10:
                continue

            # Interpolate particle color between state primary and accent
            t_col = p["color_shift"]
            r_c = int(primary_color.red() * (1 - t_col) + accent_color.red() * t_col)
            g_c = int(primary_color.green() * (1 - t_col) + accent_color.green() * t_col)
            b_c = int(primary_color.blue() * (1 - t_col) + accent_color.blue() * t_col)
            part_color = QColor(r_c, g_c, b_c, alpha)

            # Draw 4-point star sparkle or soft circular dust particle
            if p["is_star"]:
                self._draw_star_shape(painter, x, y, p["size"] * 2.0, part_color)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                # Create small radial glow for the particle
                grad = QRadialGradient(x, y, p["size"] * 1.5)
                grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
                grad.setColorAt(0.3, part_color)
                grad.setColorAt(1.0, QColor(r_c, g_c, b_c, 0))
                painter.setBrush(QBrush(grad))
                painter.drawEllipse(QPointF(x, y), p["size"] * 1.5, p["size"] * 1.5)

    # ── Render Helper: Central Star Shimmer Flare ─────────────────────
    def _draw_center_shimmer(self, painter, cx, cy, primary_color, accent_color):
        # Draw 2 layers of rotating diamond stars at the absolute center
        # Layer 1: Large glowing primary star
        star1_sz = 26.0 + 4.0 * math.sin(self._pulse * 2.5)
        star1_color = QColor(255, 255, 255, 210)
        
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle)
        self._draw_star_shape_centered(painter, 0, 0, star1_sz, star1_color)
        painter.restore()

        # Layer 2: Small accent star spinning in reverse
        star2_sz = 14.0 + 2.0 * math.cos(self._pulse * 1.8)
        star2_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 190)
        
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-self._angle * 1.5 + 45.0)
        self._draw_star_shape_centered(painter, 0, 0, star2_sz, star2_color)
        painter.restore()

    # ── Low-Level Shape Helpers ───────────────────────────────────────
    def _draw_star_shape(self, painter, x, y, sz, color):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        path = QPainterPath()
        path.moveTo(x, y - sz)
        path.quadTo(x, y, x + sz, y)
        path.quadTo(x, y, x, y + sz)
        path.quadTo(x, y, x - sz, y)
        path.quadTo(x, y, x, y - sz)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_star_shape_centered(self, painter, cx, cy, sz, color):
        # Draws a thin, sparkling 4-point star centered at coordinates
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        path = QPainterPath()
        # Make the spikes thinner for a more premium starry/sparkle appearance
        w = sz * 0.18
        path.moveTo(cx, cy - sz)
        path.quadTo(cx, cy, cx + w, cy)
        path.lineTo(cx + sz, cy)
        path.quadTo(cx, cy, cx, cy + w)
        path.lineTo(cx, cy + sz)
        path.quadTo(cx, cy, cx - w, cy)
        path.lineTo(cx - sz, cy)
        path.quadTo(cx, cy, cx, cy - w)
        path.closeSubpath()
        painter.drawPath(path)

    # ── Theme Colors ──────────────────────────────────────────────────
    def _get_state_color(self, opacity=1.0) -> QColor:
        alpha = int(opacity * 255)
        colors = {
            IDLE:       (0, 191, 255),    # Cyber cyan
            LISTENING:  (0, 245, 120),    # Emerald green
            PROCESSING: (255, 191, 0),    # Solar amber
            SPEAKING:   (186, 85, 211),   # Orchid voice violet
        }
        r, g, b = colors.get(self.state, (0, 191, 255))
        return QColor(r, g, b, alpha)

    def _get_accent_color(self, opacity=1.0) -> QColor:
        alpha = int(opacity * 255)
        accents = {
            IDLE:       (138, 43, 226),   # Violet accent
            LISTENING:  (0, 255, 235),    # Aqua accent
            PROCESSING: (255, 80, 0),     # Red-orange flare accent
            SPEAKING:   (255, 0, 128),    # Pink voice signature
        }
        r, g, b = accents.get(self.state, (138, 43, 226))
        return QColor(r, g, b, alpha)

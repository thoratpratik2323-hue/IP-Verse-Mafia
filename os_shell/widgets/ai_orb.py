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
    Ultra-Premium 3D Rotating Particle Sphere AI Orb.
    Features:
      - 3D Fibonacci Sphere node distribution
      - Rigorous 3D rotation transforms (Yaw/Pitch)
      - Perspective projection and depth sorting (painter's algorithm)
      - Depth-based connection lines (constellation network)
      - Responsive pulsing nucleus and audio-reactive scaling
    """
    orb_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.orb_size = 120  # Nice substantial default size
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.state = IDLE
        self.rot_x = 0.0
        self.rot_y = 0.0
        self._pulse = 0.0

        # Audio frequency bands
        self._num_bands = 64
        self._bands = [0.0] * self._num_bands
        
        # Load config if present
        saved_pos = self._load_config()

        # Initialize the 3D Fibonacci Sphere nodes
        self.num_nodes = 120
        self.nodes = []
        golden_ratio = (1 + math.sqrt(5)) / 2
        for i in range(self.num_nodes):
            phi = math.acos(1 - 2 * (i + 0.5) / self.num_nodes)
            theta = 2 * math.pi * i / golden_ratio
            x = math.cos(theta) * math.sin(phi)
            y = math.sin(theta) * math.sin(phi)
            z = math.cos(phi)
            self.nodes.append([x, y, z])

        # Animation timer (approx 60 FPS for buttery smooth rendering)
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._animate)
        self._tick.start(16)

        # Set default size
        widget_sz = int(self.orb_size * 2.8)
        self.setFixedSize(widget_sz, widget_sz)

    # ── Public API ─────────────────────────────
    def set_state(self, state: str):
        state = state.lower().strip()
        if state == "muted":
            state = IDLE
        if self.state != state:
            self.state = state

    def set_orb_size(self, size):
        self.orb_size = size
        widget_sz = int(size * 2.8)
        self.setFixedSize(widget_sz, widget_sz)
        self._save_config()
        self.update()

    def _save_config(self):
        import json
        from pathlib import Path
        config_path = Path("assets/orb_config.json")
        config_path.parent.mkdir(exist_ok=True)
        try:
            config = {
                "x": self.x(),
                "y": self.y(),
                "size": self.orb_size
            }
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[AIOrb] Failed to save config: {e}")

    def _load_config(self):
        import json
        from pathlib import Path
        config_path = Path("assets/orb_config.json")
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                self.orb_size = config.get("size", 120)
                widget_sz = int(self.orb_size * 2.8)
                self.setFixedSize(widget_sz, widget_sz)
                return config.get("x"), config.get("y")
            except Exception as e:
                print(f"[AIOrb] Failed to load config: {e}")
        return None

    # ── Animation Update ────────────────────────
    def _animate(self):
        self._pulse += 0.05
        
        # Rotation speeds based on state
        speed_mult = 1.0
        if self.state == PROCESSING:
            speed_mult = 3.0
        elif self.state == LISTENING:
            speed_mult = 1.8
        elif self.state == SPEAKING:
            speed_mult = 2.2
        else:
            speed_mult = 0.7
            
        self.rot_y = (self.rot_y + 0.012 * speed_mult) % (2 * math.pi)
        self.rot_x = (self.rot_x + 0.007 * speed_mult) % (2 * math.pi)

        # Update audio bands decay
        for i in range(self._num_bands):
            if self.state == LISTENING:
                target = abs(math.sin(self._pulse * 1.5 + i * 0.25)) * 0.85 + random.uniform(0.0, 0.15)
            elif self.state == SPEAKING:
                target = max(0.0, math.sin(self._pulse * 2.0 + i * 0.15) * math.cos(self._pulse * 0.5 + i * 0.08) * 0.95 + random.uniform(-0.05, 0.1))
            elif self.state == PROCESSING:
                target = 0.2 + 0.1 * math.sin(self._pulse * 4.0 + i * 0.45)
            else:
                target = 0.05 + 0.03 * math.sin(self._pulse * 0.8 + i * 0.2)
            
            self._bands[i] += (target - self._bands[i]) * 0.25

        # Smooth scale interpolation for pop-in and bounce transitions
        target_scale = 1.0
        if self.state == SPEAKING:
            avg_audio = sum(self._bands) / len(self._bands) if self._bands else 0.0
            target_scale = 1.08 + avg_audio * 0.85 + 0.08 * abs(math.sin(self._pulse * 3.0))
        elif self.state == LISTENING:
            target_scale = 1.12 + 0.08 * math.sin(self._pulse * 2.2)
            
        if not hasattr(self, "_current_scale"):
            self._current_scale = 1.0
            
        self._current_scale += (target_scale - self._current_scale) * 0.18

        self.update()

    # ── Mouse event overrides for Draggable Desktop behavior ──────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.orb_clicked.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    # ── Paint Event ────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r_base = (self.orb_size / 2.2) * getattr(self, "_current_scale", 1.0)

        primary_color = self._get_state_color(1.0)
        accent_color = self._get_accent_color(1.0)

        # ── 1. Audio Pulse Calculation ──
        avg_audio = sum(self._bands) / len(self._bands) if self._bands else 0.0
        pulse_factor = 1.0 + avg_audio * 1.6

        # ── 2. Rotate and Project 3D Nodes ──
        cos_y, sin_y = math.cos(self.rot_y), math.sin(self.rot_y)
        cos_x, sin_x = math.cos(self.rot_x), math.sin(self.rot_x)
        
        projected = []
        current_r = r_base * pulse_factor
        D = 2.4  # Camera distance
        
        for idx, (x, y, z) in enumerate(self.nodes):
            # Rotate Y
            x1 = x * cos_y - z * sin_y
            z1 = x * sin_y + z * cos_y
            # Rotate X
            y2 = y * cos_x - z1 * sin_x
            z2 = y * sin_x + z1 * cos_x
            
            # Perspective projection
            S = D / (D + z2)
            px = cx + x1 * current_r * S
            py = cy + y2 * current_r * S
            projected.append({
                'px': px,
                'py': py,
                'z': z2,
                'x1': x1,
                'y2': y2
            })

        # ── 3. Draw Connecting Edges ──
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                dx = self.nodes[i][0] - self.nodes[j][0]
                dy = self.nodes[i][1] - self.nodes[j][1]
                dz = self.nodes[i][2] - self.nodes[j][2]
                dist_sq = dx*dx + dy*dy + dz*dz
                
                # Connection threshold
                if dist_sq < 0.155:
                    p1 = projected[i]
                    p2 = projected[j]
                    
                    z_avg = (p1['z'] + p2['z']) / 2.0
                    alpha_factor = (1.0 - z_avg) / 2.0
                    edge_alpha = int(140 * alpha_factor * (0.3 + 0.7 * pulse_factor))
                    
                    if edge_alpha > 5:
                        edge_color = QColor(primary_color.red(), primary_color.green(), primary_color.blue(), edge_alpha)
                        pen = QPen(edge_color, 1.0)
                        painter.setPen(pen)
                        painter.drawLine(QPointF(p1['px'], p1['py']), QPointF(p2['px'], p2['py']))

        # ── 4. Draw Node Particles ──
        sorted_indices = sorted(range(self.num_nodes), key=lambda idx: projected[idx]['z'], reverse=True)
        
        for idx in sorted_indices:
            p = projected[idx]
            z_val = p['z']
            
            depth_factor = (1.0 - z_val) / 2.0
            node_sz = 1.8 + 2.8 * depth_factor
            
            node_alpha = int(255 * (0.2 + 0.8 * depth_factor))
            node_color = QColor(primary_color.red(), primary_color.green(), primary_color.blue(), node_alpha)
            
            if depth_factor > 0.75:
                painter.setPen(Qt.PenStyle.NoPen)
                grad = QRadialGradient(p['px'], p['py'], node_sz * 1.5)
                grad.setColorAt(0.0, QColor(255, 255, 255, node_alpha))
                grad.setColorAt(0.4, node_color)
                grad.setColorAt(1.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))
                painter.setBrush(QBrush(grad))
                painter.drawEllipse(QPointF(p['px'], p['py']), node_sz * 1.5, node_sz * 1.5)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(node_color))
                painter.drawEllipse(QPointF(p['px'], p['py']), node_sz, node_sz)

        # ── 5. Status Text ABOVE the sphere ──
        status_text = {
            IDLE: "PRIME OS",
            LISTENING: "LISTENING",
            PROCESSING: "THINKING",
            SPEAKING: "SPEAKING"
        }.get(self.state, "PRIME OS")

        painter.setPen(QPen(primary_color))
        font = QFont("Outfit", 10, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        painter.setFont(font)
        painter.drawText(int(cx - r_base * 1.5), int(cy - r_base - 38), int(r_base * 3), 25,
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, status_text)

    # ── Theme Colors ──────────────────────────────────────────────────
    def _get_state_color(self, opacity=1.0) -> QColor:
        alpha = int(opacity * 255)
        colors = {
            IDLE:       (0, 191, 255),
            LISTENING:  (0, 245, 120),
            PROCESSING: (255, 191, 0),
            SPEAKING:   (186, 85, 211),
        }
        r, g, b = colors.get(self.state, (0, 191, 255))
        return QColor(r, g, b, alpha)

    def _get_accent_color(self, opacity=1.0) -> QColor:
        alpha = int(opacity * 255)
        accents = {
            IDLE:       (138, 43, 226),
            LISTENING:  (0, 255, 235),
            PROCESSING: (255, 80, 0),
            SPEAKING:   (255, 0, 128),
        }
        r, g, b = accents.get(self.state, (138, 43, 226))
        return QColor(r, g, b, alpha)

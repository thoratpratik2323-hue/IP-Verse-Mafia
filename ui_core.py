from __future__ import annotations

import json
import math
import os
import platform
import random
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt,
    QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen,
    QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget, QSlider, QCheckBox, QComboBox,
)


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 148
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


class C:
    BG        = "#030712"  # Extremely rich deep obsidian background
    PANEL     = "rgba(15, 23, 42, 0.65)"  # Glassmorphic translucent panel background
    PANEL2    = "rgba(30, 41, 59, 0.45)"  # Soft glassmorphic secondary panel
    BORDER    = "rgba(59, 130, 246, 0.15)" # Delicate neon-blue translucent border
    BORDER_B  = "rgba(139, 92, 246, 0.25)" # Elegant neon-purple translucent border
    BORDER_A  = "rgba(6, 182, 212, 0.2)"  # Electric cyan border highlight
    PRI       = "#3B82F6"  # Electric cobalt blue
    PRI_DIM   = "#1D4ED8"  # Darker cobalt blue
    PRI_GHO   = "rgba(59, 130, 246, 0.12)" # Deep blue glowing halo
    ACC       = "#8B5CF6"  # Premium royal purple/violet
    ACC2      = "#A78BFA"  # Radiant violet highlight
    CYAN      = "#06B6D4"  # Futuristic electric cyan accent
    GREEN     = "#10B981"  # Neon emerald green (active)
    GREEN_D   = "#059669"  # Deep emerald green
    RED       = "#EF4444"  # Crimson warnings
    MUTED_C   = "#F43F5E"  # Rose blush for mute state
    TEXT      = "#F8FAFC"  # Ultra-crisp slate white
    TEXT_DIM  = "#475569"  # Deep slate gray text
    TEXT_MED  = "#94A3B8"  # Medium gray text
    WHITE     = "#FFFFFF"  # Pure white
    DARK      = "#020617"  # Deep slate black
    BAR_BG    = "#1E293B"  # Progress track background

def _load_theme():
    theme_file = CONFIG_DIR / "theme.json"
    if theme_file.exists():
        try:
            with open(theme_file, "r") as f:
                idx = json.load(f).get("theme_idx", 0)
                themes = [
                    {"BG": "#030712", "PANEL": "rgba(15, 23, 42, 0.65)", "PRI": "#3B82F6", "PRI_DIM": "#1D4ED8", "PRI_GHO": "rgba(59, 130, 246, 0.12)", "BORDER": "rgba(59, 130, 246, 0.15)", "ACC": "#8B5CF6", "ACC2": "#A78BFA", "CYAN": "#06B6D4", "GREEN": "#10B981"},
                    {"BG": "#1a0505", "PANEL": "rgba(40, 10, 10, 0.65)", "PRI": "#EF4444", "PRI_DIM": "#B91C1C", "PRI_GHO": "rgba(239, 68, 68, 0.12)", "BORDER": "rgba(239, 68, 68, 0.15)", "ACC": "#F43F5E", "ACC2": "#FB7185", "CYAN": "#FCA5A5", "GREEN": "#10B981"},
                    {"BG": "#020a05", "PANEL": "rgba(5, 30, 15, 0.65)", "PRI": "#10B981", "PRI_DIM": "#047857", "PRI_GHO": "rgba(16, 185, 129, 0.12)", "BORDER": "rgba(16, 185, 129, 0.15)", "ACC": "#34D399", "ACC2": "#6EE7B7", "CYAN": "#A7F3D0", "GREEN": "#3B82F6"},
                    {"BG": "#0a0014", "PANEL": "rgba(25, 10, 45, 0.65)", "PRI": "#D946EF", "PRI_DIM": "#C026D3", "PRI_GHO": "rgba(217, 70, 239, 0.12)", "BORDER": "rgba(217, 70, 239, 0.15)", "ACC": "#06B6D4", "ACC2": "#22D3EE", "CYAN": "#F472B6", "GREEN": "#10B981"},
                    {"BG": "#02020a", "PANEL": "rgba(10, 10, 30, 0.65)", "PRI": "#00f0ff", "PRI_DIM": "#008bb0", "PRI_GHO": "rgba(0, 240, 255, 0.12)", "BORDER": "rgba(0, 240, 255, 0.2)", "ACC": "#bd00ff", "ACC2": "#d666ff", "CYAN": "#00ffff", "GREEN": "#39ff14"}
                ]
                if 0 <= idx < len(themes):
                    for k, v in themes[idx].items():
                        setattr(C, k, v)
        except Exception:
            pass

_load_theme()


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c

class _SysMetrics:
    def __init__(self):
        self.cpu  = 0.0
        self.mem  = 0.0
        self.net  = 0.0   
        self.gpu  = -1.0  
        self.tmp  = -1.0  
        self._lock = threading.Lock()
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(1.5)

    def _update(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        nc  = psutil.net_io_counters()
        now = time.time()
        dt  = now - self._last_net_t
        if dt > 0:
            sent = (nc.bytes_sent - self._last_net.bytes_sent) / dt
            recv = (nc.bytes_recv - self._last_net.bytes_recv) / dt
            net  = (sent + recv) / (1024 * 1024)
        else:
            net = 0.0
        self._last_net   = nc
        self._last_net_t = now

        gpu = self._get_gpu()

        tmp = self._get_temp()

        with self._lock:
            self.cpu = cpu
            self.mem = mem
            self.net = net
            self.gpu = gpu
            self.tmp = tmp

    def _get_gpu(self) -> float:
        # NVIDIA
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                vals = [float(v.strip()) for v in r.stdout.strip().split("\n") if v.strip()]
                if vals:
                    return sum(vals) / len(vals)
        except Exception:
            pass

        # AMD (Linux)
        if _OS == "Linux":
            try:
                r = subprocess.run(
                    ["rocm-smi", "--showuse", "--csv"],
                    capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0:
                    for line in r.stdout.strip().split("\n"):
                        parts = line.split(",")
                        if len(parts) >= 2:
                            try:
                                return float(parts[1].strip().replace("%", ""))
                            except ValueError:
                                pass
            except Exception:
                pass

            # Intel GPU (Linux)
            try:
                r = subprocess.run(
                    ["intel_gpu_top", "-J", "-s", "500"],
                    capture_output=True, text=True, timeout=1
                )
                if r.returncode == 0 and "Render/3D" in r.stdout:
                    import re
                    m = re.search(r'"busy":\s*([\d.]+)', r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        # macOS — powermetrics (GPU Engine)
        if _OS == "Darwin":
            try:
                r = subprocess.run(
                    ["sudo", "-n", "powermetrics", "-n", "1", "-i", "500",
                     "--samplers", "gpu_power"],
                    capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0 and "GPU" in r.stdout:
                    import re
                    m = re.search(r'GPU\s+Active:\s+([\d.]+)%', r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        return -1.0

    def _get_temp(self) -> float:
        try:
            temps = psutil.sensors_temperatures()
            candidates = ["coretemp", "k10temp", "cpu_thermal", "acpitz",
                          "cpu-thermal", "zenpower", "it8688"]
            for name in candidates:
                if name in temps:
                    entries = temps[name]
                    if entries:
                        return entries[0].current
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except Exception:
            pass
        if _OS == "Darwin":
            try:
                r = subprocess.run(
                    ["osx-cpu-temp"], capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0:
                    import re
                    m = re.search(r"([\d.]+)", r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        if _OS == "Windows":
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "(Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi).CurrentTemperature"],
                    capture_output=True, text=True, timeout=3
                )
                if r.returncode == 0 and r.stdout.strip():
                    raw = float(r.stdout.strip().split("\n")[0])
                    return (raw / 10.0) - 273.15
            except Exception:
                pass

        return -1.0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu": self.cpu,
                "mem": self.mem,
                "net": self.net,
                "gpu": self.gpu,
                "tmp": self.tmp,
            }


_metrics = _SysMetrics()

class HudCanvas(QWidget):
    def __init__(self, face_path: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "LISTENING"
        self.compact_mode = False

        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 55.0
        self._tgt_halo   = 55.0
        self._last_t     = time.time()
        self._blink      = True
        self._blink_tick = 0
        
        # Organic morphing core variables
        self._blob_angles = [0.0, 120.0, 240.0]
        self._blob_phases = [0.0, 0.0, 0.0]
        self._voice_level = 0.0
        self._tgt_voice_level = 0.0
        
        # Ambient starfield particles (Cosmic space theme!)
        self._ambient_particles: list[list[float]] = []
        for _ in range(80):  # More stars for a richer space theme!
            self._ambient_particles.append([
                random.uniform(0, 1000),  # X
                random.uniform(0, 1000),  # Y
                random.uniform(0.8, 2.4), # Size
                random.uniform(0.08, 0.25),# Slow drifting speed
                random.uniform(0.15, 0.55),# Opacity
                random.choice([0, 1, 2]), # Color Type: 0=White, 1=Cyan/Blue, 2=Gold
                random.uniform(0, 2 * math.pi), # Twinkle Phase Offset
                random.uniform(0.015, 0.045) # Twinkle Speed
            ])

        self._shooting_stars = [] # Shooting stars (meteors) tracking

        # Swirling particles for THINKING state
        self._orbit_particles: list[list[float]] = []
        for i in range(24):
            self._orbit_particles.append([
                random.uniform(0, 360), # Angle
                random.uniform(1.2, 2.8), # Orbital Speed
                random.uniform(8, 14),   # Distance variance
                random.uniform(1.0, 2.2) # Size
            ])

        self._particles: list[list[float]] = []

        # Sci-Fi HUD Upgrades setup
        self.setMouseTracking(True)
        self._mouse_pos = QPointF(-1000.0, -1000.0)
        self._ring_angle_1 = 0.0
        self._ring_angle_2 = 0.0
        self._ticker_text = (
            " ◈  IP PRIME SYSTEM CORES OPERATIONAL  "
            "◈  NEURAL CONNECTIVITY SECURED  "
            "◈  RAG VECTOR SYNC COMPLETE  "
            "◈  WAKE WORD SYSTEM ALWAYS-ON ACTIVE  "
            "◈  COGNITIVE PROCESSING ONLINE  "
            "◈  UPLINK SECURED VIA EMULATED TERMINAL GRIDS  "
            "◈  AUTONOMOUS HEARTBEAT HEARTY & STABLE  "
        )
        self._ticker_offset = 0.0

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(50)

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.position()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._mouse_pos = QPointF(-1000.0, -1000.0)
        super().leaveEvent(event)

    def set_voice_level(self, level: float):
        """Set voice level from main.py audio output."""
        self._tgt_voice_level = max(0.0, min(1.0, level))

    def _step(self):
        # Dynamically scale FPS to conserve massive CPU resources!
        # If active (speaking/thinking/processing), run at ~30 FPS (33ms).
        # If idle (listening/muted), drop to ~20 FPS (50ms) to save CPU.
        target_interval = 33 if (self.speaking or self.state in ("THINKING", "PROCESSING")) else 50
        if self._tmr.interval() != target_interval:
            self._tmr.setInterval(target_interval)

        self._tick += 1
        now = time.time()
        
        # Phase tick update
        if now - self._last_t > (0.10 if self.speaking else 0.4):
            if self.speaking:
                self._tgt_scale = random.uniform(1.04, 1.15)
                self._tgt_halo  = random.uniform(120, 180)
            elif self.muted:
                self._tgt_scale = random.uniform(0.98, 1.01)
                self._tgt_halo  = random.uniform(20, 35)
            else: # LISTENING / THINKING
                self._tgt_scale = random.uniform(0.99, 1.03)
                self._tgt_halo  = random.uniform(50, 75)
            self._last_t = now

        sp = 0.28 if self.speaking else 0.12
        self._scale += (self._tgt_scale - self._scale) * sp
        self._halo  += (self._tgt_halo  - self._halo)  * sp

        # Voice level — live mic via set_voice_level(), else animated fallback
        if self.speaking:
            lvl_tgt = self._tgt_voice_level if self._tgt_voice_level > 0.01 else random.uniform(0.2, 0.95)
        else:
            lvl_tgt = 0.0
            self._tgt_voice_level = 0.0
        self._voice_level += (lvl_tgt - self._voice_level) * 0.22

        # Rotate blobs & advance shape phases
        rot_speeds = [0.65, -0.4, 0.8] if self.speaking else [0.22, -0.12, 0.35]
        if self.state in ("THINKING", "PROCESSING"):
            rot_speeds = [1.2, -0.9, 1.6]
            
        for i in range(3):
            self._blob_angles[i] = (self._blob_angles[i] + rot_speeds[i]) % 360
            self._blob_phases[i] = (self._blob_phases[i] + (0.06 if self.speaking else 0.024)) % (2 * math.pi)

        # Update HUD rings rotation angles based on active state
        ring_speed_1 = 2.2 if (self.speaking or self.state in ("THINKING", "PROCESSING")) else 0.45
        ring_speed_2 = -3.0 if (self.speaking or self.state in ("THINKING", "PROCESSING")) else -0.65
        self._ring_angle_1 = (self._ring_angle_1 + ring_speed_1) % 360
        self._ring_angle_2 = (self._ring_angle_2 + ring_speed_2) % 360

        # Ambient background particles drifting
        W, H = self.width(), self.height()
        for p in self._ambient_particles:
            p[1] -= p[3] # Upward motion
            if p[1] < 0:
                p[1] = H if H > 0 else 600
                p[0] = random.uniform(0, W if W > 0 else 800)

        # Update shooting stars
        updated_stars = []
        for star in self._shooting_stars:
            # star: [x, y, dx, dy, length, life, max_life, base_op]
            star[0] += star[2] # Update X position
            star[1] += star[3] # Update Y position
            star[5] -= 1       # Decrease life frames remaining
            if star[5] > 0:
                updated_stars.append(star)
        self._shooting_stars = updated_stars

        # Randomly spawn a shooting star
        if len(self._shooting_stars) < 2 and random.random() < 0.003:
            s_w = W if W > 0 else 800
            s_h = H if H > 0 else 600
            start_x = random.uniform(0, s_w)
            start_y = random.uniform(0, s_h * 0.4) # Spawn in the upper sky region
            dx = random.uniform(5.0, 11.0) * random.choice([-1.0, 1.0])
            dy = random.uniform(3.5, 7.5)
            life = random.randint(18, 30)
            length = random.uniform(40.0, 80.0)
            self._shooting_stars.append([start_x, start_y, dx, dy, length, life, life, 1.0])

        # Orbit swirling particles (THINKING state)
        if self.state in ("THINKING", "PROCESSING"):
            for op in self._orbit_particles:
                op[0] = (op[0] + op[1]) % 360

        # Speak explosion particles
        if self.speaking and random.random() < 0.22:
            cx, cy = self.width() / 2, self.height() / 2
            ang = random.uniform(0, 2 * math.pi)
            fw  = min(self.width(), self.height())
            r_s = fw * 0.16
            self._particles.append([
                cx + math.cos(ang) * r_s, cy + math.sin(ang) * r_s,
                math.cos(ang) * random.uniform(1.2, 3.2),
                math.sin(ang) * random.uniform(1.2, 3.2) - 0.2, 1.0
            ])
            
        self._particles = [
            [pt[0]+pt[2], pt[1]+pt[3], pt[2]*0.96, pt[3]*0.96, pt[4]-0.032]
            for pt in self._particles if pt[4] > 0
        ]

        self._blink_tick += 1
        if self._blink_tick >= 42:
            self._blink = not self._blink
            self._blink_tick = 0
        self.update()

    def _get_blob_path(self, cx: float, cy: float, base_r: float, wave_amp: float, freq: float, phase: float, rotation_deg: float) -> QPainterPath:
        path = QPainterPath()
        points = 90
        first_pt = None
        for i in range(points):
            angle_rad = i * (2 * math.pi / points)
            r = base_r + wave_amp * math.sin(freq * angle_rad + phase)
            rot_rad = math.radians(rotation_deg)
            total_rad = angle_rad + rot_rad
            x = cx + r * math.cos(total_rad)
            y = cy + r * math.sin(total_rad)
            if i == 0:
                path.moveTo(x, y)
                first_pt = QPointF(x, y)
            else:
                path.lineTo(x, y)
        if first_pt:
            path.lineTo(first_pt)
        return path

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw = min(W, H)

        if self.compact_mode:
            path = QPainterPath()
            path.addEllipse(QRectF(cx - fw/2, cy - fw/2, fw, fw))
            p.setClipPath(path)
        
        # 1. Base deep dark cosmic background
        p.fillRect(self.rect(), qcol("#020308"))

        # Slow-drifting cosmic purple nebula clouds
        purp_angle = self._tick * 0.002
        purp_cx = cx + math.cos(purp_angle) * (W * 0.15)
        purp_cy = cy + math.sin(purp_angle * 1.3) * (H * 0.12)
        purp_grad = QRadialGradient(purp_cx, purp_cy, fw * 0.65)
        purp_grad.setColorAt(0.0, qcol("#1f0a3d", 85))  # Soft violet glow
        purp_grad.setColorAt(0.5, qcol("#08031d", 35))
        purp_grad.setColorAt(1.0, qcol("#020308", 0))
        p.fillRect(self.rect(), QBrush(purp_grad))

        # Slow-drifting cosmic cyan/teal nebula clouds
        teal_angle = -self._tick * 0.0035
        teal_cx = cx + math.cos(teal_angle) * (W * 0.18)
        teal_cy = cy + math.sin(teal_angle * 0.7) * (H * 0.15)
        teal_grad = QRadialGradient(teal_cx, teal_cy, fw * 0.55)
        teal_grad.setColorAt(0.0, qcol("#03253a", 75))  # Soft space teal nebula
        teal_grad.setColorAt(0.6, qcol("#010d18", 30))
        teal_grad.setColorAt(1.0, qcol("#020308", 0))
        p.fillRect(self.rect(), QBrush(teal_grad))

        # Deep center core space aura
        bg_grad = QRadialGradient(cx, cy, fw * 0.5)
        bg_grad.setColorAt(0.0, qcol("#060b18", 110))
        bg_grad.setColorAt(0.7, qcol(C.BG, 70))
        bg_grad.setColorAt(1.0, qcol("#010206", 0))
        p.fillRect(self.rect(), QBrush(bg_grad))

        # 2. Ambient starfield particles with colors and twinkle modulation
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self._ambient_particles:
            # pt layout: [X, Y, Size, Speed, BaseOpacity, ColorType, TwinkleOffset, TwinkleSpeed]
            size = pt[2]
            base_opacity = pt[4] if len(pt) > 4 else 0.3
            color_type = pt[5] if len(pt) > 5 else 0
            twinkle_offset = pt[6] if len(pt) > 6 else 0.0
            twinkle_speed = pt[7] if len(pt) > 7 else 0.03
            
            # Twinkle modulation
            twinkle = math.sin(self._tick * twinkle_speed + twinkle_offset)
            opacity_factor = 0.55 + 0.45 * twinkle
            opacity = int(max(0, min(255, base_opacity * opacity_factor * 255)))
            
            # Select cosmic color
            if color_type == 1:
                c_str = C.CYAN if self.state in ("THINKING", "PROCESSING") else "#8ce3ff"
            elif color_type == 2:
                c_str = "#ffd88c"
            else:
                c_str = "#ffffff"
                
            col = qcol(c_str, opacity)
            p.setBrush(QBrush(col))
            p.drawEllipse(QPointF(pt[0], pt[1]), size, size)
            
            # Cross star flare glow for bright, larger stars at twinkle peak
            if size > 1.7 and twinkle > 0.82:
                flare_len = size * 2.2
                p.setPen(QPen(qcol(c_str, int(opacity * 0.35)), 0.6))
                p.drawLine(QPointF(pt[0] - flare_len, pt[1]), QPointF(pt[0] + flare_len, pt[1]))
                p.drawLine(QPointF(pt[0], pt[1] - flare_len), QPointF(pt[0], pt[1] + flare_len))
                p.setPen(Qt.PenStyle.NoPen)

        # 2b. Cosmic Shooting Stars (Meteors) rendering
        for star in self._shooting_stars:
            sx_val, sy_val, dx, dy, length, life, max_life, base_op = star
            life_pct = life / max_life
            opacity = int(255 * life_pct * base_op)
            if opacity <= 0:
                continue
                
            # Star head
            p.setBrush(QBrush(qcol("#ffffff", opacity)))
            p.drawEllipse(QPointF(sx_val, sy_val), 1.4, 1.4)
            
            # Gradient trailing tail
            trail_grad = QLinearGradient(QPointF(sx_val, sy_val), QPointF(sx_val - dx * 2.2, sy_val - dy * 2.2))
            trail_grad.setColorAt(0.0, qcol("#aae5ff", opacity))
            trail_grad.setColorAt(0.4, qcol("#8556ff", int(opacity * 0.6)))
            trail_grad.setColorAt(1.0, qcol("#020308", 0))
            
            p.setPen(QPen(QBrush(trail_grad), 1.2))
            p.drawLine(QPointF(sx_val, sy_val), QPointF(sx_val - dx * 2.2, sy_val - dy * 2.2))
            p.setPen(Qt.PenStyle.NoPen)

        # Constellation network lines
        max_dist = 85.0
        for i in range(len(self._ambient_particles)):
            p1 = self._ambient_particles[i]
            for j in range(i + 1, len(self._ambient_particles)):
                p2 = self._ambient_particles[j]
                dx = p1[0] - p2[0]
                dy = p1[1] - p2[1]
                dist = math.hypot(dx, dy)
                if dist < max_dist:
                    alpha = int(35 * (1.0 - dist / max_dist))
                    p.setPen(QPen(qcol(C.BORDER, alpha), 0.75))
                    p.drawLine(QPointF(p1[0], p1[1]), QPointF(p2[0], p2[1]))
            
            # Interactive mouse highlight
            if hasattr(self, "_mouse_pos") and self._mouse_pos.x() > -500:
                mdx = p1[0] - self._mouse_pos.x()
                mdy = p1[1] - self._mouse_pos.y()
                mdist = math.hypot(mdx, mdy)
                if mdist < 120.0:
                    m_alpha = int(45 * (1.0 - mdist / 120.0))
                    p.setPen(QPen(qcol(C.CYAN, m_alpha), 0.8))
                    p.drawLine(QPointF(p1[0], p1[1]), self._mouse_pos)
                    p.setBrush(QBrush(qcol(C.CYAN, m_alpha * 2)))
                    p.drawEllipse(QPointF(p1[0], p1[1]), p1[2] * 1.5, p1[2] * 1.5)

        # 3. Soft background glowing aura behind the core
        aura_rad = fw * 0.44 * self._scale
        aura_grad = QRadialGradient(cx, cy, aura_rad)
        
        if self.muted:
            glow_c, glow_a = C.MUTED_C, 65
        elif self.speaking:
            glow_c, glow_a = C.ACC, int(70 + 40 * self._voice_level)
        elif self.state in ("THINKING", "PROCESSING"):
            glow_c, glow_a = C.CYAN, 90
        else: # LISTENING
            glow_c, glow_a = C.PRI, 75
            
        aura_grad.setColorAt(0.0, qcol(glow_c, glow_a))
        aura_grad.setColorAt(0.5, qcol(glow_c, int(glow_a * 0.35)))
        aura_grad.setColorAt(1.0, qcol(C.BG, 0))
        p.setBrush(QBrush(aura_grad))
        p.drawEllipse(QRectF(cx - aura_rad, cy - aura_rad, aura_rad * 2, aura_rad * 2))

        # 4. Organic morphing core portal
        # Setup blob parameters based on active state
        if self.muted:
            base_r = fw * 0.18 * self._scale
            amp    = fw * 0.006
            freqs  = [2, 3, 2]
            colors = [(C.MUTED_C, 85), (C.ACC, 50), (C.PRI, 35)]
        elif self.speaking:
            base_r = fw * (0.20 + 0.05 * self._voice_level) * self._scale
            amp    = fw * (0.02 + 0.07 * self._voice_level)
            freqs  = [3, 4, 3]
            colors = [(C.ACC, 110), (C.PRI, 85), (C.MUTED_C, 65)]
        elif self.state in ("THINKING", "PROCESSING"):
            base_r = fw * 0.20 * self._scale
            amp    = fw * 0.038
            freqs  = [5, 6, 5]
            colors = [(C.ACC2, 100), (C.ACC, 70), (C.CYAN, 65)]
        else: # LISTENING
            base_r = fw * 0.19 * self._scale
            amp    = fw * 0.016 + 5 * math.sin(self._tick * 0.05)
            freqs  = [3, 4, 3]
            colors = [(C.PRI, 95), (C.ACC, 65), (C.CYAN, 55)]

        # Dynamic Rotating Cyber-Rings (HUD Rings)
        r1 = base_r + 35
        r2 = base_r + 55
        p.save()
        p.translate(cx, cy)
        
        # Ring 1 (Dashed)
        p.save()
        p.rotate(self._ring_angle_1)
        pen1 = QPen(qcol(C.CYAN, 75), 1.25)
        pen1.setDashPattern([12.0, 8.0])
        p.setPen(pen1)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-r1, -r1, r1 * 2, r1 * 2))
        p.restore()
        
        # Ring 2 (Dotted/Dashed reverse)
        p.save()
        p.rotate(self._ring_angle_2)
        pen2 = QPen(qcol(C.ACC, 55), 1.0)
        pen2.setDashPattern([4.0, 12.0])
        p.setPen(pen2)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-r2, -r2, r2 * 2, r2 * 2))
        p.restore()
        
        p.restore()

        # Draw overlapping translucent morphing blobs
        for i in range(3):
            path = self._get_blob_path(
                cx, cy, base_r - i * 8, amp, freqs[i],
                self._blob_phases[i], self._blob_angles[i]
            )
            p.setBrush(QBrush(qcol(colors[i][0], colors[i][1])))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(path)

        # 5. Celestial orbiting particles (THINKING / PROCESSING)
        if self.state in ("THINKING", "PROCESSING"):
            orbit_r = base_r + 28
            p.setPen(Qt.PenStyle.NoPen)
            for op in self._orbit_particles:
                ang_rad = math.radians(op[0])
                rad_dist = orbit_r + op[2]
                op_x = cx + rad_dist * math.cos(ang_rad)
                op_y = cy + rad_dist * math.sin(ang_rad)
                
                # Glowing trail effect
                opacity = max(0, min(255, int(180 * (0.4 + 0.6 * math.sin(ang_rad)))))
                p.setBrush(QBrush(qcol(C.CYAN, opacity)))
                p.drawEllipse(QPointF(op_x, op_y), op[3], op[3])

        # 6. Explosive sound particles
        for pt in self._particles:
            a = max(0, min(255, int(pt[4] * 230)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.CYAN if random.random() > 0.5 else C.PRI, a)))
            p.drawEllipse(QPointF(pt[0], pt[1]), 2.2, 2.2)

        # 8. Translucent State Pill Badge
        if not self.compact_mode:
            sy = cy + fw * 0.38
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            
            if self.muted:
                badge_txt, text_col, bg_col, border_col = "MUTED", qcol(C.MUTED_C), qcol(C.MUTED_C, 25), qcol(C.MUTED_C, 80)
            elif self.speaking:
                badge_txt, text_col, bg_col, border_col = "SPEAKING", qcol(C.ACC2), qcol(C.ACC, 25), qcol(C.ACC, 80)
            elif self.state in ("THINKING", "PROCESSING"):
                badge_txt, text_col, bg_col, border_col = self.state, qcol(C.CYAN), qcol(C.CYAN, 25), qcol(C.CYAN, 80)
            elif self.state == "LISTENING":
                badge_txt, text_col, bg_col, border_col = "LISTENING", qcol(C.GREEN), qcol(C.GREEN, 25), qcol(C.GREEN, 80)
            else:
                badge_txt, text_col, bg_col, border_col = self.state, qcol(C.PRI), qcol(C.PRI_GHO, 50), qcol(C.PRI, 80)

            spaced_txt = "  ".join(list(badge_txt))
            fm = p.fontMetrics()
            txt_w = fm.horizontalAdvance(spaced_txt)
            txt_h = fm.height()
            
            pill_w = txt_w + 30
            pill_h = txt_h + 10
            pill_x = cx - pill_w / 2
            pill_y = sy - 4
            
            p.setBrush(QBrush(bg_col))
            p.setPen(QPen(border_col, 1))
            p.drawRoundedRect(QRectF(pill_x, pill_y, pill_w, pill_h), pill_h / 2, pill_h / 2)
            
            p.setPen(QPen(text_col))
            p.drawText(QRectF(pill_x, pill_y, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter, spaced_txt)

            # 9. Three anti-aliased rippling bezier waveforms
            wy = sy + 38
            p.setPen(Qt.PenStyle.NoPen)
            
            waves = [
                (C.PRI,   70,  self._tick * 0.08,        0.016, 1.0),
                (C.ACC,   50,  self._tick * 0.11 + 2.0,  0.024, 0.7),
                (C.CYAN,  45,  self._tick * 0.06 + 4.0,  0.012, 0.45),
            ]
            
            for color, alpha, phase, freq, amp_fac in waves:
                path = QPainterPath()
                first = True
                
                if self.muted:
                    base_amp = 1.0
                elif self.speaking:
                    base_amp = (14.0 + 32.0 * self._voice_level) * amp_fac
                elif self.state in ("THINKING", "PROCESSING"):
                    base_amp = 5.0 * amp_fac
                else: # LISTENING
                    base_amp = (4.5 + 2.5 * math.sin(self._tick * 0.04)) * amp_fac
                    
                steps = 42
                dx = W / steps
                for i in range(steps + 1):
                    x = i * dx
                    # Smooth sine envelope to fade waves to straight lines at edges
                    envelope = math.sin(i / steps * math.pi)
                    y = wy + base_amp * envelope * math.sin(x * freq + phase)
                    if first:
                        path.moveTo(x, y)
                        first = False
                    else:
                        path.lineTo(x, y)
                
                p.setPen(QPen(qcol(color, alpha), 2))
                p.drawPath(path)


    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: #020810;
                color: #e2e8f0;
                border: 1px solid {C.PRI};
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 10px;
            }}
            QMenu::item {{
                padding: 6px 14px;
            }}
            QMenu::item:selected {{
                background-color: rgba(59, 130, 246, 0.12);
                color: {C.PRI};
            }}
        """)
        min_action = menu.addAction("─ MINIMIZE CORE")
        exit_action = menu.addAction("✕ EXIT CORE")
        action = menu.exec(self.mapToGlobal(event.pos()))
        if action == min_action:
            self.window().showMinimized()
        elif action == exit_action:
            self.window().close()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, "_drag_pos") and self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

class MetricBar(QWidget):

    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0       # 0–100
        self._text  = "--"
        self.setFixedHeight(44)
        self.setMinimumWidth(80)

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setBrush(QBrush(qcol(C.PANEL2)))
        p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 8, 8)

        bar_h   = 5
        bar_y   = H - bar_h - 8
        bar_w   = W - 16
        bar_x   = 8
        fill_w  = int(bar_w * self._value / 100)

        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2.5, 2.5)

        if self._value > 85:
            bar_col = qcol(C.RED)
        elif self._value > 65:
            bar_col = qcol(C.ACC)
        else:
            bar_col = qcol(self._color)

        if fill_w > 0:
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2.5, 2.5)
            
            # Glow dot at the tip of progress track
            dot_r = 4.0
            dot_cx = bar_x + fill_w
            dot_cy = bar_y + bar_h / 2.0
            p.setBrush(QBrush(bar_col))
            p.setPen(QPen(qcol("#ffffff"), 1))
            p.drawEllipse(QPointF(dot_cx, dot_cy), dot_r, dot_r)

        p.setFont(QFont("Segoe UI Semibold", 8))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(10, 6, 80, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 5, W - 10, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)

class MetricGraph(QWidget):
    def __init__(self, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setMinimumWidth(80)
        self._color = color
        self._history = [0.0] * 60
        
    def add_value(self, val: float):
        self._history.append(val)
        if len(self._history) > 60:
            self._history.pop(0)
        self.update()
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        
        # Transparent background card
        p.setBrush(QBrush(qcol(C.PANEL2)))
        p.setPen(QPen(qcol(C.BORDER_A, 50), 0.5))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 6, 6)
        
        # Grid lines
        p.setPen(QPen(qcol(C.WHITE, 12), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(0, H * 0.33), QPointF(W, H * 0.33))
        p.drawLine(QPointF(0, H * 0.66), QPointF(W, H * 0.66))
        
        points = []
        dx = W / 59.0
        for i, val in enumerate(self._history):
            x = i * dx
            y = H - 4 - (val / 100.0) * (H - 8)
            points.append(QPointF(x, y))
            
        path = QPainterPath()
        path.moveTo(points[0])
        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i+1]
            cx1 = p0.x() + (p1.x() - p0.x()) / 2.0
            cy1 = p0.y()
            cx2 = p0.x() + (p1.x() - p0.x()) / 2.0
            cy2 = p1.y()
            path.cubicTo(cx1, cy1, cx2, cy2, p1.x(), p1.y())
            
        area_path = QPainterPath(path)
        area_path.lineTo(W, H)
        area_path.lineTo(0, H)
        area_path.closeSubpath()
        
        grad = QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0.0, qcol(self._color, 80))
        grad.setColorAt(1.0, qcol(self._color, 0))
        p.fillPath(area_path, QBrush(grad))
        
        p.setPen(QPen(qcol(self._color), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

class ChatBubble(QFrame):
    finished = pyqtSignal()
    
    def __init__(self, tag: str, text: str, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.full_text = text
        self.display_text = ""
        self.pos = 0
        
        self.clean_text = text
        prefixes = ["you:", "ip prime:", "ipprime:", "sys:", "file:"]
        for prefix in prefixes:
            if text.lower().startswith(prefix):
                self.clean_text = text[len(prefix):].strip()
                break
                
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        
        self.bubble = QFrame()
        self.bubble.setObjectName("Bubble")
        
        if tag == "you":
            layout.addStretch()
            layout.addWidget(self.bubble)
            bg = "rgba(248, 250, 252, 0.10)"
            border = "1px solid rgba(248, 250, 252, 0.15)"
            text_col = C.TEXT
        elif tag == "ai":
            layout.addWidget(self.bubble)
            layout.addStretch()
            bg = "rgba(59, 130, 246, 0.12)"
            border = "1px solid rgba(59, 130, 246, 0.25)"
            text_col = C.PRI
        else:
            layout.addWidget(self.bubble)
            layout.addStretch()
            if tag == "err":
                bg = "rgba(239, 68, 68, 0.08)"
                border = "1px solid rgba(239, 68, 68, 0.2)"
                text_col = C.RED
            elif tag == "file":
                bg = "rgba(16, 185, 129, 0.08)"
                border = "1px solid rgba(16, 185, 129, 0.2)"
                text_col = C.GREEN
            else:
                bg = "rgba(139, 92, 246, 0.08)"
                border = "1px solid rgba(139, 92, 246, 0.2)"
                text_col = C.ACC2
                
        self.bubble.setStyleSheet(f"""
            #Bubble {{
                background: {bg};
                border: {border};
                border-radius: 12px;
            }}
        """)
        
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Segoe UI", 9))
        self.label.setStyleSheet(f"color: {text_col}; background: transparent; border: none;")
        bubble_layout.addWidget(self.label)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step_character)
        self.timer.start(10)
        
    def step_character(self):
        if self.pos < len(self.clean_text):
            self.display_text += self.clean_text[self.pos]
            self.label.setText(self.display_text)
            self.pos += 1
            
            scroll_area = self.parentWidget()
            while scroll_area and not isinstance(scroll_area, QScrollArea):
                scroll_area = scroll_area.parentWidget()
            if scroll_area:
                bar = scroll_area.verticalScrollBar()
                bar.setValue(bar.maximum())
        else:
            self.timer.stop()
            self.finished.emit()


class TypingIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setFixedWidth(60)
        self.setStyleSheet("""
            background: rgba(15, 23, 42, 0.45);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 10px;
        """)
        self.tick = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(80)
        
    def animate(self):
        self.tick += 1
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        spacing = 10.0
        
        for i in range(3):
            x = cx + (i - 1) * spacing
            offset = math.sin(self.tick * 0.4 - i * 1.2) * 2.5
            r = 3.0 + max(-1.0, min(1.0, offset))
            opacity = int(128 + 127 * math.sin(self.tick * 0.4 - i * 1.2))
            
            p.setBrush(QBrush(qcol(C.PRI, opacity)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, cy), r, r)


class LogWidget(QScrollArea):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {C.BG};
                width: 8px;
                border: none;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.container)
        self.scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch()
        self.setWidget(self.container)
        
        self._queue: list[str] = []
        self._typing = False
        self._text = ""
        self._tag = "sys"
        self._typing_indicator = TypingIndicator()
        self._typing_indicator.hide()
        
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        self._text = self._queue.pop(0)
        
        tl = self._text.lower()
        if   tl.startswith("you:"):    self._tag = "you"
        elif tl.startswith("ip prime:") or tl.startswith("ipprime:"): self._tag = "ai"
        elif tl.startswith("file:"):   self._tag = "file"
        elif "err" in tl:              self._tag = "err"
        else:                          self._tag = "sys"
        
        bubble = ChatBubble(self._tag, self._text)
        bubble.finished.connect(self._bubble_finished)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, bubble)
        QTimer.singleShot(20, self.scroll_to_bottom)

    def _bubble_finished(self):
        self._next()

    def scroll_to_bottom(self):
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def show_typing(self, show: bool):
        if show:
            if self._typing_indicator.parent() is None:
                self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, self._typing_indicator)
            self._typing_indicator.show()
            QTimer.singleShot(50, self.scroll_to_bottom)
        else:
            self._typing_indicator.hide()

_FILE_ICONS = {
    "image":   ("🖼", "#00d4ff"), "video":   ("🎬", "#ff6b00"),
    "audio":   ("🎵", "#cc44ff"), "pdf":     ("📄", "#ff4444"),
    "word":    ("📝", "#4488ff"), "excel":   ("📊", "#44bb44"),
    "code":    ("💻", "#ffcc00"), "archive": ("📦", "#ff8844"),
    "pptx":    ("📊", "#ff6622"), "text":    ("📃", "#aaaaaa"),
    "data":    ("🔧", "#88ddff"), "unknown": ("📎", "#888888"),
}
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","tiff","svg","ico"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","wmv","flv","webm","m4v"],         "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","aac","flac","wma","opus"],        "audio"),
    **dict.fromkeys(["pdf"],                                                     "pdf"),
    **dict.fromkeys(["doc","docx"],                                              "word"),
    **dict.fromkeys(["xls","xlsx","ods"],                                        "excel"),
    **dict.fromkeys(["ppt","pptx"],                                              "pptx"),
    **dict.fromkeys(["py","js","ts","jsx","tsx","html","css","java","c","cpp",
                     "cs","go","rs","rb","php","swift","kt","sh","sql","lua"],   "code"),
    **dict.fromkeys(["zip","rar","tar","gz","7z","bz2","xz"],                   "archive"),
    **dict.fromkeys(["txt","md","rst","log"],                                    "text"),
    **dict.fromkeys(["csv","tsv","json","xml"],                                  "data"),
}

def _file_category(path: Path) -> str:
    return _EXT_TO_CAT.get(path.suffix.lower().lstrip("."), "unknown")

def _fmt_size(size: int) -> str:
    if   size < 1024:    return f"{size} B"
    elif size < 1024**2: return f"{size/1024:.1f} KB"
    elif size < 1024**3: return f"{size/1024**2:.1f} MB"
    else:                return f"{size/1024**3:.1f} GB"


class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self._current_file: str | None = None
        self._hovering  = False
        self._drag_over = False
        self._dash_offset = 0.0
        self._anim_tmr = QTimer(self)
        self._anim_tmr.timeout.connect(self._animate)
        self._anim_tmr.start(40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = _DropCanvas(self)
        layout.addWidget(self._canvas)

    def _animate(self):
        self._dash_offset = (self._dash_offset + 0.8) % 20
        self._canvas.update()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag_over = True; self._canvas.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self._canvas.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self._set_file(path)
        self._canvas.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e):
        self._hovering = True; self._canvas.update()

    def leaveEvent(self, e):
        self._hovering = False; self._canvas.update()

    def current_file(self) -> str | None:
        return self._current_file

    def clear_file(self):
        self._current_file = None; self._canvas.update()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a file for IP PRIME", str(Path.home()),
            "All Files (*.*);;"
            "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg);;"
            "Documents (*.pdf *.docx *.txt *.md *.pptx);;"
            "Data (*.csv *.xlsx *.json *.xml);;"
            "Code (*.py *.js *.ts *.html *.css *.java *.cpp *.go);;"
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac);;"
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;"
            "Archives (*.zip *.rar *.tar *.gz *.7z)",
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._current_file = path
        self._canvas.update()
        self.file_selected.emit(path)


class _DropCanvas(QWidget):
    def __init__(self, zone: FileDropZone):
        super().__init__(zone)
        self._z = zone

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z    = self._z
        W, H = self.width(), self.height()
        pad  = 6
        rect = QRectF(pad, pad, W - pad * 2, H - pad * 2)

        bg_col = qcol("#001a24" if z._drag_over else ("#001218" if z._hovering else C.PANEL))
        p.setBrush(QBrush(bg_col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   border_col = qcol(C.GREEN, 200)
        elif z._drag_over:    border_col = qcol(C.PRI, 230)
        elif z._hovering:     border_col = qcol(C.BORDER_B, 200)
        else:                 border_col = qcol(C.BORDER, 160)

        pen = QPen(border_col, 1.5, Qt.PenStyle.DashLine)
        pen.setDashOffset(z._dash_offset)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   self._paint_file(p, W, H)
        elif z._drag_over:    self._paint_drag_over(p, W, H)
        else:                 self._paint_idle(p, W, H, z._hovering)

    def _paint_idle(self, p, W, H, hover):
        cx, cy = W / 2, H / 2
        col = qcol(C.PRI_DIM if not hover else C.PRI)
        p.setPen(QPen(col, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(cx, cy - 14), QPointF(cx, cy + 4))
        p.drawLine(QPointF(cx - 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx + 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx - 14, cy + 4), QPointF(cx + 14, cy + 4))
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QPen(qcol(C.PRI_DIM if not hover else C.TEXT), 1))
        p.drawText(QRectF(0, cy + 8, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "Drop file here  or  Click to Browse")
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QPen(qcol("#1a4a5a"), 1))
        p.drawText(QRectF(0, cy + 24, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "Images · Video · Audio · PDF · Docs · Code · Data")

    def _paint_drag_over(self, p, W, H):
        cy = H / 2
        p.setFont(QFont("Segoe UI", 20))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy - 24, W, 32), Qt.AlignmentFlag.AlignCenter, "⬇")
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy + 12, W, 16), Qt.AlignmentFlag.AlignCenter, "Release to load")

    def _paint_file(self, p, W, H):
        path = Path(self._z._current_file)
        cat  = _file_category(path)
        icon, icon_col = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size_str = _fmt_size(path.stat().st_size)
        ext_str  = path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 60
        p.setFont(QFont("Segoe UI Emoji", 22) if _OS == "Windows" else QFont("Arial", 22))
        p.setPen(QPen(qcol(icon_col), 1))
        p.drawText(QRectF(block_x, 0, block_w, H), Qt.AlignmentFlag.AlignCenter, icon)

        tx = block_x + block_w + 6
        tw = W - tx - 38

        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE), 1))
        name = path.name if len(path.name) <= 34 else path.name[:31] + "..."
        p.drawText(QRectF(tx, H * 0.18, tw, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(tx, H * 0.18 + 18, tw, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{ext_str}  ·  {size_str}")

        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QPen(qcol("#1e5c6a"), 1))
        par = str(path.parent)
        if len(par) > 42: par = "…" + par[-41:]
        p.drawText(QRectF(tx, H * 0.18 + 34, tw, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, par)

        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.RED, 180), 1))
        p.drawText(QRectF(W - 34, 0, 28, H), Qt.AlignmentFlag.AlignCenter, "✕")

    def mousePressEvent(self, e):
        z = self._z
        if z._current_file and e.pos().x() > self.width() - 34:
            z.clear_file()
        else:
            z.mousePressEvent(e)


class SetupOverlay(QWidget):
    done = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)

        detected = {"darwin": "mac", "windows": "windows"}.get(
            _OS.lower(), "linux"
        )
        self._sel_os = detected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(8)

        def _lbl(txt, font_size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Segoe UI", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        layout.addWidget(_lbl("◈  INITIALISATION REQUIRED", 13, True))
        layout.addWidget(_lbl("Configure IP PRIME before first boot.", 9, color=C.PRI_DIM))
        layout.addSpacing(6)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(4)

        layout.addWidget(_lbl("GEMINI API KEY", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza…")
        self._key_input.setFont(QFont("Segoe UI", 10))
        self._key_input.setFixedHeight(32)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 8px; padding: 4px 10px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        layout.addWidget(self._key_input)
        layout.addSpacing(12)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep2)
        layout.addSpacing(4)

        layout.addWidget(_lbl("OPERATING SYSTEM", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        det_name = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}[detected]
        layout.addWidget(_lbl(f"Auto-detected: {det_name}", 8, color=C.ACC2,
                               align=Qt.AlignmentFlag.AlignLeft))

        os_row = QHBoxLayout(); os_row.setSpacing(6)
        self._os_btns: dict[str, QPushButton] = {}
        for key, label in [("windows","⊞  Windows"),("mac","  macOS"),("linux","🐧  Linux")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._sel(k))
            os_row.addWidget(btn)
            self._os_btns[key] = btn
        layout.addLayout(os_row)
        self._sel(detected)
        layout.addSpacing(12)

        init_btn = QPushButton("▸  INITIALISE SYSTEMS")
        init_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        init_btn.setFixedHeight(36)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; border: 1px solid {C.PRI};
            }}
        """)
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _sel(self, key: str):
        self._sel_os = key
        pal = {"windows":(C.PRI,"#001a22"),"mac":(C.ACC2,"#1a1400"),"linux":(C.GREEN,"#001a0d")}
        for k, btn in self._os_btns.items():
            if k == key:
                fg, bg = pal[k]
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {fg}; color: {bg};
                        border: none; border-radius: 3px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #000d12; color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER}; border-radius: 3px;
                    }}
                    QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
                """)

    def _submit(self):
        key = self._key_input.text().strip()
        if not key:
            self._key_input.setStyleSheet(
                self._key_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        self.done.emit(key, self._sel_os)


class MainWindow(QMainWindow):
    _log_sig        = pyqtSignal(str)
    _state_sig      = pyqtSignal(str)
    _fullscreen_sig = pyqtSignal(bool)
    _thought_sig    = pyqtSignal(str)
    _change_theme_sig = pyqtSignal(str)
    _synth_personality_sig = pyqtSignal()
    _web_command_sig = pyqtSignal(str)
    _pulse_highlight_sig = pyqtSignal(int, int, float, str)
    _ocr_translate_sig = pyqtSignal(list)
    _router_badge_sig  = pyqtSignal(str)

    def __init__(self, face_path: str):
        super().__init__()
        self.setWindowTitle("IP Prime")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)
        self._start_time = time.time()
        
        self._f11_shortcut = QShortcut(QKeySequence("F11"), self)
        self._f11_shortcut.activated.connect(lambda: self._set_fullscreen_slot(not self.isFullScreen()))
        self._f12_shortcut = QShortcut(QKeySequence("F12"), self)
        self._f12_shortcut.activated.connect(lambda: self._set_fullscreen_slot(not self.isFullScreen()))

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        self.on_text_command  = None
        self._muted           = False
        self._current_file: str | None = None

        self._change_theme_sig.connect(self._set_theme_by_name)
        self._synth_personality_sig.connect(self._arc_synthesize_core)
        self._web_command_sig.connect(lambda cmd: self.on_text_command(cmd) if self.on_text_command else None)
        self._router_badge_sig.connect(self._on_router_badge_updated)

        self._central_widget = QWidget()
        self._central_widget.setObjectName("CentralWidget")
        self._central_widget.setStyleSheet(f"""
            QWidget#CentralWidget {{
                background: qradialgradient(cx:0.5, cy:0.4, radius:0.8, fx:0.5, fy:0.4,
                    stop:0 {C.PRI_GHO},
                    stop:0.4 rgba(3, 7, 18, 0.95),
                    stop:1 {C.BG});
            }}
        """)
        self.setCentralWidget(self._central_widget)

        root = QVBoxLayout(self._central_widget)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addWidget(self._build_header())
        self._router_badge.hide()
        self._settings_gear_btn.hide()
        self._slide_btn.hide()

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)

        self._settings_panel = self._build_settings_panel()
        self._settings_panel.setMaximumWidth(0)
        self._settings_panel.setMinimumWidth(0)
        self._settings_panel_visible = False
        body.addWidget(self._settings_panel, stretch=0)

        self._left_panel = self._build_left_panel()
        body.addWidget(self._left_panel, stretch=0)
        self._left_panel.hide()  # Permanently hide left panel containing SYS MONITOR and HUD CONFIG as requested

        self.hud = HudCanvas(face_path)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # ── Wrapped HUD inside a beautiful rounded obsidian card ──────────────
        self._hud_container = QWidget()
        self._hud_container.setStyleSheet(
            f"background: transparent; border: none; border-radius: 12px;"
        )
        hud_lay = QVBoxLayout(self._hud_container)
        hud_lay.setContentsMargins(2, 2, 2, 2)
        hud_lay.setSpacing(0)
        hud_lay.addWidget(self.hud)

        # ── NLA Thought Stream Panel ──────────────────────────────────────────
        self._thought_panel = QWidget()
        self._thought_panel.setFixedHeight(44)
        self._thought_panel.setStyleSheet(
            "background: rgba(5, 10, 20, 0.88);"
            "border-top: 1px solid rgba(6, 182, 212, 0.25);"
            "border-bottom-left-radius: 11px;"
            "border-bottom-right-radius: 11px;"
        )
        _tp_lay = QHBoxLayout(self._thought_panel)
        _tp_lay.setContentsMargins(12, 0, 12, 0)
        _tp_lay.setSpacing(8)

        # Pill badge: [LATENT MONITOR]
        self._thought_badge = QLabel("LATENT")
        self._thought_badge.setFixedSize(58, 20)
        self._thought_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thought_badge.setStyleSheet(
            f"color: {C.CYAN}; background: rgba(6,182,212,0.12);"
            f"border: 1px solid rgba(6,182,212,0.35); border-radius: 4px;"
            f"font-family: 'Consolas','Courier New',monospace; font-size: 7px; font-weight: bold; letter-spacing: 1px;"
        )
        _tp_lay.addWidget(self._thought_badge)

        # Neon pulse indicator dot
        self._thought_dot = QLabel("●")
        self._thought_dot.setFixedSize(14, 14)
        self._thought_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thought_dot.setStyleSheet(
            f"color: {C.CYAN}; font-size: 8px;"
        )
        _tp_lay.addWidget(self._thought_dot)

        # Thought text ticker
        self._thought_label = QLabel("> Ready — speak anytime")
        self._thought_label.setStyleSheet(
            "color: rgba(6,182,212,0.80); background: transparent;"
            "font-family: 'Consolas','Courier New',monospace; font-size: 10px; letter-spacing: 0.5px;"
        )
        self._thought_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._thought_label.setWordWrap(False)
        _tp_lay.addWidget(self._thought_label, stretch=1)

        hud_lay.addWidget(self._thought_panel)
        self._thought_panel.hide()
        body.addWidget(self._hud_container, stretch=5)

        self._right_panel = self._build_right_panel()
        self._right_panel.setMaximumWidth(0)
        self._right_panel.setMinimumWidth(0)
        self._right_panel_visible = False
        body.addWidget(self._right_panel, stretch=0)

        root.addLayout(body, stretch=1)
        root.addWidget(self._build_footer())
        self._footer_widget.hide()



        # Metrik güncelleme timer'ı
        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(2000)
        self._update_metrics()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._fullscreen_sig.connect(self._set_fullscreen_slot)
        self._thought_sig.connect(self._apply_thought)
        self._pulse_highlight_sig.connect(self._show_pulse_highlight)
        self._ocr_translate_sig.connect(self._show_ocr_translation)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()
        else:
            pass

    def _show_pulse_highlight(self, x: int, y: int, duration: float, color: str):
        from actions.screen_overlay import HighlightOverlay
        overlay = HighlightOverlay(x, y, duration, color, self)
        if not hasattr(self, "_active_highlights"):
            self._active_highlights = []
        self._active_highlights.append(overlay)
        overlay.show()
        overlay.destroyed.connect(lambda: self._active_highlights.remove(overlay) if overlay in self._active_highlights else None)

    def _show_ocr_translation(self, items: list):
        from actions.screen_overlay import TranslationCardOverlay
        overlay = TranslationCardOverlay(items)
        if not hasattr(self, "_active_translations"):
            self._active_translations = []
        self._active_translations.append(overlay)
        overlay.show()
        overlay.destroyed.connect(lambda: self._active_translations.remove(overlay) if overlay in self._active_translations else None)

    def _set_fullscreen_slot(self, full: bool):
        if full:
            if not self.isFullScreen():
                self._header_widget.hide()
                self._footer_widget.hide()
                if getattr(self, '_right_panel_visible', False):
                    self._right_panel.hide()
                self._central_widget.layout().setContentsMargins(0, 0, 0, 0)
                self.showFullScreen()
        else:
            if self.isFullScreen():
                self._header_widget.show()
                self._footer_widget.show()
                if getattr(self, '_right_panel_visible', False):
                    self._right_panel.show()
                self._central_widget.layout().setContentsMargins(12, 12, 12, 12)
                self.showNormal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            ow, oh = 460, 390
            cw = self.centralWidget()
            self._overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )

    def _update_metrics(self):
        snap = _metrics.snapshot()

        # CPU
        cpu = snap["cpu"]
        self._bar_cpu.set_value(cpu, f"{cpu:.0f}%")
        if hasattr(self, "_graph_cpu"):
            self._graph_cpu.add_value(cpu)

        # MEM
        mem = snap["mem"]
        self._bar_mem.set_value(mem, f"{mem:.0f}%")
        if hasattr(self, "_graph_mem"):
            self._graph_mem.add_value(mem)

        # NET
        net = snap["net"]
        if net < 1.0:
            net_str = f"{net*1024:.0f}KB/s"
        else:
            net_str = f"{net:.1f}MB/s"
        net_pct = min(100, net * 10)  # 10 MB/s = %100
        self._bar_net.set_value(net_pct, net_str)

        # GPU
        gpu = snap["gpu"]
        if gpu >= 0:
            self._bar_gpu.set_value(gpu, f"{gpu:.0f}%")
        else:
            self._bar_gpu.set_value(0, "N/A")

        # TMP
        tmp = snap["tmp"]
        if tmp >= 0:
            tmp_pct = min(100, (tmp / 100) * 100)
            self._bar_tmp.set_value(tmp_pct, f"{tmp:.0f}°C")
        else:
            self._bar_tmp.set_value(0, "N/A")

        try:
            elapsed = time.time() - self._start_time
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            s = int(elapsed % 60)
            self._uptime_lbl.setText(f"UPTIME: {h:02d}:{m:02d}:{s:02d}")
        except Exception:
            self._uptime_lbl.setText("UPTIME: --:--:--")

        try:
            from prime_platform.energy_metrics import get_footer_summary
            self._prime_metrics_lbl.setText(get_footer_summary())
        except Exception:
            if hasattr(self, "_prime_metrics_lbl"):
                self._prime_metrics_lbl.setText("")

        try:
            proc_count = len(psutil.pids())
            self._proc_lbl.setText(f"PROC  {proc_count}")
        except Exception:
            self._proc_lbl.setText("PROC  --")

        # Update MCP server rows connection states dynamically
        try:
            if hasattr(self, "_mcp_server_rows") and self._mcp_server_rows:
                from actions.mcp_client import MCPClientManager
                mcp_mgr = MCPClientManager()
                for name, (status_lbl, toggle_btn) in self._mcp_server_rows.items():
                    conn = mcp_mgr.connections.get(name)
                    running = conn.running if conn else False
                    
                    if running:
                        status_lbl.setText("🟢 Running")
                        status_lbl.setStyleSheet(f"color: {C.GREEN}; font-size: 11px;")
                        toggle_btn.setText("Stop")
                        toggle_btn.setStyleSheet(
                            f"QPushButton {{ background: rgba(239, 68, 68, 0.15); color: {C.RED}; "
                            f"border: 1px solid {C.RED}; border-radius: 5px; font-size: 10px; font-weight: bold; }} "
                            f"QPushButton:hover {{ background: rgba(239, 68, 68, 0.35); }}"
                        )
                    else:
                        status_lbl.setText("⚪ Stopped")
                        status_lbl.setStyleSheet(f"color: {C.TEXT_MED}; font-size: 11px;")
                        toggle_btn.setText("Start")
                        toggle_btn.setStyleSheet(
                            f"QPushButton {{ background: rgba(59, 130, 246, 0.15); color: {C.PRI}; "
                            f"border: 1px solid {C.PRI}; border-radius: 5px; font-size: 10px; font-weight: bold; }} "
                            f"QPushButton:hover {{ background: rgba(59, 130, 246, 0.35); }}"
                        )
        except Exception as e:
            print(f"[IP PRIME UI] Error updating MCP metrics: {e}")


    def _build_header(self) -> QWidget:
        self._header_widget = QWidget()
        self._header_widget.setObjectName("HeaderWidget")
        self._header_widget.setFixedHeight(54)
        self._header_widget.setStyleSheet(f"""
            QWidget#HeaderWidget {{
                background: {C.PANEL};
                border: 1.5px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C.PRI},
                    stop:0.5 {C.ACC if hasattr(C, 'ACC') else C.PRI},
                    stop:1 {C.PRI});
                border-radius: 27px;
            }}
        """)
        lay = QHBoxLayout(self._header_widget)
        lay.setContentsMargins(24, 0, 24, 0)

        def _badge(txt, color=C.TEXT_MED):
            l = QLabel(txt)
            l.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        self._title_lbl = QLabel()
        self._title_lbl.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"""
            QLabel {{
                color: {C.WHITE};
                background: transparent;
                border: none;
                letter-spacing: 3px;
            }}
        """)
        self._title_lbl.setText(
            f"<span style='color: {C.PRI}; font-weight: 800;'>IP</span> "
            f"<span style='color: {C.CYAN}; font-weight: 800;'>PRIME</span>"
        )
        lay.addWidget(self._title_lbl)

        # Add Smart Router pill badge indicator next to Title
        default_text = "🟢 Gemini"
        default_style = (
            "color: #10b981; background: rgba(16, 185, 129, 0.1); "
            "border: 1px solid #10b981; border-radius: 10px; padding: 3px 8px; font-weight: bold; font-size: 11px; margin-left: 10px;"
        )
        try:
            from actions.model_switcher import load_model_preference
            pref = load_model_preference()
            if pref.get("hacker_mode", False):
                default_text = "💀 Hacker Mode"
                default_style = (
                    "color: #ef4444; background: rgba(239, 68, 68, 0.1); "
                    "border: 1px solid #ef4444; border-radius: 10px; padding: 3px 8px; font-weight: bold; font-size: 11px; margin-left: 10px;"
                )
            elif pref.get("routing_mode", "auto") == "nvidia":
                default_text = "🟩 NVIDIA"
                default_style = (
                    "color: #76B900; background: rgba(118, 185, 0, 0.1); "
                    "border: 1px solid #76B900; border-radius: 10px; padding: 3px 8px; font-weight: bold; font-size: 11px; margin-left: 10px;"
                )
        except Exception:
            pass

        self._router_badge = QLabel(default_text)
        self._router_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._router_badge.setStyleSheet(default_style)
        self._router_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._router_badge)

        lay.addStretch()

        self._settings_gear_btn = QPushButton("⚙")
        self._settings_gear_btn.setFixedSize(36, 36)
        self._settings_gear_btn.setFont(QFont("Segoe UI", 14))
        self._settings_gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_gear_btn.setToolTip("Toggle Settings Panel")
        self._settings_gear_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(30, 41, 59, 0.35); color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 18px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; color: {C.WHITE}; border: 1.5px solid {C.PRI};
            }}
        """)
        self._settings_gear_btn.clicked.connect(self._toggle_settings_panel)
        lay.addWidget(self._settings_gear_btn)

        self._slide_btn = QPushButton("◂")
        self._slide_btn.setFixedSize(36, 36)
        self._slide_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._slide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._slide_btn.setToolTip("Toggle Side Panel (Logs · Files · Input)")
        self._slide_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(30, 41, 59, 0.35); color: {C.ACC};
                border: 1px solid {C.BORDER}; border-radius: 18px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; color: {C.WHITE}; border: 1.5px solid {C.ACC};
            }}
        """)
        self._slide_btn.clicked.connect(self._toggle_right_panel)
        lay.addWidget(self._slide_btn)

        return self._header_widget

        # Date and time display removed per user request; no UI update needed.
        pass

    def _build_settings_panel(self) -> QWidget:
        # ── Outer card (fixed width, no internal padding — scroll area fills it) ──
        outer = QWidget()
        outer.setFixedWidth(240)
        outer.setStyleSheet(
            f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px;"
        )
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)

        # ── Scroll Area ──────────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; border-radius: 12px; }"
            "QScrollBar:vertical {"
            "  background: rgba(15,23,42,0.6);"
            "  width: 5px;"
            "  border-radius: 3px;"
            "  margin: 4px 2px;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: rgba(59,130,246,0.45);"
            "  border-radius: 3px;"
            "  min-height: 20px;"
            "}"
            "QScrollBar::handle:vertical:hover {"
            "  background: rgba(59,130,246,0.75);"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
        )

        # ── Inner content widget (all widgets go here) ───────────────────────────
        panel = QWidget()
        panel.setStyleSheet("background: transparent; border: none;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 16, 14, 16)
        lay.setSpacing(10)

        # Title
        title = QLabel("⚙  SETTINGS")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 1px;")
        lay.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};")
        lay.addWidget(sep)

        # Camoufox Header
        cam_lbl = QLabel("🕷 CAMOUFOX STEALTH")
        cam_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        cam_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 0.5px;")
        lay.addWidget(cam_lbl)

        # Reading values
        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

        use_camou = cfg.get("use_camoufox", False)
        camou_headless = cfg.get("camoufox_headless", False)
        camou_os = cfg.get("camoufox_os", "random")
        camou_proxy = cfg.get("camoufox_proxy", "")
        camou_block = cfg.get("camoufox_block_assets", False)
        camou_human = cfg.get("camoufox_human_mimic", True)
        camou_webrtc = cfg.get("camoufox_block_webrtc", True)
        camou_webgl = cfg.get("camoufox_allow_webgl", False)
        camou_geoip = cfg.get("camoufox_geoip", True)
        camou_addons = cfg.get("camoufox_addons_path", "")

        # Master Toggle
        self._stealth_btn = QPushButton()
        self._stealth_btn.setCheckable(True)
        self._stealth_btn.setChecked(use_camou)
        self._stealth_btn.setFixedHeight(30)
        self._stealth_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stealth_btn.clicked.connect(self._toggle_stealth_mode)
        lay.addWidget(self._stealth_btn)

        # Checkboxes and fields container
        self._stealth_opts_widget = QWidget()
        self._stealth_opts_widget.setStyleSheet("background: transparent; border: none;")
        opts_lay = QVBoxLayout(self._stealth_opts_widget)
        opts_lay.setContentsMargins(0, 0, 0, 0)
        opts_lay.setSpacing(6)

        # Headless Toggle
        self._stealth_headless_cb = QCheckBox("Headless Stealth")
        self._stealth_headless_cb.setChecked(camou_headless)
        self._stealth_headless_cb.setStyleSheet(
            f"QCheckBox {{ color: {C.TEXT_MED}; font-size: 11px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {C.BORDER}; border-radius: 3px; background: #000d12; }}"
            f"QCheckBox::indicator:checked {{ background: {C.PRI}; border: 1px solid {C.PRI}; }}"
        )
        self._stealth_headless_cb.stateChanged.connect(self._save_stealth_settings)
        opts_lay.addWidget(self._stealth_headless_cb)

        # Block images/fonts
        self._stealth_block_cb = QCheckBox("Block Heavy Assets")
        self._stealth_block_cb.setChecked(camou_block)
        self._stealth_block_cb.setStyleSheet(
            f"QCheckBox {{ color: {C.TEXT_MED}; font-size: 11px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {C.BORDER}; border-radius: 3px; background: #000d12; }}"
            f"QCheckBox::indicator:checked {{ background: {C.PRI}; border: 1px solid {C.PRI}; }}"
        )
        self._stealth_block_cb.stateChanged.connect(self._save_stealth_settings)
        opts_lay.addWidget(self._stealth_block_cb)

        # Human mimicry
        self._stealth_human_cb = QCheckBox("Human Mimicry")
        self._stealth_human_cb.setChecked(camou_human)
        self._stealth_human_cb.setStyleSheet(
            f"QCheckBox {{ color: {C.TEXT_MED}; font-size: 11px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {C.BORDER}; border-radius: 3px; background: #000d12; }}"
            f"QCheckBox::indicator:checked {{ background: {C.PRI}; border: 1px solid {C.PRI}; }}"
        )
        self._stealth_human_cb.stateChanged.connect(self._save_stealth_settings)
        opts_lay.addWidget(self._stealth_human_cb)

        # Block WebRTC
        self._stealth_webrtc_cb = QCheckBox("Block WebRTC Leaks")
        self._stealth_webrtc_cb.setChecked(camou_webrtc)
        self._stealth_webrtc_cb.setStyleSheet(
            f"QCheckBox {{ color: {C.TEXT_MED}; font-size: 11px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {C.BORDER}; border-radius: 3px; background: #000d12; }}"
            f"QCheckBox::indicator:checked {{ background: {C.PRI}; border: 1px solid {C.PRI}; }}"
        )
        self._stealth_webrtc_cb.stateChanged.connect(self._save_stealth_settings)
        opts_lay.addWidget(self._stealth_webrtc_cb)

        # WebGL Canvas Spoofing
        self._stealth_webgl_cb = QCheckBox("Spoof WebGL/Canvas")
        self._stealth_webgl_cb.setChecked(not camou_webgl)
        self._stealth_webgl_cb.setStyleSheet(
            f"QCheckBox {{ color: {C.TEXT_MED}; font-size: 11px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {C.BORDER}; border-radius: 3px; background: #000d12; }}"
            f"QCheckBox::indicator:checked {{ background: {C.PRI}; border: 1px solid {C.PRI}; }}"
        )
        self._stealth_webgl_cb.stateChanged.connect(self._save_stealth_settings)
        opts_lay.addWidget(self._stealth_webgl_cb)

        # GeoIP Synchronization
        self._stealth_geoip_cb = QCheckBox("Sync Proxy Locale")
        self._stealth_geoip_cb.setChecked(camou_geoip)
        self._stealth_geoip_cb.setStyleSheet(
            f"QCheckBox {{ color: {C.TEXT_MED}; font-size: 11px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {C.BORDER}; border-radius: 3px; background: #000d12; }}"
            f"QCheckBox::indicator:checked {{ background: {C.PRI}; border: 1px solid {C.PRI}; }}"
        )
        self._stealth_geoip_cb.stateChanged.connect(self._save_stealth_settings)
        opts_lay.addWidget(self._stealth_geoip_cb)

        # Spoof OS Combo
        os_lbl = QLabel("Spoof OS Platform:")
        os_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        os_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        opts_lay.addWidget(os_lbl)

        self._stealth_os_combo = QComboBox()
        self._stealth_os_combo.addItems(["random", "windows", "macos", "linux"])
        idx = self._stealth_os_combo.findText(camou_os)
        if idx >= 0:
            self._stealth_os_combo.setCurrentIndex(idx)
        self._stealth_os_combo.setStyleSheet(
            f"QComboBox {{ background: #000d12; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 6px; padding: 3px 6px; font-size: 11px; }} "
            f"QComboBox QAbstractItemView {{ background-color: #0f172a; color: {C.TEXT}; selection-background-color: {C.BORDER}; }}"
        )
        self._stealth_os_combo.currentIndexChanged.connect(self._save_stealth_settings)
        opts_lay.addWidget(self._stealth_os_combo)

        # Proxy Input
        proxy_lbl = QLabel("HTTP/SOCKS5 Proxy:")
        proxy_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        proxy_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        opts_lay.addWidget(proxy_lbl)

        self._stealth_proxy_input = QLineEdit()
        self._stealth_proxy_input.setPlaceholderText("socks5://127.0.0.1:9050")
        self._stealth_proxy_input.setText(camou_proxy)
        self._stealth_proxy_input.setFont(QFont("Segoe UI", 8))
        self._stealth_proxy_input.setFixedHeight(26)
        self._stealth_proxy_input.setStyleSheet(
            f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
            f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
        )
        self._stealth_proxy_input.textChanged.connect(self._save_stealth_settings)
        opts_lay.addWidget(self._stealth_proxy_input)

        # Add-ons Directory Input with browse button
        addons_lbl = QLabel("Add-ons Extensions Directory:")
        addons_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        addons_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        opts_lay.addWidget(addons_lbl)

        addons_w = QWidget()
        addons_w.setStyleSheet("background: transparent; border: none;")
        addons_lay = QHBoxLayout(addons_w)
        addons_lay.setContentsMargins(0, 0, 0, 0)
        addons_lay.setSpacing(4)

        self._stealth_addons_input = QLineEdit()
        self._stealth_addons_input.setPlaceholderText("Folder path to extracted addons...")
        self._stealth_addons_input.setText(camou_addons)
        self._stealth_addons_input.setFont(QFont("Segoe UI", 8))
        self._stealth_addons_input.setFixedHeight(26)
        self._stealth_addons_input.setStyleSheet(
            f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
            f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
        )
        self._stealth_addons_input.textChanged.connect(self._save_stealth_settings)
        addons_lay.addWidget(self._stealth_addons_input)

        self._stealth_addons_browse_btn = QPushButton("Browse")
        self._stealth_addons_browse_btn.setFont(QFont("Segoe UI", 8))
        self._stealth_addons_browse_btn.setFixedHeight(26)
        self._stealth_addons_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stealth_addons_browse_btn.setStyleSheet(
            f"QPushButton {{ background: #000d12; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 6px; padding: 0 8px; }} "
            f"QPushButton:hover {{ background: rgba(255,255,255,0.06); border: 1px solid {C.TEXT_MED}; }}"
        )
        self._stealth_addons_browse_btn.clicked.connect(self._browse_addons_folder)
        addons_lay.addWidget(self._stealth_addons_browse_btn)
        opts_lay.addWidget(addons_w)

        lay.addWidget(self._stealth_opts_widget)
        self._update_stealth_btn_style()

        # ── Desktop Integrations Section ─────────────────────────────────────
        sep_integrations = QFrame(); sep_integrations.setFrameShape(QFrame.Shape.HLine)
        sep_integrations.setStyleSheet(f"color: {C.BORDER};")
        lay.addWidget(sep_integrations)

        integrations_lbl = QLabel("🔌 DESKTOP INTEGRATIONS")
        integrations_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        integrations_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 0.5px;")
        lay.addWidget(integrations_lbl)

        # 1. Obsidian Vault Path
        obs_lbl = QLabel("Obsidian Vault Directory:")
        obs_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        obs_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(obs_lbl)

        obs_w = QWidget()
        obs_w.setStyleSheet("background: transparent; border: none;")
        obs_lay = QHBoxLayout(obs_w)
        obs_lay.setContentsMargins(0, 0, 0, 0)
        obs_lay.setSpacing(4)

        self._obsidian_path_input = QLineEdit()
        self._obsidian_path_input.setPlaceholderText("Path to Obsidian vault...")
        self._obsidian_path_input.setText(cfg.get("obsidian_vault_path", ""))
        self._obsidian_path_input.setFont(QFont("Segoe UI", 8))
        self._obsidian_path_input.setFixedHeight(26)
        self._obsidian_path_input.setStyleSheet(
            f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
            f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
        )
        self._obsidian_path_input.textChanged.connect(self._save_integrations_settings)
        obs_lay.addWidget(self._obsidian_path_input)

        self._obsidian_browse_btn = QPushButton("Browse")
        self._obsidian_browse_btn.setFont(QFont("Segoe UI", 8))
        self._obsidian_browse_btn.setFixedHeight(26)
        self._obsidian_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._obsidian_browse_btn.setStyleSheet(
            f"QPushButton {{ background: #000d12; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 6px; padding: 0 8px; }} "
            f"QPushButton:hover {{ background: rgba(255,255,255,0.06); border: 1px solid {C.TEXT_MED}; }}"
        )
        self._obsidian_browse_btn.clicked.connect(self._browse_obsidian_vault)
        obs_lay.addWidget(self._obsidian_browse_btn)
        lay.addWidget(obs_w)

        # 2. Spotify Client ID
        spot_id_lbl = QLabel("Spotify Client ID:")
        spot_id_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        spot_id_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(spot_id_lbl)

        self._spotify_id_input = QLineEdit()
        self._spotify_id_input.setPlaceholderText("Spotify Client ID...")
        self._spotify_id_input.setText(cfg.get("spotify_client_id", ""))
        self._spotify_id_input.setFont(QFont("Segoe UI", 8))
        self._spotify_id_input.setFixedHeight(26)
        self._spotify_id_input.setStyleSheet(
            f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
            f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
        )
        self._spotify_id_input.textChanged.connect(self._save_integrations_settings)
        lay.addWidget(self._spotify_id_input)

        # 3. Spotify Client Secret
        spot_sec_lbl = QLabel("Spotify Client Secret:")
        spot_sec_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        spot_sec_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(spot_sec_lbl)

        self._spotify_secret_input = QLineEdit()
        self._spotify_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._spotify_secret_input.setPlaceholderText("Spotify Secret Key...")
        self._spotify_secret_input.setText(cfg.get("spotify_client_secret", ""))
        self._spotify_secret_input.setFont(QFont("Segoe UI", 8))
        self._spotify_secret_input.setFixedHeight(26)
        self._spotify_secret_input.setStyleSheet(
            f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
            f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
        )
        self._spotify_secret_input.textChanged.connect(self._save_integrations_settings)
        lay.addWidget(self._spotify_secret_input)

        # 4. Home Assistant URL
        ha_url_lbl = QLabel("Home Assistant URL:")
        ha_url_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        ha_url_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(ha_url_lbl)

        self._ha_url_input = QLineEdit()
        self._ha_url_input.setPlaceholderText("http://homeassistant.local:8123")
        self._ha_url_input.setText(cfg.get("home_assistant_url", ""))
        self._ha_url_input.setFont(QFont("Segoe UI", 8))
        self._ha_url_input.setFixedHeight(26)
        self._ha_url_input.setStyleSheet(
            f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
            f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
        )
        self._ha_url_input.textChanged.connect(self._save_integrations_settings)
        lay.addWidget(self._ha_url_input)

        # 5. Home Assistant Token
        ha_token_lbl = QLabel("HA Long-Lived Token:")
        ha_token_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        ha_token_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(ha_token_lbl)

        self._ha_token_input = QLineEdit()
        self._ha_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._ha_token_input.setPlaceholderText("HA Token key...")
        self._ha_token_input.setText(cfg.get("home_assistant_token", ""))
        self._ha_token_input.setFont(QFont("Segoe UI", 8))
        self._ha_token_input.setFixedHeight(26)
        self._ha_token_input.setStyleSheet(
            f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
            f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
        )
        self._ha_token_input.textChanged.connect(self._save_integrations_settings)
        lay.addWidget(self._ha_token_input)

        # ── MCP Servers Section ──────────────────────────────────────────────

        # ── MCP Servers Section ──────────────────────────────────────────────
        sep_mcp = QFrame(); sep_mcp.setFrameShape(QFrame.Shape.HLine)
        sep_mcp.setStyleSheet(f"color: {C.BORDER};")
        lay.addWidget(sep_mcp)

        mcp_lbl = QLabel("🔌 MCP SERVERS")
        mcp_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        mcp_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 0.5px;")
        lay.addWidget(mcp_lbl)

        self._mcp_container = QWidget()
        self._mcp_container.setStyleSheet("background: transparent; border: none;")
        self._mcp_container_lay = QVBoxLayout(self._mcp_container)
        self._mcp_container_lay.setContentsMargins(0, 0, 0, 0)
        self._mcp_container_lay.setSpacing(6)
        lay.addWidget(self._mcp_container)

        self._mcp_server_rows = {}
        self._rebuild_mcp_servers_ui()

        # Configure Config button
        self._mcp_config_btn = QPushButton("📝  Configure Servers")
        self._mcp_config_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._mcp_config_btn.setFixedHeight(30)
        self._mcp_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mcp_config_btn.setStyleSheet(
            f"QPushButton {{ background: #000d12; color: {C.TEXT_MED}; border: 1px solid {C.BORDER}; border-radius: 6px; }} "
            f"QPushButton:hover {{ background: rgba(255,255,255,0.06); border: 1px solid {C.TEXT_MED}; color: {C.WHITE}; }}"
        )
        self._mcp_config_btn.clicked.connect(self._open_mcp_config)
        lay.addWidget(self._mcp_config_btn)

        # 🧬 RAVX ARC LAB Personality Synthesis Panel
        sep_arc = QFrame(); sep_arc.setFrameShape(QFrame.Shape.HLine)
        sep_arc.setStyleSheet(f"color: {C.BORDER};")
        lay.addWidget(sep_arc)

        arc_lbl = QLabel("🧬 RAVX ARC LAB")
        arc_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        arc_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 0.5px;")
        lay.addWidget(arc_lbl)

        # Load personality config
        arc_file = CONFIG_DIR / "personality.json"
        try:
            if arc_file.exists():
                arc_data = json.loads(arc_file.read_text(encoding="utf-8"))
            else:
                arc_data = {}
        except Exception:
            arc_data = {}

        arc_name = arc_data.get("name", "IP Prime")
        arc_humour = arc_data.get("humour", 50)
        arc_energy = arc_data.get("energy", 60)
        arc_sarcasm = arc_data.get("sarcasm", 30)
        arc_prof = arc_data.get("professionalism", 80)
        arc_creat = arc_data.get("creativity", 75)

        # Name Field
        name_lbl = QLabel("Core Assistant Name:")
        name_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(name_lbl)

        self._arc_name_input = QLineEdit()
        self._arc_name_input.setPlaceholderText("e.g. IP Prime")
        self._arc_name_input.setText(arc_name)
        self._arc_name_input.setFont(QFont("Segoe UI", 9))
        self._arc_name_input.setFixedHeight(30)
        self._arc_name_input.setStyleSheet(
            f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
            f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
        )
        lay.addWidget(self._arc_name_input)

        self._arc_val_labels = []
        self._arc_sliders = []

        # Helper to create styled sliders
        def build_arc_slider(label_text, init_val):
            w = QWidget()
            w.setStyleSheet("background: transparent; border: none;")
            vlay = QVBoxLayout(w)
            vlay.setContentsMargins(0, 2, 0, 2)
            vlay.setSpacing(2)

            hlay = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            val_lbl = QLabel(f"{init_val}%")
            val_lbl.setFont(QFont("Segoe UI", 7))
            val_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
            self._arc_val_labels.append(val_lbl)
            hlay.addWidget(lbl)
            hlay.addStretch()
            hlay.addWidget(val_lbl)
            vlay.addLayout(hlay)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(init_val)
            slider.setFixedHeight(20)
            slider.setCursor(Qt.CursorShape.PointingHandCursor)
            slider.setStyleSheet(
                f"QSlider::groove:horizontal {{ height: 4px; background: {C.BORDER}; border-radius: 2px; }} "
                f"QSlider::sub-page:horizontal {{ background: {C.PRI}; border-radius: 2px; }} "
                f"QSlider::handle:horizontal {{ background: {C.ACC}; border: 1px solid {C.ACC2}; width: 12px; height: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }} "
                f"QSlider::handle:horizontal:hover {{ background: {C.CYAN}; border-radius: 6px; }}"
            )
            self._arc_sliders.append(slider)
            slider.valueChanged.connect(lambda val, vl=val_lbl: vl.setText(f"{val}%"))
            vlay.addWidget(slider)
            lay.addWidget(w)
            return slider

        self._arc_humour_slider = build_arc_slider("Humour", arc_humour)
        self._arc_energy_slider = build_arc_slider("Energy", arc_energy)
        self._arc_sarcasm_slider = build_arc_slider("Sarcasm", arc_sarcasm)
        self._arc_prof_slider = build_arc_slider("Professionalism", arc_prof)
        self._arc_creat_slider = build_arc_slider("Creativity", arc_creat)

        # Synthesize button
        self._arc_synth_btn = QPushButton("🧬  SYNTHESIZE CORE")
        self._arc_synth_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._arc_synth_btn.setFixedHeight(34)
        self._arc_synth_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._arc_synth_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C.PRI}; "
            f"border: 1px solid {C.BORDER_B}; border-radius: 8px; font-weight: bold; letter-spacing: 0.5px; }} "
            f"QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; color: {C.CYAN}; }}"
        )
        self._arc_synth_btn.clicked.connect(self._arc_synthesize_core)
        lay.addWidget(self._arc_synth_btn)

        # ── PRIME VERSE (JARVIS features) ─────────────────────────────────────
        pv_hdr = QLabel("⚡  PRIME VERSE")
        pv_hdr.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        pv_hdr.setStyleSheet(f"color: {C.CYAN}; background: transparent; letter-spacing: 1px; margin-top: 8px;")
        lay.addWidget(pv_hdr)

        self._pv_local_btn = QPushButton("🔒  LOCAL-FIRST: OFF")
        self._pv_local_btn.setFixedHeight(30)
        self._pv_local_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pv_local_btn.clicked.connect(self._pv_toggle_local_first)
        lay.addWidget(self._pv_local_btn)

        self._pv_dashboard_btn = QPushButton("📊  OPEN MONITOR DASHBOARD")
        self._pv_dashboard_btn.setFixedHeight(30)
        self._pv_dashboard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pv_dashboard_btn.clicked.connect(self._pv_open_dashboard)
        lay.addWidget(self._pv_dashboard_btn)

        self._pv_gesture_btn = QPushButton("🖐  START GESTURE CONTROL")
        self._pv_gesture_btn.setFixedHeight(30)
        self._pv_gesture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pv_gesture_btn.clicked.connect(self._pv_toggle_gesture)
        lay.addWidget(self._pv_gesture_btn)

        self._pv_memory_lbl = QLabel("Memory: —")
        self._pv_memory_lbl.setFont(QFont("Segoe UI", 8))
        self._pv_memory_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(self._pv_memory_lbl)
        self._pv_refresh_prime_verse()

        lay.addStretch()

        # ── Mount inner content into scroll area, scroll area into outer card ──
        scroll.setWidget(panel)
        outer_lay.addWidget(scroll)
        return outer

    def _rebuild_mcp_servers_ui(self):
        # Clear existing rows
        for i in reversed(range(self._mcp_container_lay.count())):
            widget = self._mcp_container_lay.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        self._mcp_server_rows.clear()

        try:
            from actions.mcp_client import MCPClientManager
            mcp_mgr = MCPClientManager()
            if not mcp_mgr.loaded:
                mcp_mgr.initialize(player=self)
            
            servers = mcp_mgr.connections
            
            if not servers:
                empty_lbl = QLabel("No MCP servers configured.")
                empty_lbl.setFont(QFont("Segoe UI", 8))
                empty_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-style: italic; background: transparent;")
                self._mcp_container_lay.addWidget(empty_lbl)
                return
            
            for name, conn in servers.items():
                row_widget = QWidget()
                row_widget.setStyleSheet("background: transparent; border: none;")
                row_lay = QHBoxLayout(row_widget)
                row_lay.setContentsMargins(0, 2, 0, 2)
                row_lay.setSpacing(6)

                name_lbl = QLabel(name.upper())
                name_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                name_lbl.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
                row_lay.addWidget(name_lbl)

                status_lbl = QLabel("⚪ Stopped")
                status_lbl.setFont(QFont("Segoe UI", 8))
                status_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
                row_lay.addWidget(status_lbl)

                toggle_btn = QPushButton("Start")
                toggle_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                toggle_btn.setFixedSize(54, 22)
                toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                toggle_btn.clicked.connect(lambda checked, n=name: self._toggle_mcp_server(n))
                row_lay.addWidget(toggle_btn)

                self._mcp_container_lay.addWidget(row_widget)
                self._mcp_server_rows[name] = (status_lbl, toggle_btn)
                
            # Initial style update
            from actions.mcp_client import MCPClientManager
            for name, (status_lbl, toggle_btn) in self._mcp_server_rows.items():
                conn = MCPClientManager().connections.get(name)
                running = conn.running if conn else False
                if running:
                    status_lbl.setText("🟢 Running")
                    status_lbl.setStyleSheet(f"color: {C.GREEN}; font-size: 11px;")
                    toggle_btn.setText("Stop")
                    toggle_btn.setStyleSheet(
                        f"QPushButton {{ background: rgba(239, 68, 68, 0.15); color: {C.RED}; "
                        f"border: 1px solid {C.RED}; border-radius: 5px; font-size: 10px; font-weight: bold; }} "
                        f"QPushButton:hover {{ background: rgba(239, 68, 68, 0.35); }}"
                    )
                else:
                    status_lbl.setText("⚪ Stopped")
                    status_lbl.setStyleSheet(f"color: {C.TEXT_MED}; font-size: 11px;")
                    toggle_btn.setText("Start")
                    toggle_btn.setStyleSheet(
                        f"QPushButton {{ background: rgba(59, 130, 246, 0.15); color: {C.PRI}; "
                        f"border: 1px solid {C.PRI}; border-radius: 5px; font-size: 10px; font-weight: bold; }} "
                        f"QPushButton:hover {{ background: rgba(59, 130, 246, 0.35); }}"
                    )
        except Exception as e:
            print(f"[IP PRIME UI] Error building MCP Server UI: {e}")

    def _toggle_mcp_server(self, name):
        try:
            from actions.mcp_client import MCPClientManager
            mcp_mgr = MCPClientManager()
            conn = mcp_mgr.connections.get(name)
            if not conn:
                return
            
            def do_toggle():
                if conn.running:
                    self.write_log(f"SYS: Stopping MCP server '{name}'...")
                    conn.stop()
                else:
                    self.write_log(f"SYS: Starting MCP server '{name}'...")
                    success = conn.start()
                    if success:
                        self.write_log(f"SYS: MCP server '{name}' successfully started.")
                    else:
                        self.write_log(f"SYS: Failed to start MCP server '{name}'.")
            
            threading.Thread(target=do_toggle, daemon=True, name=f"MCP-Toggle-{name}").start()
        except Exception as e:
            print(f"[IP PRIME UI] Error toggling MCP server '{name}': {e}")

    def _open_mcp_config(self):
        try:
            import sys
            import subprocess
            if getattr(sys, "frozen", False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).resolve().parent
            config_path = base_dir / "config" / "mcp_servers.json"
            
            if not config_path.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)
                default_cfg = {
                    "mcpServers": {
                        "fetch": {
                            "command": "npx",
                            "args": ["-y", "mcp-server-fetch-typescript"],
                            "env": {}
                        },
                        "memory": {
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-memory"],
                            "env": {}
                        }
                    }
                }
                config_path.write_text(json.dumps(default_cfg, indent=4), encoding="utf-8")

            if sys.platform == "win32":
                import os
                os.startfile(str(config_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(config_path)])
            else:
                subprocess.Popen(["xdg-open", str(config_path)])
            
            self.write_log(f"SYS: Opened configuration '{config_path}' in system editor.")
        except Exception as e:
            self.write_log(f"SYS: Failed to open MCP configuration: {e}")

    def _arc_synthesize_core(self):
        try:
            name = self._arc_name_input.text().strip() or "IP Prime"
            humour = self._arc_humour_slider.value()
            energy = self._arc_energy_slider.value()
            sarcasm = self._arc_sarcasm_slider.value()
            prof = self._arc_prof_slider.value()
            creat = self._arc_creat_slider.value()

            personality = {
                "name": name,
                "humour": humour,
                "energy": energy,
                "sarcasm": sarcasm,
                "professionalism": prof,
                "creativity": creat
            }

            arc_file = CONFIG_DIR / "personality.json"
            arc_file.parent.mkdir(parents=True, exist_ok=True)
            arc_file.write_text(json.dumps(personality, indent=4), encoding="utf-8")

            # Try to dynamically update prompt in main/voice session if applicable
            self._log.append_log("🧬 ARC LAB: Personality Synthesis successful.")
            self._log.append_log(f"🧬 ASSISTANT: Name: '{name}' | Humour: {humour}% | Energy: {energy}% | Sarcasm: {sarcasm}% | Prof: {prof}% | Creat: {creat}%")
            
            if hasattr(self, "ip_ray") and self.ip_ray:
                self.ip_ray.trigger_personality_reload_and_greeting()

            # Show visual confirmation on the button
            self._arc_synth_btn.setText("✅ SYNTHESIZED")
            self._arc_synth_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C.GREEN}; "
                f"border: 1px solid {C.GREEN}; border-radius: 8px; font-weight: bold; }}"
            )
            QTimer.singleShot(2000, self._reset_synth_btn)
        except Exception as e:
            self._log.append_log(f"🧬 ARC LAB: Synthesis failed: {e}")

    def _reset_synth_btn(self):
        try:
            self._arc_synth_btn.setText("🧬  SYNTHESIZE CORE")
            self._arc_synth_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C.PRI}; "
                f"border: 1px solid {C.BORDER_B}; border-radius: 8px; font-weight: bold; letter-spacing: 0.5px; }} "
                f"QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; color: {C.CYAN}; }}"
            )
        except Exception:
            pass

    def _toggle_stealth_mode(self):
        val = self._stealth_btn.isChecked()
        self._update_stealth_btn_style()
        self._save_stealth_settings()
        self._log.append_log(f"SYS: Stealth browser {'ENABLED' if val else 'DISABLED'}")

    def _update_stealth_btn_style(self):
        val = self._stealth_btn.isChecked()
        if val:
            self._stealth_btn.setText("🕷  Stealth Enabled")
            self._stealth_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C.GREEN}; "
                f"border: 1px solid {C.GREEN}; border-radius: 6px; font-weight: bold; }} "
                f"QPushButton:hover {{ background: rgba(16, 185, 129, 0.08); }}"
            )
        else:
            self._stealth_btn.setText("🕷  Enable Stealth")
            self._stealth_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C.TEXT_MED}; "
                f"border: 1px solid {C.BORDER}; border-radius: 6px; }} "
                f"QPushButton:hover {{ background: rgba(255, 255, 255, 0.04); border: 1px solid {C.TEXT_MED}; }}"
            )

    def _browse_addons_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(self, "Select Add-ons Extensions Directory", self._stealth_addons_input.text() or "")
        if dir_path:
            self._stealth_addons_input.setText(dir_path)
            self._save_stealth_settings()

    # ── Windows Startup Registry ─────────────────────────────────────────────
    _STARTUP_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
    _STARTUP_APP_NAME = "IPPrime"

    def _check_startup_enabled(self) -> bool:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._STARTUP_REG_KEY, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, self._STARTUP_APP_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def _toggle_startup(self):
        enabled = self._startup_btn.isChecked()
        try:
            import winreg, sys
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self._STARTUP_REG_KEY, 0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            )
            if enabled:
                # Build the launch command — use pythonw.exe so no console window pops up
                python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                main_path  = str(Path(__file__).resolve().parent / "main.py")
                cmd = f'"{python_exe}" "{main_path}"'
                winreg.SetValueEx(key, self._STARTUP_APP_NAME, 0, winreg.REG_SZ, cmd)
                msg = "✅ Startup enabled! Ab PC on karte hi IP Prime chalega."
                colour = C.GREEN
            else:
                try:
                    winreg.DeleteValue(key, self._STARTUP_APP_NAME)
                except FileNotFoundError:
                    pass
                msg = "🔴 Startup disabled."
                colour = C.RED
            winreg.CloseKey(key)
            self._startup_status_lbl.setStyleSheet(f"color: {colour}; background: transparent;")
            self._startup_status_lbl.setText(msg)
        except Exception as e:
            self._startup_btn.setChecked(not enabled)  # revert
            self._startup_status_lbl.setStyleSheet(f"color: {C.RED}; background: transparent;")
            self._startup_status_lbl.setText(f"❌ Error: {e}")
        self._update_startup_btn_style(self._startup_btn.isChecked())

    def _update_startup_btn_style(self, enabled: bool):
        if enabled:
            self._startup_btn.setText("⚡  Auto-Start: ON")
            self._startup_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C.GREEN}; "
                f"border: 1px solid {C.GREEN}; border-radius: 6px; font-weight: bold; font-size: 10px; }} "
                f"QPushButton:hover {{ background: rgba(16,185,129,0.08); }}"
            )
        else:
            self._startup_btn.setText("⚡  Auto-Start: OFF")
            self._startup_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C.TEXT_MED}; "
                f"border: 1px solid {C.BORDER}; border-radius: 6px; font-size: 10px; }} "
                f"QPushButton:hover {{ background: rgba(255,255,255,0.04); }}"
            )

    def _save_stealth_settings(self):
        try:
            try:
                existing = json.loads(API_FILE.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
            
            existing["use_camoufox"] = self._stealth_btn.isChecked()
            existing["camoufox_headless"] = self._stealth_headless_cb.isChecked()
            existing["camoufox_block_assets"] = self._stealth_block_cb.isChecked()
            existing["camoufox_human_mimic"] = self._stealth_human_cb.isChecked()
            existing["camoufox_block_webrtc"] = self._stealth_webrtc_cb.isChecked()
            existing["camoufox_allow_webgl"] = not self._stealth_webgl_cb.isChecked() # allow WebGL is True if not checked spoof
            existing["camoufox_geoip"] = self._stealth_geoip_cb.isChecked()
            existing["camoufox_os"] = self._stealth_os_combo.currentText()
            existing["camoufox_proxy"] = self._stealth_proxy_input.text().strip()
            existing["camoufox_addons_path"] = self._stealth_addons_input.text().strip()
            
            import os
            os.makedirs(CONFIG_DIR, exist_ok=True)
            API_FILE.write_text(json.dumps(existing, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[Stealth Settings] Error saving: {e}")

    def _save_integrations_settings(self):
        try:
            try:
                existing = json.loads(API_FILE.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
            
            existing["obsidian_vault_path"] = self._obsidian_path_input.text().strip()
            existing["spotify_client_id"] = self._spotify_id_input.text().strip()
            existing["spotify_client_secret"] = self._spotify_secret_input.text().strip()
            existing["home_assistant_url"] = self._ha_url_input.text().strip()
            existing["home_assistant_token"] = self._ha_token_input.text().strip()
            
            import os
            os.makedirs(CONFIG_DIR, exist_ok=True)
            API_FILE.write_text(json.dumps(existing, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[Integrations Settings] Error saving: {e}")

    def _browse_obsidian_vault(self):
        from PyQt6.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(self, "Select Obsidian Vault Directory", self._obsidian_path_input.text() or "")
        if dir_path:
            self._obsidian_path_input.setText(dir_path)
            self._save_integrations_settings()

    def _toggle_settings_panel(self):
        self._settings_panel_visible = not getattr(self, '_settings_panel_visible', False)
        target_w = 240 if self._settings_panel_visible else 0
        self._settings_anim = QPropertyAnimation(self._settings_panel, b"maximumWidth")
        self._settings_anim.setDuration(300)
        self._settings_anim.setStartValue(self._settings_panel.maximumWidth())
        self._settings_anim.setEndValue(target_w)
        self._settings_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._settings_panel.setMinimumWidth(0)
        self._settings_anim.start()
        icon = "✕" if self._settings_panel_visible else "⚙"
        self._settings_gear_btn.setText(icon)

    def _on_router_badge_updated(self, model: str):
        if not hasattr(self, "_router_badge"):
            return
        if model.upper() == "NVIDIA":
            self._router_badge.setText("🟩 NVIDIA")
            self._router_badge.setStyleSheet(
                "color: #76B900; background: rgba(118, 185, 0, 0.1); "
                "border: 1px solid #76B900; border-radius: 10px; padding: 3px 8px; font-weight: bold; font-size: 11px;"
            )
        elif model.upper() == "HACKER":
            self._router_badge.setText("💀 Hacker Mode")
            self._router_badge.setStyleSheet(
                "color: #ef4444; background: rgba(239, 68, 68, 0.1); "
                "border: 1px solid #ef4444; border-radius: 10px; padding: 3px 8px; font-weight: bold; font-size: 11px;"
            )
        else:
            self._router_badge.setText("🟢 Gemini")
            self._router_badge.setStyleSheet(
                "color: #10b981; background: rgba(16, 185, 129, 0.1); "
                "border: 1px solid #10b981; border-radius: 10px; padding: 3px 8px; font-weight: bold; font-size: 11px;"
            )

    def write_log(self, text: str):
        self._log_sig.emit(text)

    def _build_left_panel(self) -> QWidget:
        self._left_panel = QWidget()
        self._left_panel.setFixedWidth(_LEFT_W)
        self._left_panel.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px;")
        lay = QVBoxLayout(self._left_panel)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(6)

        self._left_hdr = QLabel("◈ SYS MONITOR")
        self._left_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._left_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                          f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(self._left_hdr)
        lay.addSpacing(2)

        self._bar_cpu = MetricBar("CPU", C.PRI)
        self._graph_cpu = MetricGraph(C.PRI)
        self._bar_mem = MetricBar("MEM", C.ACC2)
        self._graph_mem = MetricGraph(C.ACC2)
        
        self._bar_net = MetricBar("NET", C.GREEN)
        self._bar_gpu = MetricBar("GPU", C.ACC)
        self._bar_tmp = MetricBar("TMP", "#ff6688")

        lay.addWidget(self._bar_cpu)
        lay.addWidget(self._graph_cpu)
        lay.addWidget(self._bar_mem)
        lay.addWidget(self._graph_mem)
        for bar in [self._bar_net, self._bar_gpu, self._bar_tmp]:
            lay.addWidget(bar)

        lay.addSpacing(4)

        self._left_info_panel = QWidget()
        self._left_info_panel.setStyleSheet(
            f"background: {C.BG}; border: 1px solid {C.BORDER}; border-radius: 6px;"
        )
        ip_lay = QVBoxLayout(self._left_info_panel)
        ip_lay.setContentsMargins(8, 6, 8, 6)
        ip_lay.setSpacing(3)

        self._uptime_lbl = QLabel("UP  --:--")
        self._uptime_lbl.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
        ip_lay.addWidget(self._uptime_lbl)

        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont("Consolas", 8))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        ip_lay.addWidget(self._proc_lbl)

        os_name = {"Windows": "WIN", "Darwin": "macOS", "Linux": "LINUX"}.get(_OS, _OS.upper())
        self._os_lbl = QLabel(f"OS  {os_name}")
        self._os_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._os_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")
        ip_lay.addWidget(self._os_lbl)

        lay.addWidget(self._left_info_panel)
        
        # HUD CONFIG Panel
        self._cfg_hdr = QLabel("◈ HUD CONFIG")
        self._cfg_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._cfg_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                                    f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px; margin-top: 6px;")
        lay.addWidget(self._cfg_hdr)
        
        self._lbl_opacity = QLabel("OPACITY: 65%")
        self._lbl_opacity.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self._lbl_opacity.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        lay.addWidget(self._lbl_opacity)
        
        self._slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self._slider_opacity.setRange(0, 100)
        self._slider_opacity.setValue(65)
        self._slider_opacity.setFixedHeight(16)
        self._slider_opacity.setCursor(Qt.CursorShape.PointingHandCursor)
        self._slider_opacity.valueChanged.connect(self._on_opacity_changed)
        lay.addWidget(self._slider_opacity)
        
        self._lbl_glow = QLabel("GLOW: 15%")
        self._lbl_glow.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self._lbl_glow.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        lay.addWidget(self._lbl_glow)
        
        self._slider_glow = QSlider(Qt.Orientation.Horizontal)
        self._slider_glow.setRange(0, 100)
        self._slider_glow.setValue(15)
        self._slider_glow.setFixedHeight(16)
        self._slider_glow.setCursor(Qt.CursorShape.PointingHandCursor)
        self._slider_glow.valueChanged.connect(self._on_glow_changed)
        lay.addWidget(self._slider_glow)

        lay.addStretch()

        self._left_badges = []
        for txt, col in [
            ("AI CORE\nACTIVE",     C.GREEN),
            ("SEC\nCLEARED",        C.PRI),
            ("PROTOCOL\nXXXVIII",   C.TEXT_DIM),
        ]:
            lbl = QLabel(txt)
            lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {col}; background: {C.BG};"
                f"border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;"
            )
            lay.addWidget(lbl)
            self._left_badges.append(lbl)

        return self._left_panel
    def _build_right_panel(self) -> QWidget:
        self._right_panel = QWidget()
        self._right_panel.setFixedWidth(_RIGHT_W)
        self._right_panel.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px;")
        lay = QVBoxLayout(self._right_panel)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        self._right_secs = []
        def _sec(txt):
            l = QLabel(f"▸ {txt}")
            l.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; letter-spacing: 0.5px;")
            self._right_secs.append(l)
            return l

        lay.addWidget(_sec("ACTIVITY LOG"))
        self._log = LogWidget()
        lay.addWidget(self._log, stretch=1)

        self._right_seps = []
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep)
        self._right_seps.append(sep)

        lay.addWidget(_sec("FILE UPLOAD"))
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        lay.addWidget(self._drop_zone)

        self._file_hint = QLabel("No file loaded — drop or click above to upload")
        self._file_hint.setFont(QFont("Segoe UI", 8))
        self._file_hint.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._file_hint.setWordWrap(True)
        lay.addWidget(self._file_hint)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep2)
        self._right_seps.append(sep2)

        lay.addWidget(_sec("COMMAND INPUT"))
        lay.addLayout(self._build_input_row())





        return self._right_panel

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(8)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question…")
        self._input.setFont(QFont("Segoe UI", 9))
        self._input.setFixedHeight(34)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.BG}; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: 17px; padding: 4px 14px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        self._send_btn = QPushButton("▸")
        self._send_btn.setFixedSize(34, 34)
        self._send_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 17px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        self._send_btn.clicked.connect(self._send)
        row.addWidget(self._send_btn)
        return row

    def _build_footer(self) -> QWidget:
        self._footer_widget = QWidget()
        self._footer_widget.setFixedHeight(22)
        self._footer_widget.setStyleSheet(f"background: {C.DARK}; border-top: 1px solid {C.BORDER};")
        lay = QHBoxLayout(self._footer_widget); lay.setContentsMargins(14, 0, 14, 0)

        self._footer_labels = []
        def _fl(txt, color=C.TEXT_MED):
            l = QLabel(txt); l.setFont(QFont("Segoe UI", 8))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            self._footer_labels.append(l)
            return l
        

        
        self._uptime_lbl = QLabel("UPTIME: 00:00:00")
        self._uptime_lbl.setFont(QFont("Segoe UI", 8))
        self._uptime_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        lay.addWidget(self._uptime_lbl)

        self._prime_metrics_lbl = QLabel("")
        self._prime_metrics_lbl.setFont(QFont("Segoe UI", 8))
        self._prime_metrics_lbl.setStyleSheet(f"color: {C.CYAN}; background: transparent;")
        lay.addWidget(self._prime_metrics_lbl)

        lay.addStretch()
        self._footer_copyright_lbl = QLabel("© IP VERSE")
        self._footer_copyright_lbl.setFont(QFont("Segoe UI", 8))
        self._footer_copyright_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        lay.addWidget(self._footer_copyright_lbl)
        
        return self._footer_widget

    def _cycle_theme(self):
        theme_file = CONFIG_DIR / "theme.json"
        try:
            with open(theme_file, "r") as f:
                idx = json.load(f).get("theme_idx", 0)
        except Exception:
            idx = 0
            
        idx = (idx + 1) % 5
        try:
            with open(theme_file, "w") as f:
                json.dump({"theme_idx": idx}, f)
        except Exception:
            pass
            
        _load_theme()
        self._apply_theme()
        self._log.append_log(f"SYS: Theme dynamically cycled to Preset {idx + 1}. Interface reloaded.")

    def _set_theme_by_name(self, theme_name: str):
        mapping = {"blue": 0, "red": 1, "green": 2, "purple": 3, "cyber": 4}
        if theme_name in mapping:
            idx = mapping[theme_name]
            theme_file = CONFIG_DIR / "theme.json"
            try:
                with open(theme_file, "w") as f:
                    json.dump({"theme_idx": idx}, f)
            except Exception:
                pass
            _load_theme()
            self._apply_theme()
            self._log.append_log(f"SYS: Theme changed to '{theme_name}' via Web HUD. Interface reloaded.")

    def _apply_theme(self):
        # 1. Main Window / Central widget background
        self.setStyleSheet(f"QMainWindow {{ background-color: {C.BG}; }}")
        self._central_widget.setStyleSheet(f"""
            QWidget#CentralWidget {{
                background: qradialgradient(cx:0.5, cy:0.4, radius:0.8, fx:0.5, fy:0.4,
                    stop:0 {C.PRI_GHO},
                    stop:0.4 rgba(3, 7, 18, 0.95),
                    stop:1 {C.BG});
            }}
        """)

        # 2. Header
        self._header_widget.setStyleSheet(f"""
            QWidget#HeaderWidget {{
                background: {C.PANEL};
                border: 1.5px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C.PRI},
                    stop:0.5 {C.ACC if hasattr(C, 'ACC') else C.PRI},
                    stop:1 {C.PRI});
                border-radius: 27px;
            }}
        """)
        self._title_lbl.setStyleSheet(f"""
            QLabel {{
                color: {C.WHITE};
                background: transparent;
                border: none;
                letter-spacing: 4px;
            }}
        """)
        self._title_lbl.setText(f"<span style='color: {C.PRI}; font-weight: 800;'>IP</span> <span style='color: {C.CYAN}; font-weight: 800;'>PRIME</span>")

        # 3. Left Panel
        self._left_panel.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px;")
        self._left_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        
        # 19. Metric Graphs update
        if hasattr(self, "_graph_cpu"):
            self._graph_cpu._color = C.PRI
            self._graph_cpu.update()
        if hasattr(self, "_graph_mem"):
            self._graph_mem._color = C.ACC2
            self._graph_mem.update()

        # 20. HUD CONFIG Styling
        if hasattr(self, "_cfg_hdr"):
            self._cfg_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px; margin-top: 6px;")
        if hasattr(self, "_lbl_opacity"):
            self._lbl_opacity.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        if hasattr(self, "_lbl_glow"):
            self._lbl_glow.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")

        # 21. Sliders styling
        if hasattr(self, "_slider_opacity") and hasattr(self, "_slider_glow"):
            slider_style = f"""
                QSlider::groove:horizontal {{
                    background: {C.BG};
                    height: 4px;
                    border-radius: 2px;
                    border: 1px solid {C.BORDER};
                }}
                QSlider::sub-page:horizontal {{
                    background: {C.PRI};
                    border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    background: {C.TEXT};
                    border: 1px solid {C.PRI};
                    width: 10px;
                    margin-top: -4px;
                    margin-bottom: -4px;
                    border-radius: 5px;
                }}
                QSlider::handle:horizontal:hover {{
                    background: {C.PRI};
                    border: 1px solid {C.TEXT};
                }}
            """
            self._slider_opacity.setStyleSheet(slider_style)
            self._slider_glow.setStyleSheet(slider_style)
            
            # Sync slider values
            match_p = re.search(r"rgba\(\d+,\s*\d+,\s*\d+,\s*([\d\.]+)\)", C.PANEL)
            if match_p:
                alpha_p = float(match_p.group(1))
                self._slider_opacity.blockSignals(True)
                self._slider_opacity.setValue(int(alpha_p * 100))
                self._lbl_opacity.setText(f"OPACITY: {int(alpha_p * 100)}%")
                self._slider_opacity.blockSignals(False)
                
            match_b = re.search(r"rgba\(\d+,\s*\d+,\s*\d+,\s*([\d\.]+)\)", C.BORDER)
            if match_b:
                alpha_b = float(match_b.group(1))
                self._slider_glow.blockSignals(True)
                self._slider_glow.setValue(int(alpha_b * 100))
                self._lbl_glow.setText(f"GLOW: {int(alpha_b * 100)}%")
                self._slider_glow.blockSignals(False)

        # 21b. ARC Lab Dynamic Theme Re-application
        if hasattr(self, "_arc_name_input"):
            self._arc_name_input.setStyleSheet(
                f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
                f"border: 1px solid {C.BORDER}; border-radius: 6px; padding: 2px 8px; }} "
                f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}"
            )
        if hasattr(self, "_arc_synth_btn") and "SYNTHESIZE" in self._arc_synth_btn.text():
            self._arc_synth_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C.PRI}; "
                f"border: 1px solid {C.BORDER_B}; border-radius: 8px; font-weight: bold; letter-spacing: 0.5px; }} "
                f"QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; color: {C.CYAN}; }}"
            )
        if hasattr(self, "_arc_val_labels"):
            for val_lbl in self._arc_val_labels:
                val_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        if hasattr(self, "_arc_sliders"):
            for slider in self._arc_sliders:
                slider.setStyleSheet(
                    f"QSlider::groove:horizontal {{ height: 4px; background: {C.BORDER}; border-radius: 2px; }} "
                    f"QSlider::sub-page:horizontal {{ background: {C.PRI}; border-radius: 2px; }} "
                    f"QSlider::handle:horizontal {{ background: {C.ACC}; border: 1px solid {C.ACC2}; width: 12px; height: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }} "
                    f"QSlider::handle:horizontal:hover {{ background: {C.CYAN}; border-radius: 6px; }}"
                )

        # 4. Metric Bars
        self._bar_cpu._color = C.PRI
        self._bar_mem._color = C.ACC2
        self._bar_net._color = C.GREEN
        self._bar_gpu._color = C.ACC
        self._bar_cpu.update()
        self._bar_mem.update()
        self._bar_net.update()
        self._bar_gpu.update()
        self._bar_tmp.update()

        # 5. Left Info Panel
        self._left_info_panel.setStyleSheet(f"background: {C.BG}; border: 1px solid {C.BORDER}; border-radius: 6px;")
        self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        self._os_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")

        # 6. Left Badges
        for i, (txt, col) in enumerate([
            ("AI CORE\nACTIVE",     C.GREEN),
            ("SEC\nCLEARED",        C.PRI),
            ("PROTOCOL\nXXXVIII",   C.TEXT_DIM),
        ]):
            if i < len(self._left_badges):
                self._left_badges[i].setStyleSheet(
                    f"color: {col}; background: {C.BG};"
                    f"border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;"
                )

        # 7. HUD Container
        self._hud_container.setStyleSheet(f"background: transparent; border: none; border-radius: 12px;")

        # 8. Right Panel
        self._right_panel.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px;")
        
        # 9. Right Panel Sections
        for l in self._right_secs:
            l.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; letter-spacing: 0.5px;")

        # 10. Right Panel Separators
        for sep in self._right_seps:
            sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")

        # 11. Log Widget
        self._log.setStyleSheet(f"""
            QScrollArea {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
            QScrollBar:vertical {{
                background: {C.BG};
                width: 8px;
                border: none;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        # 12. File Hint
        self._file_hint.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")

        # 13. Command Input
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.BG}; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: 17px; padding: 4px 14px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)

        # 14. Send Button
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 17px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)

        pass

        # 17. Footer Widget & Labels
        self._footer_widget.setStyleSheet(f"background: {C.DARK}; border-top: 1px solid {C.BORDER};")
        self._theme_btn.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        self._uptime_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        for l in self._footer_labels:
            l.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")

        # 18. HUD paint invalidation
        if hasattr(self, "hud"):
            self.hud.update()

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell IP PRIME what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _toggle_right_panel(self):
        self._right_panel_visible = not getattr(self, '_right_panel_visible', False)
        target_w = _RIGHT_W if self._right_panel_visible else 0
        
        self._panel_anim = QPropertyAnimation(self._right_panel, b"maximumWidth")
        self._panel_anim.setDuration(300)
        self._panel_anim.setStartValue(self._right_panel.maximumWidth())
        self._panel_anim.setEndValue(target_w)
        self._panel_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self._right_panel.setMinimumWidth(0)
        self._panel_anim.start()

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._apply_state("MUTED" if self._muted else "LISTENING")
        self.write_log(f"SYS: {'Muted' if self._muted else 'Unmuted'}.")

    def _pv_refresh_prime_verse(self):
        try:
            from prime_platform.config import load_prime_config
            from prime_platform.infinite_memory import get_memory_stats
            lf = load_prime_config().get("local_first", {}).get("enabled", False)
            if hasattr(self, "_pv_local_btn"):
                self._pv_local_btn.setText(f"🔒  LOCAL-FIRST: {'ON' if lf else 'OFF'}")
            s = get_memory_stats()
            if hasattr(self, "_pv_memory_lbl"):
                self._pv_memory_lbl.setText(
                    f"Memory: {s['kb_entries']} KB · {s['archive_turns']} archived turns"
                )
        except Exception:
            pass

    def _pv_toggle_local_first(self):
        try:
            from prime_platform.local_first import set_local_first
            from prime_platform.config import load_prime_config
            enabled = not load_prime_config().get("local_first", {}).get("enabled", False)
            set_local_first(enabled=enabled)
            self._pv_refresh_prime_verse()
            self.write_log(f"SYS: Local-first {'enabled' if enabled else 'disabled'}.")
        except Exception as e:
            self.write_log(f"SYS: Local-first error: {e}")

    def _pv_open_dashboard(self):
        try:
            from actions.prime_features import prime_dashboard

            class _DashPlayer:
                def __init__(self, win):
                    self._win = win
                def write_log(self, text):
                    self._win.write_log(text)

            msg = prime_dashboard({"action": "start"}, player=_DashPlayer(self))
            self.write_log(f"SYS: {str(msg)[:140]}")
        except Exception as e:
            self.write_log(f"SYS: Dashboard error: {e}")

    def _pv_toggle_gesture(self):
        try:
            from prime_platform.gesture_control import GestureService
            from actions.prime_features import prime_gesture_control

            class _GesturePlayer:
                def __init__(self, win):
                    self._win = win
                def write_log(self, text):
                    self._win.write_log(text)
                @property
                def muted(self):
                    return self._win._muted
                @muted.setter
                def muted(self, value):
                    if bool(value) != bool(self._win._muted):
                        self._win._toggle_mute()

            player = _GesturePlayer(self)
            svc = GestureService.instance()
            if svc._running:
                prime_gesture_control({"action": "stop"}, player=player)
                self._pv_gesture_btn.setText("🖐  START GESTURE CONTROL")
            else:
                prime_gesture_control({"action": "start"}, player=player)
                self._pv_gesture_btn.setText("🖐  STOP GESTURE CONTROL")
        except Exception as e:
            self.write_log(f"SYS: Gesture error: {e}")

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")
        if hasattr(self, "_log"):
            self._log.show_typing(state in ("THINKING", "PROCESSING"))

    def _apply_thought(self, text: str):
        """Updates the NLA Live HUD Thought Stream Panel with new real-time reasoning text."""
        if not hasattr(self, "_thought_label"):
            return
        # Determine colour based on content keywords
        txt_lower = text.lower()
        if any(k in txt_lower for k in ("browser", "camoufox", "ui-tars", "visual", "screenshot", "desktop")):
            colour = C.CYAN      # Electric cyan for visual/browser ops
            dot_colour = C.CYAN
        elif any(k in txt_lower for k in ("worktree", "git", "compil", "agent", "orchestrat", "branch", "conflict", "merge")):
            colour = C.ACC       # Royal purple for coder/git ops
            dot_colour = C.ACC
        else:
            colour = C.GREEN     # Emerald green for general cognition
            dot_colour = C.GREEN
        self._thought_dot.setStyleSheet(f"color: {dot_colour}; font-size: 8px;")
        self._thought_label.setStyleSheet(
            f"color: {colour}; background: transparent;"
            f"font-family: 'Consolas','Courier New',monospace; font-size: 10px; letter-spacing: 0.5px;"
        )
        # Elide long text to fit width without wrapping
        max_chars = 110
        display = text if len(text) <= max_chars else text[:max_chars - 1] + "…"
        self._thought_label.setText(f"> {display}")

    def _on_opacity_changed(self, val: int):
        self._lbl_opacity.setText(f"OPACITY: {val}%")
        self._update_panel_opacity(val)
        
    def _on_glow_changed(self, val: int):
        self._lbl_glow.setText(f"GLOW: {val}%")
        self._update_border_glow(val)
        
    def _update_panel_opacity(self, val: int):
        alpha = val / 100.0
        match = re.search(r"rgba\((\d+),\s*(\d+),\s*(\d+),", C.PANEL)
        if match:
            r, g, b = match.groups()
            C.PANEL = f"rgba({r}, {g}, {b}, {alpha:.2f})"
            self._apply_theme()
            
    def _update_border_glow(self, val: int):
        alpha = val / 100.0
        match = re.search(r"rgba\((\d+),\s*(\d+),\s*(\d+),", C.BORDER)
        if match:
            r, g, b = match.groups()
            C.BORDER = f"rgba({r}, {g}, {b}, {alpha:.2f})"
            self._apply_theme()

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key")) and bool(d.get("os_system"))
        except Exception:
            return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 460, 390
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    def _on_setup_done(self, key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({"gemini_api_key": key, "os_system": os_name}, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._log.append_log(f"SYS: Initialised. OS={os_name.upper()}. IP PRIME online.")

    def closeEvent(self, event):
        try:
            from memory.memory_manager import save_shutdown_summary
            save_shutdown_summary()
        except Exception:
            pass
        super().closeEvent(event)

class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# WELCOME SPLASH  —  Matrix rain + cyberpunk boot sequence
# ═══════════════════════════════════════════════════════════════════════════════
class WelcomeSplash(QWidget):
    """Full-screen cyberpunk welcome splash with character rain and boot sequence."""

    RAIN_CHARS = (
        "アイウエオカキクケコサシスセソタチツテトナニヌネノ"
        "ハヒフヘホマミムメモヤユヨラリルレロワヲン"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        "#@$%&*!?><|[]{}01"
    )

    BOOT_LINES = [
        (0,    "[BOOT]  Quantum neural core warming up..."),
        (500,  "[SYS]   Loading cognitive matrix............. OK"),
        (900,  "[MEM]   Allocating latent space embeddings... OK"),
        (1300, "[NET]   Establishing encrypted uplinks........ OK"),
        (1700, "[SEC]   Camoufox stealth layer active......... OK"),
        (2100, "[AI]    Gemini 2.5 neural pathway online...... OK"),
        (2500, "[HUD]   Holographic display initialised....... OK"),
        (2900, "[READY] ■ IP PRIME IS ONLINE ■"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # ── Rain state ─────────────────────────────────────────────────────
        self._cols: list[dict] = []
        self._init_rain()

        # ── Boot text lines visible so far ─────────────────────────────────
        self._boot_lines_visible: list[str] = []
        self._progress = 0          # 0-100
        self._title_glitch = 0      # glitch frame counter
        self._glitch_char = "IP PRIME"
        self._done = False

        # ── Rain animation (60fps) ──────────────────────────────────────────
        self._rain_tmr = QTimer(self)
        self._rain_tmr.timeout.connect(self._tick_rain)
        self._rain_tmr.start(40)

        # ── Boot line timers ────────────────────────────────────────────────
        for delay_ms, line in self.BOOT_LINES:
            QTimer.singleShot(delay_ms, lambda l=line: self._add_boot_line(l))

        # ── Progress bar timer ─────────────────────────────────────────────
        self._prog_tmr = QTimer(self)
        self._prog_tmr.timeout.connect(self._tick_progress)
        self._prog_tmr.start(32)

        # ── Glitch timer ───────────────────────────────────────────────────
        self._glitch_tmr = QTimer(self)
        self._glitch_tmr.timeout.connect(self._tick_glitch)
        self._glitch_tmr.start(80)

        # ── Auto close after 3.6s ──────────────────────────────────────────
        QTimer.singleShot(3600, self._finish)

    # ─── helpers ───────────────────────────────────────────────────────────
    def _init_rain(self):
        w = QApplication.primaryScreen().geometry().width()
        col_w = 18
        n_cols = w // col_w + 2
        self._col_w = col_w
        self._cols = [
            {
                "x": i * col_w,
                "y": random.randint(-200, 0),
                "speed": random.uniform(8, 22),
                "len": random.randint(6, 22),
                "chars": [random.choice(self.RAIN_CHARS) for _ in range(28)],
                "bright": random.random() > 0.85,
            }
            for i in range(n_cols)
        ]

    def _tick_rain(self):
        h = self.height()
        for col in self._cols:
            col["y"] += col["speed"]
            if col["y"] - col["len"] * 18 > h + 40:
                col["y"] = random.randint(-120, -20)
                col["speed"] = random.uniform(8, 22)
                col["len"] = random.randint(6, 22)
                col["bright"] = random.random() > 0.85
            # randomly mutate one char for flicker
            idx = random.randint(0, len(col["chars"]) - 1)
            col["chars"][idx] = random.choice(self.RAIN_CHARS)
        self.update()

    def _tick_progress(self):
        if self._progress < 100:
            self._progress = min(100, self._progress + 1)
            self.update()

    def _tick_glitch(self):
        self._title_glitch = (self._title_glitch + 1) % 12
        if self._title_glitch < 2:
            glitched = ""
            for ch in "IP PRIME":
                if random.random() < 0.25:
                    glitched += random.choice("@#$%!?&*<>[]{}|01アイウ")
                else:
                    glitched += ch
            self._glitch_char = glitched
        else:
            self._glitch_char = "IP PRIME"
        self.update()

    def _add_boot_line(self, line: str):
        self._boot_lines_visible.append(line)
        self.update()

    def _finish(self):
        self._done = True
        self._rain_tmr.stop()
        self._prog_tmr.stop()
        self._glitch_tmr.stop()
        self.close()

    # ─── painting ──────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Deep background
        p.fillRect(0, 0, w, h, QColor(2, 6, 15, 252))

        # ── Matrix rain ────────────────────────────────────────────────────
        fnt_rain = QFont("Consolas", 13)
        fnt_rain.setBold(True)
        p.setFont(fnt_rain)
        fm = p.fontMetrics()
        ch_h = fm.height()

        for col in self._cols:
            n = col["len"]
            for i in range(n):
                cy = int(col["y"]) - i * ch_h
                if cy < -ch_h or cy > h + ch_h:
                    continue
                char = col["chars"][i % len(col["chars"])]
                if i == 0:  # head — bright white/cyan
                    alpha = 255
                    colour = QColor(200, 255, 255, alpha) if col["bright"] else QColor(100, 255, 200, alpha)
                elif i < 3:
                    fade = int(255 * (1 - i / n))
                    colour = QColor(0, 230, 150, fade)
                else:
                    fade = max(20, int(180 * (1 - i / n)))
                    colour = QColor(0, 160, 80, fade)
                p.setPen(colour)
                p.drawText(col["x"], cy, char)

        # ── Dark gradient overlay (centre readable zone) ───────────────────
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(2, 6, 15, 0))
        grad.setColorAt(0.28, QColor(2, 6, 15, 200))
        grad.setColorAt(0.72, QColor(2, 6, 15, 200))
        grad.setColorAt(1.0, QColor(2, 6, 15, 0))
        p.fillRect(0, 0, w, h, QBrush(grad))

        # ── Cyan top accent line ───────────────────────────────────────────
        pen_acc = QPen(QColor(6, 182, 212, 180), 1.5)
        p.setPen(pen_acc)
        p.drawLine(w // 4, h // 2 - 155, 3 * w // 4, h // 2 - 155)

        # ── Main title — GLITCH ────────────────────────────────────────────
        fnt_title = QFont("Consolas", 62)
        fnt_title.setBold(True)
        fnt_title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 14)
        p.setFont(fnt_title)

        # Shadow
        p.setPen(QColor(6, 182, 212, 30))
        p.drawText(0 + 4, h // 2 - 100 + 4, w, 100, Qt.AlignmentFlag.AlignCenter, self._glitch_char)

        # Main
        grad_title = QLinearGradient(0, h // 2 - 140, 0, h // 2 - 60)
        grad_title.setColorAt(0.0, QColor(230, 240, 255))
        grad_title.setColorAt(0.5, QColor(6, 182, 212))
        grad_title.setColorAt(1.0, QColor(99, 102, 241))
        p.setPen(QPen(QBrush(grad_title), 1))
        p.drawText(0, h // 2 - 140, w, 100, Qt.AlignmentFlag.AlignCenter, self._glitch_char)

        # ── Subtitle ───────────────────────────────────────────────────────
        fnt_sub = QFont("Consolas", 13)
        fnt_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 7)
        p.setFont(fnt_sub)
        p.setPen(QColor(6, 182, 212, 160))
        p.drawText(0, h // 2 - 55, w, 30, Qt.AlignmentFlag.AlignCenter,
                   "ADVANCED  AGENTIC  INTELLIGENCE  SYSTEM  //  v2.5")

        # ── Boot log lines ─────────────────────────────────────────────────
        fnt_log = QFont("Consolas", 10)
        p.setFont(fnt_log)
        log_y = h // 2 - 10
        max_show = 8
        lines = self._boot_lines_visible[-max_show:]
        for i, line in enumerate(lines):
            is_last = (i == len(lines) - 1)
            if "READY" in line:
                p.setPen(QColor(0, 255, 180, 255))
            elif is_last:
                p.setPen(QColor(6, 182, 212, 230))
            else:
                alpha = max(60, 200 - (len(lines) - 1 - i) * 28)
                p.setPen(QColor(100, 200, 140, alpha))
            p.drawText(0, log_y + i * 22, w, 22, Qt.AlignmentFlag.AlignCenter, line)

        # ── Progress bar ───────────────────────────────────────────────────
        bar_w = min(520, w - 120)
        bar_x = (w - bar_w) // 2
        bar_y = h // 2 + 185
        bar_h = 4

        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(15, 30, 55, 200))
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)

        # Fill
        fill_w = int(bar_w * self._progress / 100)
        if fill_w > 0:
            grad_bar = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
            grad_bar.setColorAt(0.0, QColor(6, 182, 212, 220))
            grad_bar.setColorAt(0.6, QColor(99, 102, 241, 220))
            grad_bar.setColorAt(1.0, QColor(6, 182, 212, 255))
            p.setBrush(QBrush(grad_bar))
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 2, 2)

        # Progress label
        fnt_prog = QFont("Consolas", 8)
        p.setFont(fnt_prog)
        p.setPen(QColor(71, 85, 105, 200))
        p.drawText(0, bar_y + 14, w, 16, Qt.AlignmentFlag.AlignCenter,
                   f"LOADING  {self._progress}%")

        # ── Bottom accent line ─────────────────────────────────────────────
        p.setPen(pen_acc)
        p.drawLine(w // 4, h // 2 + 220, 3 * w // 4, h // 2 + 220)

        p.end()

    def keyPressEvent(self, e):
        # Allow instant dismiss with any key
        self._finish()

    def mousePressEvent(self, e):
        self._finish()


class IPRayUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")

        # ── Show cyberpunk welcome splash ──────────────────────────────────
        self._splash = WelcomeSplash()
        self._splash.show()
        self._app.processEvents()

        self._win = MainWindow(face_path)
        self._win.showMaximized()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_thought(self, text: str):
        """Stream a live reasoning/thought update to the NLA HUD Thought Panel."""
        try:
            self._win._thought_sig.emit(str(text))
        except Exception:
            pass

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def set_fullscreen(self, full: bool):
        self._win._fullscreen_sig.emit(full)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def pulse_highlight(self, x: int, y: int, duration: float = 3.0, color: str = "cyan"):
        self._win._pulse_highlight_sig.emit(x, y, duration, color)

    def show_ocr_translation(self, items: list):
        self._win._ocr_translate_sig.emit(items)

    def set_router_badge(self, model: str):
        self._win._router_badge_sig.emit(model)

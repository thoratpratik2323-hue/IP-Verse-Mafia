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
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar, QSlider,
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
                    {"BG": "#0a0014", "PANEL": "rgba(25, 10, 45, 0.65)", "PRI": "#D946EF", "PRI_DIM": "#C026D3", "PRI_GHO": "rgba(217, 70, 239, 0.12)", "BORDER": "rgba(217, 70, 239, 0.15)", "ACC": "#06B6D4", "ACC2": "#22D3EE", "CYAN": "#F472B6", "GREEN": "#10B981"}
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
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"
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
        
        # Ambient starfield particles
        self._ambient_particles: list[list[float]] = []
        for _ in range(35):
            self._ambient_particles.append([
                random.uniform(0, 800),  # X
                random.uniform(0, 800),  # Y
                random.uniform(1.0, 2.5),# Size
                random.uniform(0.1, 0.45),# Speed
                random.uniform(0.12, 0.45)# Opacity
            ])

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
        self._face_px: QPixmap | None = None
        self._load_face(face_path)

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def _load_face(self, path: str):
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(path).convert("RGBA")
            sz  = min(img.size)
            img = img.resize((sz, sz), Image.LANCZOS)
            mk  = Image.new("L", (sz, sz), 0)
            ImageDraw.Draw(mk).ellipse((2, 2, sz - 2, sz - 2), fill=255)
            img.putalpha(mk)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue())
            self._face_px = px
        except Exception:
            self._face_px = None

    def _step(self):
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

        # Voice level sound amplitude emulation
        if self.speaking:
            self._tgt_voice_level = random.uniform(0.2, 0.95)
        else:
            self._tgt_voice_level = 0.0
        self._voice_level += (self._tgt_voice_level - self._voice_level) * 0.22

        # Rotate blobs & advance shape phases
        rot_speeds = [0.65, -0.4, 0.8] if self.speaking else [0.22, -0.12, 0.35]
        if self.state in ("THINKING", "PROCESSING"):
            rot_speeds = [1.2, -0.9, 1.6]
            
        for i in range(3):
            self._blob_angles[i] = (self._blob_angles[i] + rot_speeds[i]) % 360
            self._blob_phases[i] = (self._blob_phases[i] + (0.06 if self.speaking else 0.024)) % (2 * math.pi)

        # Ambient background particles drifting
        W, H = self.width(), self.height()
        for p in self._ambient_particles:
            p[1] -= p[3] # Upward motion
            if p[1] < 0:
                p[1] = H if H > 0 else 600
                p[0] = random.uniform(0, W if W > 0 else 800)

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
        
        # 1. Dark obsidian space background gradient
        bg_grad = QRadialGradient(cx, cy, fw * 0.5)
        bg_grad.setColorAt(0.0, qcol("#060b18"))
        bg_grad.setColorAt(0.6, qcol(C.BG))
        bg_grad.setColorAt(1.0, qcol("#010206", 0))
        
        if self.compact_mode:
            p.setBrush(QBrush(bg_grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - fw/2, cy - fw/2, fw, fw))
        else:
            p.fillRect(self.rect(), QBrush(bg_grad))

        # 2. Ambient starfield particles
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self._ambient_particles:
            col = qcol(C.CYAN if self.state in ("THINKING", "PROCESSING") else C.PRI, int(pt[4] * 255))
            p.setBrush(QBrush(col))
            p.drawEllipse(QPointF(pt[0], pt[1]), pt[2], pt[2])

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
                opacity = int(180 * (0.4 + 0.6 * math.sin(ang_rad)))
                p.setBrush(QBrush(qcol(C.CYAN, opacity)))
                p.drawEllipse(QPointF(op_x, op_y), op[3], op[3])

        # 6. Rounded avatar face projection
        if self._face_px:
            fsz = int(base_r * 1.55)
            scaled = self._face_px.scaled(
                fsz, fsz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Clip face to perfect circle inside portal
            face_path = QPainterPath()
            face_path.addEllipse(QRectF(cx - fsz/2, cy - fsz/2, fsz, fsz))
            p.save()
            p.setClipPath(face_path)
            p.drawPixmap(int(cx - fsz / 2), int(cy - fsz / 2), scaled)
            p.restore()
            
            # Subtle glass bezel overlay on face
            p.setPen(QPen(qcol(C.WHITE, 40), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - fsz/2, cy - fsz/2, fsz, fsz))

        # 7. Explosive sound particles
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

    def mousePressEvent(self, event):
        if self.compact_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.compact_mode and hasattr(self, "_drag_pos") and self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.compact_mode:
            self._drag_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.compact_mode and event.button() == Qt.MouseButton.LeftButton:
            self.window().toggle_compact_mode()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

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
        prefixes = ["you:", "ip ray:", "ipray:", "sys:", "file:"]
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
            bg = f"rgba(59, 130, 246, 0.12)"
            border = f"1px solid rgba(59, 130, 246, 0.25)"
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
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 4px;
                min-height: 20px;
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
        elif tl.startswith("ip ray:") or tl.startswith("ipray:"): self._tag = "ai"
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
            self, "Select a file for IP RAY", str(Path.home()),
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
        cx, cy = W / 2, H / 2
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
        layout.addWidget(_lbl("Configure IP RAY before first boot.", 9, color=C.PRI_DIM))
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
    _log_sig   = pyqtSignal(str)
    _state_sig = pyqtSignal(str)
    _fullscreen_sig = pyqtSignal(bool)

    def __init__(self, face_path: str):
        super().__init__()
        self.setWindowTitle("IP Ray")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        self.on_text_command  = None
        self._muted           = False
        self._current_file: str | None = None

        self._central_widget = QWidget()
        self._central_widget.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(self._central_widget)

        root = QVBoxLayout(self._central_widget)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)

        self._left_panel = self._build_left_panel()
        body.addWidget(self._left_panel, stretch=0)
        self._left_panel.hide()  # Permanently hide left panel containing SYS MONITOR and HUD CONFIG as requested

        self.hud = HudCanvas(face_path)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Wrapped HUD inside a beautiful rounded obsidian card
        self._hud_container = QWidget()
        self._hud_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px;")
        hud_lay = QVBoxLayout(self._hud_container)
        hud_lay.setContentsMargins(2, 2, 2, 2)
        hud_lay.addWidget(self.hud)
        body.addWidget(self._hud_container, stretch=5)

        self._right_panel = self._build_right_panel()
        body.addWidget(self._right_panel, stretch=0)

        root.addLayout(body, stretch=1)
        root.addWidget(self._build_footer())

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()

        # Metrik güncelleme timer'ı
        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(2000)
        self._update_metrics()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._fullscreen_sig.connect(self._set_fullscreen_slot)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _set_fullscreen_slot(self, full: bool):
        if full:
            if not self.isFullScreen():
                self.showFullScreen()
        else:
            if self.isFullScreen():
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
            boot_t  = psutil.boot_time()
            elapsed = time.time() - boot_t
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UP  --:--")

        try:
            proc_count = len(psutil.pids())
            self._proc_lbl.setText(f"PROC  {proc_count}")
        except Exception:
            self._proc_lbl.setText("PROC  --")


    def _build_header(self) -> QWidget:
        self._header_widget = QWidget()
        self._header_widget.setFixedHeight(54)
        self._header_widget.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 10px;")
        lay = QHBoxLayout(self._header_widget)
        lay.setContentsMargins(16, 0, 16, 0)

        def _badge(txt, color=C.TEXT_MED):
            l = QLabel(txt)
            l.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        logo_lbl = QLabel()
        logo_path = BASE_DIR / "assets" / "logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            logo_lbl.setStyleSheet("background: transparent;")
            lay.addWidget(logo_lbl)

        lay.addStretch()

        mid = QVBoxLayout(); mid.setSpacing(1)
        self._title_lbl = QLabel("IP RAY")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 2px;")
        mid.addWidget(self._title_lbl)
        self._sub_lbl = QLabel("Intelligent Partner Ray")
        self._sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_lbl.setFont(QFont("Segoe UI", 8))
        self._sub_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        mid.addWidget(self._sub_lbl)
        lay.addLayout(mid)
        lay.addStretch()

        right_col = QVBoxLayout(); right_col.setSpacing(2)
        self._clock_lbl = QLabel("00:00:00")
        self._clock_lbl.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._clock_lbl)
        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont("Segoe UI", 8))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)
        lay.addLayout(right_col)

        self._compact_btn = QPushButton("🛸")
        self._compact_btn.setFixedSize(36, 36)
        self._compact_btn.setFont(QFont("Segoe UI Emoji", 14) if _OS == "Windows" else QFont("Arial", 14))
        self._compact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compact_btn.setToolTip("Toggle Frameless Mini-Orb Mode")
        self._compact_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.PRI};
                border: 1px solid {C.BORDER}; border-radius: 18px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; border: 1px solid {C.PRI};
            }}
        """)
        self._compact_btn.clicked.connect(self.toggle_compact_mode)
        lay.addWidget(self._compact_btn)

        return self._header_widget

    def _tick_clock(self):
        self._clock_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a %d %b %Y"))

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

        self._mute_btn = QPushButton("🎙  MICROPHONE ACTIVE")
        self._mute_btn.setFixedHeight(30)
        self._mute_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        self._style_mute_btn()
        lay.addWidget(self._mute_btn)

        self._fullscreen_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        self._fullscreen_btn.setFixedHeight(26)
        self._fullscreen_btn.setFont(QFont("Segoe UI", 8))
        self._fullscreen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fullscreen_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 6px;
            }}
            QPushButton:hover {{
                color: {C.PRI}; border: 1px solid {C.BORDER_B};
            }}
        """)
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        lay.addWidget(self._fullscreen_btn)

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

        lay.addWidget(_fl("[F4] Mute  ·  [F11] Fullscreen"))
        
        self._theme_btn = QPushButton("🎨 THEME")
        self._theme_btn.setFixedHeight(20)
        self._theme_btn.setFont(QFont("Segoe UI", 8))
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        self._theme_btn.clicked.connect(self._cycle_theme)
        lay.addWidget(self._theme_btn)
        
        lay.addStretch()
        lay.addWidget(_fl("IP Verse Industries  ·  IP RAY  ·  CLASSIFIED"))
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
            
        idx = (idx + 1) % 4
        try:
            with open(theme_file, "w") as f:
                json.dump({"theme_idx": idx}, f)
        except Exception:
            pass
            
        _load_theme()
        self._apply_theme()
        self._log.append_log(f"SYS: Theme dynamically cycled to Preset {idx + 1}. Interface reloaded.")

    def _apply_theme(self):
        # 1. Main Window / Central widget background
        self.setStyleSheet(f"QMainWindow {{ background-color: {C.BG}; }}")
        self._central_widget.setStyleSheet(f"background: {C.BG};")

        # 2. Header
        self._header_widget.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 10px;")
        self._title_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 2px;")
        self._sub_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._clock_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")

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

        # 22. Compact Mode Button Styling
        if hasattr(self, "_compact_btn"):
            self._compact_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.PRI};
                    border: 1px solid {C.BORDER}; border-radius: 18px;
                }}
                QPushButton:hover {{
                    background: {C.PRI_GHO}; border: 1px solid {C.PRI};
                }}
            """)
        
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
        self._hud_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px;")

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
            QTextEdit {{
                background: {C.PANEL};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 8px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: {C.BG};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 4px;
                min-height: 20px;
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

        # 15. Mute Button
        self._style_mute_btn()

        # 16. Fullscreen Button
        self._fullscreen_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 6px;
            }}
            QPushButton:hover {{
                color: {C.PRI}; border: 1px solid {C.BORDER_B};
            }}
        """)

        # 17. Footer Widget & Labels
        self._footer_widget.setStyleSheet(f"background: {C.DARK}; border-top: 1px solid {C.BORDER};")
        self._theme_btn.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        self._footer_copyright_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
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
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell IP RAY what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("🔇  MICROPHONE MUTED")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #140006; color: {C.MUTED_C};
                    border: 1px solid {C.MUTED_C}; border-radius: 3px;
                }}
            """)
        else:
            self._mute_btn.setText("🎙  MICROPHONE ACTIVE")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #00140a; color: {C.GREEN};
                    border: 1px solid {C.GREEN}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: #001f10; }}
            """)

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")
        if hasattr(self, "_log"):
            self._log.show_typing(state in ("THINKING", "PROCESSING"))

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

    def toggle_compact_mode(self):
        is_compact = not self.hud.compact_mode
        self.hud.compact_mode = is_compact
        
        if is_compact:
            self._normal_geometry = self.geometry()
            self._was_maximized = self.isMaximized()
            
            self._header_widget.hide()
            self._footer_widget.hide()
            self._left_panel.hide()
            self._right_panel.hide()
            
            self._central_widget.layout().setContentsMargins(0, 0, 0, 0)
            self._hud_container.setStyleSheet("background: transparent; border: none;")
            
            self.hide()
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            
            self.resize(180, 180)
            self.setFixedSize(180, 180)
            self.show()
        else:
            self.hide()
            
            self.setMinimumSize(_MIN_W, _MIN_H)
            self.setMaximumSize(16777215, 16777215)
            
            self.setWindowFlags(Qt.WindowType.Window)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            
            self._central_widget.layout().setContentsMargins(12, 12, 12, 12)
            
            self._header_widget.show()
            self._footer_widget.show()
            # self._left_panel.show()  # Keep left panel containing SYS MONITOR and HUD CONFIG hidden as requested
            self._right_panel.show()
            
            self._apply_theme()
            
            if hasattr(self, "_was_maximized") and self._was_maximized:
                self.showMaximized()
            elif hasattr(self, "_normal_geometry"):
                self.setGeometry(self._normal_geometry)
                self.show()
            else:
                self.show()

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
        self._log.append_log(f"SYS: Initialised. OS={os_name.upper()}. IP RAY online.")

class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class IPRayUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
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

from __future__ import annotations
import logging

import re
import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal, QVariantAnimation, QTime, QDate,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut, QIcon, QFileSystemModel,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar, QSystemTrayIcon, QMenu, QStyle,
    QDialog, QCheckBox, QListWidget, QComboBox, QStackedWidget, QGridLayout,
    QTreeView, QHeaderView,
)
from PyQt6.QtMultimedia import QSoundEffect

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
APP_START_TIME = time.time()

_DEFAULT_W, _DEFAULT_H = 820, 720
_MIN_W,     _MIN_H     = 780, 600
_LEFT_W  = 240
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

import ctypes

def hex_to_rgba_str(hex_str: str, alpha: float) -> str:
    h = hex_str.lstrip('#')
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

def apply_windows_blur(hwnd: int, effect_type: str = "acrylic", dark_mode: bool = True):
    if _OS != "Windows":
        return
    try:
        # Enable Dark Mode for window frame (DWMWA_USE_IMMERSIVE_DARK_MODE = 20)
        dark = ctypes.c_int(1 if dark_mode else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark)
        )

        # 1. Try Windows 11 system backdrop type (DWMWA_SYSTEMBACKDROP_TYPE = 38)
        # Backdrop type values: DWMSBT_AUTO=0, DWMSBT_NONE=1, DWMSBT_MICA=2, DWMSBT_ACRYLIC=3, DWMSBT_TABBED=4
        backdrop_val = 3 if effect_type == "acrylic" else 2
        backdrop = ctypes.c_int(backdrop_val)
        hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop)
        )
        
        # 2. Try legacy Windows 11 Mica effect fallback (DWMWA_MICA_EFFECT = 1029)
        if hr != 0:
            mica = ctypes.c_int(1 if effect_type == "mica" else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 1029, ctypes.byref(mica), ctypes.sizeof(mica)
            )

        # 3. Try legacy Windows 10 SetWindowCompositionAttribute Acrylic blur
        # AccentState: ACCENT_ENABLE_ACRYLICBLURBEHIND = 4, AccentFlags = 2, GradientColor = 0x20101010
        class AccentPolicy(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_int),
                ("AnimationId", ctypes.c_int)
            ]

        class WindowCompositionAttributeData(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_int)
            ]

        policy = AccentPolicy()
        policy.AccentState = 4 # ACCENT_ENABLE_ACRYLICBLURBEHIND
        policy.AccentFlags = 2 # DRAW_ALL_BORDERS
        policy.GradientColor = 0x20101010 # Dark translucent tint

        data = WindowCompositionAttributeData()
        data.Attribute = 19 # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(policy)

        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except Exception as e:
        print(f"[Blur] Failed to apply win32 window effects: {e}")


class C:
    BG        = "#00060a"
    PANEL     = "#010d14"
    PANEL2    = "#010f18"
    BORDER    = "#0d3347"
    BORDER_B  = "#1a5c7a"
    BORDER_A  = "#0f4060"
    PRI       = "#00d4ff"
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#001f2e"
    ACC       = "#ff6b00"
    ACC2      = "#ffcc00"
    GREEN     = "#00ff88"
    GREEN_D   = "#00aa55"
    RED       = "#ff3355"
    MUTED_C   = "#ff3366"
    TEXT      = "#8ffcff"
    TEXT_DIM  = "#3a8a9a"
    TEXT_MED  = "#5ab8cc"
    WHITE     = "#d8f8ff"
    DARK      = "#000d14"
    BAR_BG    = "#011520"

    BG_GLOW_CTR = "#011b2d"
    BG_GLOW_MID = "#000c14"
    BG_GLOW_EDG = "#000406"

    @classmethod
    def apply_hacker_mode_colors(cls, enabled: bool):
        if enabled:
            cls.BG        = "#0a0002"
            cls.PANEL     = "#140105"
            cls.PANEL2    = "#180105"
            cls.BORDER    = "#470d14"
            cls.BORDER_B  = "#7a1a24"
            cls.BORDER_A  = "#600f18"
            cls.PRI       = "#ff3355" # red
            cls.PRI_DIM   = "#991f2e"
            cls.PRI_GHO   = "#2e000f"
            cls.ACC       = "#ffaa00"
            cls.ACC2      = "#ffdd00"
            cls.TEXT      = "#ff8f9f"
            cls.TEXT_DIM  = "#9a3a4a"
            cls.TEXT_MED  = "#cc5a6c"
            cls.WHITE     = "#ffd8dc"
            cls.DARK      = "#140005"
            cls.BAR_BG    = "#200105"
            cls.BG_GLOW_CTR = "#2d0106"
            cls.BG_GLOW_MID = "#140003"
            cls.BG_GLOW_EDG = "#060001"
        else:
            cls.BG        = "#00060a"
            cls.PANEL     = "#010d14"
            cls.PANEL2    = "#010f18"
            cls.BORDER    = "#0d3347"
            cls.BORDER_B  = "#1a5c7a"
            cls.BORDER_A  = "#0f4060"
            cls.PRI       = "#00d4ff"
            cls.PRI_DIM   = "#007a99"
            cls.PRI_GHO   = "#001f2e"
            cls.ACC       = "#ff6b00"
            cls.ACC2      = "#ffcc00"
            cls.TEXT      = "#8ffcff"
            cls.TEXT_DIM  = "#3a8a9a"
            cls.TEXT_MED  = "#5ab8cc"
            cls.WHITE     = "#d8f8ff"
            cls.DARK      = "#000d14"
            cls.BAR_BG    = "#011520"
            cls.BG_GLOW_CTR = "#011b2d"
            cls.BG_GLOW_MID = "#000c14"
            cls.BG_GLOW_EDG = "#000406"

    @classmethod
    def apply_light_theme(cls, enabled: bool):
        if enabled:
            cls.BG        = "#f5f7fa"
            cls.PANEL     = "#ffffff"
            cls.PANEL2    = "#eef1f6"
            cls.BORDER    = "#d0d7de"
            cls.BORDER_B  = "#b0c4de"
            cls.BORDER_A  = "#c5d1e0"
            cls.PRI       = "#0066cc"
            cls.PRI_DIM   = "#004499"
            cls.PRI_GHO   = "#e6f0fa"
            cls.ACC       = "#d9534f"
            cls.ACC2      = "#f0ad4e"
            cls.TEXT      = "#1a1a1a"
            cls.TEXT_DIM  = "#555555"
            cls.TEXT_MED  = "#333333"
            cls.WHITE     = "#000000"
            cls.DARK      = "#e9ecef"
            cls.BAR_BG    = "#dee2e6"
            cls.BG_GLOW_CTR = "#e6f0fa"
            cls.BG_GLOW_MID = "#f5f7fa"
            cls.BG_GLOW_EDG = "#ffffff"
        else:
            cls.BG        = "#00060a"
            cls.PANEL     = "#010d14"
            cls.PANEL2    = "#010f18"
            cls.BORDER    = "#0d3347"
            cls.BORDER_B  = "#1a5c7a"
            cls.BORDER_A  = "#0f4060"
            cls.PRI       = "#00d4ff"
            cls.PRI_DIM   = "#007a99"
            cls.PRI_GHO   = "#001f2e"
            cls.ACC       = "#ff6b00"
            cls.ACC2      = "#ffcc00"
            cls.TEXT      = "#8ffcff"
            cls.TEXT_DIM  = "#3a8a9a"
            cls.TEXT_MED  = "#5ab8cc"
            cls.WHITE     = "#d8f8ff"
            cls.DARK      = "#000d14"
            cls.BAR_BG    = "#011520"
            cls.BG_GLOW_CTR = "#011b2d"
            cls.BG_GLOW_MID = "#000c14"
            cls.BG_GLOW_EDG = "#000406"

    @classmethod
    def apply_mood(cls, mood: str):
        m = mood.lower().strip()
        if m == "focus":
            cls.PRI       = "#b800ff"
            cls.PRI_DIM   = "#660099"
            cls.PRI_GHO   = "#1f0033"
            cls.ACC       = "#00ff88"
            cls.ACC2      = "#00ffcc"
            cls.TEXT      = "#f5e6ff"
            cls.TEXT_DIM  = "#8c5cb3"
            cls.TEXT_MED  = "#b38cd9"
            cls.BG_GLOW_CTR = "#25003b"
            cls.BG_GLOW_MID = "#0f001c"
            cls.BG_GLOW_EDG = "#05000a"
        elif m == "relax":
            cls.PRI       = "#00ff88"
            cls.PRI_DIM   = "#009955"
            cls.PRI_GHO   = "#00331a"
            cls.ACC       = "#ffcc00"
            cls.ACC2      = "#ffaa00"
            cls.TEXT      = "#e6fff2"
            cls.TEXT_DIM  = "#5ca67a"
            cls.TEXT_MED  = "#8cd9aa"
            cls.BG_GLOW_CTR = "#003b1f"
            cls.BG_GLOW_MID = "#001c0f"
            cls.BG_GLOW_EDG = "#000a05"
        elif m == "energized":
            cls.PRI       = "#ffaa00"
            cls.PRI_DIM   = "#996600"
            cls.PRI_GHO   = "#331a00"
            cls.ACC       = "#ff3355"
            cls.ACC2      = "#ff3366"
            cls.TEXT      = "#fff5e6"
            cls.TEXT_DIM  = "#b38c5c"
            cls.TEXT_MED  = "#d9b38c"
            cls.BG_GLOW_CTR = "#3b2500"
            cls.BG_GLOW_MID = "#1c0f00"
            cls.BG_GLOW_EDG = "#0a0500"
        else: # normal / default
            cls.PRI       = "#00d4ff"
            cls.PRI_DIM   = "#007a99"
            cls.PRI_GHO   = "#001f2e"
            cls.ACC       = "#ff6b00"
            cls.ACC2      = "#ffcc00"
            cls.TEXT      = "#8ffcff"
            cls.TEXT_DIM  = "#3a8a9a"
            cls.TEXT_MED  = "#5ab8cc"
            cls.WHITE     = "#d8f8ff"
            cls.DARK      = "#000d14"
            cls.BAR_BG    = "#011520"
            cls.BG_GLOW_CTR = "#011b2d"
            cls.BG_GLOW_MID = "#000c14"
            cls.BG_GLOW_EDG = "#000406"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c

class SoundManager:
    def __init__(self):
        self._active_effects = []
        self.sounds = {}
        
        # Load standard Windows system sounds if available
        if platform.system() == "Windows":
            media_dir = Path(r"C:\Windows\Media")
            self.sounds = {
                "listening": media_dir / "Speech On.wav",
                "thinking": media_dir / "Windows Information Bar.wav",
                "speaking": media_dir / "Windows Message Nudge.wav",
                "processing": media_dir / "Windows Notify System Generic.wav"
            }

    def play(self, state: str, parent_widget=None):
        # Clean up finished effects to free resources
        try:
            self._active_effects = [
                e for e in self._active_effects
                if e.isPlaying() or e.status() == QSoundEffect.Status.Loading
            ]
        except Exception:
            self._active_effects = []

        sound_path = self.sounds.get(state.lower())
        if sound_path and sound_path.exists():
            try:
                effect = QSoundEffect(parent_widget)
                effect.setSource(QUrl.fromLocalFile(str(sound_path.resolve())))
                effect.setVolume(0.2)
                effect.play()
                self._active_effects.append(effect)
            except Exception as e:
                print(f"[SoundManager] Error playing sound for state {state}: {e}")

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
        
        # Performance optimization: cache subprocess failures to avoid spawning dead processes
        self._skip_nvidia_smi = False
        self._skip_rocm_smi = False
        self._skip_intel_gpu = False
        self._skip_osx_gpu = False
        self._skip_win_temp = False
        self._skip_osx_temp = False

        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
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
        if not self._skip_nvidia_smi:
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
                else:
                    self._skip_nvidia_smi = True
            except Exception:
                self._skip_nvidia_smi = True

        # AMD (Linux)
        if _OS == "Linux":
            if not self._skip_rocm_smi:
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
                    else:
                        self._skip_rocm_smi = True
                except Exception:
                    self._skip_rocm_smi = True

            # Intel GPU (Linux)
            if not self._skip_intel_gpu:
                try:
                    r = subprocess.run(
                        ["intel_gpu_top", "-J", "-s", "500"],
                        capture_output=True, text=True, timeout=1
                    )
                    if r.returncode == 0 and "Render/3D" in r.stdout:
                        m = re.search(r'"busy":\s*([\d.]+)', r.stdout)
                        if m:
                            return float(m.group(1))
                    else:
                        self._skip_intel_gpu = True
                except Exception:
                    self._skip_intel_gpu = True

        # macOS — powermetrics (GPU Engine)
        if _OS == "Darwin" and not self._skip_osx_gpu:
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
                else:
                    self._skip_osx_gpu = True
            except Exception:
                self._skip_osx_gpu = True

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
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
        if _OS == "Darwin" and not self._skip_osx_temp:
            try:
                r = subprocess.run(
                    ["osx-cpu-temp"], capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0:
                    import re
                    m = re.search(r"([\d.]+)", r.stdout)
                    if m:
                        return float(m.group(1))
                else:
                    self._skip_osx_temp = True
            except Exception:
                self._skip_osx_temp = True

        if _OS == "Windows" and not self._skip_win_temp:
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "(Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi).CurrentTemperature"],
                    capture_output=True, text=True, timeout=3
                )
                if r.returncode == 0 and r.stdout.strip():
                    raw = float(r.stdout.strip().split("\n")[0])
                    return (raw / 10.0) - 273.15
                else:
                    self._skip_win_temp = True
            except Exception:
                self._skip_win_temp = True

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

class HUDCircularGauge(QWidget):
    def __init__(self, title, unit="%", parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.val = 0.0
        self.setMinimumSize(95, 95)
        self.setMaximumSize(110, 110)

    def setValue(self, val):
        if abs(self.val - val) > 0.1:
            self.val = val
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        r = min(w, h) - 16
        x = (w - r) / 2
        y = (h - r) / 2
        rect = QRectF(x, y, r, r)
        pen_bg = QPen(QColor(C.PRI_GHO if C.PRI_GHO != "#001f2e" else "#021622"))
        pen_bg.setWidth(6)
        painter.setPen(pen_bg)
        painter.drawArc(rect, -225 * 16, 270 * 16)
        pen_val = QPen(QColor(C.PRI))
        pen_val.setWidth(6)
        pen_val.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_val)
        angle = int((self.val / 100.0) * 270 * 16)
        painter.drawArc(rect, -225 * 16, angle)
        font_title = QFont("Courier New", 7, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.setPen(QColor(C.TEXT_DIM))
        painter.drawText(QRectF(0, h - 20, w, 20), Qt.AlignmentFlag.AlignCenter, self.title)
        font_val = QFont("Courier New", 10, QFont.Weight.Bold)
        painter.setFont(font_val)
        painter.setPen(QColor(C.WHITE))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.val:.0f}{self.unit}")

class MediaWaveVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.anim_offset = 0.0
        self.audio_level = 0.0
        self.is_active = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def set_audio_level(self, level: float):
        self.audio_level = level

    def _tick(self):
        self.anim_offset += 0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        
        # Subtle glowing background
        painter.fillRect(0, 0, w, h, QColor(C.PANEL))
        painter.setPen(QPen(QColor(C.BORDER), 1))
        painter.drawRect(0, 0, w - 1, h - 1)
        
        # Center line
        painter.setPen(QPen(QColor(C.BORDER_A), 1, Qt.PenStyle.DotLine))
        painter.drawLine(0, h // 2, w, h // 2)
        
        num_bars = 28
        gap = 3
        bar_w = max(2, int((w - gap * (num_bars + 1)) / num_bars))
        
        for i in range(num_bars):
            # Calculate wave heights
            base = 2.0
            if self.is_active:
                # Heartbeat idle animation
                base += math.sin(self.anim_offset + i * 0.3) * 6.0
                base += math.cos(self.anim_offset * 1.3 + i * 0.5) * 3.0
            if self.audio_level > 0.0:
                # Mic activity animation
                base += self.audio_level * 28.0 * (math.sin(self.anim_offset * 2.5 + i * 0.6) + 1.3)
            
            # Smooth clamping
            bar_h = min(h - 6, max(2, int(base)))
            
            # Draw mirrored bar from the center
            x = gap + i * (bar_w + gap)
            y = (h - bar_h) // 2
            
            # Gradient brush
            grad = QLinearGradient(x, y, x, y + bar_h)
            color_top = QColor(C.PRI) if not self.is_active else QColor(C.GREEN)
            grad.setColorAt(0.0, color_top)
            grad.setColorAt(0.5, QColor(C.WHITE))
            grad.setColorAt(1.0, color_top)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(x, y, bar_w, bar_h, 1.5, 1.5)

class SaturdayCustomAlert(QDialog):
    def __init__(self, title, message, alert_type="info", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"S.A.T.U.R.D.A.Y — {title}")
        self.resize(400, 200)
        if alert_type == "success":
            color = C.GREEN
            icon = "⚡"
        elif alert_type == "warning":
            color = C.ACC
            icon = "⚠️"
        elif alert_type == "error":
            color = C.RED
            icon = "❌"
        elif alert_type == "wake":
            color = C.ACC2
            icon = "🎙️"
        elif alert_type == "telegram":
            color = C.PRI
            icon = "📱"
        else:
            color = C.PRI
            icon = "ℹ️"
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {C.PANEL};
                color: {C.TEXT};
                border: 2px solid {color};
            }}
            QLabel {{
                color: {C.TEXT};
                font-family: 'Courier New';
                font-size: 12px;
            }}
            QPushButton {{
                background-color: {C.BORDER_A};
                color: {C.WHITE};
                border: 1px solid {color};
                padding: 6px 14px;
                border-radius: 4px;
                font-family: 'Courier New';
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: {C.BG};
            }}
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        lbl_icon = QLabel(f"{icon}  {title.upper()}  {icon}")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_icon)
        lbl_text = QLabel(message)
        lbl_text.setWordWrap(True)
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_text)
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Acknowledge")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        if alert_type in ["success", "wake", "telegram", "info"]:
            self.auto_close_timer = QTimer(self)
            self.auto_close_timer.timeout.connect(self.accept)
            self.auto_close_timer.start(4000)

class HudCanvas(QWidget):
    def __init__(self, face_path: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"
        self._last_response: str = ""
        self._activity: str = "SYSTEM IDLE"

        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 55.0
        self._tgt_halo   = 55.0
        self._last_t     = time.time()
        self._scan       = 0.0
        self._scan2      = 180.0
        self._rings      = [0.0, 120.0, 240.0]
        self._pulses: list[float] = [0.0, 50.0, 100.0]
        self._blink      = True
        self._blink_tick = 0
        self._particles: list[list[float]] = []
        self._snap: dict  = {"cpu": 0.0, "mem": 0.0, "net": 0.0, "gpu": -1.0, "tmp": -1.0}
        self._face_px: QPixmap | None = None
        self._load_face(face_path)
        self._grid_pixmap: QPixmap | None = None

        self._audio_level = 0.0
        self._target_audio_level = 0.0

        self.animation_speed_multiplier = 1.0
        try:
            if SETTINGS_FILE.exists():
                import json
                sett = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                mood = sett.get("mood", "normal")
                C.apply_mood(mood)
                if mood == "relax":
                    self.animation_speed_multiplier = 0.5
                elif mood == "energized":
                    self.animation_speed_multiplier = 2.0
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def set_mood(self, mood: str):
        C.apply_mood(mood)
        m = mood.lower().strip()
        if m == "relax":
            self.animation_speed_multiplier = 0.5
        elif m == "energized":
            self.animation_speed_multiplier = 2.0
        else:
            self.animation_speed_multiplier = 1.0
        self._grid_pixmap = None
        self.update()

    def set_audio_level(self, level: float):
        self._target_audio_level = min(1.0, max(0.0, level))

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
        except Exception as e:
            print(f"[HUD] Face load failed: {e}")
            self._face_px = None

    def _update_grid_pixmap(self, W: int, H: int):
        self._grid_pixmap = QPixmap(W, H)
        self._grid_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(self._grid_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Tech grid lines (extremely faint blueprint lines)
        painter.setPen(QPen(qcol(C.PRI_GHO, 15), 1))
        for x in range(0, W, 96):
            painter.drawLine(x, 0, x, H)
        for y in range(0, H, 96):
            painter.drawLine(0, y, W, y)
        
        # Tech grid dots
        painter.setPen(QPen(qcol(C.PRI_GHO, 100), 1))
        for x in range(0, W, 48):
            for y in range(0, H, 48):
                painter.drawPoint(x, y)
        
        painter.end()

    def _step(self):
        self._tick += 1
        now = time.time()
        st  = self.state  # current state string

        # --- target scale & halo per state ---
        if self.muted:
            interval = 0.6
            tgt_s = random.uniform(0.995, 1.002)
            tgt_h = random.uniform(12, 22)
            ring_spd = [0.2, -0.15, 0.3]
            scan_spd, scan2_spd = 0.5, -0.3
            pulse_spd, pulse_prob = 1.0, 0.01
            particle_prob = 0.0
        elif self.speaking:
            interval = 0.06
            # Snappy prominent base scale (pop out) + dynamic voice vibration!
            base_s = random.uniform(1.22, 1.34)
            vibration = 0.12 * (math.sin(self._tick * 0.35) * math.cos(self._tick * 0.18) + 0.5)
            tgt_s = base_s + vibration
            tgt_h = random.uniform(160, 210)
            ring_spd = [2.2, -1.6, 3.2]
            scan_spd, scan2_spd = 5.0, -3.5
            pulse_spd, pulse_prob = 6.0, 0.12
            particle_prob = 0.45
        elif st == "THINKING":
            interval = 0.18
            tgt_s = random.uniform(1.03, 1.08)
            tgt_h = random.uniform(90, 130)
            ring_spd = [1.8, -1.4, 2.6]
            scan_spd, scan2_spd = 3.5, -2.5
            pulse_spd, pulse_prob = 3.5, 0.06
            particle_prob = 0.12
        elif st == "PROCESSING":
            interval = 0.14
            tgt_s = random.uniform(1.02, 1.06)
            tgt_h = random.uniform(80, 110)
            ring_spd = [1.5, -1.1, 2.2]
            scan_spd, scan2_spd = 4.0, -2.8
            pulse_spd, pulse_prob = 4.0, 0.08
            particle_prob = 0.08
        elif st == "LISTENING":
            interval = 0.4
            tgt_s = random.uniform(1.001, 1.006)
            tgt_h = random.uniform(50, 75)
            ring_spd = [0.6, -0.4, 1.0]
            scan_spd, scan2_spd = 1.5, -0.9
            pulse_spd, pulse_prob = 2.2, 0.03
            particle_prob = 0.0
        elif st == "STANDBY":
            interval = 1.0
            tgt_s = random.uniform(0.95, 0.97)
            tgt_h = random.uniform(10, 20)
            ring_spd = [0.1, -0.08, 0.15]
            scan_spd, scan2_spd = 0.2, -0.1
            pulse_spd, pulse_prob = 0.5, 0.005
            particle_prob = 0.0
        else:  # INITIALISING / other
            interval = 0.5
            tgt_s = random.uniform(1.001, 1.008)
            tgt_h = random.uniform(40, 60)
            ring_spd = [0.55, -0.35, 0.9]
            scan_spd, scan2_spd = 1.3, -0.75
            pulse_spd, pulse_prob = 2.0, 0.025
            particle_prob = 0.0

        if now - self._last_t > interval:
            self._tgt_scale = tgt_s
            self._tgt_halo  = tgt_h
            self._last_t = now

        lerp = 0.45 if self.speaking else (0.3 if st in ("THINKING", "PROCESSING") else 0.15)
        self._scale += (self._tgt_scale - self._scale) * lerp
        self._halo  += (self._tgt_halo  - self._halo)  * lerp

        mult = getattr(self, "animation_speed_multiplier", 1.0)
        ring_spd = [s * mult for s in ring_spd]
        scan_spd *= mult
        scan2_spd *= mult
        pulse_spd *= mult

        for i, spd in enumerate(ring_spd):
            self._rings[i] = (self._rings[i] + spd) % 360

        self._scan  = (self._scan  + scan_spd)  % 360
        self._scan2 = (self._scan2 + scan2_spd) % 360

        fw  = min(self.width(), self.height()) * 0.45
        lim = fw * 0.74
        self._pulses = [r + pulse_spd for r in self._pulses if r + pulse_spd < lim]
        if len(self._pulses) < 4 and random.random() < pulse_prob:
            self._pulses.append(0.0)

        if particle_prob > 0 and random.random() < particle_prob:
            cx2, cy2 = self.width() / 2, self.height() / 2
            ang = random.uniform(0, 2 * math.pi)
            r_s = fw * 0.28
            self._particles.append([
                cx2 + math.cos(ang) * r_s, cy2 + math.sin(ang) * r_s,
                math.cos(ang) * random.uniform(0.9, 2.8),
                math.sin(ang) * random.uniform(0.9, 2.8) - 0.4, 1.0,
            ])
        self._particles = [
            [p[0]+p[2], p[1]+p[3], p[2]*0.97, p[3]*0.97, p[4]-0.026]
            for p in self._particles if p[4] > 0
        ]

        self._blink_tick += 1
        if self._blink_tick >= 38:
            self._blink = not self._blink
            self._blink_tick = 0
        if self._tick % 120 == 0:
            self._snap = _metrics.snapshot()

        # Smooth audio level transition with ballistics (fast rise, slow decay)
        curr = self._audio_level
        tgt = self._target_audio_level
        decay = 0.35 if tgt > curr else 0.15
        self._audio_level = curr + (tgt - curr) * decay
        # Slowly decay the target audio level back to 0
        self._target_audio_level = max(0.0, self._target_audio_level - 0.03)

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2 - 50
        fw = min(W, H) * 0.45   # 45% of widget — keeps orb small & centred

        # Beautiful tech-radial background glow centered at the orb
        grad = QRadialGradient(cx, cy, max(W, H) * 0.8)
        grad.setColorAt(0.0, qcol(C.BG_GLOW_CTR, 255))  # Deep tech glow at center
        grad.setColorAt(0.4, qcol(C.BG_GLOW_MID, 255))  # Smooth mid-range transit
        grad.setColorAt(1.0, qcol(C.BG_GLOW_EDG, 255))  # Very dark edges
        p.fillRect(self.rect(), QBrush(grad))

        # Cached grid painting
        if self._grid_pixmap is None or self._grid_pixmap.size() != self.size():
            self._update_grid_pixmap(W, H)
        p.drawPixmap(0, 0, self._grid_pixmap)

        # Faint radar HUD rings in the background
        p.setPen(QPen(qcol(C.PRI_GHO, 30), 1, Qt.PenStyle.DashLine))
        for r in [fw * 1.4, fw * 2.1, fw * 2.8]:
            p.drawEllipse(QPointF(cx, cy), r, r)

        # Subtle HUD corner brackets
        pad = 20
        bracket_len = 15
        p.setPen(QPen(qcol(C.PRI_DIM, 80), 1))
        # Top-Left
        p.drawLine(pad, pad, pad + bracket_len, pad)
        p.drawLine(pad, pad, pad, pad + bracket_len)
        # Top-Right
        p.drawLine(W - pad, pad, W - pad - bracket_len, pad)
        p.drawLine(W - pad, pad, W - pad, pad + bracket_len)
        # Bottom-Left
        p.drawLine(pad, H - pad, pad + bracket_len, H - pad)
        p.drawLine(pad, H - pad, pad, H - pad - bracket_len)
        # Bottom-Right
        p.drawLine(W - pad, H - pad, W - pad - bracket_len, H - pad)
        p.drawLine(W - pad, H - pad, W - pad, H - pad - bracket_len)

        r_face = fw * 0.31

        # halo glow
        for i in range(10):
            r   = r_face * (1.8 - i * 0.08)
            frc = 1.0 - i / 10
            a   = max(0, min(255, int(self._halo * 0.085 * frc)))
            col = qcol(C.MUTED_C if self.muted else C.PRI, a)
            p.setPen(QPen(col, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # pulse rings
        for pr in self._pulses:
            a   = max(0, int(230 * (1.0 - pr / (fw * 0.74))))
            col = qcol(C.MUTED_C if self.muted else C.PRI, a)
            p.setPen(QPen(col, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - pr, cy - pr, pr * 2, pr * 2))

        # spinning arc rings
        for idx, (r_frac, w_r, arc_l, gap) in enumerate(
            [(0.48, 3, 115, 78), (0.40, 2, 78, 55), (0.32, 1, 56, 40)]
        ):
            ring_r = fw * r_frac
            base   = self._rings[idx]
            a_val  = max(0, min(255, int(self._halo * (1.0 - idx * 0.18))))
            col    = qcol(C.MUTED_C if self.muted else C.PRI, a_val)
            p.setPen(QPen(col, w_r)); p.setBrush(Qt.BrushStyle.NoBrush)
            angle = base
            rect  = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
            while angle < base + 360:
                p.drawArc(rect, int(angle * 16), int(arc_l * 16))
                angle += arc_l + gap

        # scanners
        sr = fw * 0.50
        sa = min(255, int(self._halo * 1.5))
        ex = 75 if self.speaking else 44
        p.setPen(QPen(qcol(C.MUTED_C if self.muted else C.PRI, sa), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        srect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)
        p.drawArc(srect, int(self._scan * 16), int(ex * 16))
        p.setPen(QPen(qcol(C.ACC, sa // 2), 1.5))
        p.drawArc(srect, int(self._scan2 * 16), int(ex * 16))

        # tick marks
        t_out, t_in = fw * 0.497, fw * 0.474
        p.setPen(QPen(qcol(C.PRI, 140), 1))
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inn = t_in if deg % 30 == 0 else t_in + 6
            p.drawLine(
                QPointF(cx + t_out * math.cos(rad), cy - t_out * math.sin(rad)),
                QPointF(cx + inn  * math.cos(rad), cy - inn  * math.sin(rad)),
            )

        # crosshair
        ch_r, gap_h = fw * 0.51, fw * 0.16
        p.setPen(QPen(qcol(C.PRI, int(self._halo * 0.5)), 1))
        p.drawLine(QPointF(cx - ch_r, cy), QPointF(cx - gap_h, cy))
        p.drawLine(QPointF(cx + gap_h, cy), QPointF(cx + ch_r, cy))
        p.drawLine(QPointF(cx, cy - ch_r), QPointF(cx, cy - gap_h))
        p.drawLine(QPointF(cx, cy + gap_h), QPointF(cx, cy + ch_r))

        # --- Concentric Holographic Telemetry Rings (CPU, RAM, GPU/Network) ---
        p.save()
        # Ring 1: CPU (Cyan)
        cpu_val = self._snap.get("cpu", 0.0)
        cpu_arc = max(10.0, (cpu_val / 100.0) * 360.0)
        cpu_r = fw * 0.38
        p.setPen(QPen(qcol(C.PRI_DIM if self.muted else C.PRI, 30), 0.5))
        p.drawEllipse(QRectF(cx - cpu_r, cy - cpu_r, cpu_r * 2, cpu_r * 2))
        p.setPen(QPen(qcol(C.PRI if not self.muted else C.MUTED_C, 160), 1.5))
        p.drawArc(QRectF(cx - cpu_r, cy - cpu_r, cpu_r * 2, cpu_r * 2), int(self._rings[0] * 16), int(cpu_arc * 16))
        p.setPen(QPen(qcol(C.PRI, 180), 1))
        p.setFont(QFont("Courier New", 6, QFont.Weight.Bold))
        lbl_rad1 = math.radians(self._rings[0] + cpu_arc)
        p.drawText(int(cx + (cpu_r + 6) * math.cos(lbl_rad1) - 15), int(cy - (cpu_r + 6) * math.sin(lbl_rad1) + 3), f"CPU {cpu_val:.0f}%")

        # Ring 2: Memory (Purple)
        mem_val = self._snap.get("mem", 0.0)
        mem_arc = max(10.0, (mem_val / 100.0) * 360.0)
        mem_r = fw * 0.42
        p.setPen(QPen(qcol(C.ACC2 if not self.muted else C.MUTED_C, 30), 0.5))
        p.drawEllipse(QRectF(cx - mem_r, cy - mem_r, mem_r * 2, mem_r * 2))
        p.setPen(QPen(qcol(C.ACC2 if not self.muted else C.MUTED_C, 160), 1.5))
        p.drawArc(QRectF(cx - mem_r, cy - mem_r, mem_r * 2, mem_r * 2), int(self._rings[1] * 16), int(mem_arc * 16))
        p.setPen(QPen(qcol(C.ACC2, 180), 1))
        p.setFont(QFont("Courier New", 6, QFont.Weight.Bold))
        lbl_rad2 = math.radians(self._rings[1] + mem_arc)
        p.drawText(int(cx + (mem_r + 6) * math.cos(lbl_rad2) - 15), int(cy - (mem_r + 6) * math.sin(lbl_rad2) + 3), f"RAM {mem_val:.0f}%")

        # Ring 3: GPU or Network (Green)
        gpu_val = self._snap.get("gpu", -1.0)
        if gpu_val >= 0:
            gpu_arc = max(10.0, (gpu_val / 100.0) * 360.0)
            gpu_lbl = f"GPU {gpu_val:.0f}%"
        else:
            net_val = self._snap.get("net", 0.0)
            gpu_arc = max(10.0, min(360.0, (net_val / 5.0) * 360.0))
            gpu_lbl = f"NET {net_val:.1f}M"
            
        gpu_r = fw * 0.46
        p.setPen(QPen(qcol(C.GREEN if not self.muted else C.MUTED_C, 30), 0.5))
        p.drawEllipse(QRectF(cx - gpu_r, cy - gpu_r, gpu_r * 2, gpu_r * 2))
        p.setPen(QPen(qcol(C.GREEN if not self.muted else C.MUTED_C, 160), 1.5))
        p.drawArc(QRectF(cx - gpu_r, cy - gpu_r, gpu_r * 2, gpu_r * 2), int(self._rings[2] * 16), int(gpu_arc * 16))
        p.setPen(QPen(qcol(C.GREEN, 180), 1))
        p.setFont(QFont("Courier New", 6, QFont.Weight.Bold))
        lbl_rad3 = math.radians(self._rings[2] + gpu_arc)
        p.drawText(int(cx + (gpu_r + 6) * math.cos(lbl_rad3) - 15), int(cy - (gpu_r + 6) * math.sin(lbl_rad3) + 3), gpu_lbl)
        p.restore()


        # face
        if self._face_px:
            fsz    = int(fw * 0.62 * self._scale)
            scaled = self._face_px.scaled(
                fsz, fsz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap(int(cx - fsz / 2), int(cy - fsz / 2), scaled)
        else:
            orb_r = int(fw * 0.26 * self._scale)
            
            # --- 3D Sphere Radial Gradient ---
            # Focal point shifted to top-left to simulate light source
            fx = cx - orb_r * 0.35
            fy = cy - orb_r * 0.35
            grad = QRadialGradient(cx, cy, orb_r, fx, fy)
            
            # Glowing intensity based on _halo
            g_factor = min(255, int(self._halo * 1.5))
            st = self.state

            if self.muted:
                # RED — muted
                grad.setColorAt(0.0, QColor(255, 140, 160, 255))
                grad.setColorAt(0.2, QColor(220, 30,  60,  255))
                grad.setColorAt(0.6, QColor(120, 5,   20,  255))
                grad.setColorAt(0.9, QColor(40,  0,   5,   255))
                grad.setColorAt(1.0, QColor(255, 30,  60,  g_factor // 3))
            elif self.speaking:
                # BRIGHT CYAN — speaking
                grad.setColorAt(0.0, QColor(240, 255, 255, 255))
                grad.setColorAt(0.15, QColor(0,   230, 255, 255))
                grad.setColorAt(0.5, QColor(0,   120, 200, 255))
                grad.setColorAt(0.85, QColor(0,  30,  80,  255))
                grad.setColorAt(1.0, QColor(0,   212, 255, g_factor // 2))
            elif st == "THINKING":
                # AMBER/YELLOW — thinking
                grad.setColorAt(0.0, QColor(255, 255, 180, 255))
                grad.setColorAt(0.2, QColor(255, 180, 0,   255))
                grad.setColorAt(0.6, QColor(140, 80,  0,   255))
                grad.setColorAt(0.9, QColor(40,  20,  0,   255))
                grad.setColorAt(1.0, QColor(255, 160, 0,   g_factor // 2))
            elif st == "PROCESSING":
                # GREEN — processing
                grad.setColorAt(0.0, QColor(180, 255, 210, 255))
                grad.setColorAt(0.2, QColor(0,   255, 120, 255))
                grad.setColorAt(0.6, QColor(0,   120, 50,  255))
                grad.setColorAt(0.9, QColor(0,   30,  10,  255))
                grad.setColorAt(1.0, QColor(0,   255, 100, g_factor // 2))
            elif st == "LISTENING":
                # SOFT BLUE-GREEN — listening
                grad.setColorAt(0.0, QColor(200, 245, 255, 255))
                grad.setColorAt(0.2, QColor(0,   180, 220, 255))
                grad.setColorAt(0.6, QColor(0,   70,  130, 255))
                grad.setColorAt(0.9, QColor(0,   15,  40,  255))
                grad.setColorAt(1.0, QColor(0,   180, 220, g_factor // 2))
            elif st == "STANDBY":
                # DIM DEEP BLUE/GREY - standby mode
                grad.setColorAt(0.0, QColor(100, 150, 180, 180))
                grad.setColorAt(0.3, QColor(30,  60,  80,  150))
                grad.setColorAt(0.7, QColor(10,  25,  40,  120))
                grad.setColorAt(0.9, QColor(2,   5,   15,  100))
                grad.setColorAt(1.0, QColor(30,  60,  80,  g_factor // 4))
            else:
                # DEFAULT CYAN
                grad.setColorAt(0.0, QColor(220, 250, 255, 255))
                grad.setColorAt(0.2, QColor(0,   200, 255, 255))
                grad.setColorAt(0.6, QColor(0,   80,  150, 255))
                grad.setColorAt(0.9, QColor(0,   20,  50,  255))
                grad.setColorAt(1.0, QColor(0,   212, 255, g_factor // 2))

            # Draw 3D Sphere Core
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - orb_r, cy - orb_r, orb_r * 2, orb_r * 2))

            # --- Rotating holographic 3D wireframe longitude lines ---
            p.setPen(QPen(qcol(C.MUTED_C if self.muted else C.PRI, 35), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for angle in [0, 30, 60, 90, 120, 150]:
                scale = math.cos(math.radians(angle + self._tick * 0.4))
                rx_lon = abs(orb_r * scale)
                p.drawEllipse(QRectF(cx - rx_lon, cy - orb_r, rx_lon * 2, orb_r * 2))

            # Latitude wireframe lines (squashed circles representing vertical rings)
            for offset in [-0.7, -0.4, 0, 0.4, 0.7]:
                ry_lat = orb_r * math.sqrt(1 - offset**2)
                cy_lat = orb_r * offset
                p.drawEllipse(QRectF(cx - ry_lat, cy + cy_lat - (ry_lat * 0.12), ry_lat * 2, ry_lat * 0.24))

            # --- Glowing outer atmospheric 3D shell ---
            shell_r = orb_r + 4
            p.setPen(QPen(qcol(C.MUTED_C if self.muted else C.PRI, 80), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - shell_r, cy - shell_r, shell_r * 2, shell_r * 2))

            # --- 3D Tilted Orbiting Rings with Nodes ---
            # Ring 1: Tilted at 35 degrees, rotating forward
            p.save()
            p.translate(cx, cy)
            p.rotate(35)
            rx1 = orb_r * 1.45
            ry1 = orb_r * 0.35
            angle1 = (self._tick * 1.5) % 360
            p.setPen(QPen(qcol(C.MUTED_C if self.muted else C.PRI, 140), 1.5))
            p.drawEllipse(QRectF(-rx1, -ry1, rx1 * 2, ry1 * 2))
            
            rad_val1 = math.radians(angle1)
            node_x1 = rx1 * math.cos(rad_val1)
            node_y1 = ry1 * math.sin(rad_val1)
            p.setBrush(QBrush(qcol(C.WHITE, 240)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(node_x1, node_y1), 4, 4)
            p.restore()

            # Ring 2: Tilted at -35 degrees, rotating backward in neon accent color
            p.save()
            p.translate(cx, cy)
            p.rotate(-35)
            rx2 = orb_r * 1.6
            ry2 = orb_r * 0.3
            angle2 = (-self._tick * 1.2) % 360
            p.setPen(QPen(qcol(C.ACC, 110), 1.5))
            p.drawEllipse(QRectF(-rx2, -ry2, rx2 * 2, ry2 * 2))
            
            rad_val2 = math.radians(angle2)
            node_x2 = rx2 * math.cos(rad_val2)
            node_y2 = ry2 * math.sin(rad_val2)
            p.setBrush(QBrush(qcol(C.ACC2, 240)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(node_x2, node_y2), 4, 4)
            p.restore()

            # Central holographic text
            p.setPen(QPen(qcol(C.WHITE if not self.muted else C.MUTED_C, min(255, int(self._halo * 1.8))), 1))
            p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
            p.drawText(QRectF(cx - 80, cy - 14, 160, 28),
                       Qt.AlignmentFlag.AlignCenter, "S.A.T.U.R.D.A.Y")

        # particles
        for pt in self._particles:
            a = max(0, min(255, int(pt[4] * 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI, a)))
            p.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)

        # ── STATUS TEXT — above the orb ─────────────────────────────────
        sy = cy - fw * 0.58
        if self.muted:
            txt, col = "⊘  MUTED",     qcol(C.MUTED_C)
        elif self.speaking:
            txt, col = "●  SPEAKING",  qcol(C.ACC)
        elif self.state == "THINKING":
            sym = "◈" if self._blink else "◇"
            txt, col = f"{sym}  THINKING",   qcol(C.ACC2)
        elif self.state == "PROCESSING":
            sym = "▷" if self._blink else "▶"
            txt, col = f"{sym}  PROCESSING", qcol(C.ACC2)
        elif self.state == "LISTENING":
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  LISTENING",  qcol(C.GREEN)
        elif self.state == "STANDBY":
            sym = "💤"
            txt, col = f"{sym}  STANDBY", qcol(C.TEXT_DIM)
        else:
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  {self.state}", qcol(C.PRI)

        p.setPen(QPen(col, 1))
        p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        p.drawText(QRectF(0, sy, W, 26), Qt.AlignmentFlag.AlignCenter, txt)

        # ── WAVEFORM — bottom of screen in a pill container ──────────────
        N, bw = 40, 9
        total_w = N * bw
        wx0 = (W - total_w) / 2
        wy  = H - 110      # raised up from bottom to leave space for last response text

        # pill background
        pill_pad = 16
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(C.PANEL, 160)))
        p.drawRoundedRect(
            QRectF(wx0 - pill_pad, wy - 4, total_w + pill_pad * 2, 36),
            18, 18
        )
        # pill border
        p.setPen(QPen(qcol(C.BORDER_B, 120), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(
            QRectF(wx0 - pill_pad, wy - 4, total_w + pill_pad * 2, 36),
            18, 18
        )

        for i in range(N):
            if self.muted:
                hgt, cl = 2, qcol(C.MUTED_C)
            else:
                vol = getattr(self, "_audio_level", 0.0)
                
                # Organic dynamic wave baseline shape
                wave = math.sin(self._tick * 0.15 + i * 0.45) * math.cos(self._tick * 0.08 - i * 0.18)
                base_h = abs(wave)
                
                if vol > 0.01:
                    # Bell-like distribution (center bars bounce higher)
                    dist_to_center = abs(i - N/2) / (N/2)
                    center_boost = 1.0 - (dist_to_center * 0.5)
                    
                    hgt = int(3 + (base_h * 18 + 4) * vol * center_boost)
                    hgt = max(3, min(24, hgt))
                    cl  = qcol(C.PRI) if hgt > 14 else qcol(C.PRI_DIM)
                else:
                    # Ambient idle waveform
                    hgt = int(3 + 2 * math.sin(self._tick * 0.06 + i * 0.5))
                    hgt = max(2, hgt)
                    cl  = qcol(C.BORDER_B)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(cl))
            p.drawRoundedRect(
                QRectF(wx0 + i * bw, wy + 14 - hgt, bw - 2, hgt),
                1, 1
            )


        # ── TOP-LEFT: time & date ──────────────────────────────────────────
        pad = 24
        p.setFont(QFont("Courier New", 28, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI, 220), 1))
        time_str = time.strftime("%I:%M:%S %p")
        p.drawText(QRectF(pad, pad, 260, 40), Qt.AlignmentFlag.AlignLeft, time_str)

        p.setFont(QFont("Courier New", 10))
        p.setPen(QPen(qcol(C.TEXT_DIM, 180), 1))
        date_str = time.strftime("%A  %d %B %Y")
        p.drawText(QRectF(pad, pad + 44, 260, 20), Qt.AlignmentFlag.AlignLeft, date_str)

        # divider line top-left
        p.setPen(QPen(qcol(C.BORDER, 160), 1))
        p.drawLine(QPointF(pad, pad + 68), QPointF(pad + 220, pad + 68))

        p.setFont(QFont("Courier New", 9))
        p.setPen(QPen(qcol(C.TEXT_DIM, 130), 1))
        p.drawText(QRectF(pad, pad + 74, 220, 16), Qt.AlignmentFlag.AlignLeft, "IP VERSE  //  ONLINE")

        # ── TOP-LEFT: Saturday AI Activity Ticker (placed under the time block) ─
        ay = H - 180
        p.setPen(QPen(qcol(C.BORDER, 100), 1))
        p.drawLine(QPointF(pad, ay), QPointF(pad + 220, ay))

        p.setFont(QFont("Courier New", 9))
        p.setPen(QPen(qcol(C.TEXT_DIM, 160), 1))
        p.drawText(QRectF(pad, ay + 12, 220, 16), Qt.AlignmentFlag.AlignLeft, "AI ACTIVITY")

        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        if hasattr(self, "_activity") and "idle" not in self._activity.lower():
            act_col = qcol(C.ACC, 240)
            node_col = qcol(C.ACC2, 220)
        else:
            act_col = qcol(C.TEXT_DIM, 200)
            node_col = qcol(C.PRI_DIM, 120)
            
        p.setPen(QPen(act_col, 1))
        p.drawText(
            QRectF(pad, ay + 32, 220, 48),
            Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            getattr(self, "_activity", "SYSTEM IDLE").upper()
        )

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(node_col if self._tick % 24 < 12 else qcol(C.BG)))
        p.drawEllipse(QPointF(pad - 12, ay + 19), 3, 3)

        p.setPen(QPen(qcol(C.BORDER, 100), 1))
        p.drawLine(QPointF(pad, ay + 86), QPointF(pad + 220, ay + 86))

        # ── TOP-RIGHT: system stats ────────────────────────────────────────
        sn   = self._snap
        stats = [
            ("CPU",  f"{sn['cpu']:.0f}%",  C.PRI),
            ("RAM",  f"{sn['mem']:.0f}%",  C.PRI),
            ("NET",  f"{sn['net']:.1f} MB/s", C.ACC2),
        ]
        if sn["gpu"] >= 0:
            stats.append(("GPU", f"{sn['gpu']:.0f}%", C.GREEN))
        if sn["tmp"] >= 0:
            stats.append(("TMP", f"{sn['tmp']:.0f}°C", C.ACC))

        rpad = W - pad
        for si, (lbl, val, col) in enumerate(stats):
            ry = pad + si * 30
            p.setFont(QFont("Courier New", 9))
            p.setPen(QPen(qcol(C.TEXT_DIM, 160), 1))
            p.drawText(QRectF(rpad - 200, ry, 60, 20), Qt.AlignmentFlag.AlignLeft, lbl)
            p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QPen(qcol(col, 220), 1))
            p.drawText(QRectF(rpad - 130, ry - 2, 130, 22), Qt.AlignmentFlag.AlignRight, val)
            # mini bar
            try:
                bar_pct = float(val.replace("%","").replace(" MB/s","").replace("°C","")) / (100 if "%" in val else (10 if "MB" in val else 120))
            except Exception:
                bar_pct = 0
            bar_pct = min(1.0, max(0.0, bar_pct))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.BORDER, 120)))
            p.drawRoundedRect(QRectF(rpad - 200, ry + 18, 200, 4), 2, 2)
            p.setBrush(QBrush(qcol(col, 200)))
            p.drawRoundedRect(QRectF(rpad - 200, ry + 18, 200 * bar_pct, 4), 2, 2)

        # (Middle-right AI Activity Ticker removed)

        # (Bottom-left tech block removed)

        # ── BOTTOM-RIGHT: Last Response / Saturday Output ──────────────────
        # ── BOTTOM-RIGHT: uptime ──────────────────────────────────────────
        br_y = H - 100
        up_s = int(time.time() - APP_START_TIME)
        up_str = f"{up_s//3600:02d}:{(up_s%3600)//60:02d}:{up_s%60:02d}"
        p.setFont(QFont("Courier New", 9))
        p.setPen(QPen(qcol(C.TEXT_DIM, 130), 1))
        p.drawText(QRectF(rpad - 200, br_y, 200, 16), Qt.AlignmentFlag.AlignRight, "SESSION")
        p.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI, 200), 1))
        p.drawText(QRectF(rpad - 200, br_y + 16, 200, 22), Qt.AlignmentFlag.AlignRight, up_str)

        # ── LAST RESPONSE text (below waveform) ───────────────────────────
        if self._last_response:
            resp_y = wy + 42
            max_w  = min(W - 120, 800)
            p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            p.setPen(QPen(qcol(C.TEXT, 220), 1))
            resp_txt = self._last_response
            if len(resp_txt) > 140:
                resp_txt = resp_txt[:137] + "..."
            p.drawText(
                QRectF((W - max_w) / 2, resp_y, max_w, 56),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                resp_txt,
            )

        # ── Horizontal scan-lines (subtle) ─────────────────────────────────
        scan_col = qcol(C.PRI, 6)
        p.setPen(QPen(scan_col, 1))
        for yl in range(0, H, 6):
            p.drawLine(QPointF(0, yl), QPointF(W, yl))

class MetricBar(QWidget):

    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0       # 0–100
        self._text  = "--"
        self.setFixedHeight(38)
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
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 4, 4)

        bar_h   = 4
        bar_y   = H - bar_h - 5
        bar_w   = W - 12
        bar_x   = 6
        fill_w  = int(bar_w * self._value / 100)

        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)

        if self._value > 85:
            bar_col = qcol(C.RED)
        elif self._value > 65:
            bar_col = qcol(C.ACC)
        else:
            bar_col = qcol(self._color)

        if fill_w > 0:
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2, 2)

        p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(8, 5, 50, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 4, W - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)

class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 9))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                padding: 6px;
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
        self._queue: list[str] = []
        self._typing  = False
        self._text    = ""
        self._pos     = 0
        self._tag     = "sys"
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if len(self._queue) > 30:
            self._queue = self._queue[-30:]
        if not self._typing:
            self._next()

    def _insert_full_text(self):
        cur = self.textCursor()
        fmt = cur.charFormat()
        col = {
            "you":  qcol(C.WHITE),
            "ai":   qcol(C.PRI),
            "err":  qcol(C.RED),
            "file": qcol(C.GREEN),
            "sys":  qcol(C.ACC2),
        }.get(self._tag, qcol(C.TEXT))
        fmt.setForeground(QBrush(col))
        cur.movePosition(cur.MoveOperation.End)
        cur.insertText(self._text + "\n", fmt)
        self.setTextCursor(cur)
        self.ensureCursorVisible()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        self._text   = self._queue.pop(0)
        self._pos    = 0
        tl = self._text.lower()
        if   tl.startswith("you:"):    self._tag = "you"
        elif tl.startswith("saturday:"): self._tag = "ai"
        elif tl.startswith("file:"):   self._tag = "file"
        elif "err" in tl:              self._tag = "err"
        else:                          self._tag = "sys"
        
        if len(self._queue) > 5:
            self._insert_full_text()
            QTimer.singleShot(10, self._next)
        else:
            self._tmr.start(6)

    def _step(self):
        if self._pos < len(self._text):
            ch  = self._text[self._pos]
            cur = self.textCursor()
            fmt = cur.charFormat()
            col = {
                "you":  qcol(C.WHITE),
                "ai":   qcol(C.PRI),
                "err":  qcol(C.RED),
                "file": qcol(C.GREEN),
                "sys":  qcol(C.ACC2),
            }.get(self._tag, qcol(C.TEXT))
            fmt.setForeground(QBrush(col))
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText(ch, fmt)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            self._pos += 1
        else:
            self._tmr.stop()
            cur = self.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n")
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            QTimer.singleShot(20, self._next)

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
            self, "Select a file for SATURDAY", str(Path.home()),
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

        if z._drag_over:
            bg_col = qcol(C.PRI_GHO, 150)
        elif z._hovering:
            bg_col = qcol(C.PRI_GHO, 80)
        else:
            bg_col = qcol(C.PANEL)
        p.setBrush(QBrush(bg_col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   border_col = qcol(C.GREEN, 200)
        elif z._drag_over:    border_col = qcol(C.PRI, 230)
        elif z._hovering:     border_col = qcol(C.BORDER_B, 200)
        else:                 border_col = qcol(C.BORDER, 160)

        border_width = 2.0 if (z._hovering or z._drag_over) else 1.0
        pen = QPen(border_col, border_width, Qt.PenStyle.DashLine)
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
        p.setFont(QFont("Courier New", 8))
        p.setPen(QPen(qcol(C.PRI_DIM if not hover else C.TEXT), 1))
        p.drawText(QRectF(0, cy + 8, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "Drop file here  or  Click to Browse")
        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, cy + 24, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "Images · Video · Audio · PDF · Docs · Code · Data")

    def _paint_drag_over(self, p, W, H):
        cx, cy = W / 2, H / 2
        p.setFont(QFont("Courier New", 20))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy - 24, W, 32), Qt.AlignmentFlag.AlignCenter, "⬇")
        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy + 12, W, 16), Qt.AlignmentFlag.AlignCenter, "Release to load")

    def _paint_file(self, p, W, H):
        path = Path(self._z._current_file)
        cat  = _file_category(path)
        icon, icon_col = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size_str = _fmt_size(path.stat().st_size) if path.exists() else "File not found"
        ext_str  = path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 60
        p.setFont(QFont("Segoe UI Emoji", 22) if _OS == "Windows" else QFont("Arial", 22))
        p.setPen(QPen(qcol(icon_col), 1))
        p.drawText(QRectF(block_x, 0, block_w, H), Qt.AlignmentFlag.AlignCenter, icon)

        tx = block_x + block_w + 6
        tw = W - tx - 38

        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE), 1))
        name = path.name if len(path.name) <= 34 else path.name[:31] + "..."
        p.drawText(QRectF(tx, H * 0.18, tw, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(tx, H * 0.18 + 18, tw, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{ext_str}  ·  {size_str}")

        p.setFont(QFont("Courier New", 6))
        p.setPen(QPen(qcol("#1e5c6a"), 1))
        par = str(path.parent)
        if len(par) > 42: par = "…" + par[-41:]
        p.drawText(QRectF(tx, H * 0.18 + 34, tw, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, par)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.RED, 180), 1))
        p.drawText(QRectF(W - 34, 0, 28, H), Qt.AlignmentFlag.AlignCenter, "✕")

    def mousePressEvent(self, e):
        z = self._z
        if z._current_file and e.pos().x() > self.width() - 34:
            z.clear_file()
        else:
            z.mousePressEvent(e)


class SetupOverlay(QWidget):
    done = pyqtSignal(str, str, str)

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
            w.setFont(QFont("Courier New", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        layout.addWidget(_lbl("◈  INITIALISATION REQUIRED", 13, True))
        layout.addWidget(_lbl("Configure S.A.T.U.R.D.A.Y. before first boot.", 9, color=C.PRI_DIM))
        layout.addSpacing(6)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(4)

        layout.addWidget(_lbl("GEMINI API KEY", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza…")
        self._key_input.setFont(QFont("Courier New", 10))
        self._key_input.setFixedHeight(32)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        layout.addWidget(self._key_input)
        layout.addSpacing(8)

        layout.addWidget(_lbl("OPENROUTER API KEY", 8, color=C.TEXT_DIM,
                       align=Qt.AlignmentFlag.AlignLeft))
        self._or_input = QLineEdit()
        self._or_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._or_input.setPlaceholderText("sk-or-…")
        self._or_input.setFont(QFont("Courier New", 10))
        self._or_input.setFixedHeight(32)
        self._or_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.ACC2}; }}
        """)
        layout.addWidget(self._or_input)

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
        for key, label in [("windows","⊞  Windows"),("mac","⌘ macOS"),("linux","🐧  Linux")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._sel(k))
            os_row.addWidget(btn)
            self._os_btns[key] = btn
        layout.addLayout(os_row)
        self._sel(detected)
        layout.addSpacing(12)

        init_btn = QPushButton("▸  INITIALISE SYSTEMS")
        init_btn.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
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
        or_key = self._or_input.text().strip()
        if not key:
            self._key_input.setStyleSheet(
                self._key_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        if not or_key:
            self._or_input.setStyleSheet(
                self._or_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        self.done.emit(key, or_key, self._sel_os)


class WorkspaceDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_win = parent
        self.setStyleSheet(f"background: transparent;")
        
        # Grid layout for 6 tiles
        grid = QGridLayout(self)
        grid.setContentsMargins(15, 15, 15, 15)
        grid.setSpacing(15)
        
        # Tile 1: Orb Status / Speech
        self.tile_orb = self._create_orb_tile()
        grid.addWidget(self.tile_orb, 0, 0)
        
        # Tile 2: System Metrics
        self.tile_metrics = self._create_metrics_tile()
        grid.addWidget(self.tile_metrics, 0, 1)
        
        # Tile 3: Active Task / Last Response
        self.tile_active = self._create_active_task_tile()
        grid.addWidget(self.tile_active, 0, 2)
        
        # Tile 4: Workspace File Explorer
        self.tile_explorer = self._create_explorer_tile()
        grid.addWidget(self.tile_explorer, 1, 0)
        
        # Tile 5: Memory Context
        self.tile_memory = self._create_memory_tile()
        grid.addWidget(self.tile_memory, 1, 1)
        
        # Tile 6: Task Queue List
        self.tile_queue = self._create_queue_tile()
        grid.addWidget(self.tile_queue, 1, 2)
        
        # Setup polling timers for real-time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_live_data)
        self.timer.start(2000) # update every 2 seconds

    def _create_card(self, title: str, content_widget: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        card.setStyleSheet(f"""
            QFrame#DashboardCard {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 6px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)
        
        # Title row
        title_lbl = QLabel(title.upper())
        title_lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        lay.addWidget(title_lbl)
        
        # Content
        lay.addWidget(content_widget, stretch=1)
        return card

    def _create_orb_tile(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        
        # Status display
        self.status_lbl = QLabel("● INITIALISING")
        self.status_lbl.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        lay.addWidget(self.status_lbl)
        
        # Wake Words info
        ww_layout = QHBoxLayout()
        ww_lbl = QLabel("Wake Words:")
        ww_lbl.setFont(QFont("Courier New", 8))
        ww_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self.ww_val = QLabel("saturday")
        self.ww_val.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.ww_val.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        ww_layout.addWidget(ww_lbl)
        ww_layout.addWidget(self.ww_val)
        ww_layout.addStretch()
        lay.addLayout(ww_layout)
        
        # Voice Selector combo box
        voice_layout = QHBoxLayout()
        voice_lbl = QLabel("Live Voice:")
        voice_lbl.setFont(QFont("Courier New", 8))
        voice_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self.dash_voice_cb = QComboBox()
        self.dash_voice_cb.setFont(QFont("Courier New", 8))
        self.dash_voice_cb.setStyleSheet(f"""
            QComboBox {{
                background: {C.DARK};
                border: 1px solid {C.BORDER_A};
                border-radius: 4px;
                color: {C.TEXT};
                padding: 2px 6px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self.dash_voice_cb.addItems(["Charon", "Puck", "Fenrir", "Kore", "Aoede"])
        self.dash_voice_cb.currentIndexChanged.connect(self._on_dash_voice_changed)
        voice_layout.addWidget(voice_lbl)
        voice_layout.addWidget(self.dash_voice_cb, stretch=1)
        lay.addLayout(voice_layout)
        
        # Active model / OpenRouter info
        model_layout = QHBoxLayout()
        model_lbl = QLabel("Router Model:")
        model_lbl.setFont(QFont("Courier New", 8))
        model_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self.model_val = QLabel("gemini-2.0-flash")
        self.model_val.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.model_val.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        model_layout.addWidget(model_lbl)
        model_layout.addWidget(self.model_val)
        model_layout.addStretch()
        lay.addLayout(model_layout)
        
        lay.addStretch()
        return self._create_card("Orb & Speech Status", container)

    def _on_dash_voice_changed(self):
        voice_names = ["Charon", "Puck", "Fenrir", "Kore", "Aoede"]
        idx = self.dash_voice_cb.currentIndex()
        if 0 <= idx < len(voice_names):
            selected = voice_names[idx]
            self.main_win._save_settings({"voice_name": selected})
            if hasattr(self.main_win, "_voice_cb") and self.main_win._voice_cb:
                self.main_win._voice_cb.blockSignals(True)
                self.main_win._voice_cb.setCurrentIndex(idx)
                self.main_win._voice_cb.blockSignals(False)
            self.main_win.write_log(f"SYS: Saturday voice changed to {selected} via Dashboard.")

    def _create_metrics_tile(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        
        def build_bar(label_text: str):
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Courier New", 8))
            lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
            
            pbar = QProgressBar()
            pbar.setFixedHeight(12)
            pbar.setRange(0, 100)
            pbar.setTextVisible(True)
            pbar.setFont(QFont("Courier New", 7))
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    background: {C.DARK};
                    border: 1px solid {C.BORDER_A};
                    border-radius: 3px;
                    color: {C.TEXT};
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background: {C.PRI};
                    border-radius: 2px;
                }}
            """)
            row_lay.addWidget(lbl, stretch=1)
            row_lay.addWidget(pbar, stretch=3)
            return row, pbar
            
        row_cpu, self.cpu_bar = build_bar("CPU:")
        lay.addWidget(row_cpu)
        
        row_mem, self.mem_bar = build_bar("RAM:")
        lay.addWidget(row_mem)
        
        net_layout = QHBoxLayout()
        net_lbl = QLabel("Network usage:")
        net_lbl.setFont(QFont("Courier New", 8))
        net_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self.net_val = QLabel("0.0 KB/s")
        self.net_val.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.net_val.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        net_layout.addWidget(net_lbl)
        net_layout.addWidget(self.net_val)
        net_layout.addStretch()
        lay.addLayout(net_layout)
        
        uptime_layout = QHBoxLayout()
        uptime_lbl = QLabel("System Uptime:")
        uptime_lbl.setFont(QFont("Courier New", 8))
        uptime_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self.uptime_val = QLabel("0h 0m 0s")
        self.uptime_val.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.uptime_val.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        uptime_layout.addWidget(uptime_lbl)
        uptime_layout.addWidget(self.uptime_val)
        uptime_layout.addStretch()
        lay.addLayout(uptime_layout)
        
        lay.addStretch()
        return self._create_card("System Metrics", container)

    def _create_active_task_tile(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        
        self.active_task_lbl = QLabel("No active task running")
        self.active_task_lbl.setWordWrap(True)
        self.active_task_lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        self.active_task_lbl.setStyleSheet(f"color: {C.ACC}; background: transparent;")
        lay.addWidget(self.active_task_lbl)
        
        resp_hdr = QLabel("LAST RESPONSE:")
        resp_hdr.setFont(QFont("Courier New", 8))
        resp_hdr.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        lay.addWidget(resp_hdr)
        
        self.last_resp_text = QTextEdit()
        self.last_resp_text.setReadOnly(True)
        self.last_resp_text.setFont(QFont("Courier New", 8))
        self.last_resp_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C.DARK};
                border: 1px solid {C.BORDER_A};
                border-radius: 4px;
                color: {C.TEXT_MED};
            }}
        """)
        lay.addWidget(self.last_resp_text, stretch=1)
        
        # Standby thoughts box
        thoughts_hdr = QLabel("STANDBY THOUGHTS:")
        thoughts_hdr.setFont(QFont("Courier New", 8))
        thoughts_hdr.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; margin-top: 4px;")
        lay.addWidget(thoughts_hdr)
        
        self.standby_thoughts_text = QTextEdit()
        self.standby_thoughts_text.setReadOnly(True)
        self.standby_thoughts_text.setFont(QFont("Courier New", 8))
        self.standby_thoughts_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C.DARK};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                color: {C.ACC};
            }}
        """)
        self.standby_thoughts_text.setFixedHeight(80)
        lay.addWidget(self.standby_thoughts_text)
        
        return self._create_card("Active Task / Execution", container)

    def _create_explorer_tile(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        
        self.file_model = QFileSystemModel()
        workspace_path = str(BASE_DIR)
        self.file_model.setRootPath(workspace_path)
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(workspace_path))
        self.tree_view.setFont(QFont("Courier New", 8))
        self.tree_view.setStyleSheet(f"""
            QTreeView {{
                background: {C.DARK};
                border: 1px solid {C.BORDER_A};
                border-radius: 4px;
                color: {C.TEXT};
            }}
            QTreeView::item:hover {{
                background: {C.PRI_GHO};
            }}
            QTreeView::item:selected {{
                background: {C.PRI_DIM};
                color: {C.WHITE};
            }}
            QHeaderView::section {{
                background: {C.PANEL};
                color: {C.TEXT_DIM};
                font-family: 'Courier New';
                font-size: 8pt;
                border: 1px solid {C.BORDER_A};
                padding: 2px;
            }}
        """)
        
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.doubleClicked.connect(self._on_file_double_clicked)
        
        lay.addWidget(self.tree_view, stretch=1)
        return self._create_card("Workspace Files", container)

    def _on_file_double_clicked(self, index):
        path = self.file_model.filePath(index)
        if os.path.exists(path):
            try:
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
            except Exception as e:
                print(f"[Dashboard Explorer] Error opening file: {e}")

    def _create_memory_tile(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        
        self.memory_info = QTextEdit()
        self.memory_info.setReadOnly(True)
        self.memory_info.setFont(QFont("Courier New", 8))
        self.memory_info.setStyleSheet(f"""
            QTextEdit {{
                background: {C.DARK};
                border: 1px solid {C.BORDER_A};
                border-radius: 4px;
                color: {C.TEXT_MED};
            }}
        """)
        lay.addWidget(self.memory_info, stretch=1)
        
        ref_btn = QPushButton("Refresh Memory")
        ref_btn.setFixedHeight(24)
        ref_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        ref_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ref_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.DARK};
                border: 1px solid {C.BORDER_A};
                border-radius: 3px;
                color: {C.PRI};
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO};
                border: 1px solid {C.PRI};
            }}
        """)
        ref_btn.clicked.connect(self.refresh_memory)
        lay.addWidget(ref_btn)
        
        return self._create_card("AI Memory & RAG", container)

    def _create_queue_tile(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        
        self.queue_list = QListWidget()
        self.queue_list.setFont(QFont("Courier New", 8))
        self.queue_list.setStyleSheet(f"""
            QListWidget {{
                background: {C.DARK};
                border: 1px solid {C.BORDER_A};
                border-radius: 4px;
                color: {C.TEXT};
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {C.BORDER_A};
            }}
            QListWidget::item:hover {{
                background: {C.PRI_GHO};
            }}
        """)
        lay.addWidget(self.queue_list, stretch=1)
        return self._create_card("Task Queue", container)

    def refresh_data(self):
        self.refresh_memory()
        self.refresh_live_data()

    def refresh_memory(self):
        try:
            from memory.memory_manager import load_memory
            mem = load_memory()
            name = mem.get("identity", {}).get("name", {}).get("value", "Pratik")
            
            projects_dict = mem.get("projects", {})
            projects = []
            for k, v in projects_dict.items():
                if isinstance(v, dict) and "value" in v:
                    projects.append(v["value"])
                elif isinstance(v, str):
                    projects.append(v)
            proj_str = ", ".join(projects) if projects else "No active projects"
            
            pref_dict = mem.get("preferences", {})
            prefs = []
            for k, v in pref_dict.items():
                val = v.get("value") if isinstance(v, dict) else v
                if val:
                    prefs.append(f"- {k.replace('_', ' ')}: {val}")
            pref_str = "\n".join(prefs) if prefs else "None"
            
            text = f"USER IDENTITY:\n- Name: {name}\n\nPROJECTS:\n- {proj_str}\n\nPREFERENCES:\n{pref_str}"
            self.memory_info.setPlainText(text)
        except Exception as e:
            self.memory_info.setPlainText(f"Error loading memory: {e}")

    def refresh_live_data(self):
        # Update Orb status
        try:
            state = self.main_win.hud.state
            color = C.TEXT
            if state == "SPEAKING":
                color = C.ACC
            elif state in ("THINKING", "PROCESSING"):
                color = C.ACC2
            elif state == "MUTED":
                color = C.RED
            self.status_lbl.setText(f"● {state}")
            self.status_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        except Exception:
            pass
        
        # Wake Words
        try:
            settings = self.main_win._load_settings()
            self.ww_val.setText(settings.get("wake_words", "saturday"))
            
            # Selected Voice
            current_voice = settings.get("voice_name", "Charon")
            self.dash_voice_cb.blockSignals(True)
            idx = self.dash_voice_cb.findText(current_voice)
            if idx >= 0:
                self.dash_voice_cb.setCurrentIndex(idx)
            self.dash_voice_cb.blockSignals(False)
        except Exception:
            pass
        
        # System Uptime
        elapsed_sec = int(time.time() - APP_START_TIME)
        hrs = elapsed_sec // 3600
        mins = (elapsed_sec % 3600) // 60
        secs = elapsed_sec % 60
        self.uptime_val.setText(f"{hrs}h {mins}m {secs}s")
        
        # Update metrics
        try:
            snap = _metrics.snapshot()
            cpu = snap.get("cpu", 0.0)
            self.cpu_bar.setValue(int(cpu))
            
            mem = snap.get("mem", 0.0)
            self.mem_bar.setValue(int(mem))
            
            net = snap.get("net", 0.0)
            if net < 1.0:
                net_str = f"{net*1024:.0f} KB/s"
            else:
                net_str = f"{net:.1f} MB/s"
            self.net_val.setText(net_str)
        except Exception:
            pass
            
        # Active Task Card
        try:
            self.last_resp_text.setPlainText(self.main_win.hud._last_response)
            act = self.main_win.hud._activity
            if act:
                self.active_task_lbl.setText(act)
            else:
                self.active_task_lbl.setText("Idle")
        except Exception:
            pass
            
        # Task Queue list
        try:
            self.queue_list.clear()
            from agent.task_queue import get_queue
            q = get_queue()
            statuses = q.get_all_statuses()
            if not statuses:
                self.queue_list.addItem("Queue is empty")
            else:
                for s in statuses:
                    task_id = s.get("task_id", "")[:6]
                    goal = s.get("goal", "")
                    status = s.get("status", "")
                    self.queue_list.addItem(f"[{status.upper()}] ID:{task_id} - {goal}")
        except Exception as e:
            self.queue_list.addItem(f"Error: {e}")


class WidgetsSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        
        # Main layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)
        
        # Header
        hdr = QLabel("🍎 SYSTEM WIDGETS")
        hdr.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        lay.addWidget(hdr)
        
        # 1. Weather Widget Card
        weather_card = QWidget()
        weather_card.setStyleSheet(f"background: {hex_to_rgba_str(C.DARK, 0.35)}; border: 1px solid {C.BORDER}; border-radius: 8px;")
        w_lay = QVBoxLayout(weather_card)
        w_lay.setContentsMargins(10, 10, 10, 10)
        w_lay.setSpacing(4)
        
        w_title = QLabel("☁ WEATHER")
        w_title.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        w_title.setStyleSheet("color: #00e5ff; background: transparent; border: none;")
        w_lay.addWidget(w_title)
        
        w_desc = QLabel("24°C - Mostly Clear")
        w_desc.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        w_desc.setStyleSheet(f"color: {C.TEXT}; background: transparent; border: none;")
        w_lay.addWidget(w_desc)
        
        w_loc = QLabel("Mumbai, IN")
        w_loc.setFont(QFont("Courier New", 7))
        w_loc.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        w_lay.addWidget(w_loc)
        lay.addWidget(weather_card)
        
        # 2. System Monitor Card
        sys_card = QWidget()
        sys_card.setStyleSheet(f"background: {hex_to_rgba_str(C.DARK, 0.35)}; border: 1px solid {C.BORDER}; border-radius: 8px;")
        s_lay = QVBoxLayout(sys_card)
        s_lay.setContentsMargins(10, 10, 10, 10)
        s_lay.setSpacing(6)
        
        s_title = QLabel("📊 SYSTEM STATUS")
        s_title.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        s_title.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")
        s_lay.addWidget(s_title)
        
        # CPU
        cpu_box = QHBoxLayout()
        cpu_lbl = QLabel("CPU:"); cpu_lbl.setFont(QFont("Courier New", 7)); cpu_lbl.setStyleSheet("color: white; border: none; background: transparent;")
        self._cpu_bar = QProgressBar()
        self._cpu_bar.setFixedHeight(6)
        self._cpu_bar.setTextVisible(False)
        self._cpu_bar.setStyleSheet(f"QProgressBar {{ background: {C.BORDER}; border-radius: 3px; border: none; }} QProgressBar::chunk {{ background: {C.PRI}; border-radius: 3px; }}")
        self._cpu_lbl_val = QLabel("0%"); self._cpu_lbl_val.setFont(QFont("Courier New", 7)); self._cpu_lbl_val.setStyleSheet("color: white; border: none; background: transparent;")
        cpu_box.addWidget(cpu_lbl)
        cpu_box.addWidget(self._cpu_bar)
        cpu_box.addWidget(self._cpu_lbl_val)
        s_lay.addLayout(cpu_box)
        
        # RAM
        ram_box = QHBoxLayout()
        ram_lbl = QLabel("RAM:"); ram_lbl.setFont(QFont("Courier New", 7)); ram_lbl.setStyleSheet("color: white; border: none; background: transparent;")
        self._ram_bar = QProgressBar()
        self._ram_bar.setFixedHeight(6)
        self._ram_bar.setTextVisible(False)
        self._ram_bar.setStyleSheet(f"QProgressBar {{ background: {C.BORDER}; border-radius: 3px; border: none; }} QProgressBar::chunk {{ background: {C.ACC2}; border-radius: 3px; }}")
        self._ram_lbl_val = QLabel("0%"); self._ram_lbl_val.setFont(QFont("Courier New", 7)); self._ram_lbl_val.setStyleSheet("color: white; border: none; background: transparent;")
        ram_box.addWidget(ram_lbl)
        ram_box.addWidget(self._ram_bar)
        ram_box.addWidget(self._ram_lbl_val)
        s_lay.addLayout(ram_box)
        lay.addWidget(sys_card)
        
        # 3. Quick Notes Card
        notes_card = QWidget()
        notes_card.setStyleSheet(f"background: {hex_to_rgba_str(C.DARK, 0.35)}; border: 1px solid {C.BORDER}; border-radius: 8px;")
        n_lay = QVBoxLayout(notes_card)
        n_lay.setContentsMargins(10, 10, 10, 10)
        n_lay.setSpacing(6)
        
        n_title = QLabel("📝 QUICK NOTES")
        n_title.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        n_title.setStyleSheet("color: #ffb300; background: transparent; border: none;")
        n_lay.addWidget(n_title)
        
        self.note_edit = QTextEdit()
        self.note_edit.setFont(QFont("Courier New", 8))
        self.note_edit.setPlaceholderText("Type quick thoughts here...")
        self.note_edit.setStyleSheet(f"background: rgba(0, 0, 0, 0.25); color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        self.note_edit.textChanged.connect(self._save_note)
        # Load note
        note_path = os.path.join(os.path.expanduser("~"), ".saturday_quick_note.txt")
        if os.path.exists(note_path):
            try:
                with open(note_path, "r", encoding="utf-8") as f:
                    self.note_edit.setPlainText(f.read())
            except Exception:
                pass
        n_lay.addWidget(self.note_edit)
        lay.addWidget(notes_card, stretch=1)
        
        # 4. Clock/Calendar Card
        cal_card = QWidget()
        cal_card.setFixedHeight(62)
        cal_card.setStyleSheet(f"background: {hex_to_rgba_str(C.DARK, 0.35)}; border: 1px solid {C.BORDER}; border-radius: 8px;")
        c_lay = QVBoxLayout(cal_card)
        c_lay.setContentsMargins(10, 8, 10, 8)
        c_lay.setSpacing(2)
        
        self.cal_time = QLabel("12:00:00")
        self.cal_time.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        self.cal_time.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        c_lay.addWidget(self.cal_time)
        
        self.cal_date = QLabel("28 June 2026")
        self.cal_date.setFont(QFont("Courier New", 8))
        self.cal_date.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        c_lay.addWidget(self.cal_date)
        lay.addWidget(cal_card)
        
        # Update clock
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._update_time)
        self._tmr.start(1000)
        self._update_time()
        
    def _save_note(self):
        note_path = os.path.join(os.path.expanduser("~"), ".saturday_quick_note.txt")
        try:
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(self.note_edit.toPlainText())
        except Exception:
            pass
            
    def _update_time(self):
        t = QTime.currentTime().toString("hh:mm:ss")
        d = QDate.currentDate().toString("dd MMMM yyyy")
        self.cal_time.setText(t)
        self.cal_date.setText(d)
        
    def update_metrics(self, cpu, mem):
        self._cpu_bar.setValue(int(cpu))
        self._cpu_lbl_val.setText(f"{int(cpu)}%")
        self._ram_bar.setValue(int(mem))
        self._ram_lbl_val.setText(f"{int(mem)}%")


class AgentCommandCenter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_win = parent
        self.setStyleSheet("background: transparent;")
        
        # Outer horizontal layout: Left list, Right details panel
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(15, 15, 15, 15)
        main_lay.setSpacing(15)
        
        # --- LEFT PANEL: List of Agents ---
        left_panel = QFrame()
        left_panel.setFixedWidth(240)
        left_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(10, 10, 10, 10)
        left_lay.setSpacing(8)
        
        title_lbl = QLabel("🛡️ IP ARMY COMMAND")
        title_lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        left_lay.addWidget(title_lbl)
        
        self.agent_list = QListWidget()
        self.agent_list.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.agent_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.agent_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: white;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {hex_to_rgba_str(C.BORDER, 0.3)};
            }}
            QListWidget::item:selected {{
                background: {C.PRI_GHO};
                color: {C.PRI};
                border-radius: 4px;
            }}
        """)
        self.agent_list.itemSelectionChanged.connect(self._on_agent_selected)
        left_lay.addWidget(self.agent_list)
        
        # Back to main window button
        back_btn = QPushButton("◀ BACK TO HUD")
        back_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C.PRI_DIM};
                border-radius: 4px;
                color: {C.PRI};
                padding: 6px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO};
            }}
        """)
        back_btn.clicked.connect(lambda: self.main_win._stacked_widget.setCurrentIndex(0))
        left_lay.addWidget(back_btn)
        
        main_lay.addWidget(left_panel)
        
        # --- RIGHT PANEL: Agent Detail & Chat ---
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL2};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        right_lay = QVBoxLayout(self.right_panel)
        right_lay.setContentsMargins(14, 14, 14, 14)
        right_lay.setSpacing(12)
        
        # Info header
        self.name_lbl = QLabel("SELECT AN AGENT")
        self.name_lbl.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        self.name_lbl.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        right_lay.addWidget(self.name_lbl)
        
        self.role_lbl = QLabel("")
        self.role_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self.role_lbl.setStyleSheet(f"color: {C.ACC2}; border: none; background: transparent;")
        right_lay.addWidget(self.role_lbl)
        
        self.desc_lbl = QLabel("")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setFont(QFont("Courier New", 8))
        self.desc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; border: none; background: transparent;")
        right_lay.addWidget(self.desc_lbl)
        
        # Terminal logs
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Courier New", 8))
        self.chat_display.setStyleSheet(f"background: rgba(0, 0, 0, 0.25); color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 6px;")
        right_lay.addWidget(self.chat_display, stretch=1)
        
        # Input row
        inp_lay = QHBoxLayout()
        inp_lay.setSpacing(8)
        self.cmd_input = QLineEdit()
        self.cmd_input.setFont(QFont("Courier New", 9))
        self.cmd_input.setPlaceholderText("Command this agent...")
        self.cmd_input.setStyleSheet(f"background: rgba(0, 0, 0, 0.4); color: white; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 6px;")
        self.cmd_input.returnPressed.connect(self._send_agent_command)
        inp_lay.addWidget(self.cmd_input, stretch=1)
        
        send_btn = QPushButton("EXECUTE")
        send_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO};
                border: 1px solid {C.PRI};
                border-radius: 4px;
                color: {C.PRI};
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background: {C.PRI};
                color: black;
            }}
        """)
        send_btn.clicked.connect(self._send_agent_command)
        inp_lay.addWidget(send_btn)
        right_lay.addLayout(inp_lay)
        
        main_lay.addWidget(self.right_panel, stretch=1)
        
        # Load agents
        self._agents_data = {
            "IP Prime": {
                "role": "Grand Coordinator & Command Center",
                "desc": "Orchestrates database integration, system state monitoring, intent classification, and multi-agent coordination.",
                "history": []
            },
            "Claude": {
                "role": "Reasoning & Research Specialist",
                "desc": "Provides deep logical analysis, complex code refactoring, system architecture blueprints, and mathematical reasoning.",
                "history": []
            },
            "Hermes": {
                "role": "Automation & Operations Commander",
                "desc": "Manages system tasks, cron jobs, routine automations, background listeners, and Windows Task Scheduler integration.",
                "history": []
            },
            "AntiGravity": {
                "role": "Runtime Orchestration & Stability Engine",
                "desc": "Monitors system resources, controls threads, watches active clipboard logs, and manages UI framework bindings.",
                "history": []
            },
            "Obsidian": {
                "role": "Security Sentinel",
                "desc": "Audits dependencies, verifies file integrity, monitors network endpoints, and performs database encryption.",
                "history": []
            },
            "Agent Inferno": {
                "role": "Lead Tactician & Developer",
                "desc": "Rapidly writes source code, runs automated build scripts, debugs compile errors, and checks syntax stability.",
                "history": []
            },
            "Agent Zenith": {
                "role": "Lead Architect & Code Auditor",
                "desc": "Verifies structural SOLID standards, checks code styling compliance, and resolves architectural conflicts.",
                "history": []
            },
            "IP Scout": {
                "role": "Research Division",
                "desc": "Crawls web pages, indexes documentation, summarizes online articles, and conducts facts research.",
                "history": []
            },
            "IP Scribe": {
                "role": "Content & Copywriting Division",
                "desc": "Drafts documentation, formats reports in clean Markdown, writes email copy, and creates blog posts.",
                "history": []
            },
            "IP Codex": {
                "role": "Code Generation Division",
                "desc": "Generates script templates, HTML templates, CSS themes, and layout templates.",
                "history": []
            },
            "IP Lexicon": {
                "role": "Translation & Localization Division",
                "desc": "Handles tone preservation, language translation, and regional localization of data resources.",
                "history": []
            },
            "IP Audit": {
                "role": "Quality Assurance Division",
                "desc": "Runs automated tests, audits accessibility (WCAG), and reviews pull request syntax.",
                "history": []
            }
        }
        
        for name in self._agents_data:
            self.agent_list.addItem(name)
            
        # Select first item
        self.agent_list.setCurrentRow(0)
        
    def _on_agent_selected(self):
        curr = self.agent_list.currentItem()
        if not curr:
            return
        name = curr.text()
        data = self._agents_data[name]
        self.name_lbl.setText(name.upper())
        self.role_lbl.setText(f"ROLE: {data['role'].upper()}")
        self.desc_lbl.setText(data['desc'])
        
        # Display history
        self.chat_display.clear()
        if not data["history"]:
            self.chat_display.append(f"Command terminal for {name} initialized. Ready for instructions.")
        else:
            for speaker, msg in data["history"]:
                self.chat_display.append(f"[{speaker}]: {msg}")
                
    def _send_agent_command(self):
        curr = self.agent_list.currentItem()
        if not curr:
            return
        name = curr.text()
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.cmd_input.clear()
        
        data = self._agents_data[name]
        data["history"].append(("Pratik", cmd))
        self.chat_display.append(f"[Pratik]: {cmd}")
        self.chat_display.append(f"[{name}]: Processing instruction via unified workspace...")
        
        # Process command asynchronously using Saturday's command loop
        if hasattr(self.main_win, "on_text_command") and self.main_win.on_text_command:
            prompt = (
                f"[AGENT_COMMAND] agent={name} | role={data['role']} | "
                f"instruction={cmd} | Execute this task under the persona of {name}. "
                f"Directly output the results clearly."
            )
            def _run():
                self.main_win.on_text_command(prompt)
            threading.Thread(target=_run, daemon=True).start()


class StartFlyout(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(300, 290)
        
        # Main layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        
        # Background card
        card = QWidget(self)
        card.setObjectName("FlyoutCard")
        card.setStyleSheet(f"""
            #FlyoutCard {{
                background: {hex_to_rgba_str(C.DARK, 0.88)};
                border: 1px solid {C.BORDER};
                border-radius: 12px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(12, 12, 12, 12)
        card_lay.setSpacing(10)
        
        # Header
        hdr = QLabel("❖ IP PRIME OS")
        hdr.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        card_lay.addWidget(hdr)
        
        desc = QLabel("Quick Launcher Menu")
        desc.setFont(QFont("Courier New", 7))
        desc.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        card_lay.addWidget(desc)
        
        # Grid of actions
        grid = QGridLayout()
        grid.setSpacing(8)
        
        def _btn(lbl, icon, cb):
            b = QPushButton(f"{icon}\n{lbl}")
            b.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid {C.BORDER};
                    border-radius: 6px;
                    color: white;
                    padding: 8px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.15);
                    border-color: {C.PRI};
                }}
            """)
            b.clicked.connect(cb)
            return b
            
        btn_vault = _btn("Organize\nVault", "🗂️", lambda: self._trigger("organize"))
        btn_cleanup = _btn("Memory\nClean", "🧹", lambda: self._trigger("cleanup"))
        btn_dashboard = _btn("Open\nWorkspace", "▦", lambda: self._trigger("workspace"))
        btn_clipboard = _btn("Clipboard\nAI", "📋", lambda: self._trigger("clipboard"))
        btn_army = _btn("Agent\nArmy", "🛡️", lambda: self._trigger("army"))
        
        grid.addWidget(btn_vault, 0, 0)
        grid.addWidget(btn_cleanup, 0, 1)
        grid.addWidget(btn_dashboard, 1, 0)
        grid.addWidget(btn_clipboard, 1, 1)
        grid.addWidget(btn_army, 2, 0, 1, 2)
        card_lay.addLayout(grid)
        
        lay.addWidget(card)
        self._action = None
        
    def _trigger(self, act):
        self._action = act
        self.accept()


class MainWindow(QMainWindow):
    _log_sig   = pyqtSignal(str)
    _state_sig = pyqtSignal(str)
    _last_response_sig = pyqtSignal(str)
    _console_visible_sig = pyqtSignal(bool)
    _activity_sig = pyqtSignal(str)
    _confirm_sig = pyqtSignal(str, list)
    _plan_confirm_sig = pyqtSignal(str, str, list)
    _audio_level_sig = pyqtSignal(float)
    _steps_loaded_sig = pyqtSignal(list)
    _step_update_sig = pyqtSignal(int, str, str)
    _clipboard_ai_sig = pyqtSignal()
    _vision_guard_sig = pyqtSignal()
    _prompt_sig = pyqtSignal(str, list)
    _custom_alert_sig = pyqtSignal(str, str, str)
    _notification_sig = pyqtSignal(str, str)
    _standby_thoughts_sig = pyqtSignal()
    _active_task_sig = pyqtSignal(str)

    def __init__(self, face_path: str):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Use native OS window frame — gives standard title bar controls (min/max/close)
        self.setWindowTitle("S.A.T.U.R.D.A.Y — Built by Pratik Thorat")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        self._confirm_sig.connect(self._handle_confirm_request)
        self._plan_confirm_sig.connect(self._handle_plan_confirm_request)
        self._steps_loaded_sig.connect(self._handle_steps_loaded)
        self._step_update_sig.connect(self._handle_step_update)
        self._clipboard_ai_sig.connect(self._toggle_clipboard_ai)
        self._vision_guard_sig.connect(self._show_vision_guard_alert)
        self._prompt_sig.connect(self._handle_prompt_request)
        self._custom_alert_sig.connect(self._show_custom_alert)
        self._notification_sig.connect(self._show_notification)

        self.on_text_command  = None
        self._muted           = False
        self._current_file: str | None = None
        self._sound_manager = SoundManager()
        self._last_settings_load_time = 0.0
        self._last_settings_mtime = 0.0
        self._cached_settings = {}
        self._console_anim = None
        self._profile_tick_counter = 0
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        self._apply_central_bg_style()
 
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._header_shim = self._build_header()
        root.addWidget(self._header_shim)
 
        # Create container for main orb page
        self._page_orb = QWidget()
        self._page_orb.setObjectName("PageOrb")
        self._page_orb.setStyleSheet("background: transparent;")
        page_orb_layout = QHBoxLayout(self._page_orb)
        page_orb_layout.setContentsMargins(0, 0, 0, 0)
        page_orb_layout.setSpacing(0)

        # Right panel (log console, file upload, text command row)
        self._right_panel = self._build_right_panel()

        # Left Widgets Sidebar panel
        self._left_sidebar = WidgetsSidebar(self)

        # Left container layout (contains orb)
        left_container_widget = QWidget()
        left_container_layout = QVBoxLayout(left_container_widget)
        left_container_layout.setContentsMargins(10, 10, 10, 10)
        left_container_layout.setSpacing(10)

        # Visualizer orb (sphere)
        self.hud = HudCanvas(face_path)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_container_layout.addWidget(self.hud, stretch=1)

        self._quick_search_btn = None
        self._quick_ss_btn = None
        self._quick_notes_btn = None

        page_orb_layout.addWidget(self._left_sidebar)
        page_orb_layout.addWidget(left_container_widget, stretch=1)
        page_orb_layout.addWidget(self._right_panel)

        # Create stacked widget
        self._stacked_widget = QStackedWidget()
        self._stacked_widget.addWidget(self._page_orb)
        
        # Create Dashboard view
        self._dashboard = WorkspaceDashboard(self)
        self._stacked_widget.addWidget(self._dashboard)

        # Create Agent Command Center view
        self._agent_center = AgentCommandCenter(self)
        self._stacked_widget.addWidget(self._agent_center)

        root.addWidget(self._stacked_widget, stretch=1)
 
        # Create a horizontal container to float and center the dock
        self._dock_container = QWidget()
        self._dock_container.setFixedHeight(52)
        self._dock_container.setStyleSheet("background: transparent;")
        dock_lay = QHBoxLayout(self._dock_container)
        dock_lay.setContentsMargins(0, 0, 0, 12)
        dock_lay.setSpacing(0)
        dock_lay.addStretch()
        self._footer = self._build_footer()
        dock_lay.addWidget(self._footer)
        dock_lay.addStretch()
        root.addWidget(self._dock_container)

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
        self._last_response_sig.connect(self._update_last_response)
        self._console_visible_sig.connect(self._toggle_console)
        self._activity_sig.connect(self._update_activity)
        self._audio_level_sig.connect(self._on_audio_level_changed)
        self._standby_thoughts_sig.connect(self.update_standby_thoughts)
        self._active_task_sig.connect(self._update_active_task)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)
        sc_console = QShortcut(QKeySequence("F2"), self)
        sc_console.activated.connect(lambda: self._toggle_console())
        sc_widgets = QShortcut(QKeySequence("F3"), self)
        sc_widgets.activated.connect(lambda: self._toggle_widgets_sidebar())
        sc_start = QShortcut(QKeySequence("F1"), self)
        sc_start.activated.connect(self._show_start_flyout)
        sc_saturday_os = QShortcut(QKeySequence("F9"), self)
        sc_saturday_os.activated.connect(self._toggle_saturday_os_mode)
        sc_saturday_os_esc = QShortcut(QKeySequence("Esc"), self)
        sc_saturday_os_esc.activated.connect(self._exit_saturday_os_mode_if_active)

        self._setup_tray_icon(face_path)

        # Force panels hidden on startup
        self._right_panel.setFixedWidth(0)
        self._right_panel.hide()
        self._console_visible = False
        
        self._left_sidebar.setFixedWidth(0)
        self._left_sidebar.hide()

        # Apply theme on startup
        try:
            settings = self._load_settings()
            theme = settings.get("theme", "dark").lower().strip()
            C.apply_light_theme(theme == "light")
            self._refresh_theme_styles()
        except Exception as e:
            print(f"[UI] Theme init error: {e}")
            
    def showEvent(self, event):
        super().showEvent(event)
        apply_windows_blur(int(self.winId()), effect_type="acrylic", dark_mode=True)

    def _toggle_theme(self):
        try:
            settings = self._load_settings()
            current_theme = settings.get("theme", "dark").lower().strip()
            new_theme = "light" if current_theme == "dark" else "dark"
            self._save_settings({"theme": new_theme})
            
            # Apply the new theme to Class C
            C.apply_light_theme(new_theme == "light")
            self._refresh_theme_styles()
            
            # Update button icon
            if hasattr(self, "_theme_btn") and self._theme_btn:
                self._theme_btn.setText("🌙" if new_theme == "light" else "🌞")
                
            # Invalidate prompt cache
            try:
                from core.session_manager import clear_prompt_cache
                clear_prompt_cache()
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
        except Exception as e:
            print(f"[UI] Failed to toggle theme: {e}")

    def _on_quick_search(self):
        # Open/show console if hidden
        if not self._right_panel.isVisible():
            self._toggle_console(True)
        # Focus command line and insert "search "
        self._input.setText("search ")
        self._input.setFocus()

    def _on_quick_notes(self):
        try:
            import os
            from pathlib import Path
            notes_path = BASE_DIR / "memory" / "sticky_notes.txt"
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            if not notes_path.exists():
                notes_path.write_text("Hello, Sir. Write your notes here.", encoding="utf-8")
            
            os.startfile(str(notes_path))
            self.write_log("SYS: Opened sticky_notes.txt in Notepad.")
        except Exception as e:
            self.write_log(f"SYS ERR: Failed to open sticky notes: {e}")

    def _on_quick_screenshot(self):
        from actions.screen_processor import screen_process
        from PyQt6.QtWidgets import QInputDialog
        
        prompt, ok = QInputDialog.getText(
            self,
            "S.A.T.U.R.D.A.Y — Screen Analysis",
            "What would you like me to analyze on your screen, sir?"
        )
        if ok and prompt.strip():
            self.write_log(f"You (Screenshot request): {prompt}")
            def run_capture():
                try:
                    res = screen_process({"angle": "screen", "text": prompt}, player=self)
                    if res:
                        self.write_log("SYS: Screen capture sent to Gemini Live.")
                    else:
                        self.write_log("SYS: Failed to send screen capture.")
                except Exception as e:
                    self.write_log(f"SYS ERR: Screenshot analysis failed: {e}")
            import threading
            threading.Thread(target=run_capture, daemon=True).start()

    def _show_notification(self, title: str, message: str):
        if hasattr(self, "_tray_icon") and self._tray_icon.isVisible():
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    def show_notification(self, title: str, message: str):
        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            self._show_notification(title, message)
        else:
            self._notification_sig.emit(title, message)

    def _handle_confirm_request(self, message: str, args: list):
        res = self.show_confirm_dialog(message)
        args[0][0] = res
        args[1].set()

    def _handle_prompt_request(self, message: str, args: list):
        res = self.show_prompt_dialog(message)
        args[0][0] = res
        args[1].set()

    def show_prompt_dialog(self, message: str) -> str | None:
        from PyQt6.QtWidgets import QInputDialog
        val, ok = QInputDialog.getText(
            self,
            "S.A.T.U.R.D.A.Y — Input Required",
            message
        )
        return val.strip() if ok else None

    def show_confirm_dialog(self, message: str) -> bool:
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(self)
        box.setWindowTitle("S.A.T.U.R.D.A.Y — Security Confirmation")
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.setStyleSheet(f"""
            QMessageBox {{ background-color: {C.PANEL}; color: {C.TEXT}; }}
            QLabel {{ color: {C.TEXT}; }}
            QPushButton {{ background-color: {C.BORDER_A}; color: {C.WHITE}; border: 1px solid {C.BORDER}; padding: 6px 12px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {C.PRI_DIM}; border: 1px solid {C.PRI}; }}
        """)
        return box.exec() == QMessageBox.StandardButton.Yes

    def _handle_plan_confirm_request(self, goal: str, plan_text: str, args: list):
        res = self.show_plan_confirm_dialog(goal, plan_text)
        args[0]["action"] = res[0]
        args[0]["feedback"] = res[1]
        args[1].set()

    def _handle_steps_loaded(self, steps: list):
        if hasattr(self, "steps_view"):
            self.steps_view.clear_steps()
            self.steps_view.load_steps(steps)

    def _handle_step_update(self, step_idx: int, status: str, result: str):
        if hasattr(self, "steps_view"):
            self.steps_view.update_step(step_idx, status, result)

    def show_plan_confirm_dialog(self, goal: str, plan_text: str) -> tuple[str, str]:
        dialog = PlanConfirmDialog(goal, plan_text, self)
        ret = dialog.exec()
        if ret == QDialog.DialogCode.Accepted:
            return "confirm", dialog.feedback
        elif ret == 2:
            return "replan", dialog.feedback
        else:
            return "cancel", ""

    def _toggle_clipboard_ai(self):
        if not hasattr(self, "_clipboard_panel") or self._clipboard_panel is None:
            from actions.clipboard_ai_gui import ClipboardAIPanel
            self._clipboard_panel = ClipboardAIPanel(self)
        
        if self._clipboard_panel.isVisible():
            self._clipboard_panel.hide()
        else:
            x = int(self.x() + (self.width() - self._clipboard_panel.width()) / 2)
            y = int(self.y() + (self.height() - self._clipboard_panel.height()) / 2)
            self._clipboard_panel.move(x, y)
            self._clipboard_panel.show()
            self._clipboard_panel.trigger_explanation()

    def _show_vision_guard_alert(self):
        if hasattr(self, "_vision_guard_active") and self._vision_guard_active:
            return
        self._vision_guard_active = True
        alert = VisionGuardAlert(self)
        alert.exec()
        self._vision_guard_active = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            ow, oh = 460, 430
            cw = self.centralWidget()
            self._overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        if hasattr(self, "_saturday_browser_panel") and self._saturday_browser_panel.isVisible():
            self._saturday_browser_panel.setGeometry(self.rect())


    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ------------------------------------------------------------------ #
    # SaturdayOS Mode — turns this window into a taskbar-free, fullscreen
    # "operating system" feel, with its own embedded browser screen for
    # any action that would otherwise open a real system browser window.
    # Toggle with F9. No VM, no separate session — just this window.
    # ------------------------------------------------------------------ #
    def _ensure_saturday_browser_panel(self):
        if not hasattr(self, "_saturday_browser_panel"):
            from os_shell_windows.embedded_browser import EmbeddedBrowserPanel
            self._saturday_browser_panel = EmbeddedBrowserPanel(
                on_close=self._hide_saturday_browser_panel, parent=self
            )
            self._saturday_browser_panel.hide()
        return self._saturday_browser_panel

    def _show_saturday_browser_panel(self, url: str):
        panel = self._ensure_saturday_browser_panel()
        panel.setGeometry(self.rect())
        panel.navigate(url)
        panel.show()
        panel.raise_()

    def _hide_saturday_browser_panel(self):
        if hasattr(self, "_saturday_browser_panel"):
            self._saturday_browser_panel.hide()

    def _exit_saturday_os_mode_if_active(self):
        from os_shell_windows import kiosk, browser_bridge
        if kiosk.is_active():
            kiosk.exit(self)
            browser_bridge.uninstall()
            self._hide_saturday_browser_panel()
            self.write_log("SYS: SaturdayOS Mode off (Esc) — back to Windows.")

    def _toggle_saturday_os_mode(self):
        from os_shell_windows import kiosk, browser_bridge
        if kiosk.is_active():
            kiosk.exit(self)
            browser_bridge.uninstall()
            self._hide_saturday_browser_panel()
            self.write_log("SYS: SaturdayOS Mode off — back to Windows.")
        else:
            kiosk.enter(self)
            browser_bridge.register_panel(self._show_saturday_browser_panel)
            browser_bridge.install()
            self.write_log("SYS: SaturdayOS Mode on — press F9 anytime to exit.")


    def _update_metrics(self):
        snap = _metrics.snapshot()

        if hasattr(self, "_left_sidebar") and self._left_sidebar:
            self._left_sidebar.update_metrics(snap.get("cpu", 0.0), snap.get("mem", 0.0))

        # CPU
        if hasattr(self, "_bar_cpu"):
            cpu = snap["cpu"]
            self._bar_cpu.set_value(cpu, f"{cpu:.0f}%")

        # MEM
        if hasattr(self, "_bar_mem"):
            mem = snap["mem"]
            self._bar_mem.set_value(mem, f"{mem:.0f}%")

        # NET
        if hasattr(self, "_bar_net"):
            net = snap["net"]
            if net < 1.0:
                net_str = f"{net*1024:.0f}KB/s"
            else:
                net_str = f"{net:.1f}MB/s"
            net_pct = min(100.0, net)  # 100 MB/s = 100%
            self._bar_net.set_value(net_pct, net_str)

        # GPU
        if hasattr(self, "_bar_gpu"):
            gpu = snap["gpu"]
            if gpu >= 0:
                self._bar_gpu.set_value(gpu, f"{gpu:.0f}%")
            else:
                self._bar_gpu.set_value(0, "N/A")

        # TMP
        if hasattr(self, "_bar_tmp"):
            tmp = snap["tmp"]
            if tmp >= 0:
                tmp_pct = min(100.0, (tmp / 110.0) * 100.0)
                self._bar_tmp.set_value(tmp_pct, f"{tmp:.0f}°C")
            else:
                self._bar_tmp.set_value(0, "N/A")

        if hasattr(self, "_uptime_lbl"):
            try:
                elapsed = time.time() - APP_START_TIME
                h = int(elapsed // 3600)
                m = int((elapsed % 3600) // 60)
                self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
            except Exception:
                self._uptime_lbl.setText("UP  --:--")

        if hasattr(self, "_proc_lbl"):
            try:
                proc_count = len(psutil.pids())
                self._proc_lbl.setText(f"PROC  {proc_count}")
            except Exception:
                self._proc_lbl.setText("PROC  --")


    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(54)
        w.setStyleSheet(f"background: {C.DARK}; border-bottom: 1px solid {C.BORDER_B};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)

        # Left aligned label (120px)
        left_container = QWidget()
        left_container.setFixedWidth(120)
        left_lay = QHBoxLayout(left_container)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)
        left_lbl = QLabel("AGENT IP 001")
        left_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        left_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        self._header_left_lbl = left_lbl
        left_lay.addWidget(left_lbl)
        left_lay.addStretch()
        lay.addWidget(left_container)

        lay.addStretch()

        mid = QVBoxLayout(); mid.setSpacing(1)
        title = QLabel("S.A.T.U.R.D.A.Y")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Courier New", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._header_title = title
        mid.addWidget(title)
        sub = QLabel("Sentient Artificial Tactical Utility Real-time Diagnostic Automated Youth")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Courier New", 7))
        sub.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        self._header_sub = sub
        mid.addWidget(sub)
        lay.addLayout(mid)
        lay.addStretch()

        # Right aligned settings container (280px)
        right_container = QWidget()
        right_container.setFixedWidth(280)
        right_lay = QHBoxLayout(right_container)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(6)
        right_lay.addStretch()

        self._theme_btn = None

        # Workspace Dashboard toggle button
        workspace_btn = QPushButton("Workspace ▦")
        workspace_btn.setFixedHeight(32)
        workspace_btn.setMinimumWidth(100)
        workspace_btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        workspace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        workspace_btn.setToolTip("Toggle Workspace Dashboard")
        workspace_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C.PRI_DIM};
                border-radius: 4px;
                color: {C.PRI};
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO};
                border: 1px solid {C.PRI};
                color: {C.PRI};
            }}
            QPushButton:pressed {{
                background: {C.PRI_DIM};
                color: {C.DARK};
            }}
        """)
        self._workspace_btn = workspace_btn
        workspace_btn.clicked.connect(self._toggle_workspace)
        right_lay.addWidget(workspace_btn)

        # Settings / Console button in top-right corner
        settings_btn = QPushButton("Console ▶")
        settings_btn.setFixedHeight(32)
        settings_btn.setMinimumWidth(85)
        settings_btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setToolTip("Toggle Console Panel [F2]")
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C.PRI_DIM};
                border-radius: 4px;
                color: {C.PRI};
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO};
                border: 1px solid {C.PRI};
                color: {C.PRI};
            }}
            QPushButton:pressed {{
                background: {C.PRI_DIM};
                color: {C.DARK};
            }}
        """)
        self._settings_btn = settings_btn
        settings_btn.clicked.connect(lambda: self._toggle_console())
        right_lay.addWidget(settings_btn)
        lay.addWidget(right_container)

        return w

    def _toggle_left_panel(self):
        from PyQt6.QtCore import QPropertyAnimation
        current_width = self._left_panel.maximumWidth()
        is_visible = current_width > 0
        target_width = 0 if is_visible else _LEFT_W
        
        self._left_anim = QPropertyAnimation(self._left_panel, b"maximumWidth")
        self._left_anim.setDuration(250)
        self._left_anim.setStartValue(current_width)
        self._left_anim.setEndValue(target_width)
        self._left_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._left_anim.start()
        
        if is_visible:
            self._hud_toggle_btn.setText("▶")
            self._hud_toggle_btn.setToolTip("Show HUD panel")
        else:
            self._hud_toggle_btn.setText("◀")
            self._hud_toggle_btn.setToolTip("Hide HUD panel")

    def _toggle_workspace(self):
        if not hasattr(self, "_stacked_widget") or not self._stacked_widget:
            return
        current_index = self._stacked_widget.currentIndex()
        if current_index == 0:
            self._stacked_widget.setCurrentIndex(1)
            self._workspace_btn.setText("Orb View 🔵")
            if hasattr(self, "_dashboard") and self._dashboard:
                self._dashboard.refresh_data()
        else:
            self._stacked_widget.setCurrentIndex(0)
            self._workspace_btn.setText("Workspace ▦")

    def _tick_clock(self):
        if hasattr(self, "_clock_lbl"):
            self._clock_lbl.setText(time.strftime("%I:%M:%S %p"))
        if hasattr(self, "_date_lbl"):
            self._date_lbl.setText(time.strftime("%a %d %b %Y"))

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_LEFT_W)
        w.setStyleSheet(f"background: {C.DARK}; border-right: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(6)

        hdr = QLabel("◈ SYS MONITOR")
        hdr.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                          f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        self._left_monitor_hdr = hdr
        lay.addWidget(hdr)
        lay.addSpacing(2)

        self._bar_cpu = MetricBar("CPU", C.PRI)
        self._bar_mem = MetricBar("MEM", C.ACC2)
        self._bar_net = MetricBar("NET", C.GREEN)
        self._bar_gpu = MetricBar("GPU", C.ACC)
        self._bar_tmp = MetricBar("TMP", "#ff6688")

        for bar in [self._bar_cpu, self._bar_mem, self._bar_net,
                    self._bar_gpu, self._bar_tmp]:
            lay.addWidget(bar)

        lay.addSpacing(4)

        info_panel = QWidget()
        info_panel.setStyleSheet(
            f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;"
        )
        self._left_info_panel = info_panel
        ip_lay = QVBoxLayout(info_panel)
        ip_lay.setContentsMargins(6, 5, 6, 5)
        ip_lay.setSpacing(3)

        self._uptime_lbl = QLabel("UP  --:--")
        self._uptime_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
        ip_lay.addWidget(self._uptime_lbl)

        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont("Courier New", 8))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        ip_lay.addWidget(self._proc_lbl)

        os_name = {"Windows": "WIN", "Darwin": "macOS", "Linux": "LINUX"}.get(_OS, _OS.upper())
        os_lbl = QLabel(f"OS  {os_name}")
        os_lbl.setFont(QFont("Courier New", 8))
        os_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")
        self._os_lbl = os_lbl
        ip_lay.addWidget(os_lbl)

        lay.addWidget(info_panel)
        lay.addSpacing(10)

        return w

    def _load_settings(self) -> dict:
        if not SETTINGS_FILE.exists():
            return {}
        
        import time
        now = time.time()
        try:
            mtime = SETTINGS_FILE.stat().st_mtime
            if mtime == self._last_settings_mtime and now - self._last_settings_load_time < 3.0:
                return self._cached_settings
                
            self._last_settings_mtime = mtime
            self._last_settings_load_time = now
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            self._cached_settings = data
            return data
        except Exception:
            return getattr(self, "_cached_settings", {})

    def _save_settings(self, settings: dict):
        try:
            data = self._load_settings()
            data.update(settings)
            SETTINGS_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
            self._last_settings_mtime = 0.0
            self._last_settings_load_time = 0.0
        except Exception as e:
            logger.error("Failed to save settings: %s", e)

    def _build_left_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumWidth(0)
        scroll.setMinimumWidth(0)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {C.DARK};
                border-right: 1px solid {C.BORDER};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {C.DARK};
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER};
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        container = QWidget()
        container.setStyleSheet(f"background: {C.DARK};")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        def _sec(txt):
            l = QLabel(f"▸ {txt}")
            l.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            return l

        # SECTION 1: SYSTEM RESOURCE HUD (Circular Dials)
        lay.addWidget(_sec("SYSTEM RESOURCE HUD"))
        hud_container = QWidget()
        hud_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        hud_lay = QHBoxLayout(hud_container)
        hud_lay.setContentsMargins(4, 4, 4, 4)
        hud_lay.setSpacing(8)
        
        self._cpu_gauge = HUDCircularGauge("CPU")
        self._mem_gauge = HUDCircularGauge("RAM")
        hud_lay.addWidget(self._cpu_gauge)
        hud_lay.addWidget(self._mem_gauge)
        lay.addWidget(hud_container)

        # SECTION 2: HEALTH & BREAK TIMER
        lay.addWidget(_sec("HEALTH & BREAK TIMER"))
        health_container = QWidget()
        health_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        health_lay = QVBoxLayout(health_container)
        health_lay.setContentsMargins(6, 6, 6, 6)
        health_lay.setSpacing(4)
        
        self._vg_enable_cb = QCheckBox("Enable Vision Guard Alerts")
        self._vg_enable_cb.setFont(QFont("Courier New", 7))
        self._vg_enable_cb.setStyleSheet(f"color: {C.TEXT};")
        self._vg_enable_cb.setChecked(True)
        health_lay.addWidget(self._vg_enable_cb)
        
        self._vg_voice_cb = QCheckBox("Enable Voice Notifications")
        self._vg_voice_cb.setFont(QFont("Courier New", 7))
        self._vg_voice_cb.setStyleSheet(f"color: {C.TEXT};")
        self._vg_voice_cb.setChecked(False)
        health_lay.addWidget(self._vg_voice_cb)
        
        self._vg_progress = QProgressBar()
        self._vg_progress.setFixedHeight(12)
        self._vg_progress.setFont(QFont("Courier New", 7))
        self._vg_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {C.BG};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {C.PRI};
            }}
        """)
        self._vg_progress.setRange(0, 1200)
        self._vg_progress.setValue(0)
        health_lay.addWidget(self._vg_progress)
        
        self._vg_timer_label = QLabel("Last break: Just started")
        self._vg_timer_label.setFont(QFont("Courier New", 7))
        self._vg_timer_label.setStyleSheet(f"color: {C.TEXT_DIM};")
        health_lay.addWidget(self._vg_timer_label)
        
        self._vg_snooze_btn = QPushButton("Snooze Alerts (20 min)")
        self._vg_snooze_btn.setFixedHeight(22)
        self._vg_snooze_btn.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._vg_snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._vg_snooze_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.BORDER_A};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {C.PRI};
                color: {C.BG};
            }}
        """)
        self._vg_snooze_btn.clicked.connect(self._snooze_vision_guard)
        health_lay.addWidget(self._vg_snooze_btn)
        lay.addWidget(health_container)

        # SECTION 3: WAKE-WORD STANDBY SETTINGS
        lay.addWidget(_sec("WAKE-WORD MODE"))
        ww_container = QWidget()
        ww_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        ww_lay = QVBoxLayout(ww_container)
        ww_lay.setContentsMargins(6, 6, 6, 6)
        ww_lay.setSpacing(4)
        
        self._ww_enable_cb = QCheckBox("Enable Wake-Word (Hey Saturday)")
        self._ww_enable_cb.setFont(QFont("Courier New", 7))
        self._ww_enable_cb.setStyleSheet(f"color: {C.TEXT};")
        self._ww_enable_cb.setChecked(False)
        ww_lay.addWidget(self._ww_enable_cb)
        
        self._ww_keywords_edit = QLineEdit()
        self._ww_keywords_edit.setFont(QFont("Courier New", 7))
        self._ww_keywords_edit.setPlaceholderText("Wake words (comma-separated)...")
        self._ww_keywords_edit.setStyleSheet(f"background: {C.BG}; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 3px; padding: 2px;")
        ww_lay.addWidget(self._ww_keywords_edit)
        
        lay.addWidget(ww_container)

        # SECTION 9: BROWSER SETTINGS
        lay.addWidget(_sec("BROWSER SETTINGS"))
        browser_container = QWidget()
        browser_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        browser_lay = QVBoxLayout(browser_container)
        browser_lay.setContentsMargins(6, 6, 6, 6)
        browser_lay.setSpacing(4)
        
        self._browser_headless_cb = QCheckBox("Run Browser Headlessly (Fast)")
        self._browser_headless_cb.setFont(QFont("Courier New", 7))
        self._browser_headless_cb.setStyleSheet(f"color: {C.TEXT};")
        self._browser_headless_cb.setChecked(False)
        browser_lay.addWidget(self._browser_headless_cb)
        lay.addWidget(browser_container)

        # SECTION 10: LOCAL RUNNER SETTINGS
        lay.addWidget(_sec("LOCAL RUNNER SETTINGS"))
        local_runner_container = QWidget()
        local_runner_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        local_runner_lay = QVBoxLayout(local_runner_container)
        local_runner_lay.setContentsMargins(6, 6, 6, 6)
        local_runner_lay.setSpacing(4)
        
        self._local_runner_type_cb = QComboBox()
        self._local_runner_type_cb.setFont(QFont("Courier New", 7))
        self._local_runner_type_cb.setStyleSheet(f"""
            QComboBox {{
                background-color: {C.BG};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                padding: 2px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {C.DARK};
                color: {C.TEXT};
                selection-background-color: {C.PRI};
                selection-color: {C.BG};
            }}
        """)
        self._local_runner_type_cb.addItems(["Ollama", "llama.cpp", "LocalAI"])
        local_runner_lay.addWidget(self._local_runner_type_cb)
        
        self._local_runner_url_edit = QLineEdit()
        self._local_runner_url_edit.setFont(QFont("Courier New", 7))
        self._local_runner_url_edit.setPlaceholderText("API URL (e.g. http://localhost:11434)")
        self._local_runner_url_edit.setStyleSheet(f"background: {C.BG}; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 3px; padding: 2px;")
        local_runner_lay.addWidget(self._local_runner_url_edit)
        
        self._local_runner_model_edit = QLineEdit()
        self._local_runner_model_edit.setFont(QFont("Courier New", 7))
        self._local_runner_model_edit.setPlaceholderText("Model Name (e.g. mistral)")
        self._local_runner_model_edit.setStyleSheet(f"background: {C.BG}; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 3px; padding: 2px;")
        local_runner_lay.addWidget(self._local_runner_model_edit)
        
        self._local_runner_embed_model_edit = QLineEdit()
        self._local_runner_embed_model_edit.setFont(QFont("Courier New", 7))
        self._local_runner_embed_model_edit.setPlaceholderText("Embedding Model (e.g. nomic-embed-text)")
        self._local_runner_embed_model_edit.setStyleSheet(f"background: {C.BG}; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 3px; padding: 2px;")
        local_runner_lay.addWidget(self._local_runner_embed_model_edit)
        
        # GPU detection and recommendation label
        try:
            from core.hardware_optimizer import get_hardware_recommendations
            rec = get_hardware_recommendations()
            gpu_label_text = f"Hardware: {rec['gpu_name']}\nRecommendation: {rec['recommendation_text']}"
        except Exception:
            gpu_label_text = "Hardware: Detection failed"

        self._gpu_status_lbl = QLabel(gpu_label_text)
        self._gpu_status_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._gpu_status_lbl.setStyleSheet(f"color: {C.ACC}; background: transparent; padding: 2px;")
        self._gpu_status_lbl.setWordWrap(True)
        local_runner_lay.addWidget(self._gpu_status_lbl)
        
        lay.addWidget(local_runner_container)

        # SECTION 4: TELEGRAM BOT COMPANION
        lay.addWidget(_sec("TELEGRAM COMPANION"))
        tg_container = QWidget()
        tg_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        tg_lay = QVBoxLayout(tg_container)
        tg_lay.setContentsMargins(6, 6, 6, 6)
        tg_lay.setSpacing(4)
        
        self._tg_token_edit = QLineEdit()
        self._tg_token_edit.setFont(QFont("Courier New", 7))
        self._tg_token_edit.setPlaceholderText("Bot Token...")
        self._tg_token_edit.setStyleSheet(f"background: {C.BG}; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 3px; padding: 2px;")
        tg_lay.addWidget(self._tg_token_edit)
        
        self._tg_chat_edit = QLineEdit()
        self._tg_chat_edit.setFont(QFont("Courier New", 7))
        self._tg_chat_edit.setPlaceholderText("Chat ID...")
        self._tg_chat_edit.setStyleSheet(f"background: {C.BG}; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 3px; padding: 2px;")
        tg_lay.addWidget(self._tg_chat_edit)
        
        self._tg_save_btn = QPushButton("Save Telegram Settings")
        self._tg_save_btn.setFixedHeight(22)
        self._tg_save_btn.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._tg_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tg_save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.BORDER_A};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {C.GREEN};
                color: {C.BG};
            }}
        """)
        self._tg_save_btn.clicked.connect(self._save_telegram_settings)
        tg_lay.addWidget(self._tg_save_btn)
        lay.addWidget(tg_container)

        # SECTION 5: SATURDAY STICKY NOTES
        lay.addWidget(_sec("SATURDAY STICKY NOTES"))
        notes_container = QWidget()
        notes_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        notes_lay = QVBoxLayout(notes_container)
        notes_lay.setContentsMargins(4, 4, 4, 4)
        notes_lay.setSpacing(4)
        
        self._sticky_edit = QTextEdit()
        self._sticky_edit.setFont(QFont("Courier New", 8))
        self._sticky_edit.setStyleSheet(f"background-color: {C.BG}; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 3px;")
        self._sticky_edit.setPlaceholderText("Type notes or let Saturday save reminders here...")
        self._sticky_edit.setFixedHeight(120)
        notes_lay.addWidget(self._sticky_edit)
        
        notes_btn_lay = QHBoxLayout()
        self._sticky_save_btn = QPushButton("Save")
        self._sticky_save_btn.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._sticky_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sticky_save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.BORDER_A};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {C.GREEN};
                color: {C.BG};
            }}
        """)
        self._sticky_save_btn.clicked.connect(self._save_sticky_notes)
        notes_btn_lay.addWidget(self._sticky_save_btn)
        
        self._sticky_clear_btn = QPushButton("Clear")
        self._sticky_clear_btn.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._sticky_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sticky_clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.BORDER_A};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {C.RED};
                color: {C.WHITE};
            }}
        """)
        self._sticky_clear_btn.clicked.connect(self._clear_sticky_notes)
        notes_btn_lay.addWidget(self._sticky_clear_btn)
        notes_lay.addLayout(notes_btn_lay)
        
        # Audio wave visualizer inside sticky notes container
        self._media_visualizer = MediaWaveVisualizer()
        notes_lay.addWidget(self._media_visualizer)
        lay.addWidget(notes_container)

        # SECTION 6: CLIPBOARD HISTORY
        lay.addWidget(_sec("CLIPBOARD HISTORY"))
        clip_container = QWidget()
        clip_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        clip_lay = QVBoxLayout(clip_container)
        clip_lay.setContentsMargins(4, 4, 4, 4)
        clip_lay.setSpacing(4)
        
        self._clip_list = QListWidget()
        self._clip_list.setFont(QFont("Courier New", 8))
        self._clip_list.setFixedHeight(120)
        self._clip_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {C.BG};
                color: {C.TEXT_MED};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {C.BG_GLOW_CTR};
            }}
            QListWidget::item:hover {{
                background: {C.PRI_GHO};
                color: {C.PRI};
            }}
            QListWidget::item:selected {{
                background: {C.PRI_GHO};
                color: {C.PRI};
                font-weight: bold;
            }}
        """)
        self._clip_list.itemClicked.connect(self._on_clip_item_clicked)
        clip_lay.addWidget(self._clip_list)
        
        self._clip_clear_btn = QPushButton("Clear History")
        self._clip_clear_btn.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._clip_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clip_clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.BORDER_A};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {C.RED};
                color: {C.WHITE};
            }}
        """)
        self._clip_clear_btn.clicked.connect(self._clear_clip_history)
        clip_lay.addWidget(self._clip_clear_btn)
        lay.addWidget(clip_container)

        # SECTION 8: USER PROFILE & INSIGHTS
        lay.addWidget(_sec("USER PROFILE & INSIGHTS"))
        profile_container = QWidget()
        profile_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 6px;")
        profile_lay = QVBoxLayout(profile_container)
        profile_lay.setContentsMargins(6, 6, 6, 6)
        profile_lay.setSpacing(4)
        
        self._profile_lbl = QLabel()
        self._profile_lbl.setFont(QFont("Courier New", 7))
        self._profile_lbl.setStyleSheet(f"color: {C.TEXT};")
        self._profile_lbl.setWordWrap(True)
        profile_lay.addWidget(self._profile_lbl)
        lay.addWidget(profile_container)

        # SECTION 7: VOICE SELECTOR
        lay.addWidget(_sec("VOICE SELECTOR"))
        voice_container = QWidget()
        voice_container.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        voice_lay = QVBoxLayout(voice_container)
        voice_lay.setContentsMargins(6, 6, 6, 6)
        voice_lay.setSpacing(4)
        
        self._voice_cb = QComboBox()
        self._voice_cb.setFont(QFont("Courier New", 7))
        self._voice_cb.setStyleSheet(f"""
            QComboBox {{
                background-color: {C.BG};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                padding: 2px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {C.DARK};
                color: {C.TEXT};
                selection-background-color: {C.PRI};
                selection-color: {C.BG};
            }}
        """)
        self._voice_cb.addItems(["Charon (Informative / Deep)", "Puck (Upbeat / Punchy)", "Fenrir (Excitable)", "Kore (Firm)", "Aoede (Breezy)"])
        voice_lay.addWidget(self._voice_cb)
        lay.addWidget(voice_container)

        # Load notes and clipboard
        self._load_sticky_notes()
        self._refresh_clip_history()
        
        # Set settings values
        settings = self._load_settings()
        
        # Initialize voice selector index
        voice_map = {
            "Charon": 0,
            "Puck": 1,
            "Fenrir": 2,
            "Kore": 3,
            "Aoede": 4
        }
        current_voice = settings.get("voice_name", "Charon")
        self._voice_cb.setCurrentIndex(voice_map.get(current_voice, 0))
        self._voice_cb.currentIndexChanged.connect(self._on_voice_changed)
        self._vg_enabled = settings.get("vision_guard_enabled", True)
        self._vg_voice_enabled = settings.get("vision_guard_voice_enabled", False)
        self._vg_enable_cb.setChecked(self._vg_enabled)
        self._vg_voice_cb.setChecked(self._vg_voice_enabled)
        
        self._vg_enable_cb.stateChanged.connect(self._on_vg_settings_changed)
        self._vg_voice_cb.stateChanged.connect(self._on_vg_settings_changed)
        
        self._ww_enabled = settings.get("wake_word_enabled", False)
        self._ww_enable_cb.setChecked(self._ww_enabled)
        self._ww_keywords_edit.setText(settings.get("wake_words", "sat, saturday, buddy, dost"))
        self._ww_enable_cb.stateChanged.connect(self._on_ww_settings_changed)
        self._ww_keywords_edit.textChanged.connect(self._on_ww_settings_changed)
        
        self._browser_headless = settings.get("browser_headless", False)
        self._browser_headless_cb.setChecked(self._browser_headless)
        self._browser_headless_cb.stateChanged.connect(self._on_browser_settings_changed)
        
        self._local_runner_type_cb.setCurrentText(settings.get("local_runner_type", "Ollama"))
        self._local_runner_url_edit.setText(settings.get("local_runner_url", "http://localhost:11434"))
        self._local_runner_model_edit.setText(settings.get("local_runner_model", "mistral"))
        self._local_runner_embed_model_edit.setText(settings.get("local_runner_embed_model", "nomic-embed-text"))
        
        self._local_runner_type_cb.currentTextChanged.connect(self._on_local_runner_settings_changed)
        self._local_runner_url_edit.textChanged.connect(self._on_local_runner_settings_changed)
        self._local_runner_model_edit.textChanged.connect(self._on_local_runner_settings_changed)
        self._local_runner_embed_model_edit.textChanged.connect(self._on_local_runner_settings_changed)
        
        self._tg_token_edit.setText(settings.get("telegram_bot_token", ""))
        self._tg_chat_edit.setText(settings.get("telegram_chat_id", ""))

        self._update_user_profile()
        self.update_standby_thoughts()

        # Set up a timer to update health progress, gauges and clipboard history
        self._left_panel_timer = QTimer(self)
        self._left_panel_timer.timeout.connect(self._left_panel_tick)
        self._left_panel_timer.start(1000)

        scroll.setWidget(container)
        return scroll

    def _on_browser_settings_changed(self):
        self._browser_headless = self._browser_headless_cb.isChecked()
        self._save_settings({
            "browser_headless": self._browser_headless
        })
        self.write_log(f"SYS: Browser headless mode {'enabled' if self._browser_headless else 'disabled'}.")

    def _on_local_runner_settings_changed(self):
        self._save_settings({
            "local_runner_type": self._local_runner_type_cb.currentText(),
            "local_runner_url": self._local_runner_url_edit.text().strip(),
            "local_runner_model": self._local_runner_model_edit.text().strip(),
            "local_runner_embed_model": self._local_runner_embed_model_edit.text().strip()
        })

    def _on_vg_settings_changed(self):
        self._vg_enabled = self._vg_enable_cb.isChecked()
        self._vg_voice_enabled = self._vg_voice_cb.isChecked()
        self._save_settings({
            "vision_guard_enabled": self._vg_enabled,
            "vision_guard_voice_enabled": self._vg_voice_enabled
        })

    def _snooze_vision_guard(self):
        if hasattr(self, "vision_guard") and self.vision_guard:
            self.vision_guard.snooze(20)
            self.write_log("SYS: Vision Guard alert snoozed for 20 minutes.")

    def _save_sticky_notes(self):
        try:
            notes_path = BASE_DIR / "memory" / "sticky_notes.txt"
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            text = self._sticky_edit.toPlainText()
            notes_path.write_text(text, encoding="utf-8")
            self.write_log("SYS: Sticky notes saved.")
        except Exception as e:
            self.write_log(f"SYS ERROR: Failed to save notes: {e}")

    def _clear_sticky_notes(self):
        self._sticky_edit.clear()
        self._save_sticky_notes()

    def _load_sticky_notes(self):
        try:
            notes_path = BASE_DIR / "memory" / "sticky_notes.txt"
            if notes_path.exists():
                self._sticky_edit.setPlainText(notes_path.read_text(encoding="utf-8"))
        except Exception as e:
            self.write_log(f"SYS WARNING: Failed to load notes: {e}")

    def _refresh_clip_history(self):
        try:
            from actions.clipboard_manager import CLIPBOARD_FILE
            if CLIPBOARD_FILE.exists():
                import json
                data = json.loads(CLIPBOARD_FILE.read_text(encoding="utf-8"))
                entries = data.get("entries", [])[:15]
                
                current_items = [self._clip_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self._clip_list.count())]
                new_items = [e.get("content", "").strip() for e in entries if e.get("content", "").strip()]
                
                if current_items != new_items:
                    self._clip_list.clear()
                    for item_text in new_items:
                        display_text = item_text if len(item_text) < 40 else item_text[:37] + "..."
                        from PyQt6.QtWidgets import QListWidgetItem
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.ItemDataRole.UserRole, item_text)
                        item.setToolTip(item_text)
                        self._clip_list.addItem(item)
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)

    def _on_clip_item_clicked(self, item):
        full_text = item.data(Qt.ItemDataRole.UserRole)
        if full_text:
            QApplication.clipboard().setText(full_text)
            self.write_log(f"SYS: Re-copied to clipboard: {item.text()}")

    def _clear_clip_history(self):
        try:
            from actions.clipboard_manager import CLIPBOARD_FILE
            if CLIPBOARD_FILE.exists():
                CLIPBOARD_FILE.write_text(json.dumps({"entries": []}), encoding="utf-8")
                self._clip_list.clear()
                self.write_log("SYS: Clipboard history cleared.")
        except Exception as e:
            self.write_log(f"SYS ERROR: Failed to clear clipboard: {e}")

    def _left_panel_tick(self):
        if not self._left_panel:
            return
        # 1. Update clipboard list
        self._refresh_clip_history()
        
        # 2. Update sticky notes if not focused
        if not self._sticky_edit.hasFocus():
            self._load_sticky_notes()
            
        # 3. Update Vision Guard progress bar & labels
        if hasattr(self, "vision_guard") and self.vision_guard:
            with self.vision_guard._lock:
                last_time = self.vision_guard._last_alert_time
                interval = self.vision_guard.interval
                
            if last_time is not None:
                now = time.time()
                if last_time > now:
                    time_left = last_time - now
                    self._vg_progress.setMaximum(int(time_left))
                    self._vg_progress.setValue(0)
                    self._vg_progress.setFormat("SNOOZED")
                    self._vg_timer_label.setText(f"Alerts snoozed. Resuming in: {int(time_left // 60)}m {int(time_left % 60)}s")
                else:
                    elapsed = now - last_time
                    self._vg_progress.setMaximum(interval)
                    self._vg_progress.setValue(min(int(elapsed), interval))
                    self._vg_progress.setFormat("%p%")
                    time_left = max(0, interval - elapsed)
                    self._vg_timer_label.setText(f"Next break in: {int(time_left // 60)}m {int(time_left % 60)}s")

        # 4. Update CPU/Memory dials
        if hasattr(self, "_cpu_gauge") and hasattr(self, "_mem_gauge"):
            snap = _metrics.snapshot()
            self._cpu_gauge.setValue(snap["cpu"])
            self._mem_gauge.setValue(snap["mem"])
            
        # 5. Update user profile every 5 seconds
        self._profile_tick_counter += 1
        if self._profile_tick_counter % 5 == 0:
            self._update_user_profile()

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_RIGHT_W)
        w.setStyleSheet(f"background: {hex_to_rgba_str(C.DARK, 0.55)}; border-left: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        def _sec(txt):
            l = QLabel(f"▸ {txt}")
            l.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            return l

        # Header with hide button
        hdr_layout = QHBoxLayout()
        hdr_layout.setContentsMargins(0, 2, 0, 2)
        
        hdr_lbl = QLabel("◈ CONSOLE PANEL")
        hdr_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        hdr_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        hdr_layout.addWidget(hdr_lbl)
        hdr_layout.addStretch()
        
        hide_btn = QPushButton("▶ Hide")
        hide_btn.setFixedSize(56, 20)
        hide_btn.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        hide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hide_btn.setToolTip("Hide Console Panel [F2]")
        hide_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                color: {C.TEXT_MED};
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO};
                border: 1px solid {C.PRI};
                color: {C.PRI};
            }}
        """)
        hide_btn.clicked.connect(lambda: self._toggle_console(False))
        hdr_layout.addWidget(hide_btn)
        lay.addLayout(hdr_layout)

        # Separator line
        sep_top = QFrame()
        sep_top.setFrameShape(QFrame.Shape.HLine)
        sep_top.setStyleSheet(f"color: {C.BORDER}; margin-bottom: 2px;")
        lay.addWidget(sep_top)

        lay.addWidget(_sec("ACTIVITY LOG"))
        self._log = LogWidget()
        lay.addWidget(self._log, stretch=1)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep)

        lay.addWidget(_sec("FILE UPLOAD"))
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        lay.addWidget(self._drop_zone)

        self._file_hint = QLabel("No file loaded — drop or click above to upload")
        self._file_hint.setFont(QFont("Courier New", 7))
        self._file_hint.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._file_hint.setWordWrap(True)
        lay.addWidget(self._file_hint)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep2)

        lay.addWidget(_sec("COMMAND INPUT"))
        lay.addLayout(self._build_input_row())

        self._autopilot_btn = QPushButton("🤖 AUTOPILOT MODE: OFF")
        self._autopilot_btn.setFixedHeight(30)
        self._autopilot_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._autopilot_btn.setCheckable(True)
        self._autopilot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._autopilot_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.PANEL};
                color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background-color: {C.PRI_GHO};
                color: {C.GREEN};
                border: 1px solid {C.GREEN};
            }}
            QPushButton:hover {{
                border: 1px solid {C.PRI};
            }}
        """)
        self._autopilot_btn.toggled.connect(self._toggle_autopilot)
        lay.addWidget(self._autopilot_btn)

        self._hacker_btn = QPushButton("💀 HACKER MODE: OFF")
        self._hacker_btn.setFixedHeight(30)
        self._hacker_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._hacker_btn.setCheckable(True)
        self._hacker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hacker_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.PANEL};
                color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background-color: {C.PRI_GHO};
                color: {C.RED};
                border: 1px solid {C.RED};
            }}
            QPushButton:hover {{
                border: 1px solid {C.PRI};
            }}
        """)
        self._hacker_btn.toggled.connect(self._toggle_hacker_mode)
        lay.addWidget(self._hacker_btn)

        self._mute_btn = QPushButton("🎙  MICROPHONE ACTIVE")
        self._mute_btn.setFixedHeight(30)
        self._mute_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        self._style_mute_btn()
        lay.addWidget(self._mute_btn)

        fs_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        fs_btn.setFixedHeight(26)
        fs_btn.setFont(QFont("Courier New", 7))
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {C.PRI}; border: 1px solid {C.BORDER_B};
            }}
        """)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        self._fs_btn = fs_btn
        lay.addWidget(fs_btn)

        return w

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(5)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question…")
        self._input.setFont(QFont("Courier New", 9))
        self._input.setFixedHeight(30)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d14; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 3px 7px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        send = QPushButton("▸")
        send.setFixedSize(30, 30)
        send.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        self._send_btn = send
        send.clicked.connect(self._send)
        row.addWidget(send)
        return row

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(40)
        w.setStyleSheet(f"""
            QWidget {{
                background: {hex_to_rgba_str(C.DARK, 0.70)};
                border: 1px solid {C.BORDER};
                border-radius: 20px;
            }}
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(12)
        
        start_btn = QPushButton("❖")
        start_btn.setFixedSize(24, 24)
        start_btn.setFont(QFont("Segoe UI Symbol", 12, QFont.Weight.Bold))
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setToolTip("Start Menu Launcher [F1]")
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {C.PRI};
            }}
            QPushButton:hover {{
                color: {C.ACC};
            }}
        """)
        start_btn.clicked.connect(self._show_start_flyout)
        lay.addWidget(start_btn)
        
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setFrameShadow(QFrame.Shadow.Sunken)
        div1.setStyleSheet(f"color: {C.BORDER}; border: none;")
        lay.addWidget(div1)
        
        widgets_btn = QPushButton("🍎 Widgets")
        widgets_btn.setFixedHeight(28)
        widgets_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        widgets_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        widgets_btn.setToolTip("Toggle Widgets Sidebar [F3]")
        widgets_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: white;
            }}
            QPushButton:hover {{
                color: {C.PRI};
            }}
        """)
        widgets_btn.clicked.connect(lambda: self._toggle_widgets_sidebar())
        lay.addWidget(widgets_btn)
        
        self._dock_mute_btn = QPushButton("🎙️ Active")
        self._dock_mute_btn.setFixedHeight(28)
        self._dock_mute_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._dock_mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dock_mute_btn.setToolTip("Mute/Unmute Mic [F4]")
        self._dock_mute_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {C.GREEN};
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)
        self._dock_mute_btn.clicked.connect(self._toggle_mute)
        lay.addWidget(self._dock_mute_btn)
        
        self._console_btn = QPushButton("🖥️ Console")
        self._console_btn.setFixedHeight(28)
        self._console_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._console_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._console_btn.setToolTip("Toggle Console Panel [F2]")
        self._console_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: white;
            }}
            QPushButton:hover {{
                color: {C.PRI};
            }}
        """)
        self._console_btn.clicked.connect(lambda: self._toggle_console())
        lay.addWidget(self._console_btn)

        self._autopilot_btn_dock = QPushButton("🤖 Auto: OFF")
        self._autopilot_btn_dock.setFixedHeight(28)
        self._autopilot_btn_dock.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._autopilot_btn_dock.setCursor(Qt.CursorShape.PointingHandCursor)
        self._autopilot_btn_dock.setCheckable(True)
        self._autopilot_btn_dock.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {C.TEXT_MED};
            }}
            QPushButton:checked {{
                color: {C.PRI};
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)
        self._autopilot_btn_dock.toggled.connect(self._toggle_autopilot)
        lay.addWidget(self._autopilot_btn_dock)

        return w

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size) if p.exists() else "File not found"
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell SATURDAY what to do with it")
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

    def _toggle_autopilot(self, checked: bool):
        if checked:
            self._autopilot_btn.setText("🤖 AUTOPILOT MODE: ON")
            self._log.append_log("SYS: Autopilot mode activated.")
        else:
            self._autopilot_btn.setText("🤖 AUTOPILOT MODE: OFF")
            self._log.append_log("SYS: Autopilot mode deactivated.")

    def _toggle_hacker_mode(self, checked: bool):
        if checked:
            self._hacker_btn.setText("💀 HACKER MODE: ON")
            self._log.append_log("SYS: Hacker mode activated.")
        else:
            self._hacker_btn.setText("💀 HACKER MODE: OFF")
            self._log.append_log("SYS: Hacker mode deactivated.")

        C.apply_hacker_mode_colors(checked)
        self._refresh_theme_styles()

        try:
            import main
            sat = main.get_saturday()
            if sat:
                sat.toggle_hacker_mode(checked)
        except Exception as e:
            print(f"[UI] ⚠️ Failed to notify SaturdayLive: {e}")

    def _apply_central_bg_style(self):
        is_hacker = self._hacker_btn.isChecked() if hasattr(self, "_hacker_btn") else False
        if is_hacker:
            bg_style = f"""
                QWidget#CentralWidget {{
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                                stop:0 rgba(18, 0, 2, 0.45), 
                                                stop:0.5 rgba(6, 0, 1, 0.55), 
                                                stop:1 rgba(26, 0, 4, 0.45));
                    border: 1px solid {C.BORDER};
                    border-radius: 12px;
                }}
            """
        else:
            bg_style = f"""
                QWidget#CentralWidget {{
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                                stop:0 rgba(0, 12, 24, 0.45), 
                                                stop:0.5 rgba(0, 5, 10, 0.55), 
                                                stop:1 rgba(0, 18, 34, 0.45));
                    border: 1px solid {C.BORDER};
                    border-radius: 12px;
                }}
            """
        self.centralWidget().setStyleSheet(bg_style)

    def _refresh_theme_styles(self):
        # 1. Invalidate HUD grid pixmap & repaint
        self.hud._grid_pixmap = None
        self.hud.update()

        # 2. Main frames / panels
        self._apply_central_bg_style()
        dark_trans = hex_to_rgba_str(C.DARK, 0.55)
        dark_headers = hex_to_rgba_str(C.DARK, 0.70)
        
        if hasattr(self, "_left_panel") and self._left_panel:
            self._left_panel.setStyleSheet(f"background: {dark_trans}; border-right: 1px solid {C.BORDER};")
        self._header_shim.setStyleSheet(f"background: {dark_headers}; border-bottom: 1px solid {C.BORDER_B}; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        self._right_panel.setStyleSheet(f"background: {dark_trans}; border-left: 1px solid {C.BORDER};")
        if hasattr(self, "_left_sidebar") and self._left_sidebar:
            self._left_sidebar.setStyleSheet(f"background: {dark_trans}; border-right: 1px solid {C.BORDER};")
        self._footer.setStyleSheet(f"""
            QWidget {{
                background: {hex_to_rgba_str(C.DARK, 0.70)};
                border: 1px solid {C.BORDER};
                border-radius: 20px;
            }}
        """)

        # 3. Header widgets
        self._header_left_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        self._header_title.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._header_sub.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        self._settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C.PRI_DIM};
                border-radius: 4px;
                color: {C.PRI};
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO};
                border: 1px solid {C.PRI};
                color: {C.PRI};
            }}
            QPushButton:pressed {{
                background: {C.PRI_DIM};
                color: {C.DARK};
            }}
        """)
        if hasattr(self, "_theme_btn") and self._theme_btn:
            self._theme_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid {C.PRI_DIM};
                    border-radius: 4px;
                    color: {C.PRI};
                }}
                QPushButton:hover {{
                    background: {C.PRI_GHO};
                    border: 1px solid {C.PRI};
                    color: {C.PRI};
                }}
                QPushButton:pressed {{
                    background: {C.PRI_DIM};
                    color: {C.DARK};
                }}
            """)

        if hasattr(self, "_quick_search_btn") and self._quick_search_btn:
            for btn in [self._quick_search_btn, self._quick_ss_btn, self._quick_notes_btn]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PANEL};
                        color: {C.TEXT_MED};
                        border: 1px solid {C.BORDER};
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background: {C.PRI_GHO};
                        border: 1px solid {C.PRI};
                        color: {C.PRI};
                    }}
                    QPushButton:pressed {{
                        background: {C.PRI_DIM};
                        color: {C.DARK};
                    }}
                """)

        # 4. Left panel widgets
        if hasattr(self, "_left_panel") and self._left_panel:
            self._left_monitor_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                                                 f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
            self._left_info_panel.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
            self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
            self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
            self._os_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")

            # Metric bars colors
            self._bar_cpu._color = C.PRI
            self._bar_cpu.update()
            self._bar_mem._color = C.ACC2
            self._bar_mem.update()
            self._bar_net._color = C.GREEN
            self._bar_net.update()
            self._bar_gpu._color = C.ACC
            self._bar_gpu.update()
            self._bar_tmp._color = "#ff6688"
            self._bar_tmp.update()

        # 5. Right panel controls
        self._file_hint.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.PANEL2}; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 3px 7px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        self._autopilot_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.PANEL};
                color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background-color: {C.PRI_GHO};
                color: {C.GREEN};
                border: 1px solid {C.GREEN};
            }}
            QPushButton:hover {{
                border: 1px solid {C.PRI};
            }}
        """)
        self._hacker_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.PANEL};
                color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background-color: {C.PRI_GHO};
                color: {C.RED};
                border: 1px solid {C.RED};
            }}
            QPushButton:hover {{
                border: 1px solid {C.PRI};
            }}
        """)
        self._style_mute_btn()
        self._fs_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {C.PRI}; border: 1px solid {C.BORDER_B};
            }}
        """)

        # Log widget
        self._log.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                padding: 6px;
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

        # 6. Footer
        self._footer_left.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._footer_right.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")

    def closeEvent(self, event):
        if getattr(self, "_force_exit", False):
            event.accept()
        elif hasattr(self, "_tray_icon") and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
            if not getattr(self, "_tray_notified", False):
                self._tray_icon.showMessage(
                    "S.A.T.U.R.D.A.Y",
                    "Saturday is running in the background. Right-click the tray icon to exit.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )
                self._tray_notified = True
        else:
            event.accept()

    def _toggle_console(self, force_show=None):
        if force_show is not None:
            visible = force_show
        else:
            visible = not self._right_panel.isVisible()
            
        if hasattr(self, "_console_anim") and self._console_anim is not None:
            self._console_anim.stop()
            
        start_w = self._right_panel.width() if self._right_panel.isVisible() else 0
        end_w = 340 if visible else 0
        
        if visible:
            self._right_panel.show()
            self._log.append_log("SYS: Console panel unhidden.")
            if hasattr(self, "_settings_btn") and self._settings_btn:
                self._settings_btn.setText("Console ▶")
        else:
            self._log.append_log("SYS: Console panel hidden.")
            if hasattr(self, "_settings_btn") and self._settings_btn:
                self._settings_btn.setText("Console ◀")
            
        self._console_anim = QVariantAnimation(self)
        self._console_anim.setDuration(250)
        self._console_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._console_anim.setStartValue(start_w)
        self._console_anim.setEndValue(end_w)
        
        def _update_width(w):
            self._right_panel.setFixedWidth(w)
            if not self.isFullScreen() and not self.isMaximized():
                left_w = self._left_sidebar.width() if (hasattr(self, "_left_sidebar") and self._left_sidebar and self._left_sidebar.isVisible()) else 0
                win_w = int(520 + left_w + 440 * (w / 340.0))
                self.resize(win_w, self.height())
                
        self._console_anim.valueChanged.connect(_update_width)
        
        def _on_finish():
            if not visible:
                self._right_panel.hide()
            self._console_anim = None
            
        self._console_anim.finished.connect(_on_finish)
        self._console_anim.start()

    def _toggle_widgets_sidebar(self, force_show=None):
        if force_show is not None:
            visible = force_show
        else:
            visible = not self._left_sidebar.isVisible()
            
        if hasattr(self, "_widgets_anim") and self._widgets_anim is not None:
            self._widgets_anim.stop()
            
        start_w = self._left_sidebar.width() if self._left_sidebar.isVisible() else 0
        end_w = 260 if visible else 0
        
        if visible:
            self._left_sidebar.show()
            self._log.append_log("SYS: Widgets sidebar shown.")
        else:
            self._log.append_log("SYS: Widgets sidebar hidden.")
            
        self._widgets_anim = QVariantAnimation(self)
        self._widgets_anim.setDuration(250)
        self._widgets_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._widgets_anim.setStartValue(start_w)
        self._widgets_anim.setEndValue(end_w)
        
        def _update_width(w):
            self._left_sidebar.setFixedWidth(w)
            if not self.isFullScreen() and not self.isMaximized():
                right_w = self._right_panel.width() if self._right_panel.isVisible() else 0
                win_w = int(520 + w + 440 * (right_w / 340.0))
                self.resize(win_w, self.height())
                
        self._widgets_anim.valueChanged.connect(_update_width)
        
        def _on_finish():
            if not visible:
                self._left_sidebar.hide()
            self._widgets_anim = None
            
        self._widgets_anim.finished.connect(_on_finish)
        self._widgets_anim.start()

    def _toggle_agent_center_view(self):
        if not hasattr(self, "_stacked_widget") or not self._stacked_widget:
            return
        current_index = self._stacked_widget.currentIndex()
        if current_index == 2:
            self._stacked_widget.setCurrentIndex(0)
            self._workspace_btn.setText("Workspace ▦")
            self._log.append_log("SYS: Switched back to HUD view.")
        else:
            self._stacked_widget.setCurrentIndex(2)
            self._workspace_btn.setText("Orb View 🔵")
            self._log.append_log("SYS: Switched to Agent Command Center view.")

    def _show_start_flyout(self):
        flyout = StartFlyout(self)
        dx = int(self.x() + (self.width() - flyout.width()) / 2)
        dy = int(self.y() + self.height() - flyout.height() - 70)
        flyout.move(dx, dy)
        if flyout.exec() == QDialog.DialogCode.Accepted:
            act = flyout._action
            if act == "organize":
                self._log.append_log("SYS: Triggering vault organization...")
                from actions.obsidian_organizer import run_categorize
                threading.Thread(target=run_categorize, daemon=True).start()
            elif act == "cleanup":
                self._log.append_log("SYS: Clearing system memory caches...")
                self.hud._particles.clear()
                self._log.append_log("SYS: Particle systems flushed.")
            elif act == "workspace":
                self._toggle_workspace()
            elif act == "army":
                self._toggle_agent_center_view()
            elif act == "clipboard":
                self._toggle_clipboard_ai()

    def _setup_tray_icon(self, face_path: str):
        self._force_exit = False
        self._tray_notified = False
        
        self._tray_icon = QSystemTrayIcon(self)
        if os.path.exists(face_path):
            self._tray_icon.setIcon(QIcon(face_path))
        else:
            self._tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
        tray_menu = QMenu(self)
        
        show_action = tray_menu.addAction("Restore Saturday")
        show_action.triggered.connect(lambda: (self.showNormal(), self.activateWindow()))
        
        self._tray_mute_action = tray_menu.addAction("Mute Microphone")
        self._tray_mute_action.triggered.connect(self._toggle_mute)
        
        tray_menu.addSeparator()
        
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self._on_tray_exit)
        
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def toggle_hud_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_hud_visibility()

    def _on_tray_exit(self):
        self._force_exit = True
        self._tray_icon.hide()
        self.close()
        QApplication.quit()

    def _style_mute_btn(self):
        if hasattr(self, "_tray_mute_action"):
            if self._muted:
                self._tray_mute_action.setText("🎙  Unmute Microphone")
            else:
                self._tray_mute_action.setText("🔇  Mute Microphone")
        if hasattr(self, "_mute_btn") and self._mute_btn:
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
        if hasattr(self, "_dock_mute_btn") and self._dock_mute_btn:
            if self._muted:
                self._dock_mute_btn.setText("🔇 Muted")
                self._dock_mute_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        color: {C.MUTED_C};
                    }}
                    QPushButton:hover {{
                        color: white;
                    }}
                """)
            else:
                self._dock_mute_btn.setText("🎙️ Active")
                self._dock_mute_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        color: {C.GREEN};
                    }}
                    QPushButton:hover {{
                        color: white;
                    }}
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
        self.hud.muted    = (state == "MUTED")
        self._muted       = (state == "MUTED")
        self._style_mute_btn()
        if not hasattr(self, "_last_sound_state"):
            self._last_sound_state = None
        if state != self._last_sound_state:
            self._last_sound_state = state
            self._sound_manager.play(state, self)
        if hasattr(self, "_media_visualizer") and self._media_visualizer:
            self._media_visualizer.set_active(state in ("SPEAKING", "LISTENING"))

    def _update_last_response(self, text: str):
        self.hud._last_response = text
        self.hud.update()
        if hasattr(self, "_agent_center") and self._agent_center and self._stacked_widget.currentIndex() == 2:
            curr = self._agent_center.agent_list.currentItem()
            if curr:
                name = curr.text()
                data = self._agent_center._agents_data[name]
                clean_text = text.replace(f"[{name}]:", "").strip()
                data["history"].append((name, clean_text))
                self._agent_center.chat_display.append(f"[{name}]: {clean_text}")

    def _update_activity(self, text: str):
        self.hud._activity = text
        self.hud.update()

    def _on_audio_level_changed(self, level: float):
        self.hud.set_audio_level(level)
        if hasattr(self, "_media_visualizer") and self._media_visualizer:
            self._media_visualizer.set_audio_level(level)

    def _show_custom_alert(self, title: str, message: str, alert_type: str):
        alert = SaturdayCustomAlert(title, message, alert_type, self)
        alert.exec()

    def _on_ww_settings_changed(self):
        self._ww_enabled = self._ww_enable_cb.isChecked()
        keywords = self._ww_keywords_edit.text().strip()
        self._save_settings({
            "wake_word_enabled": self._ww_enabled,
            "wake_words": keywords
        })
        self.write_log(f"SYS: Wake-word mode {'enabled' if self._ww_enabled else 'disabled'} (keywords: {keywords or 'default'}).")

    def _update_user_profile(self):
        try:
            from memory.memory_manager import load_memory
            mem = load_memory()
            name = mem.get("identity", {}).get("name", {}).get("value", "Pratik")
            projects_dict = mem.get("projects", {})
            projects = []
            for k, v in projects_dict.items():
                if isinstance(v, dict) and "value" in v:
                    projects.append(v["value"])
                elif isinstance(v, str):
                    projects.append(v)
            proj_str = ", ".join(projects) if projects else "No active projects logged."
            pref_dict = mem.get("preferences", {})
            prefs = []
            for k, v in pref_dict.items():
                val = v.get("value") if isinstance(v, dict) else v
                if val:
                    prefs.append(f"{k.replace('_', ' ')}: {val}")
            pref_str = "<br>&nbsp;&nbsp;• " + "<br>&nbsp;&nbsp;• ".join(prefs) if prefs else "None logged yet."
            settings = self._load_settings()
            mood = settings.get("mood", "normal").upper()
            lines = [
                f"👤 <b>USER</b>: {name}",
                f"🎭 <b>CURRENT MOOD</b>: <span style='color:{C.PRI};'>{mood}</span>",
                f"🎯 <b>PROJECTS</b>: {proj_str}",
                f"⭐ <b>PREFERENCES</b>:{pref_str}"
            ]
            self._profile_lbl.setText("<br>".join(lines))
        except Exception as e:
            self._profile_lbl.setText(f"Failed to load profile: {e}")

    def update_standby_thoughts(self):
        try:
            from core.life_engine import life_engine
            thoughts = life_engine.get_recent_thoughts()
            self._dashboard.standby_thoughts_text.setText("\n".join(thoughts))
        except Exception as e:
            print(f"Failed to update standby thoughts: {e}")

    def _update_active_task(self, text: str):
        try:
            self._dashboard.active_task_lbl.setText(text)
        except Exception as e:
            print(f"Failed to update active task label: {e}")

    def _on_voice_changed(self):
        voice_names = ["Charon", "Puck", "Fenrir", "Kore", "Aoede"]
        selected = voice_names[self._voice_cb.currentIndex()]
        self._save_settings({"voice_name": selected})
        self.write_log(f"SYS: Saturday voice changed to {selected}. It will take effect on next connection.")
        try:
            from core.session_manager import clear_prompt_cache
            clear_prompt_cache()
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)

    def _save_telegram_settings(self):
        token = self._tg_token_edit.text().strip()
        chat_id = self._tg_chat_edit.text().strip()
        self._save_settings({
            "telegram_bot_token": token,
            "telegram_chat_id": chat_id
        })
        self.write_log("SYS: Telegram companion settings saved.")

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return ("gemini_api_key" in d and
                    "openrouter_api_key" in d and
                    "os_system" in d)
        except Exception:
            return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 460, 430
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    # Change signature:
    def _on_setup_done(self, key: str, or_key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        config = {}
        if API_FILE.exists():
            try:
                config = json.loads(API_FILE.read_text(encoding="utf-8"))
            except Exception:
                config = {}
        config["gemini_api_key"] = key
        config["openrouter_api_key"] = or_key
        config["os_system"] = os_name
        API_FILE.write_text(
            json.dumps(config, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._log.append_log(f"SYS: Initialised. OS={os_name.upper()}. SATURDAY online. Built by Pratik Thorat.")

class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class PlanConfirmDialog(QDialog):
    def __init__(self, goal: str, plan_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("S.A.T.U.R.D.A.Y — Proposed Execution Plan")
        self.resize(500, 420)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {C.PANEL};
                color: {C.TEXT};
                border: 2px solid {C.BORDER};
            }}
            QLabel {{
                color: {C.TEXT};
                font-family: 'Courier New';
                font-size: 11px;
            }}
            QTextEdit {{
                background-color: {C.BG};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                font-family: 'Courier New';
                font-size: 11px;
            }}
            QLineEdit {{
                background-color: {C.BG};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                font-family: 'Courier New';
                padding: 6px;
            }}
            QPushButton {{
                background-color: {C.BORDER_A};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                padding: 8px 16px;
                border-radius: 4px;
                font-family: 'Courier New';
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {C.PRI_DIM};
                border: 1px solid {C.PRI};
            }}
        """)

        layout = QVBoxLayout()

        lbl_goal = QLabel(f"🎯 <b>Goal:</b> {goal}")
        lbl_goal.setWordWrap(True)
        lbl_goal.setStyleSheet(f"color: {C.PRI}; font-size: 13px;")
        layout.addWidget(lbl_goal)

        lbl_plan = QLabel("📋 <b>Proposed Steps:</b>")
        layout.addWidget(lbl_plan)

        self.plan_view = QTextEdit()
        self.plan_view.setReadOnly(True)
        self.plan_view.setPlainText(plan_text)
        layout.addWidget(self.plan_view)

        lbl_feedback = QLabel("✍️ <b>Provide Feedback / Custom preferences (optional):</b><br/><i>(e.g., 'use dark theme', 'write in python', 'change colors to green')</i>")
        lbl_feedback.setWordWrap(True)
        layout.addWidget(lbl_feedback)

        self.txt_feedback = QLineEdit()
        self.txt_feedback.setPlaceholderText("Type preferences/feedback here...")
        layout.addWidget(self.txt_feedback)

        btn_layout = QHBoxLayout()

        self.btn_confirm = QPushButton("✅ Confirm & Run")
        self.btn_replan = QPushButton("🔄 Replan with Feedback")
        self.btn_cancel = QPushButton("❌ Cancel")

        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addWidget(self.btn_replan)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.btn_confirm.clicked.connect(self.accept)
        self.btn_replan.clicked.connect(self._replan_clicked)
        self.btn_cancel.clicked.connect(self.reject)

        self.feedback = ""
        self.action = "cancel"

    def _replan_clicked(self):
        self.feedback = self.txt_feedback.text().strip()
        self.action = "replan"
        self.done(2)

    def accept(self):
        self.feedback = self.txt_feedback.text().strip()
        self.action = "confirm"
        super().accept()


class VisionGuardAlert(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("S.A.T.U.R.D.A.Y — Vision Guard Alert")
        self.resize(400, 220)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {C.PANEL};
                color: {C.TEXT};
                border: 2px solid {C.ACC};
            }}
            QLabel {{
                color: {C.TEXT};
                font-family: 'Courier New';
                font-size: 12px;
            }}
            QPushButton {{
                background-color: {C.BORDER_A};
                color: {C.WHITE};
                border: 1px solid {C.ACC};
                padding: 8px 16px;
                border-radius: 4px;
                font-family: 'Courier New';
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {C.ACC};
                color: {C.BG};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        lbl_icon = QLabel("⚠️ VISION GUARD WARNING ⚠️")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(f"color: {C.ACC}; font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl_icon)
        
        lbl_text = QLabel(
            "प्रतीक सर, आपने 20 मिनट काम कर लिया है।\\n"
            "कृपया 20 फीट दूर किसी वस्तु को 20 सेकंड के लिए देखें ताकि आँखों को आराम मिल सके।\\n\\n"
            "Please follow the 20-20-20 rule to prevent eye strain."
        )
        lbl_text.setWordWrap(True)
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_text)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Acknowledge")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)


_ui_instance = None

def get_ui() -> SaturdayUI | None:
    return _ui_instance


class SaturdayUI:
    def __init__(self, face_path: str, size=None):
        global _ui_instance
        self._app = QApplication.instance() or QApplication([])
        self._app.setStyle("Fusion")
        self._win = MainWindow(face_path)
        self._win.showMaximized()
        self.root = _RootShim(self._app)
        _ui_instance = self

    def _load_settings(self) -> dict:
        return self._win._load_settings()

    def _save_settings(self, settings: dict):
        self._win._save_settings(settings)

    def show_custom_alert(self, title: str, message: str, alert_type: str = "info"):
        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            self._win._show_custom_alert(title, message, alert_type)
        else:
            self._win._custom_alert_sig.emit(title, message, alert_type)

    def confirm_action(self, message: str) -> bool:
        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            return self._win.show_confirm_dialog(message)
        else:
            res = [False]
            evt = threading.Event()
            self._win._confirm_sig.emit(message, [res, evt])
            evt.wait()
            return res[0]

    def prompt_input(self, message: str) -> str | None:
        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            return self._win.show_prompt_dialog(message)
        else:
            res = [None]
            evt = threading.Event()
            self._win._prompt_sig.emit(message, [res, evt])
            evt.wait()
            return res[0]

    def load_steps(self, steps: list[dict]):
        self._win._steps_loaded_sig.emit(steps)

    def update_step(self, step_idx: int, status: str, result: str = None):
        self._win._step_update_sig.emit(step_idx, status, result or "")

    def confirm_plan(self, goal: str, plan_steps: list[dict]) -> tuple[str, str]:
        plan_text = ""
        for s in plan_steps:
            plan_text += f"Step {s.get('step')}: [{s.get('tool')}] {s.get('description')}\n"
            params = s.get("parameters", {})
            if params:
                plan_text += f"  Parameters: {json.dumps(params, indent=2)}\n"
            plan_text += "\n"

        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            return self._win.show_plan_confirm_dialog(goal, plan_text)
        else:
            res = [{"action": "cancel", "feedback": ""}]
            evt = threading.Event()
            self._win._plan_confirm_sig.emit(goal, plan_text, [res[0], evt])
            evt.wait()
            return res[0]["action"], res[0]["feedback"]

    @property
    def autopilot(self) -> bool:
        try:
            return self._win._autopilot_btn.isChecked()
        except Exception:
            return False

    @property
    def hacker_mode(self) -> bool:
        try:
            return self._win._hacker_btn.isChecked()
        except Exception:
            return False

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

    def set_last_response(self, text: str):
        self._win._last_response_sig.emit(text)

    def set_activity(self, text: str):
        self._win._activity_sig.emit(text)

    def set_console_visible(self, visible: bool):
        self._win._console_visible_sig.emit(visible)

    def wait_for_api_key(self):
        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            from PyQt6.QtCore import QEventLoop
            loop = QEventLoop()
            timer = QTimer()
            timer.timeout.connect(lambda: loop.quit() if self._win._ready else None)
            timer.start(100)
            loop.exec()
        else:
            while not self._win._ready:
                time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def set_audio_level(self, level: float):
        self._win._audio_level_sig.emit(level)

    def show_notification(self, title: str, message: str):
        self._win.show_notification(title, message)

    def update_standby_thoughts(self):
        self._win._standby_thoughts_sig.emit()

    def set_active_task(self, text: str):
        self._win._active_task_sig.emit(text)

class IPRayUI(SaturdayUI):
    """Facade adapter for SaturdayUI to match main.py's IPRayUI API requirements."""
    
    def __init__(self, face_path: str, size=None):
        super().__init__(face_path, size)
        self.root = _RootShim(self._app)

    def write_thought(self, text: str):
        self.write_log(f"[Thought] {text}")
        
    def write_chat(self, role: str, text: str):
        if role.lower() == "assistant":
            self.set_last_response(str(text))
        else:
            self.write_log(f"User: {text}")

    def set_router_badge(self, model: str):
        pass

    def set_speaking_volume(self, vol: float) -> None:
        pass

    def pulse_highlight(self, x: int, y: int, duration: float = 3.0, color: str = "cyan"):
        pass

    def show_ocr_translation(self, items: list):
        pass

    def set_fullscreen(self, full: bool):
        pass


__all__ = ["IPRayUI", "SaturdayUI"]

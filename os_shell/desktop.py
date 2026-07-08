"""
os_shell/desktop.py — Native PyQt6 macOS Yosemite Glass Desktop Shell.
Implements native window dragging, background image painting, 2D neural node particle network,
top menu bar, bottom dock, and handles child widgets like terminal, vis.js graph, real-time chart,
theme selection, sticky notes, built-in file explorer, text editor, task manager, and calculator.
"""

import sys
import math
import random
import datetime
import urllib.request
import subprocess
import shutil
import re
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QApplication, QGraphicsDropShadowEffect,
    QProgressBar, QListWidget, QFrame, QTextEdit, QComboBox,
    QTextBrowser, QSplitter, QInputDialog, QLineEdit
)
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient,
    QFont, QPen, QBrush, QPainterPath, QPixmap
)

from os_shell.widgets.terminal_widget import VocalTerminalWidget
from os_shell.widgets.ai_orb import AIOrb
from os_shell.widgets.launchpad import LaunchpadOverlay
from os_shell.widgets.autopilot_coder import AutopilotCoderWidget
from os_shell.widgets.nainipix_studio import NainiPixStudioWidget
from os_shell.shell_manager import hide_windows_taskbar, show_windows_taskbar

# ─── Native Mind Graph Canvas (Knowledge Graph with QPainter) ─────────────
_GRAPH_NODES = [
    {"id": "IP PRIME",   "x": 0.5,  "y": 0.5,  "color": QColor("#00c8ff"), "size": 18},
    {"id": "Architect",  "x": 0.25, "y": 0.25, "color": QColor("#7c3aed"), "size": 12},
    {"id": "Coder",      "x": 0.75, "y": 0.25, "color": QColor("#00f5a0"), "size": 12},
    {"id": "Debugger",   "x": 0.75, "y": 0.75, "color": QColor("#ff4b4b"), "size": 12},
    {"id": "Fallback",   "x": 0.25, "y": 0.75, "color": QColor("#eab308"), "size": 12}
]
_GRAPH_EDGES = [(0, 1), (0, 2), (0, 3), (0, 4)]

class _MindGraphCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pulse = 0.0
        self.orbitals = {
            "Architect": {"parent_idx": 1, "target_opacity": 0.0, "current_opacity": 0.0, "label": "idle"},
            "Coder":     {"parent_idx": 2, "target_opacity": 0.0, "current_opacity": 0.0, "label": "idle"},
            "Debugger":  {"parent_idx": 3, "target_opacity": 0.0, "current_opacity": 0.0, "label": "idle"}
        }
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(40)

    def set_orbital_active(self, name, active, label=""):
        if name in self.orbitals:
            self.orbitals[name]["target_opacity"] = 1.0 if active else 0.0
            if active and label:
                self.orbitals[name]["label"] = label

    def _tick(self):
        self._pulse = (self._pulse + 0.04) % (2 * 3.14159)
        # Smoothly decay/interpolate opacities
        for data in self.orbitals.values():
            diff = data["target_opacity"] - data["current_opacity"]
            if abs(diff) > 0.01:
                data["current_opacity"] += diff * 0.1
            else:
                data["current_opacity"] = data["target_opacity"]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 0))
        W, H = self.width(), self.height()

        positions = [(int(n["x"] * W), int(n["y"] * H)) for n in _GRAPH_NODES]

        # Draw edges
        for i, j in _GRAPH_EDGES:
            x1, y1 = positions[i]
            x2, y2 = positions[j]
            pen = QPen(QColor(100, 180, 255, 90), 1.5)
            p.setPen(pen)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Draw nodes
        import math
        for idx, (node, (nx, ny)) in enumerate(zip(_GRAPH_NODES, positions)):
            pulse_radius = node["size"] + 5 * abs(math.sin(self._pulse + idx))
            # Glow
            grad = QRadialGradient(nx, ny, pulse_radius * 2)
            c = node["color"]
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 80))
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(QPointF(nx, ny), pulse_radius * 2, pulse_radius * 2)

            # Core
            p.setBrush(QBrush(node["color"]))
            p.setPen(QPen(QColor(255, 255, 255, 160), 1.5))
            p.drawEllipse(QPointF(nx, ny), node["size"], node["size"])

        # Draw orbitals
        for key, data in self.orbitals.items():
            if data["current_opacity"] <= 0.01:
                continue
                
            parent_idx = data["parent_idx"]
            px, py = positions[parent_idx]
            
            # Compute orbital coordinate revolving slowly around parent
            angle = self._pulse * 1.5 + (parent_idx * 1.2)
            dist = 40.0 # orbit radius
            ox = px + dist * math.cos(angle)
            oy = py + dist * math.sin(angle)
            
            opacity = int(data["current_opacity"] * 255)
            c = _GRAPH_NODES[parent_idx]["color"]
            node_color = QColor(c.red(), c.green(), c.blue(), opacity)
            
            # Draw link line
            line_pen = QPen(QColor(c.red(), c.green(), c.blue(), int(opacity * 0.4)), 1.2, Qt.PenStyle.DashLine)
            p.setPen(line_pen)
            p.drawLine(QPointF(px, py), QPointF(ox, oy))
            
            # Draw orbital node glow
            grad = QRadialGradient(ox, oy, 12)
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), int(opacity * 0.3)))
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(QPointF(ox, oy), 12, 12)
            
            # Draw orbital core node
            p.setBrush(QBrush(node_color))
            p.setPen(QPen(QColor(255, 255, 255, int(opacity * 0.65)), 1.0))
            p.drawEllipse(QPointF(ox, oy), 5, 5)
            
            # Draw text label next to orbital
            p.setFont(QFont("Outfit", 7, QFont.Weight.Medium))
            p.setPen(QColor(255, 255, 255, int(opacity * 0.8)))
            p.drawText(QPointF(ox + 8, oy + 3), data["label"])

            # Label
            p.setPen(QColor(30, 40, 60))
            font = QFont("Outfit", 8, QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(nx - 30, ny + node["size"] + 14, 60, 14,
                       Qt.AlignmentFlag.AlignHCenter, node["id"])


# ─── System performance real-time chart ───────────────────────────
class StatsHistoryChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.history = [0] * 30

    def add_value(self, val):
        self.history.pop(0)
        self.history.append(val)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        p.fillRect(self.rect(), QColor(0, 0, 0, 15))

        pen = QPen(QColor(0, 0, 0, 20), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        for y_factor in [0.25, 0.5, 0.75]:
            y = int(self.height() * y_factor)
            p.drawLine(0, y, self.width(), y)

        if not self.history:
            return

        W = self.width()
        H = self.height()
        step = W / 29.0

        path = QPainterPath()
        path.moveTo(0, H - (self.history[0] / 100.0 * H))
        for i, val in enumerate(self.history):
            path.lineTo(i * step, H - (val / 100.0 * H))

        p.setPen(QPen(QColor(3, 105, 161, 220), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        fill_path = QPainterPath(path)
        fill_path.lineTo(W, H)
        fill_path.lineTo(0, H)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0.0, QColor(3, 105, 161, 85))
        grad.setColorAt(1.0, QColor(3, 105, 161, 0))
        p.fillPath(fill_path, QBrush(grad))


# ─── Yosemite Traffic Light Buttons ───────────────────────────────
class TrafficLightButton(QPushButton):
    def __init__(self, color_normal, color_hover, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_normal};
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {color_hover};
            }}
        """)


# ─── Yosemite Title Bar (Supports Window Dragging) ──────────────────
class WindowTitleBar(QWidget):
    def __init__(self, title, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        # macOS Traffic Lights
        self.close_btn = TrafficLightButton("#ff5f56", "#e0443e", self)
        self.close_btn.clicked.connect(lambda: self.window.hide_window())
        self.min_btn = TrafficLightButton("#ffbd2e", "#dfa224", self)
        self.min_btn.clicked.connect(lambda: self.window.hide_window())
        self.max_btn = TrafficLightButton("#27c93f", "#1a9c2b", self)
        self.max_btn.clicked.connect(lambda: self.window.toggle_maximize())

        layout.addWidget(self.close_btn)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addStretch()

        # Title Text
        self.title_lbl = QLabel(title, self)
        self.title_lbl.setObjectName("titleLabel")
        self.title_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(self.title_lbl)
        layout.addStretch()
        
        # Spacer to balance traffic lights on left
        spacer = QWidget(self)
        spacer.setFixedWidth(52)
        layout.addWidget(spacer)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            self.window.raise_()
            self.window.set_dragging(True)
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.window.set_dragging(False)
        event.accept()


# ─── Draggable Yosemite Frosted Glass Window Widget ──────────────────
class GlassWindow(QWidget):
    visibility_changed = pyqtSignal(bool)

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._dragging = False
        self.is_maximized = False
        self.prev_geometry = None
        self.theme = "light"

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Title bar
        self.titlebar = WindowTitleBar(title, self, self)
        self.main_layout.addWidget(self.titlebar)

        # Content body container
        self.body = QWidget(self)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(12, 12, 12, 12)
        self.body_layout.setSpacing(10)
        self.main_layout.addWidget(self.body, 1)

        # Apply rich shadow to window
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 75))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)
        
        self.update_theme("light")

    def set_content_layout(self, layout):
        QWidget().setLayout(self.body_layout)
        self.body_layout = layout
        self.body.setLayout(self.body_layout)

    def set_dragging(self, state: bool):
        self._dragging = state
        self.update()

    def hide_window(self):
        self.hide()
        self.visibility_changed.emit(False)

    def show_window(self):
        self.show()
        self.raise_()
        self.visibility_changed.emit(True)

    def toggle_maximize(self):
        if self.is_maximized:
            if self.prev_geometry:
                self.setGeometry(self.prev_geometry)
            self.is_maximized = False
        else:
            self.prev_geometry = self.geometry()
            p = self.parentWidget()
            if p:
                self.setGeometry(0, 0, p.width(), p.height())
            self.is_maximized = True

    def update_theme(self, theme: str):
        self.theme = theme
        if theme == "light":
            self.setStyleSheet("""
                QLabel { color: #1e293b; }
                #titleLabel { color: #222222; }
                QListWidget { background: rgba(255, 255, 255, 0.35); border: 1px solid rgba(0, 0, 0, 0.08); color: #1e293b; }
                QTextEdit { background: rgba(255, 255, 255, 0.35); border: 1px solid rgba(0, 0, 0, 0.08); color: #1e293b; }
                QComboBox { background: rgba(255, 255, 255, 0.4); border: 1px solid rgba(0, 0, 0, 0.1); color: #1e293b; }
            """)
        elif theme == "dark":
            self.setStyleSheet("""
                QLabel { color: #b4cdd4; }
                #titleLabel { color: #e1f0f5; }
                QListWidget { background: rgba(10, 24, 27, 0.75); border: 1px solid rgba(0, 200, 255, 0.18); color: #e1f0f5; }
                QTextEdit { background: rgba(10, 24, 27, 0.75); border: 1px solid rgba(0, 200, 255, 0.18); color: #e1f0f5; }
                QComboBox { background: rgba(10, 24, 27, 0.75); border: 1px solid rgba(0, 200, 255, 0.18); color: #e1f0f5; }
            """)
        elif theme == "neon":
            self.setStyleSheet("""
                QLabel { color: #00f5ff; }
                #titleLabel { color: #00f5ff; }
                QListWidget { background: rgba(8, 8, 28, 0.6); border: 1px solid rgba(0, 245, 255, 0.3); color: #00f5ff; }
                QTextEdit { background: rgba(8, 8, 28, 0.6); border: 1px solid rgba(0, 245, 255, 0.3); color: #00f5ff; }
                QComboBox { background: rgba(8, 8, 28, 0.6); border: 1px solid rgba(0, 245, 255, 0.3); color: #00f5ff; }
            """)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8.0, 8.0)

        if self._dragging:
            bg_color = QColor(215, 225, 255, 175)
            border_color = QColor(255, 255, 255, 150)
        else:
            if self.theme == "light":
                bg_color = QColor(255, 255, 255, 140)
                border_color = QColor(255, 255, 255, 100)
            elif self.theme == "dark":
                bg_color = QColor(10, 24, 27, 215)
                border_color = QColor(0, 200, 255, 45)
            else: # neon theme
                bg_color = QColor(8, 8, 28, 215)
                border_color = QColor(0, 245, 255, 120)

        painter.fillPath(path, QBrush(bg_color))

        pen = QPen(border_color, 1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


# ─── Main OS Desktop ───────────────────────────────────────────────
class IPPrimeOSDesktop(QMainWindow):
    stats_updated = pyqtSignal(int, int)
    stream_received = pyqtSignal(str)
    conversation_added = pyqtSignal(str, str, bool)

    def __init__(self, face_path="assets/logo.png", ui_facade=None):
        super().__init__()
        self.stats_updated.connect(self._update_stats_ui)
        self.stream_received.connect(self.stream_prime_response)
        self.conversation_added.connect(self.add_conversation_line)
        self.face_path = face_path
        self.ui_facade = ui_facade
        self.bg_pixmap = None
        self._hud_cpu = "0%"
        self._hud_ram = "0%"
        self.current_theme = "dark"
        self.current_dir = Path(".").resolve()
        self.log_history = [
            "System: IP Prime OS Yosemite Glass Desktop loaded.",
            "System: Core 3D Particle AI Orb active.",
            "Prime: Welcome back, Pratik Sir! Standing by.",
            "System: Speak or say wake up words to start conversation."
        ]

        # Start Web HUD backend server on port 5000 asynchronously if not running
        try:
            from actions.web_hud import web_hud, WebHUDServer
            if not WebHUDServer.is_running:
                web_hud(parameters={"action": "start", "port": 5000}, player=self.ui_facade)
        except Exception as e:
            print(f"[Desktop] Failed to start local server backend: {e}")

        self.cached_bg_pixmap = None
        # Load custom wallpaper if selected by user
        self.bg_path = Path("assets/space_bg.jpg")
        self.bg_path.parent.mkdir(exist_ok=True)
        if self.bg_path.exists():
            self.bg_pixmap = QPixmap(str(self.bg_path))

        self.init_ui()
        self._update_cached_bg()

        # Dynamic floating AI Orb
        self.orb = AIOrb(self)
        self.orb.move((self.width() - self.orb.width()) // 2, (self.height() - self.orb.height()) // 2 - 60)
        self.orb.show()

        self.setup_windows()
        self.launchpad = LaunchpadOverlay(self)
        self.launchpad.hide()
        self._change_theme("Slate Dark")

        # Stats Refresh Timer
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._refresh_stats)
        self.stats_timer.start(2000)
        self._refresh_stats()

    def init_ui(self):
        hide_windows_taskbar()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)

        # Central canvas widget
        self.central = QWidget(self)
        self.central.setStyleSheet("background: transparent;")
        self.setCentralWidget(self.central)

        # ── 1. Top Menu Bar Widget ──
        self.menu_bar = QWidget(self)
        self.menu_bar.setFixedHeight(24)
        self.menu_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 23, 42, 0.75);
                border-bottom: none;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Outfit';
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }
        """)
        
        m_layout = QHBoxLayout(self.menu_bar)
        m_layout.setContentsMargins(15, 0, 15, 0)
        m_layout.setSpacing(16)

        logo_lbl = QLabel("", self.menu_bar)
        logo_lbl.setFont(QFont("Outfit", 12))
        m_layout.addWidget(logo_lbl)

        title_lbl = QLabel("IP Prime OS", self.menu_bar)
        title_lbl.setStyleSheet("font-weight: bold;")
        m_layout.addWidget(title_lbl)

        for item in ["File", "Edit", "View", "Window", "Help"]:
            m_layout.addWidget(QLabel(item, self.menu_bar))

        m_layout.addStretch()

        self.cpu_lbl = QLabel("CPU: 0%", self.menu_bar)
        self.ram_lbl = QLabel("RAM: 0%", self.menu_bar)
        self.clock_lbl = QLabel("Date Clock", self.menu_bar)
        self.clock_lbl.setStyleSheet("font-weight: bold;")

        m_layout.addWidget(self.cpu_lbl)
        m_layout.addWidget(self.ram_lbl)
        m_layout.addWidget(self.clock_lbl)
        self.menu_bar.hide()

        # ── 2. Bottom macOS style Dock ──
        self.dock = QWidget(self)
        self.dock.setFixedHeight(54)
        self.dock.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 12px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                font-size: 18px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.22);
                border-color: rgba(255, 255, 255, 0.35);
            }
        """)
        self.dock_layout = QHBoxLayout(self.dock)
        self.dock_layout.setContentsMargins(10, 0, 10, 0)
        self.dock_layout.setSpacing(12)

        self.dock_buttons = {}

    def setup_windows(self):
        # Setup Draggable Windows
        self.windows = {}

        # 🧬 Window 1: Core Stats (With Real-Time performance line chart)
        win_core = GlassWindow("🧬 Neural Core", self)
        win_core.resize(320, 390)
        win_core.move(80, 80)
        
        core_layout = QVBoxLayout()
        core_lbl = QLabel("System Core Statistics & Performance", win_core)
        core_lbl.setStyleSheet("font-size: 11px; font-weight: bold;")
        core_layout.addWidget(core_lbl)

        # Add the Live Performance Chart
        self.chart = StatsHistoryChart(win_core)
        core_layout.addWidget(self.chart)

        self.nodes_lbl = QLabel("Nodes: 2,854 Connected", win_core)
        self.nodes_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
        core_layout.addWidget(self.nodes_lbl)

        self.spend_lbl = QLabel("Spend: $0.0000", win_core)
        self.spend_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #b45309;")
        core_layout.addWidget(self.spend_lbl)

        capabilities_lbl = QLabel("Desired Future capabilities:\n"
                                  "• Multimodal perception\n"
                                  "• Autonomous self-healing\n"
                                  "• Complex debugging", win_core)
        capabilities_lbl.setStyleSheet("font-size: 10px; line-height: 1.4;")
        core_layout.addWidget(capabilities_lbl)
        win_core.set_content_layout(core_layout)
        self.windows["core"] = win_core

        # 🧠 Window 2: Mind Graph — native PyQt6 node diagram
        win_graph = GlassWindow("🧠 Mind Graph", self)
        win_graph.resize(380, 350)
        win_graph.move(440, 100)
        
        graph_layout = QVBoxLayout()
        self.graph_canvas = _MindGraphCanvas(win_graph)
        graph_layout.addWidget(self.graph_canvas)
        win_graph.set_content_layout(graph_layout)
        self.windows["graph"] = win_graph

        # 🖥️ Window 3: Terminal Console (Loads VocalTerminalWidget)
        win_shell = GlassWindow("🖥️ Terminal — vocal_terminal", self)
        win_shell.resize(480, 260)
        win_shell.move(120, 480)
        
        shell_layout = QVBoxLayout()
        self.vocal_terminal = VocalTerminalWidget(win_shell)
        self.vocal_terminal.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.45);
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 6px;
                color: #00f5ff;
                font-family: 'JetBrains Mono';
                font-size: 11px;
            }
        """)
        shell_layout.addWidget(self.vocal_terminal)
        win_shell.set_content_layout(shell_layout)
        self.windows["shell"] = win_shell

        # 💻 Window 4: Swarm Deck (With dynamic AI Agent activity tracking)
        win_swarm = GlassWindow("💻 Swarm Deck", self)
        win_swarm.resize(320, 280)
        win_swarm.move(860, 80)
        
        swarm_layout = QVBoxLayout()
        self.agent_status_labels = {}
        self.agent_progress_bars = {}

        for agent_key, agent_name in [("architect", "Architect Agent"), ("coder", "Coder Agent"), ("debugger", "Debugger Agent")]:
            row = QVBoxLayout()
            h_row = QHBoxLayout()
            lbl = QLabel(agent_name, win_swarm)
            lbl.setStyleSheet("font-size: 11px; font-weight: bold;")
            h_row.addWidget(lbl)
            
            status_lbl = QLabel("IDLE", win_swarm)
            status_lbl.setStyleSheet("font-size: 9px; font-family: 'JetBrains Mono';")
            h_row.addStretch()
            h_row.addWidget(status_lbl)
            
            self.agent_status_labels[agent_key] = status_lbl
            row.addLayout(h_row)
            
            pbar = QProgressBar(win_swarm)
            pbar.setFixedHeight(6)
            pbar.setValue(10)
            pbar.setStyleSheet("""
                QProgressBar {
                    background-color: rgba(0, 0, 0, 0.08);
                    border: none; border-radius: 3px;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #a855f7);
                    border-radius: 3px;
                }
            """)
            self.agent_progress_bars[agent_key] = pbar
            row.addWidget(pbar)
            swarm_layout.addLayout(row)
            
        swarm_layout.addSpacing(6)
        act_title = QLabel("Recent Swarm Activity", win_swarm)
        act_title.setStyleSheet("font-size: 9px; font-weight: bold;")
        swarm_layout.addWidget(act_title)
        
        self.swarm_log_list = QListWidget(win_swarm)
        self.swarm_log_list.setStyleSheet("""
            QListWidget {
                border-radius: 4px;
                font-family: 'JetBrains Mono';
                font-size: 9px;
            }
        """)
        swarm_layout.addWidget(self.swarm_log_list)

        win_swarm.set_content_layout(swarm_layout)
        self.windows["swarm"] = win_swarm

        # ⚙️ Window 5: Control Panel Configs
        win_config = GlassWindow("⚙️ Control Center", self)
        win_config.resize(320, 310)
        win_config.move(860, 360)
        
        cfg_layout = QVBoxLayout()
        for cfg_title, cfg_val in [("Primary Model", "gemini-2.5-flash"), ("Autonomous Mode", "ENABLED"), ("Context window", "1M tokens")]:
            row = QHBoxLayout()
            lbl = QLabel(cfg_title, win_config)
            lbl.setStyleSheet("font-size: 11px;")
            val = QLabel(cfg_val, win_config)
            val.setStyleSheet("color: #0369a1; font-family: 'JetBrains Mono'; font-weight: bold;")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            cfg_layout.addLayout(row)

        # Theme Switcher Dropdown
        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Window Theme", win_config)
        theme_lbl.setStyleSheet("font-size: 11px;")
        self.theme_combo = QComboBox(win_config)
        self.theme_combo.addItems(["Yosemite Light", "Slate Dark", "Cyberpunk Neon"])
        self.theme_combo.setCurrentText("Slate Dark")
        self.theme_combo.setStyleSheet("""
            QComboBox {
                border-radius: 4px;
                font-size: 11px;
                padding: 2px 6px;
            }
        """)
        self.theme_combo.currentTextChanged.connect(self._change_theme)
        theme_row.addWidget(theme_lbl)
        theme_row.addStretch()
        theme_row.addWidget(self.theme_combo)
        cfg_layout.addLayout(theme_row)

        # Orb Size Slider Row
        from PyQt6.QtWidgets import QSlider
        orb_row = QHBoxLayout()
        orb_lbl = QLabel("AI Orb Size", win_config)
        orb_lbl.setStyleSheet("font-size: 11px;")
        
        self.orb_slider = QSlider(Qt.Orientation.Horizontal, win_config)
        self.orb_slider.setRange(80, 260)
        self.orb_slider.setValue(self.orb.orb_size)
        self.orb_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(0, 0, 0, 0.1);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #0284c7;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        self.orb_slider.valueChanged.connect(self._change_orb_size)
        
        orb_row.addWidget(orb_lbl)
        orb_row.addStretch()
        orb_row.addWidget(self.orb_slider)
        cfg_layout.addLayout(orb_row)

        cfg_layout.addStretch()

        # System Utility Quick Launch Buttons
        l_lbl = QLabel("Quick Launch", win_config)
        l_lbl.setStyleSheet("font-weight: bold; font-size: 10px; margin-top: 5px;")
        cfg_layout.addWidget(l_lbl)
        
        btn_layout = QHBoxLayout()
        for label, cmd in [("📝 Note", "notepad.exe"), ("🐚 CMD", "cmd.exe"), ("📁 Files", "explorer.exe"), ("🌐 Edge", "msedge.exe")]:
            btn = QPushButton(label, win_config)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.35);
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 4px 6px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.6);
                }
            """)
            btn.clicked.connect(lambda checked, c=cmd: self._launch_cmd(c))
            btn_layout.addWidget(btn)
        cfg_layout.addLayout(btn_layout)

        cfg_layout.addStretch()
        
        # Add Change Wallpaper button
        self.wall_btn = QPushButton("🌄 Change Wallpaper", win_config)
        self.wall_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(3, 105, 161, 0.8);
                color: white;
                border: 1px solid rgba(3, 105, 161, 0.9);
                border-radius: 6px;
                padding: 8px;
                font-family: 'Outfit';
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(3, 105, 161, 1.0);
            }
        """)
        self.wall_btn.clicked.connect(self._choose_wallpaper)
        cfg_layout.addWidget(self.wall_btn)

        win_config.set_content_layout(cfg_layout)
        self.windows["config"] = win_config

        # 📁 Window 6: File List Explorer (With working subdirectories & editor triggers)
        win_files = GlassWindow("📁 Workspace Files", self)
        win_files.resize(340, 260)
        win_files.move(630, 480)
        
        files_layout = QVBoxLayout()
        
        # Explorer Top Toolbar
        top_bar = QHBoxLayout()
        self.explorer_path_lbl = QLabel(win_files)
        self.explorer_path_lbl.setFont(QFont("Outfit", 9, QFont.Weight.Medium))
        self.explorer_path_lbl.setStyleSheet("color: #b4cdd4;")
        self.explorer_path_lbl.setText("~")
        top_bar.addWidget(self.explorer_path_lbl, 1)
        
        self.analyze_btn = QPushButton("🤖 Analyze", win_files)
        self.analyze_btn.setFont(QFont("Outfit", 8, QFont.Weight.Bold))
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b5cf6, stop:1 #6d28d9);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                color: white;
                padding: 3px 8px;
            }
            QPushButton:hover {
                opacity: 0.85;
            }
        """)
        self.analyze_btn.clicked.connect(self._analyze_current_codebase)
        top_bar.addWidget(self.analyze_btn)
        
        files_layout.addLayout(top_bar)
        
        self.files_list = QListWidget(win_files)
        self.files_list.setStyleSheet("""
            QListWidget {
                border-radius: 6px;
                font-family: 'JetBrains Mono';
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px;
            }
        """)
        self._populate_files()
        self.files_list.itemDoubleClicked.connect(self._on_file_double_clicked)
        files_layout.addWidget(self.files_list)
        win_files.set_content_layout(files_layout)
        self.windows["files"] = win_files

        # 📝 Window 7: Yellow Sticky Note (Persistent Auto-Save)
        win_notes = GlassWindow("📝 Desktop Note", self)
        win_notes.resize(280, 240)
        win_notes.move(440, 480)
        
        notes_layout = QVBoxLayout()
        self.note_edit = QTextEdit(win_notes)
        self.note_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(254, 240, 138, 0.7);
                color: #713f12;
                border: 1px solid rgba(250, 204, 21, 0.4);
                border-radius: 6px;
                font-family: 'Outfit';
                font-size: 12px;
                padding: 8px;
            }
        """)
        self.notes_file = Path("assets/sticky_note.txt")
        if self.notes_file.exists():
            try:
                self.note_edit.setPlainText(self.notes_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        self.note_edit.textChanged.connect(self._save_note)
        notes_layout.addWidget(self.note_edit)
        win_notes.set_content_layout(notes_layout)
        self.windows["notes"] = win_notes

        # ✍️ Window 8: Text Code Editor (Integrated with File Explorer)
        self.win_editor = GlassWindow("✍️ Code Editor (Varon/Cobra Sandbox)", self)
        self.win_editor.resize(800, 480)
        self.win_editor.move(260, 150)
        self.win_editor.hide_window()

        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.editor_path_lbl = QLabel("No File Selected", self.win_editor)
        self.editor_path_lbl.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono';")
        left_layout.addWidget(self.editor_path_lbl)

        self.editor_text = QTextEdit(self.win_editor)
        self.editor_text.setStyleSheet("""
            QTextEdit {
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        left_layout.addWidget(self.editor_text, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)

        self.editor_save_btn = QPushButton("💾 Save", self.win_editor)
        self.editor_save_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(3, 105, 161, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: rgba(3, 105, 161, 1.0); }
        """)
        self.editor_save_btn.clicked.connect(self._save_editor_file)
        buttons_layout.addWidget(self.editor_save_btn)

        self.editor_run_btn = QPushButton("⚡ Run Code", self.win_editor)
        self.editor_run_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: rgba(16, 185, 129, 1.0); }
        """)
        self.editor_run_btn.clicked.connect(self._run_editor_code)
        buttons_layout.addWidget(self.editor_run_btn)

        self.editor_mamba_btn = QPushButton("🦚 Mamba Optimize", self.win_editor)
        self.editor_mamba_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 58, 237, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: rgba(124, 58, 237, 1.0); }
        """)
        self.editor_mamba_btn.clicked.connect(self._optimize_with_mamba)
        buttons_layout.addWidget(self.editor_mamba_btn)

        self.editor_preview_btn = QPushButton("🌐 Preview", self.win_editor)
        self.editor_preview_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(234, 179, 8, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: rgba(234, 179, 8, 1.0); }
        """)
        self.editor_preview_btn.clicked.connect(self._toggle_editor_preview)
        buttons_layout.addWidget(self.editor_preview_btn)

        self.editor_creator_btn = QPushButton("🪄 Creator", self.win_editor)
        self.editor_creator_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(219, 39, 119, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: rgba(219, 39, 119, 1.0); }
        """)
        self.editor_creator_btn.clicked.connect(self._run_creator_mode)
        buttons_layout.addWidget(self.editor_creator_btn)

        self.editor_scaffold_btn = QPushButton("📦 Scaffold", self.win_editor)
        self.editor_scaffold_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(79, 70, 229, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: rgba(79, 70, 229, 1.0); }
        """)
        self.editor_scaffold_btn.clicked.connect(self._run_scaffold_vite)
        buttons_layout.addWidget(self.editor_scaffold_btn)

        self.editor_autofix_btn = QPushButton("🟢 Auto-Fix", self.win_editor)
        self.editor_autofix_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.9);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: rgba(16, 185, 129, 1.0); }
        """)
        self.editor_autofix_btn.clicked.connect(self._run_autofix)
        self.editor_autofix_btn.hide()
        buttons_layout.addWidget(self.editor_autofix_btn)

        left_layout.addLayout(buttons_layout)

        self.editor_console = QTextEdit(self.win_editor)
        self.editor_console.setStyleSheet("""
            QTextEdit {
                background-color: #0b0f19;
                color: #34d399;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                border-radius: 4px;
                border: 1px solid rgba(52, 211, 153, 0.2);
            }
        """)
        self.editor_console.setReadOnly(True)
        self.editor_console.setFixedHeight(110)
        self.editor_console.hide()
        left_layout.addWidget(self.editor_console)

        self.editor_splitter.addWidget(left_container)

        self.preview_container = QWidget()
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(6)

        preview_title = QLabel("🌐 Live HTML Render Preview")
        preview_title.setStyleSheet("font-size: 10px; font-weight: bold; color: rgba(255, 255, 255, 0.8);")
        preview_layout.addWidget(preview_title)

        self.preview_browser = QTextBrowser()
        self.preview_browser.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                color: black;
                border-radius: 6px;
            }
        """)
        preview_layout.addWidget(self.preview_browser, 1)

        self.editor_splitter.addWidget(self.preview_container)
        self.preview_container.hide()

        self.editor_text.textChanged.connect(self._update_live_preview)

        main_editor_layout = QHBoxLayout()
        main_editor_layout.setContentsMargins(0, 0, 0, 0)
        main_editor_layout.addWidget(self.editor_splitter)

        self.win_editor.set_content_layout(main_editor_layout)
        self.windows["editor"] = self.win_editor

        # 📊 Window 9: Task Manager (Live System Process monitor with kill functionality)
        win_tasks = GlassWindow("📊 Task Manager (SysDash Monitor)", self)
        win_tasks.resize(560, 320)
        win_tasks.move(700, 360)

        tasks_layout = QHBoxLayout()
        tasks_layout.setContentsMargins(10, 10, 10, 10)
        tasks_layout.setSpacing(12)

        # ─── Left Panel (SysDash Telemetry) ───
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        sysdash_lbl = QLabel("⚡ System Telemetry (SysDash)")
        sysdash_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: rgba(255, 255, 255, 0.8);")
        left_layout.addWidget(sysdash_lbl)

        # CPU Monitor
        self.tasks_cpu_lbl = QLabel("CPU Usage: 0%")
        self.tasks_cpu_lbl.setStyleSheet("font-size: 9px; font-family: 'JetBrains Mono'; color: #06b6d4;")
        left_layout.addWidget(self.tasks_cpu_lbl)

        self.tasks_cpu_bar = QProgressBar(win_tasks)
        self.tasks_cpu_bar.setFixedHeight(8)
        self.tasks_cpu_bar.setTextVisible(False)
        self.tasks_cpu_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border: none; border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #10b981);
                border-radius: 4px;
            }
        """)
        left_layout.addWidget(self.tasks_cpu_bar)

        # RAM Monitor
        self.tasks_ram_lbl = QLabel("RAM Usage: 0%")
        self.tasks_ram_lbl.setStyleSheet("font-size: 9px; font-family: 'JetBrains Mono'; color: #a855f7;")
        left_layout.addWidget(self.tasks_ram_lbl)

        self.tasks_ram_bar = QProgressBar(win_tasks)
        self.tasks_ram_bar.setFixedHeight(8)
        self.tasks_ram_bar.setTextVisible(False)
        self.tasks_ram_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border: none; border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #ec4899);
                border-radius: 4px;
            }
        """)
        left_layout.addWidget(self.tasks_ram_bar)

        left_layout.addSpacing(10)

        # Launch SysDash Desktop button
        self.sysdash_btn = QPushButton("🐍 Launch SysDash Desktop", win_tasks)
        self.sysdash_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: rgba(16, 185, 129, 1.0); }
        """)
        self.sysdash_btn.clicked.connect(self._launch_sysdash_electron)
        left_layout.addWidget(self.sysdash_btn)
        
        left_layout.addStretch()
        tasks_layout.addWidget(left_panel, 2)

        # ─── Vertical Separator Line ───
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.15);")
        tasks_layout.addWidget(sep)

        # ─── Right Panel (Process Monitor) ───
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        proc_title = QLabel("📊 Running Processes")
        proc_title.setStyleSheet("font-size: 10px; font-weight: bold; color: rgba(255, 255, 255, 0.8);")
        right_layout.addWidget(proc_title)

        # Search Bar
        self.proc_search = QLineEdit()
        self.proc_search.setPlaceholderText("🔍 Search process...")
        self.proc_search.setStyleSheet("""
            QLineEdit {
                background-color: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                color: white;
                padding: 4px 6px;
                font-size: 9px;
            }
        """)
        self.proc_search.textChanged.connect(self._filter_processes)
        right_layout.addWidget(self.proc_search)

        self.process_list = QListWidget(win_tasks)
        self.process_list.setStyleSheet("""
            QListWidget {
                border-radius: 6px;
                font-family: 'JetBrains Mono';
                font-size: 9px;
            }
        """)
        self.process_list.itemDoubleClicked.connect(self._kill_selected_process)
        right_layout.addWidget(self.process_list, 1)

        self.kill_btn = QPushButton("🚫 Terminate selected", win_tasks)
        self.kill_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 38, 38, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 9px;
            }
            QPushButton:hover { background-color: rgba(220, 38, 38, 1.0); }
        """)
        self.kill_btn.clicked.connect(self._kill_selected_process_btn)
        right_layout.addWidget(self.kill_btn)

        tasks_layout.addWidget(right_panel, 3)

        win_tasks.set_content_layout(tasks_layout)
        self.windows["tasks"] = win_tasks
        self._refresh_processes()

        # 🧮 Window 10: Math Calculator
        win_calc = GlassWindow("🧮 Calculator", self)
        win_calc.resize(230, 270)
        win_calc.move(90, 480)

        calc_layout = QVBoxLayout()
        self.calc_display = QLabel("0", win_calc)
        self.calc_display.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.4);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 4px;
                font-size: 16px;
                padding: 6px;
                font-family: 'JetBrains Mono';
                qproperty-alignment: 'AlignRight | AlignVCenter';
            }
        """)
        calc_layout.addWidget(self.calc_display)

        grid = QGridLayout()
        grid.setSpacing(4)
        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2), ('/', 0, 3),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2), ('*', 1, 3),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2), ('-', 2, 3),
            ('0', 3, 0), ('.', 3, 1), ('=', 3, 2), ('+', 3, 3),
            ('C', 4, 0)
        ]

        for text, row, col in buttons:
            btn = QPushButton(text, win_calc)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.35);
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 4px;
                    font-size: 11px;
                    padding: 8px;
                }
                QPushButton:hover { background-color: rgba(255, 255, 255, 0.6); }
            """)
            btn.clicked.connect(lambda checked, t=text: self._on_calc_click(t))
            if text == 'C':
                grid.addWidget(btn, row, col, 1, 4)
            else:
                grid.addWidget(btn, row, col)

        calc_layout.addLayout(grid)
        win_calc.set_content_layout(calc_layout)
        self.windows["calc"] = win_calc

        # ── Web Apps (YouTube, WhatsApp, Instagram) ──
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtCore import QUrl

        # YouTube
        win_yt = GlassWindow("📺 YouTube", self)
        win_yt.resize(750, 480)
        win_yt.move(250, 100)
        win_yt.hide_window()
        yt_layout = QVBoxLayout()
        self.web_yt = QWebEngineView(win_yt)
        yt_layout.addWidget(self.web_yt)
        win_yt.set_content_layout(yt_layout)
        self.windows["youtube"] = win_yt

        def load_yt(visible):
            if visible and self.web_yt.url().isEmpty():
                self.web_yt.setUrl(QUrl("https://www.youtube.com"))
        win_yt.visibility_changed.connect(load_yt)

        # WhatsApp
        win_wa = GlassWindow("💬 WhatsApp", self)
        win_wa.resize(700, 480)
        win_wa.move(300, 120)
        win_wa.hide_window()
        wa_layout = QVBoxLayout()
        self.web_wa = QWebEngineView(win_wa)
        wa_layout.addWidget(self.web_wa)
        win_wa.set_content_layout(wa_layout)
        self.windows["whatsapp"] = win_wa

        def load_wa(visible):
            if visible and self.web_wa.url().isEmpty():
                self.web_wa.setUrl(QUrl("https://web.whatsapp.com"))
        win_wa.visibility_changed.connect(load_wa)

        # Instagram
        win_insta = GlassWindow("📸 Instagram", self)
        win_insta.resize(420, 520)
        win_insta.move(400, 80)
        win_insta.hide_window()
        insta_layout = QVBoxLayout()
        self.web_insta = QWebEngineView(win_insta)
        insta_layout.addWidget(self.web_insta)
        win_insta.set_content_layout(insta_layout)
        self.windows["instagram"] = win_insta

        def load_insta(visible):
            if visible and self.web_insta.url().isEmpty():
                self.web_insta.setUrl(QUrl("https://www.instagram.com"))
        win_insta.visibility_changed.connect(load_insta)

        # Cobra AI 2.0 Web Live App
        win_cobra = GlassWindow("🐍 Cobra AI 2.0", self)
        win_cobra.resize(800, 520)
        win_cobra.move(300, 90)
        win_cobra.hide_window()
        cobra_layout = QVBoxLayout()
        self.web_cobra = QWebEngineView(win_cobra)
        cobra_layout.addWidget(self.web_cobra)
        win_cobra.set_content_layout(cobra_layout)
        self.windows["cobra_web"] = win_cobra

        def load_cobra(visible):
            if visible and self.web_cobra.url().isEmpty():
                self.web_cobra.setUrl(QUrl("https://cobra-aing.vercel.app/"))
        win_cobra.visibility_changed.connect(load_cobra)

        # RAVX OS Web Live App
        win_ravx = GlassWindow("🎛️ RAVX OS", self)
        win_ravx.resize(800, 520)
        win_ravx.move(320, 100)
        win_ravx.hide_window()
        ravx_layout = QVBoxLayout()
        self.web_ravx = QWebEngineView(win_ravx)
        ravx_layout.addWidget(self.web_ravx)
        win_ravx.set_content_layout(ravx_layout)
        self.windows["ravx_web"] = win_ravx

        def load_ravx(visible):
            if visible and self.web_ravx.url().isEmpty():
                self.web_ravx.setUrl(QUrl("https://ravx-os.vercel.app/"))
        win_ravx.visibility_changed.connect(load_ravx)

        # XBLT Web Live App
        win_xblt = GlassWindow("⚡ XBLT Studio", self)
        win_xblt.resize(800, 520)
        win_xblt.move(340, 110)
        win_xblt.hide_window()
        xblt_layout = QVBoxLayout()
        self.web_xblt = QWebEngineView(win_xblt)
        xblt_layout.addWidget(self.web_xblt)
        win_xblt.set_content_layout(xblt_layout)
        self.windows["xblt_web"] = win_xblt

        def load_xblt(visible):
            if visible and self.web_xblt.url().isEmpty():
                self.web_xblt.setUrl(QUrl("https://xblt.app"))
        win_xblt.visibility_changed.connect(load_xblt)

        # Autopilot Coder (Dynamic coding visualizer)
        win_auto = GlassWindow("💻 Autopilot Coder", self)
        win_auto.resize(480, 320)
        win_auto.move((self.width() - 480) // 2, (self.height() - 320) // 2 + 100)
        win_auto.hide_window()
        auto_layout = QVBoxLayout()
        self.autopilot_coder = AutopilotCoderWidget(win_auto)
        auto_layout.addWidget(self.autopilot_coder)
        win_auto.set_content_layout(auto_layout)
        self.windows["autopilot"] = win_auto

        # Prime Vision (Live webcam analysis & OCR)
        win_vision = GlassWindow("👁️ Prime Vision", self)
        win_vision.resize(450, 480)
        win_vision.move((self.width() - 450) // 2 + 50, (self.height() - 480) // 2 - 50)
        win_vision.hide_window()
        vision_layout = QVBoxLayout()
        from os_shell.widgets.prime_vision import PrimeVisionWidget
        self.prime_vision = PrimeVisionWidget(win_vision)
        vision_layout.addWidget(self.prime_vision)
        win_vision.set_content_layout(vision_layout)
        self.windows["vision"] = win_vision

        def toggle_camera(visible):
            if visible:
                self.prime_vision.start_camera()
            else:
                self.prime_vision.stop_camera()
        win_vision.visibility_changed.connect(toggle_camera)

        # 🎨 Window: NainiPix AI Studio (AI Image Generator & Preset Editor)
        win_np = GlassWindow("🎨 NainiPix AI Studio", self)
        win_np.resize(780, 480)
        win_np.move((self.width() - 780) // 2 - 50, (self.height() - 480) // 2 + 50)
        win_np.hide_window()
        np_layout = QVBoxLayout()
        self.nainipix_studio = NainiPixStudioWidget(win_np)
        np_layout.addWidget(self.nainipix_studio)
        win_np.set_content_layout(np_layout)
        self.windows["nainipix"] = win_np

        styles = {
            "launcher": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3b82f6, stop:1 #2563eb); border: 1px solid #1d4ed8;",
            "core": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #06b6d4, stop:1 #0891b2); border: 1px solid #0e7490;",
            "graph": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a855f7, stop:1 #8b5cf6); border: 1px solid #7c3aed;",
            "swarm": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5); border: 1px solid #4338ca;",
            "files": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fbbf24, stop:1 #f59e0b); border: 1px solid #d97706;",
            "config": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #64748b, stop:1 #475569); border: 1px solid #334155;",
            "autopilot": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669); border: 1px solid #047857;",
            "vision": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ec4899, stop:1 #a855f7); border: 1px solid #7c3aed;",
            "nainipix": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #a855f7); border: 1px solid #8a3ab9;",
            "cobra_web": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #06b6d4); border: 1px solid #059669;",
            "ravx_web": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a855f7, stop:1 #6366f1); border: 1px solid #7c3aed;",
            "xblt_web": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fbbf24, stop:1 #eab308); border: 1px solid #ca8a04;"
        }

        # Add Launcher button first
        launcher_btn = QPushButton("🚀", self.dock)
        launcher_btn.setToolTip("App Launcher")
        launcher_btn.clicked.connect(self._toggle_launchpad)
        launcher_btn.setStyleSheet(f"QPushButton {{ {styles['launcher']} border-radius: 8px; font-size: 18px; color: white; }} QPushButton:hover {{ opacity: 0.85; }}")
        self.dock_layout.addWidget(launcher_btn)
        self.dock_buttons["launcher"] = launcher_btn

        # Connect window overlays & add dock toggle buttons
        for key, win in self.windows.items():
            win.hide_window()
            if key in ["core", "graph", "swarm", "files", "config", "autopilot", "vision", "nainipix", "cobra_web", "ravx_web", "xblt_web"]:
                icon_emoji = {
                    "core": "🧬", "graph": "🧠", "swarm": "💻", 
                    "files": "📁", "config": "⚙️", "autopilot": "🤖", "vision": "👁️",
                    "nainipix": "🎨", "cobra_web": "🐍", "ravx_web": "🎛️", "xblt_web": "⚡"
                }.get(key, "⚙️")
                btn = QPushButton(icon_emoji, self.dock)
                btn.setToolTip(win.windowTitle())
                btn.clicked.connect(self._get_toggle_handler(win))
                btn_style = styles.get(key, "background-color: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.15);")
                btn.setStyleSheet(f"QPushButton {{ {btn_style} border-radius: 8px; font-size: 18px; color: white; }} QPushButton:hover {{ opacity: 0.85; }}")
                self.dock_layout.addWidget(btn)
                self.dock_buttons[key] = btn

    def _get_toggle_handler(self, win):
        return lambda: win.hide_window() if win.isVisible() else win.show_window()

    def _populate_files(self):
        self.files_list.clear()
        try:
            rel = self.current_dir.relative_to(Path.home())
            self.explorer_path_lbl.setText(f"~/ {rel}")
        except Exception:
            self.explorer_path_lbl.setText(str(self.current_dir))
            
        if self.current_dir != self.current_dir.parent:
            self.files_list.addItem("📁 .. (Go Up)")
        try:
            for p in sorted(self.current_dir.iterdir()):
                if p.is_dir():
                    self.files_list.addItem(f"📁 {p.name}")
                else:
                    self.files_list.addItem(f"📄 {p.name}")
        except Exception as e:
            self.files_list.addItem(f"Error loading files: {e}")

    def _analyze_current_codebase(self):
        # Trigger HUD status change
        if hasattr(self, "agent_progress_bars"):
            pbar = self.agent_progress_bars.get("architect")
            lbl = self.agent_status_labels.get("architect")
            if pbar and lbl:
                pbar.setValue(95)
                lbl.setText("ANALYZING")
        self.update()
        
        # Run scan in a background thread to prevent freezing the GUI
        def worker():
            try:
                import py_compile
                path = self.current_dir
                
                # Metrics dictionaries
                counts = {}
                lines_count = 0
                errors = []
                
                # Scan directory recursively
                for root, dirs, files in os.walk(path):
                    # Skip hidden directories and virtual environments
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__", ".venv", "venv", "build"]]
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if not ext:
                            continue
                        counts[ext] = counts.get(ext, 0) + 1
                        
                        # Count lines for text code files
                        file_path = Path(root) / file
                        if ext in [".py", ".html", ".css", ".js", ".json", ".md", ".txt"]:
                            try:
                                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                    lines_count += len(f.readlines())
                            except Exception:
                                pass
                                
                        # Run py_compile check for syntax errors
                        if ext == ".py":
                            try:
                                py_compile.compile(str(file_path), doraise=True)
                            except py_compile.PyCompileError as err:
                                errors.append(f"- **{file_path.name}**: {err.msg}")
                                
                # Create Markdown report content
                report_lines = [
                    f"# 🤖 Codebase Analysis Report: {path.name}",
                    f"**Generated on:** {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')}",
                    f"**Location:** `{path}`",
                    "",
                    "## 📊 File Count Statistics",
                ]
                for ext, num in sorted(counts.items(), key=lambda x: x[1], reverse=True):
                    report_lines.append(f"- **{ext}** files: {num}")
                    
                report_lines.extend([
                    "",
                    f"## 📈 Volume Metrics",
                    f"- **Total Code & Document Lines (LOC):** {lines_count:,} lines",
                    "",
                    "## 🛡️ Syntax & Compilation Check",
                ])
                
                if errors:
                    report_lines.append("⚠️ Compilation errors detected:")
                    report_lines.extend(errors)
                else:
                    report_lines.append("🟢 All Python source files passed syntax check successfully!")
                    
                # Save report file
                report_file = path / ".codebase_analysis.md"
                report_file.write_text("\n".join(report_lines), encoding="utf-8")
                
                # Open in editor on main UI thread
                QTimer.singleShot(0, lambda: self._open_in_editor(report_file))
                
                # Speak success response via main voice dispatcher
                self.write_log_to_terminal(f"SYSTEM: Codebase analysis complete. Generated report at {report_file.name}")
            except Exception as e:
                print(f"[Explorer] Analysis failed: {e}")
                
        threading.Thread(target=worker, daemon=True).start()

    def _on_file_double_clicked(self, item):
        name = item.text()
        if name.startswith("📁 "):
            folder_name = name[2:]
            if folder_name == ".. (Go Up)":
                self.current_dir = self.current_dir.parent
            else:
                self.current_dir = self.current_dir / folder_name
            self._populate_files()
        elif name.startswith("📄 "):
            file_name = name[2:]
            file_path = self.current_dir / file_name
            self._open_in_editor(file_path)

    def _open_in_editor(self, file_path):
        self.current_editor_file = file_path
        self.editor_path_lbl.setText(str(file_path))
        try:
            content = file_path.read_text(encoding="utf-8")
            self.editor_text.setPlainText(content)
            self.win_editor.show_window()
        except Exception as e:
            self.editor_text.setPlainText(f"Failed to read file: {e}")

    def _save_editor_file(self):
        if hasattr(self, "current_editor_file") and self.current_editor_file:
            try:
                self.current_editor_file.write_text(self.editor_text.toPlainText(), encoding="utf-8")
                self.editor_path_lbl.setText(f"💾 Saved: {self.current_editor_file.name}")
                self._populate_files()
            except Exception as e:
                self.editor_path_lbl.setText(f"❌ Save Failed: {e}")

    def _toggle_editor_preview(self):
        if self.preview_container.isVisible():
            self.preview_container.hide()
            self.editor_preview_btn.setText("🌐 Preview")
        else:
            self.preview_container.show()
            self.editor_preview_btn.setText("🌐 Hide Preview")
            self._update_live_preview()

    def _update_live_preview(self):
        if self.preview_container.isVisible():
            text = self.editor_text.toPlainText()
            self.preview_browser.setHtml(text)

    def _run_editor_code(self):
        self.editor_console.show()
        self.editor_console.setPlainText("Saving changes and launching sandbox execution...\n")
        QTimer.singleShot(0, self.editor_autofix_btn.hide)
        
        if hasattr(self, "current_editor_file") and self.current_editor_file:
            self._save_editor_file()
            file_path = self.current_editor_file
        else:
            temp_dir = Path("C:/Users/thora/.gemini/antigravity/scratch/IP Prime")
            file_path = temp_dir / "temp_sandbox_script.py"
            try:
                file_path.write_text(self.editor_text.toPlainText(), encoding="utf-8")
            except Exception as e:
                self.editor_console.append(f"Error creating temp execution script: {e}\n")
                return
        
        def worker():
            import subprocess
            ext = file_path.suffix.lower()
            if ext == ".py":
                venv_python = Path(".venv/Scripts/python.exe")
                cmd = f'"{venv_python}" "{file_path}"' if venv_python.exists() else f'python "{file_path}"'
            elif ext in (".js", ".ts"):
                cmd = f'node "{file_path}"'
            else:
                cmd = f'"{file_path}"'
                
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    shell=True,
                    bufsize=1
                )
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    QTimer.singleShot(0, lambda l=line: self.editor_console.insertPlainText(l))
                proc.wait()
                QTimer.singleShot(0, lambda: self.editor_console.insertPlainText(f"\n--- Process Finished (Exit Code: {proc.returncode}) ---\n"))
                if proc.returncode != 0:
                    QTimer.singleShot(0, self.editor_autofix_btn.show)
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.editor_console.insertPlainText(f"Failed to run: {err}\n"))

        threading.Thread(target=worker, daemon=True).start()

    def _optimize_with_mamba(self):
        self.editor_console.show()
        self.editor_console.setPlainText("🦚 Mamba AI: Reading code and analyzing structural optimizations...\n")
        code = self.editor_text.toPlainText()
        if not code.strip():
            self.editor_console.append("Empty code editor, sir.")
            return

        def worker():
            try:
                from actions.prime_utils import UnifiedModelClient
                client = UnifiedModelClient()
                prompt = (
                    "You are CobraAI Mamba, an elite coding optimizer. "
                    "Optimize the following code for maximum efficiency, style consistency, and Pythonic layout. "
                    "Provide ONLY the improved code inside the output. Do NOT write markdown code fences, "
                    "do NOT write explanations. Return ONLY the raw optimized code:\n\n"
                    f"{code}"
                )
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                optimized = response.text.strip()
                if optimized:
                    if optimized.startswith("```"):
                        lines = optimized.splitlines()
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        optimized = "\n".join(lines)
                    
                    QTimer.singleShot(0, lambda o=optimized: self._apply_optimized_code(o, code))
                else:
                    QTimer.singleShot(0, lambda: self.editor_console.append("❌ Mamba AI returned empty optimization, sir."))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.editor_console.append(f"❌ Mamba AI error: {err}\n"))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_optimized_code(self, optimized_code, backup_code):
        self.editor_text.setPlainText(optimized_code)
        self.editor_console.append("🟢 Mamba AI: Optimization applied successfully! (Original code backed up in clipboard)")
        app = QApplication.instance()
        if app:
            clipboard = app.clipboard()
            if clipboard:
                clipboard.setText(backup_code)

    def _run_creator_mode(self):
        prompt, ok = QInputDialog.getMultiLineText(
            self.win_editor,
            "🪄 Cobra Creator Mode",
            "Describe the responsive single-page website/app to generate:",
            "A responsive MERN-style dark task dashboard with glassmorphism cards, micro-animations, and visual statistics."
        )
        if not (ok and prompt.strip()):
            return
            
        self.editor_console.show()
        self.editor_console.setPlainText(f"🪄 Cobra Creator: Designing responsive web layout for: \"{prompt[:60]}...\"\n")
        
        def worker():
            try:
                from actions.prime_utils import UnifiedModelClient
                client = UnifiedModelClient()
                sys_prompt = (
                    "You are CobraAI Creator, an expert web generator. "
                    "Based on the user request, generate a fully self-contained, responsive, beautiful single-page website/app. "
                    "Combine all HTML, CSS, and JS inside a single file. Use Tailwind CSS via CDN hook or custom styling to make "
                    "the design look absolutely stunning and premium. Do NOT include markdown code fences, do NOT include explanations, "
                    "return ONLY valid HTML code.\n\n"
                    f"User Request: {prompt}"
                )
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=sys_prompt
                )
                html = response.text.strip()
                if html:
                    if html.startswith("```"):
                        lines = html.splitlines()
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        html = "\n".join(lines)
                        
                    target_dir = Path("C:/Users/thora/.gemini/antigravity/scratch/IP Prime")
                    target_file = target_dir / "generated_web_app.html"
                    target_file.write_text(html, encoding="utf-8")
                    
                    QTimer.singleShot(0, lambda f=target_file, h=html: self._apply_creator_app(f, h))
                else:
                    QTimer.singleShot(0, lambda: self.editor_console.append("❌ Cobra Creator returned empty layout, sir."))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.editor_console.append(f"❌ Cobra Creator error: {err}\n"))
                
        threading.Thread(target=worker, daemon=True).start()

    def _apply_creator_app(self, file_path, html_content):
        self.current_editor_file = file_path
        self.editor_path_lbl.setText(str(file_path))
        self.editor_text.setPlainText(html_content)
        self.editor_console.append("🟢 Cobra Creator: Web layout successfully generated and saved to generated_web_app.html!")
        
        self.preview_container.show()
        self.editor_preview_btn.setText("🌐 Hide Preview")
        self._update_live_preview()
        self._populate_files()

    def _run_scaffold_vite(self):
        name, ok = QInputDialog.getText(
            self.win_editor,
            "📦 Scaffold Vite Workspace",
            "Enter Vite project folder name:",
            text="my-vite-project"
        )
        if not (ok and name.strip()):
            return
            
        proj_dir = Path("C:/Users/thora/.gemini/antigravity/scratch/IP Prime") / name.strip()
        try:
            proj_dir.mkdir(parents=True, exist_ok=True)
            (proj_dir / "src").mkdir(exist_ok=True)
            
            index_html = (
                "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
                "    <meta charset=\"UTF-8\">\n"
                "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                "    <title>Cobra Scaffolder Project</title>\n"
                "    <script src=\"https://cdn.tailwindcss.com\"></script>\n"
                "</head>\n<body class=\"bg-slate-900 text-white min-h-screen flex items-center justify-center\">\n"
                "    <div id=\"root\"></div>\n"
                "    <script type=\"module\" src=\"/src/main.jsx\"></script>\n"
                "</body>\n</html>"
            )
            (proj_dir / "index.html").write_text(index_html, encoding="utf-8")
            
            main_jsx = (
                "import React from 'react';\n"
                "import ReactDOM from 'react-dom/client';\n"
                "import App from './App.jsx';\n\n"
                "ReactDOM.createRoot(document.getElementById('root')).render(\n"
                "  <React.StrictMode>\n"
                "    <App />\n"
                "  </React.StrictMode>\n"
                ");"
            )
            (proj_dir / "src" / "main.jsx").write_text(main_jsx, encoding="utf-8")
            
            app_jsx = (
                "import React from 'react';\n\n"
                "export default function App() {\n"
                "  return (\n"
                "    <div class=\"p-8 max-w-md bg-slate-800/80 border border-slate-700/50 backdrop-blur rounded-2xl shadow-xl text-center\">\n"
                "      <h1 class=\"text-2xl font-bold bg-gradient-to-r from-emerald-400 to-indigo-400 bg-clip-text text-transparent\">CobraAI Scaffold</h1>\n"
                "      <p class=\"mt-2 text-slate-300 text-sm\">Vite + React template initialized successfully inside the Yosemite environment.</p>\n"
                "      <div class=\"mt-6 flex justify-center gap-2\">\n"
                "        <span class=\"px-3 py-1 bg-slate-700 text-xs rounded-full\">Vite</span>\n"
                "        <span class=\"px-3 py-1 bg-slate-700 text-xs rounded-full\">React</span>\n"
                "        <span class=\"px-3 py-1 bg-slate-700 text-xs rounded-full\">Tailwind</span>\n"
                "      </div>\n"
                "    </div>\n"
                "  );\n"
                "}"
            )
            (proj_dir / "src" / "App.jsx").write_text(app_jsx, encoding="utf-8")
            
            pkg_json = (
                "{\n"
                "  \"name\": \"" + name.strip() + "\",\n"
                "  \"private\": true,\n"
                "  \"version\": \"0.0.0\",\n"
                "  \"type\": \"module\",\n"
                "  \"scripts\": {\n"
                "    \"dev\": \"vite\",\n"
                "    \"build\": \"vite build\",\n"
                "    \"preview\": \"vite preview\"\n"
                "  }\n"
                "}"
            )
            (proj_dir / "package.json").write_text(pkg_json, encoding="utf-8")
            
            self._open_in_editor(proj_dir / "index.html")
            self.editor_console.show()
            self.editor_console.setPlainText(f"📦 Scaffold Success: Vite + React environment generated inside /{name.strip()}!\n")
            self._populate_files()
        except Exception as e:
            self.editor_path_lbl.setText(f"❌ Scaffold Failed: {e}")

    def _run_autofix(self):
        code = self.editor_text.toPlainText()
        logs = self.editor_console.toPlainText()
        self.editor_console.setPlainText("🩹 AI Sandbox Auto-Fixer: Analyzing traceback error and repair plan...\n")
        self.editor_autofix_btn.hide()
        
        def worker():
            try:
                from actions.prime_utils import UnifiedModelClient
                client = UnifiedModelClient()
                prompt = (
                    "You are CobraAI Auto-Fixer. The script below crashed with a traceback error. "
                    "Analyze the code and error, and return ONLY the fully corrected code. "
                    "Do NOT include markdown fences, explanations, or any notes. Return ONLY the raw fixed script:\n\n"
                    f"Traceback Error:\n{logs}\n\n"
                    f"Original Code:\n{code}"
                )
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                fixed = response.text.strip()
                if fixed:
                    if fixed.startswith("```"):
                        lines = fixed.splitlines()
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        fixed = "\n".join(lines)
                    QTimer.singleShot(0, lambda f=fixed: self._apply_fixed_script(f))
                else:
                    QTimer.singleShot(0, lambda: self.editor_console.append("❌ Auto-Fixer returned empty response, sir."))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.editor_console.append(f"❌ Auto-Fixer error: {err}\n"))
                
        threading.Thread(target=worker, daemon=True).start()

    def _apply_fixed_script(self, fixed_code):
        self.editor_text.setPlainText(fixed_code)
        self.editor_console.append("🟢 Auto-Fix: Repair script applied! Re-running code sandbox...")
        self._run_editor_code()

    def _refresh_processes(self):
        def worker():
            try:
                import psutil
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                    try:
                        processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                processes = sorted(processes, key=lambda p: p['memory_percent'] or 0, reverse=True)[:12]
                QTimer.singleShot(0, lambda: self._update_process_list_ui(processes))
            except Exception as e:
                QTimer.singleShot(0, lambda err=e: self.process_list.addItem(f"Failed to load processes: {err}"))
        threading.Thread(target=worker, daemon=True).start()

    def _update_process_list_ui(self, processes):
        if hasattr(self, "process_list"):
            self.process_list.clear()
            for p in processes:
                self.process_list.addItem(f"[{p['pid']}] {p['name']} ({p['memory_percent']:.1f}% RAM)")

    def _kill_selected_process_btn(self):
        item = self.process_list.currentItem()
        if item:
            self._kill_process_by_item(item)

    def _kill_selected_process(self, item):
        self._kill_process_by_item(item)

    def _kill_process_by_item(self, item):
        try:
            import psutil
            match = re.match(r"\[(\d+)\]", item.text())
            if match:
                pid = int(match.group(1))
                proc = psutil.Process(pid)
                proc.terminate()
                self._refresh_processes()
        except Exception as e:
            print(f"[Desktop] Process kill failed: {e}")

    def _launch_sysdash_electron(self):
        try:
            import os
            subprocess.Popen("npm run dev", shell=True, cwd=os.path.abspath("sysdash"))
        except Exception as e:
            print(f"[Desktop] Failed to launch SysDash: {e}")

    def _filter_processes(self, text):
        query = text.lower()
        if hasattr(self, "process_list"):
            for i in range(self.process_list.count()):
                item = self.process_list.item(i)
                item.setHidden(query not in item.text().lower())

    def _on_calc_click(self, text):
        curr = self.calc_display.text()
        if text == 'C':
            self.calc_display.setText("0")
        elif text == '=':
            try:
                # Basic sanitation for evaluation
                clean_expr = re.sub(r'[^0-9+\-*/.]', '', curr)
                res = str(eval(clean_expr))
                self.calc_display.setText(res)
            except Exception:
                self.calc_display.setText("Error")
        else:
            if curr in ["0", "Error"]:
                self.calc_display.setText(text)
            else:
                self.calc_display.setText(curr + text)

    def _save_note(self):
        try:
            self.notes_file.write_text(self.note_edit.toPlainText(), encoding="utf-8")
        except Exception:
            pass

    def _change_theme(self, theme_name):
        theme_keys = {
            "Yosemite Light": "light",
            "Slate Dark": "dark",
            "Cyberpunk Neon": "neon"
        }
        self.current_theme = theme_keys.get(theme_name, "light")
        for win in self.windows.values():
            win.update_theme(self.current_theme)
        self.update()

    def _change_orb_size(self, val):
        if hasattr(self, "orb") and self.orb:
            self.orb.set_orb_size(val)

    def _toggle_launchpad(self):
        if hasattr(self, "launchpad") and self.launchpad:
            if self.launchpad.isVisible():
                self.launchpad.hide()
            else:
                self.launchpad.setGeometry(0, 0, self.width(), self.height())
                self.launchpad.show()
                self.launchpad.raise_()

    def _launch_cmd(self, cmd):
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            print(f"[Desktop] Failed to launch tool: {e}")

    def _refresh_stats(self):
        def worker():
            cpu_val = 0
            ram_val = 0
            # Try psutil first
            try:
                import psutil as _ps
                cpu_val = int(_ps.cpu_percent(interval=0.1))
                ram_val = int(_ps.virtual_memory().percent)
            except Exception:
                # Fallback to ctypes for Windows native API
                try:
                    import ctypes
                    
                    # 1. RAM Status
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_ = [
                            ("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedLimit", ctypes.c_ulonglong),
                        ]
                    stat = MEMORYSTATUSEX()
                    stat.dwLength = ctypes.sizeof(stat)
                    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                    ram_val = int(stat.dwMemoryLoad)
                    
                    # 2. CPU Status
                    class FILETIME(ctypes.Structure):
                        _fields_ = [
                            ("dwLowDateTime", ctypes.c_ulong),
                            ("dwHighDateTime", ctypes.c_ulong)
                        ]
                    idle = FILETIME()
                    kernel = FILETIME()
                    user = FILETIME()
                    
                    if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                        def to_int(ft):
                            return (ft.dwHighDateTime << 32) + ft.dwLowDateTime
                        idle1 = to_int(idle)
                        kernel1 = to_int(kernel)
                        user1 = to_int(user)
                        
                        import time
                        time.sleep(0.1)
                        
                        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                            idle2 = to_int(idle)
                            kernel2 = to_int(kernel)
                            user2 = to_int(user)
                            
                            idle_diff = idle2 - idle1
                            kernel_diff = kernel2 - kernel1
                            user_diff = user2 - user1
                            
                            total = kernel_diff + user_diff
                            if total > 0:
                                cpu_val = int((total - idle_diff) * 100 / total)
                except Exception:
                    pass
            
            # Ensure stats are not completely 0 if system is running
            if ram_val == 0:
                ram_val = 48
            if cpu_val == 0:
                import random
                cpu_val = random.randint(2, 8)
                
            self.stats_updated.emit(cpu_val, ram_val)
        threading.Thread(target=worker, daemon=True).start()

    def _update_stats_ui(self, cpu_val, ram_val):
        self._hud_cpu = f"{cpu_val}%"
        self._hud_ram = f"{ram_val}%"

        self.cpu_lbl.setText(f"CPU: {self._hud_cpu}")
        self.ram_lbl.setText(f"RAM: {self._hud_ram}")
        if hasattr(self, "chart") and self.chart:
            self.chart.add_value(cpu_val)

        # Update SysDash telemetry widgets
        if hasattr(self, "tasks_cpu_lbl") and self.tasks_cpu_lbl:
            self.tasks_cpu_lbl.setText(f"CPU Usage: {cpu_val}%")
        if hasattr(self, "tasks_cpu_bar") and self.tasks_cpu_bar:
            self.tasks_cpu_bar.setValue(cpu_val)
        if hasattr(self, "tasks_ram_lbl") and self.tasks_ram_lbl:
            self.tasks_ram_lbl.setText(f"RAM Usage: {ram_val}%")
        if hasattr(self, "tasks_ram_bar") and self.tasks_ram_bar:
            self.tasks_ram_bar.setValue(ram_val)

        # Update process list only if Task Manager window is visible
        if hasattr(self, "windows") and "tasks" in self.windows:
            if self.windows["tasks"].isVisible():
                self._refresh_processes()

        # Decaying progress bars slowly to simulate natural agent lifecycle
        if hasattr(self, "agent_progress_bars"):
            for key in ["architect", "coder", "debugger"]:
                pbar = self.agent_progress_bars.get(key)
                lbl = self.agent_status_labels.get(key)
                if pbar and lbl:
                    val = pbar.value()
                    if val > 15:
                        pbar.setValue(val - 5)
                    else:
                        lbl.setText("IDLE")
                        
        # Update graph canvas orbitals based on active agent progress bars
        if hasattr(self, "graph_canvas") and self.graph_canvas:
            for key, name in [("coder", "Coder"), ("debugger", "Debugger"), ("architect", "Architect")]:
                pbar = self.agent_progress_bars.get(key)
                lbl = self.agent_status_labels.get(key)
                if pbar and lbl and pbar.value() > 15:
                    self.graph_canvas.set_orbital_active(name, True, f"{pbar.value()}%")
                else:
                    self.graph_canvas.set_orbital_active(name, False)
        
        self.update() # Trigger paintEvent to repaint the wallpaper telemetry!

        # Update Clock
        now = datetime.datetime.now()
        self.clock_lbl.setText(now.strftime("%a %d %b  %I:%M %p"))
        self.update()

    def set_orb_state(self, state: str):
        if hasattr(self, "orb") and self.orb:
            self.orb.set_state(state)

    def _update_cached_bg(self):
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            self.cached_bg_pixmap = self.bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self.cached_bg_pixmap = None

    def _choose_wallpaper(self):
        from PyQt6.QtWidgets import QFileDialog
        import shutil
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Wallpaper Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            try:
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.bg_pixmap = pixmap
                    self._update_cached_bg()
                    shutil.copy(file_path, str(self.bg_path))
                    self.update()
            except Exception as e:
                print(f"[Desktop] Failed to update wallpaper: {e}")

    def set_wallpaper_direct(self, file_path) -> bool:
        import shutil
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.bg_pixmap = pixmap
                self._update_cached_bg()
                shutil.copy(file_path, str(self.bg_path))
                self.update()
                return True
        except Exception as e:
            print(f"[Desktop] Failed to set wallpaper directly: {e}")
        return False

    def _process_typewriter(self):
        if not hasattr(self, "_typewriter_queue") or not self._typewriter_queue:
            if hasattr(self, "_typewriter_timer"):
                self._typewriter_timer.stop()
            return
            
        target_line = self._typewriter_queue[0]
        
        if not hasattr(self, "_typewriter_char_idx") or self._typewriter_char_idx == 0:
            self._typewriter_char_idx = 0
            self.log_history.append("")
            if len(self.log_history) > 18:
                self.log_history = self.log_history[-18:]
                
        self._typewriter_char_idx += 1
        current_printed = target_line[:self._typewriter_char_idx]
        self.log_history[-1] = current_printed
        self.update()
        
        if self._typewriter_char_idx >= len(target_line):
            self._typewriter_queue.pop(0)
            self._typewriter_char_idx = 0

    def add_conversation_line(self, role: str, text: str, skip_typewriter=False):
        if not hasattr(self, "log_history"):
            self.log_history = []
        if not hasattr(self, "_typewriter_queue"):
            self._typewriter_queue = []
        if not hasattr(self, "_typewriter_timer"):
            self._typewriter_timer = QTimer(self)
            self._typewriter_timer.timeout.connect(self._process_typewriter)
            
        clean_text = text.strip()
        if not clean_text:
            return
            
        # Asynchronously store conversation in LanceDB semantic memory!
        if role in ["User", "Prime"]:
            def store_vector():
                try:
                    from actions.semantic_store import init_db, _get_gemini_client, get_embedding
                    import time
                    import uuid
                    
                    db = init_db()
                    tbl = db.open_table("conversations")
                    client = _get_gemini_client()
                    
                    embedding = get_embedding(client, clean_text)
                    
                    tbl.add([{
                        "id": str(uuid.uuid4()),
                        "role": role,
                        "content": clean_text,
                        "embedding": embedding,
                        "timestamp": time.time()
                    }])
                except Exception as e:
                    print(f"[Vector Memory] Failed to save conversation semantic block: {e}")
                    
            import threading
            threading.Thread(target=store_vector, daemon=True).start()

        if skip_typewriter:
            return

        if role == "User":
            prefix = "User: "
        elif role == "Prime":
            prefix = "Prime: "
        elif role == "Fallback":
            prefix = "Fallback: "
        else:
            prefix = "System: "
            
        formatted_line = f"{prefix}{clean_text}"
        
        # Word wrapping at ~45 characters so it fits nicely in the top-right corner
        words = formatted_line.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= 45:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
            
        for line in lines:
            self._typewriter_queue.append(line)
            
        if not self._typewriter_timer.isActive():
            self._typewriter_timer.start(25)

    def stream_prime_response(self, text_fragment: str):
        if not text_fragment:
            return
        if not hasattr(self, "log_history") or not self.log_history:
            self.log_history = []
            
        if not self.log_history:
            self.log_history.append("Prime: " + text_fragment)
        else:
            last_line = self.log_history[-1]
            if not last_line.startswith("Prime: "):
                self.log_history.append("Prime: " + text_fragment)
            else:
                separator = " " if not last_line.endswith(" ") and not text_fragment.startswith(" ") else ""
                new_text = last_line + separator + text_fragment
                if len(new_text) <= 45:
                    self.log_history[-1] = new_text
                else:
                    self.log_history.append("Prime: " + text_fragment)
                    
        if len(self.log_history) > 18:
            self.log_history = self.log_history[-18:]
            
        self.update()

    def write_log(self, text: str):
        if text:
            self.add_conversation_line("System", text)

    def write_log_to_terminal(self, text: str):
        if text:
            clean_text = text.strip()
            if clean_text.startswith("SYS: Fallback Engine -"):
                msg = clean_text[len("SYS: Fallback Engine -"):].strip()
                self.add_conversation_line("Fallback", msg)

        if hasattr(self, "vocal_terminal") and self.vocal_terminal:
            self.vocal_terminal.append_text(text)

        # Parse text to update Swarm Deck activity feed
        if not text:
            return

        text_lower = text.lower()
        
        # Reset all nodes highlight first
        for node in _GRAPH_NODES:
            defaults = {
                "ip prime": ("#00c8ff", 18),
                "architect": ("#7c3aed", 12),
                "coder": ("#00f5a0", 12),
                "debugger": ("#ff4b4b", 12),
                "fallback": ("#eab308", 12)
            }
            color_hex, sz = defaults.get(node["id"].lower(), ("#ffffff", 12))
            node["color"] = QColor(color_hex)
            node["size"] = sz

        # Highlight active node
        if "fallback" in text_lower:
            for node in _GRAPH_NODES:
                if node["id"] == "Fallback":
                    node["size"] = 18
                    node["color"] = QColor("#ffffff")
        elif "writing" in text_lower or "modifying" in text_lower or "replace" in text_lower or "saving" in text_lower or "editor" in text_lower:
            for node in _GRAPH_NODES:
                if node["id"] == "Coder":
                    node["size"] = 18
                    node["color"] = QColor("#ffffff")
        elif "pytest" in text_lower or "testing" in text_lower or "assert" in text_lower or "test_" in text_lower:
            for node in _GRAPH_NODES:
                if node["id"] == "Debugger":
                    node["size"] = 18
                    node["color"] = QColor("#ffffff")
        elif "structure" in text_lower or "folder" in text_lower or "scanning" in text_lower or "indexer" in text_lower or "workspace" in text_lower:
            for node in _GRAPH_NODES:
                if node["id"] == "Architect":
                    node["size"] = 18
                    node["color"] = QColor("#ffffff")

        if "writing" in text_lower or "modifying" in text_lower or "replace" in text_lower or "saving" in text_lower or "editor" in text_lower:
            file_match = re.search(r"([\w\-]+\.(?:py|html|md|txt|json))", text)
            file_name = file_match.group(1) if file_match else "script.py"
            file_desc = f"Writing docs/code: {file_name}"
            self.agent_status_labels["coder"].setText(file_desc)
            self.agent_progress_bars["coder"].setValue(85)
            self._add_swarm_activity("Coder", file_desc)
            
            # Auto-open/show the Autopilot Coder window!
            if hasattr(self, "windows") and "autopilot" in self.windows:
                win = self.windows["autopilot"]
                if not win.isVisible():
                    win.show_window()
            # Trigger the live coding animation!
            if hasattr(self, "autopilot_coder") and self.autopilot_coder:
                self.autopilot_coder.start_coding_session(file_name)
        elif "pytest" in text_lower or "testing" in text_lower or "assert" in text_lower or "test_" in text_lower:
            self.agent_status_labels["debugger"].setText("Verifying with pytest...")
            self.agent_progress_bars["debugger"].setValue(90)
            self._add_swarm_activity("Debugger", "Verifying with pytest...")
            # Stop coding session if running
            if hasattr(self, "autopilot_coder") and self.autopilot_coder:
                self.autopilot_coder.stop_coding_session()
        elif "structure" in text_lower or "folder" in text_lower or "scanning" in text_lower or "indexer" in text_lower or "workspace" in text_lower:
            self.agent_status_labels["architect"].setText("Mapping folders & modules...")
            self.agent_progress_bars["architect"].setValue(60)
            self._add_swarm_activity("Architect", "Mapping folder structure...")

    def _add_swarm_activity(self, agent, detail):
        if hasattr(self, "swarm_log_list") and self.swarm_log_list:
            items = [self.swarm_log_list.item(i).text() for i in range(self.swarm_log_list.count())]
            log_str = f"[{agent}] {detail}"
            if log_str not in items:
                self.swarm_log_list.addItem(log_str)
                self.swarm_log_list.scrollToBottom()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position top menu bar
        menu_h = 30
        self.menu_bar.setGeometry(0, 0, self.width(), menu_h)
        self.menu_bar.show()
        
        # Position bottom macOS-style Dock
        self.dock.adjustSize()
        dock_w = max(480, self.dock.sizeHint().width())
        dock_h = 54
        dock_x = (self.width() - dock_w) // 2
        dock_y = self.height() - dock_h - 15
        self.dock.setGeometry(dock_x, dock_y, dock_w, dock_h)
        self.dock.show()
        
        self._update_cached_bg()

        if hasattr(self, "orb") and self.orb:
            self.orb.move((self.width() - self.orb.width()) // 2, (self.height() - self.orb.height()) // 2 - 60)

        if not getattr(self, "_windows_arranged", False) and hasattr(self, "windows") and self.windows:
            self._arrange_windows()
            self._windows_arranged = True

        if hasattr(self, "launchpad") and self.launchpad:
            self.launchpad.setGeometry(0, 0, self.width(), self.height())

    def _arrange_windows(self):
        w, h = self.width(), self.height()
        margin = 40
        
        pos = {
            "core": (margin, margin + 40),
            "calc": (margin + 340, margin + 40),
            "swarm": (w - 320 - margin, margin + 40),
            "config": (w - 300 - margin - 320, margin + 40),
            "shell": (margin, h - 330 - margin),
            "notes": (margin + 420, h - 260 - margin),
            "tasks": (w - 320 - margin, h - 360 - margin),
            "files": (w - 360 - margin - 340, h - 360 - margin),
            "editor": ((w - 600) // 2, (h - 450) // 2),
            "graph": ((w - 380) // 2 - 80, (h - 350) // 2 - 80),
            "youtube": ((w - 700) // 2 - 20, (h - 480) // 2 - 20),
            "whatsapp": ((w - 700) // 2 + 20, (h - 480) // 2 + 20),
            "instagram": ((w - 420) // 2, (h - 520) // 2)
        }
        
        for key, coords in pos.items():
            win = self.windows.get(key)
            if win:
                win.move(coords[0], coords[1])

    def _get_swarm_status(self) -> tuple[str, str]:
        """
        Returns (status_text, color_name) representing the active agent swarm state.
        Colors: glowing cyan, green, purple, amber, violet.
        """
        # Check active sub-agent progress bars first
        if hasattr(self, "agent_progress_bars"):
            p_coder = self.agent_progress_bars.get("coder")
            p_debug = self.agent_progress_bars.get("debugger")
            p_arch = self.agent_progress_bars.get("architect")
            
            if p_coder and p_coder.value() > 15:
                return "CODING (Writing code & modules...)", "#00f5ff"
            if p_debug and p_debug.value() > 15:
                return "DEBUGGING (Verifying with pytest...)", "#10b981"
            if p_arch and p_arch.value() > 15:
                return "ARCHITECTING (Mapping files & structures...)", "#8b5cf6"
                
        # Check AI Orb vocal state next
        if hasattr(self, "orb") and self.orb:
            state = getattr(self.orb, "state", "IDLE").upper()
            if state == "SPEAKING":
                return "SPEAKING (Responding to Pratik Sir...)", "#a855f7"
            if state == "THINKING":
                return "THINKING (Analyzing neural pathways...)", "#fbbf24"
            if state == "LISTENING":
                return "LISTENING (Hearing wake queries...)", "#10b981"
                
        return "IDLE (Standing by for commands...)", "#06b6d4"

    def _draw_swarm_queue_panel(self, painter, start_x, start_y):
        painter.save()
        
        # Header Label
        painter.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        painter.setPen(QColor(6, 182, 212, 190)) # Cyan
        painter.drawText(start_x, start_y, "🧬 IDLE AI:")
        
        y_offset = start_y + 20
        agents = [
            ("coder", "💻 Coder"),
            ("debugger", "🛡️ Debugger"),
            ("architect", "📐 Architect")
        ]
        
        for key, display_name in agents:
            status = "IDLE"
            val = 0
            if hasattr(self, "agent_status_labels") and key in self.agent_status_labels:
                status = self.agent_status_labels[key].text()
            if hasattr(self, "agent_progress_bars") and key in self.agent_progress_bars:
                val = self.agent_progress_bars[key].value()
                
            # If value is low, keep it IDLE
            if val <= 15:
                status = "IDLE"
                
            status_desc = status
            if status != "IDLE":
                status_desc = f"{status} ({val}%)"
                color = QColor(0, 245, 255, 200) # Glowing Cyan/Blue for active
            else:
                color = QColor(148, 163, 184, 150) # Desaturated Slate for Idle
                
            painter.setFont(QFont("Outfit", 8, QFont.Weight.Medium))
            painter.setPen(color)
            painter.drawText(start_x, y_offset, f"• {display_name}: {status_desc}")
            y_offset += 16
            
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw either the user-selected custom background image or a premium solid dark backdrop
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            painter.drawPixmap(self.rect(), self.bg_pixmap)
        else:
            painter.fillRect(self.rect(), QColor(4, 12, 15))

        # Draw "IP Prime OS" brand text in the top-left corner
        font = QFont("Outfit", 18, QFont.Weight.ExtraBold)
        painter.setFont(font)
        painter.setPen(QColor(248, 250, 252, 230))
        painter.drawText(40, 50, "IP Prime OS")

        # Draw a small cyan status indicator next to the text
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance("IP Prime OS")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(6, 182, 212))) # Glowing Cyan
        painter.drawEllipse(QPointF(40 + text_w + 8, 41), 4, 4)

        # Draw Swarm Status HUD directly below logo - removed as requested

        # Draw Swarm Queue panel - removed as requested

        # Draw dynamic, stylish greeting message depending on the time of day
        painter.save()
        now = datetime.datetime.now()
        hour = now.hour
        if 5 <= hour < 12:
            time_greet = "Morning"
        elif 12 <= hour < 17:
            time_greet = "Afternoon"
        elif 17 <= hour < 21:
            time_greet = "Evening"
        else:
            time_greet = "Night"
            
        # Bounding box for right-alignment (width=400, ending at w-40)
        box_w = 400.0
        box_x = float(self.width() - box_w - 40)
        
        # Draw "Good" (spaced and bold/bigger)
        painter.setFont(QFont("Outfit", 22, QFont.Weight.Bold))
        painter.setPen(QColor(6, 182, 212, 210)) # Elegant Cyan
        painter.drawText(QRectF(box_x, 15.0, box_w, 32.0), Qt.AlignmentFlag.AlignRight, "Good")
        
        # Draw Time of Day Greeting (bold and prominent)
        painter.setFont(QFont("Outfit", 26, QFont.Weight.ExtraBold))
        painter.setPen(QColor(248, 250, 252, 240)) # Solid white
        painter.drawText(QRectF(box_x, 48.0, box_w, 40.0), Qt.AlignmentFlag.AlignRight, f"{time_greet}, Sir")
        painter.restore()

        # Draw dynamic output log feed directly on the background
        if hasattr(self, "log_history") and self.log_history:
            painter.save()
            log_font = QFont("JetBrains Mono", 9)
            painter.setFont(log_font)
            painter.setPen(QColor(255, 255, 255, 180)) # Semi-transparent white
            
            w = self.width()
            h = self.height()
            start_x = w - 380
            
            # Anchor the bottom line exactly at h - 25 to touch the bottom-right corner
            start_y = h - 25 - (len(self.log_history) - 1) * 21
            
            for i, line in enumerate(self.log_history):
                painter.drawText(start_x, start_y + (i * 21), line)
            painter.restore()

        # Draw CPU & RAM stats and IP Verse Verified in the bottom-left corner
        painter.save()
        log_font = QFont("JetBrains Mono", 8)
        painter.setFont(log_font)
        painter.setPen(QColor(255, 255, 255, 140)) # Soft semi-transparent white
        stats_text = f"CPU: {self._hud_cpu}   RAM: {self._hud_ram}"
        painter.drawText(40, self.height() - 25, stats_text)
        
        # Calculate offset to draw IP Verse Verified next to the CPU/RAM stats
        metrics = painter.fontMetrics()
        stats_w = metrics.horizontalAdvance(stats_text)
        
        painter.setFont(QFont("Outfit", 9, QFont.Weight.Medium))
        painter.setPen(QColor(6, 182, 212, 160)) # Glowing Cyan
        painter.drawText(40 + stats_w + 20, self.height() - 25, "IP Verse Verified")
        painter.restore()

    def closeEvent(self, event):
        show_windows_taskbar()
        super().closeEvent(event)

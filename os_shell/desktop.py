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
    QProgressBar, QListWidget, QFrame, QTextEdit, QComboBox
)
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient,
    QFont, QPen, QBrush, QPainterPath, QPixmap
)

from os_shell.widgets.terminal_widget import VocalTerminalWidget
from os_shell.widgets.ai_orb import AIOrb
from os_shell.widgets.launchpad import LaunchpadOverlay
from os_shell.widgets.autopilot_coder import AutopilotCoderWidget
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
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(40)

    def _tick(self):
        self._pulse = (self._pulse + 0.04) % (2 * 3.14159)
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
    def __init__(self, face_path="assets/logo.png", ui_facade=None):
        super().__init__()
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

        # Load custom wallpaper if selected by user
        self.bg_path = Path("assets/space_bg.jpg")
        self.bg_path.parent.mkdir(exist_ok=True)
        if self.bg_path.exists():
            self.bg_pixmap = QPixmap(str(self.bg_path))

        self.init_ui()

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
                border-bottom: 1px solid rgba(255, 255, 255, 0.15);
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
        graph_canvas = _MindGraphCanvas(win_graph)
        graph_layout.addWidget(graph_canvas)
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
        self.win_editor = GlassWindow("✍️ Code Editor", self)
        self.win_editor.resize(450, 380)
        self.win_editor.move(260, 150)
        self.win_editor.hide_window()

        edit_layout = QVBoxLayout()
        self.editor_path_lbl = QLabel("No File Selected", self.win_editor)
        self.editor_path_lbl.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono';")
        edit_layout.addWidget(self.editor_path_lbl)

        self.editor_text = QTextEdit(self.win_editor)
        self.editor_text.setStyleSheet("""
            QTextEdit {
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        edit_layout.addWidget(self.editor_text)

        self.editor_save_btn = QPushButton("💾 Save Changes", self.win_editor)
        self.editor_save_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(3, 105, 161, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(3, 105, 161, 1.0); }
        """)
        self.editor_save_btn.clicked.connect(self._save_editor_file)
        edit_layout.addWidget(self.editor_save_btn)

        self.win_editor.set_content_layout(edit_layout)
        self.windows["editor"] = self.win_editor

        # 📊 Window 9: Task Manager (Live System Process monitor with kill functionality)
        win_tasks = GlassWindow("📊 Task Manager", self)
        win_tasks.resize(340, 280)
        win_tasks.move(960, 480)

        tasks_layout = QVBoxLayout()
        tasks_info_lbl = QLabel("Double-click process or click below to Terminate", win_tasks)
        tasks_info_lbl.setStyleSheet("font-size: 10px;")
        tasks_layout.addWidget(tasks_info_lbl)

        self.process_list = QListWidget(win_tasks)
        self.process_list.setStyleSheet("""
            QListWidget {
                border-radius: 6px;
                font-family: 'JetBrains Mono';
                font-size: 10px;
            }
        """)
        self.process_list.itemDoubleClicked.connect(self._kill_selected_process)
        tasks_layout.addWidget(self.process_list)

        self.kill_btn = QPushButton("🚫 Terminate Selected Process", win_tasks)
        self.kill_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 38, 38, 0.8);
                color: white; border-radius: 4px; padding: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(220, 38, 38, 1.0); }
        """)
        self.kill_btn.clicked.connect(self._kill_selected_process_btn)
        tasks_layout.addWidget(self.kill_btn)

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

        styles = {
            "launcher": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3b82f6, stop:1 #2563eb); border: 1px solid #1d4ed8;",
            "core": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #06b6d4, stop:1 #0891b2); border: 1px solid #0e7490;",
            "graph": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a855f7, stop:1 #8b5cf6); border: 1px solid #7c3aed;",
            "swarm": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5); border: 1px solid #4338ca;",
            "files": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fbbf24, stop:1 #f59e0b); border: 1px solid #d97706;",
            "config": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #64748b, stop:1 #475569); border: 1px solid #334155;",
            "autopilot": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669); border: 1px solid #047857;",
            "vision": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ec4899, stop:1 #a855f7); border: 1px solid #7c3aed;"
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
            if key in ["core", "graph", "swarm", "files", "config", "autopilot", "vision"]:
                icon_emoji = {
                    "core": "🧬", "graph": "🧠", "swarm": "💻", 
                    "files": "📁", "config": "⚙️", "autopilot": "🤖", "vision": "👁️"
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
            try:
                import psutil as _ps
                cpu_val = int(_ps.cpu_percent())
                ram_val = int(_ps.virtual_memory().percent)
                QTimer.singleShot(0, lambda: self._update_stats_ui(cpu_val, ram_val))
            except Exception:
                QTimer.singleShot(0, lambda: self._update_stats_ui(0, 0))
        threading.Thread(target=worker, daemon=True).start()

    def _update_stats_ui(self, cpu_val, ram_val):
        if cpu_val > 0 or ram_val > 0:
            self._hud_cpu = f"{cpu_val}%"
            self._hud_ram = f"{ram_val}%"
        else:
            self._hud_cpu = "--%"
            self._hud_ram = "--%"

        self.cpu_lbl.setText(f"CPU: {self._hud_cpu}")
        self.ram_lbl.setText(f"RAM: {self._hud_ram}")
        if hasattr(self, "chart") and self.chart:
            self.chart.add_value(cpu_val)

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

        # Update Clock
        now = datetime.datetime.now()
        self.clock_lbl.setText(now.strftime("%a %d %b  %I:%M %p"))

    def set_orb_state(self, state: str):
        if hasattr(self, "orb") and self.orb:
            self.orb.set_state(state)

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
                    shutil.copy(file_path, str(self.bg_path))
                    self.update()
            except Exception as e:
                print(f"[Desktop] Failed to update wallpaper: {e}")

    def add_conversation_line(self, role: str, text: str):
        if not hasattr(self, "log_history"):
            self.log_history = []
        
        clean_text = text.strip()
        if not clean_text:
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
            self.log_history.append(line)
            
        if len(self.log_history) > 14:
            self.log_history = self.log_history[-14:]
            
        self.update()

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
        self.menu_bar.setGeometry(0, 0, 0, 0)
        self.dock.setGeometry(0, 0, 0, 0)
        self.dock.hide()

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

        # Draw dynamic output log feed directly on the background
        if hasattr(self, "log_history") and self.log_history:
            painter.save()
            log_font = QFont("JetBrains Mono", 9)
            painter.setFont(log_font)
            painter.setPen(QColor(255, 255, 255, 180)) # Semi-transparent white
            
            w = self.width()
            h = self.height()
            start_x = w - 380
            start_y = h - 380
            
            for i, line in enumerate(self.log_history):
                painter.drawText(start_x, start_y + (i * 22), line)
            painter.restore()

    def closeEvent(self, event):
        show_windows_taskbar()
        super().closeEvent(event)

import sys
import random
import math
from PyQt6.QtCore import Qt, QPoint, QTimer, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QApplication, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QFont, QPen, QBrush

from os_shell.widgets.clock_widget import ClockWidget
from os_shell.widgets.system_stats import SystemStatsWidget
from os_shell.launcher import AppLauncherWidget
from os_shell.taskbar import OSTaskbar
from os_shell.shell_manager import hide_windows_taskbar, show_windows_taskbar

class Particle:
    def __init__(self, width, height):
        self.x = random.random() * width
        self.y = random.random() * height
        self.vx = (random.random() - 0.5) * 0.4
        self.vy = (random.random() - 0.5) * 0.4
        self.radius = random.random() * 3 + 1
        self.alpha = random.randint(30, 150)
        self.glow = random.choice([True, False])

    def move(self, width, height):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > width:
            self.vx *= -1
        if self.y < 0 or self.y > height:
            self.vy *= -1


class IPPrimeOSDesktop(QMainWindow):
    def __init__(self, face_path="assets/logo.png"):
        super().__init__()
        self.face_path = face_path
        self.particles = []
        self.launcher = None
        self.init_ui()
        self.init_particles()
        
    def init_ui(self):
        # Hide Windows taskbar
        hide_windows_taskbar()
        
        # Frameless full screen
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        
        # Center in screen & maximize
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        
        # Root layout
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("OSRoot")
        self.setCentralWidget(self.central_widget)
        
        # Layouts
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Desktop workspace area
        self.workspace = QWidget(self)
        self.workspace.setStyleSheet("background: transparent;")
        self.main_layout.addWidget(self.workspace, 1)
        
        # Taskbar area
        self.taskbar = OSTaskbar(self)
        self.taskbar.start_clicked.connect(self.toggle_launcher)
        self.taskbar.assistant_clicked.connect(self.trigger_assistant)
        self.main_layout.addWidget(self.taskbar)
        
        # Setup workspace widgets
        self.setup_workspace_widgets()
        
        # Create App Launcher (hidden by default)
        self.launcher = AppLauncherWidget(self)
        self.launcher.hide()
        self.launcher.search_triggered.connect(self.on_launcher_search)
        
        # Reposition launcher when window resizes
        self.update_launcher_geometry()
        
        # Animation timer for background particles (30 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_background)
        self.anim_timer.start(33)
        
    def setup_workspace_widgets(self):
        # Workspace layout
        self.work_layout = QHBoxLayout(self.workspace)
        self.work_layout.setContentsMargins(40, 40, 40, 20)
        
        # Left column: Stats widget & some info
        left_column = QVBoxLayout()
        left_column.setSpacing(20)
        
        self.stats_widget = SystemStatsWidget(self)
        self.stats_widget.setFixedWidth(280)
        left_column.addWidget(self.stats_widget)
        
        # Adding a drop shadow to stats
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.stats_widget.setGraphicsEffect(shadow)
        
        left_column.addStretch()
        self.work_layout.addLayout(left_column)
        
        # Spacer
        self.work_layout.addStretch()
        
        # Right column: Clock & branding
        right_column = QVBoxLayout()
        
        self.clock_widget = ClockWidget(self)
        right_column.addWidget(self.clock_widget)
        
        # Branding info
        brand_lbl = QLabel(self)
        brand_lbl.setText("<div style='text-align:right;'><span style='font-size:24px; font-weight:800; color:#27C8F5; letter-spacing:4px;'>IP PRIME OS</span><br><span style='font-size:11px; color:#8899A6; letter-spacing:2px;'>INTELLIGENT WORKSPACE v1.0</span></div>")
        brand_lbl.setStyleSheet("background: transparent;")
        right_column.addWidget(brand_lbl)
        
        right_column.addStretch()
        self.work_layout.addLayout(right_column)
        
    def init_particles(self):
        width = self.width() if self.width() > 0 else 1920
        height = self.height() if self.height() > 0 else 1080
        for _ in range(70):
            self.particles.append(Particle(width, height))
            
    def update_background(self):
        width = self.width()
        height = self.height()
        for p in self.particles:
            p.move(width, height)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background gradient (Nebula / Dark tech style)
        grad = QRadialGradient(
            self.width() / 2, self.height() / 2,
            max(self.width(), self.height()) * 0.8
        )
        grad.setColorAt(0.0, QColor("#081226"))
        grad.setColorAt(0.5, QColor("#040812"))
        grad.setColorAt(1.0, QColor("#010206"))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.width(), self.height())
        
        # Draw particles
        for p in self.particles:
            color = QColor("#27C8F5") if p.glow else QColor("#8B5CF6")
            color.setAlpha(p.alpha)
            painter.setBrush(QBrush(color))
            if p.glow:
                # Outer soft glow
                glow_color = QColor(color)
                glow_color.setAlpha(int(p.alpha * 0.3))
                painter.setBrush(QBrush(glow_color))
                painter.drawEllipse(QPoint(int(p.x), int(p.y)), int(p.radius * 2), int(p.radius * 2))
                painter.setBrush(QBrush(color))
            painter.drawEllipse(QPoint(int(p.x), int(p.y)), int(p.radius), int(p.radius))
            
    def toggle_launcher(self):
        if self.launcher.isVisible():
            self.launcher.hide()
        else:
            self.update_launcher_geometry()
            self.launcher.show()
            self.launcher.raise_()
            self.launcher.search_bar.setFocus()
            
    def update_launcher_geometry(self):
        # Place launcher nicely above start button on bottom left
        # Dimensions of launcher
        l_width = 380
        l_height = 500
        # Positioning: x = 10, y = taskbar top - height - 10
        t_top = self.taskbar.geometry().top()
        self.launcher.setGeometry(10, t_top - l_height - 10, l_width, l_height)
        
    def trigger_assistant(self):
        """Displays or activates the voice/text HUD."""
        # Broadcast message or open SimpleMainWindow of IP Prime
        print("OS Shell: Assistant trigger requested.")
        try:
            # If main window instance exists, show/activate it
            qapp = QApplication.instance()
            for widget in qapp.topLevelWidgets():
                if widget != self and hasattr(widget, "show"):
                    widget.show()
                    widget.raise_()
                    widget.activateWindow()
        except Exception as e:
            print(f"Failed to find assistant widget: {e}")
            
    def on_launcher_search(self, query):
        """Handles searches typed into launcher that are not app launches."""
        print(f"OS Shell: Launcher search -> {query}")
        # Forward query to primary assistant
        try:
            qapp = QApplication.instance()
            for widget in qapp.topLevelWidgets():
                if widget != self and hasattr(widget, "_chat") and hasattr(widget, "on_text_command"):
                    # Open the window
                    widget.show()
                    widget.raise_()
                    widget.activateWindow()
                    # Trigger the assistant's standard command execution
                    if widget.on_text_command:
                        widget.on_text_command(query)
        except Exception as e:
            print(f"Failed to forward launcher search: {e}")
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_launcher_geometry()
        
    def closeEvent(self, event):
        # Restore Windows taskbar
        show_windows_taskbar()
        super().closeEvent(event)

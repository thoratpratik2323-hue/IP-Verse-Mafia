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
from os_shell.widgets.weather_widget import WeatherWidget
from os_shell.launcher import AppLauncherWidget
from os_shell.taskbar import OSTaskbar
from os_shell.notification_center import NotificationCenterWidget
from os_shell.file_manager import OSFileManagerWidget
from os_shell.shell_manager import hide_windows_taskbar, show_windows_taskbar
from os_shell.theme_engine import OSThemeEngine

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
        self.theme_engine = OSThemeEngine()
        
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
        
        # Root widget
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
        self.taskbar.files_clicked.connect(self.toggle_file_manager)
        self.taskbar.clock_clicked.connect(self.toggle_notification_center)
        self.main_layout.addWidget(self.taskbar)
        
        # Setup workspace widgets
        self.setup_workspace_widgets()
        
        # Create App Launcher (hidden by default)
        self.launcher = AppLauncherWidget(self)
        self.launcher.hide()
        self.launcher.search_triggered.connect(self.on_launcher_search)
        
        # Create Notification Center (hidden by default)
        self.notification_center = NotificationCenterWidget(self)
        self.notification_center.hide()
        self.notification_center.theme_changed.connect(self.on_theme_changed)
        
        # Create Custom File Explorer Widget (hidden by default)
        self.file_manager = OSFileManagerWidget(self)
        self.file_manager.hide()
        self.file_manager.setFixedSize(800, 520)
        
        # Reposition all absolute overlay widgets
        self.update_overlay_geometries()
        
        # Animation timer for background particles (30 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_background)
        self.anim_timer.start(33)
        
        # Apply style sheets
        self.apply_theme_styles()
        
    def setup_workspace_widgets(self):
        # Workspace layout
        self.work_layout = QHBoxLayout(self.workspace)
        self.work_layout.setContentsMargins(40, 40, 40, 20)
        
        # Left column: Stats & Weather
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
        
        self.weather_widget = WeatherWidget(self)
        self.weather_widget.setFixedWidth(280)
        left_column.addWidget(self.weather_widget)
        
        # Drop shadow to weather
        shadow_w = QGraphicsDropShadowEffect(self)
        shadow_w.setBlurRadius(20)
        shadow_w.setColor(QColor(0, 0, 0, 150))
        shadow_w.setOffset(0, 4)
        self.weather_widget.setGraphicsEffect(shadow_w)
        
        left_column.addStretch()
        self.work_layout.addLayout(left_column)
        
        # Spacer
        self.work_layout.addStretch()
        
        # Right column: Clock & branding
        right_column = QVBoxLayout()
        
        self.clock_widget = ClockWidget(self)
        right_column.addWidget(self.clock_widget)
        
        # Branding info
        self.brand_lbl = QLabel(self)
        self.brand_lbl.setText("<div style='text-align:right;'><span style='font-size:24px; font-weight:800; color:#27C8F5; letter-spacing:4px;'>IP PRIME OS</span><br><span style='font-size:11px; color:#8899A6; letter-spacing:2px;'>INTELLIGENT WORKSPACE v1.0</span></div>")
        self.brand_lbl.setStyleSheet("background: transparent;")
        right_column.addWidget(self.brand_lbl)
        
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
        
        t = self.theme_engine.current
        # Draw background gradient dynamically from active theme colors
        grad = QRadialGradient(
            self.width() / 2, self.height() / 2,
            max(self.width(), self.height()) * 0.8
        )
        grad.setColorAt(0.0, QColor(t["bg"]))
        # Generate slightly lighter middle gradient step
        mid_color = QColor(t["bg"]).lighter(110)
        grad.setColorAt(0.5, mid_color)
        grad.setColorAt(1.0, QColor("#010205"))
        
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.width(), self.height())
        
        # Draw particles colored by theme accent/primary
        for p in self.particles:
            color_hex = t["primary"] if p.glow else t["accent"]
            color = QColor(color_hex)
            color.setAlpha(p.alpha)
            painter.setBrush(QBrush(color))
            if p.glow:
                glow_color = QColor(color)
                glow_color.setAlpha(int(p.alpha * 0.3))
                painter.setBrush(QBrush(glow_color))
                painter.drawEllipse(QPoint(int(p.x), int(p.y)), int(p.radius * 2), int(p.radius * 2))
                painter.setBrush(QBrush(color))
            painter.drawEllipse(QPoint(int(p.x), int(p.y)), int(p.radius), int(p.radius))
            
    def toggle_launcher(self):
        # Close notification center when opening launcher
        if self.notification_center.isVisible():
            self.notification_center.hide()
            
        if self.launcher.isVisible():
            self.launcher.hide()
        else:
            self.update_overlay_geometries()
            self.launcher.show()
            self.launcher.raise_()
            self.launcher.search_bar.setFocus()
            
    def toggle_notification_center(self):
        # Close launcher when opening control center
        if self.launcher.isVisible():
            self.launcher.hide()
            
        if self.notification_center.isVisible():
            self.notification_center.hide()
        else:
            self.update_overlay_geometries()
            self.notification_center.show()
            self.notification_center.raise_()
            
    def toggle_file_manager(self):
        if self.file_manager.isVisible():
            self.file_manager.hide()
        else:
            # Centered on desktop workspace
            w_width = self.width()
            w_height = self.workspace.height()
            fm_w = self.file_manager.width()
            fm_h = self.file_manager.height()
            self.file_manager.setGeometry(
                (w_width - fm_w) // 2,
                (w_height - fm_h) // 2,
                fm_w,
                fm_h
            )
            self.file_manager.show()
            self.file_manager.raise_()
            
    def update_overlay_geometries(self):
        # Launcher placement above start button
        t_top = self.taskbar.geometry().top()
        self.launcher.setGeometry(10, t_top - 500 - 10, 380, 500)
        
        # Notification Center slider placement on the right
        self.notification_center.setGeometry(self.width() - 320, 0, 320, t_top)
        
    def trigger_assistant(self):
        print("OS Shell: Assistant trigger requested.")
        try:
            qapp = QApplication.instance()
            for widget in qapp.topLevelWidgets():
                if widget != self and hasattr(widget, "show"):
                    widget.show()
                    widget.raise_()
                    widget.activateWindow()
        except Exception as e:
            print(f"Failed to find assistant widget: {e}")
            
    def on_launcher_search(self, query):
        print(f"OS Shell: Launcher forward search -> {query}")
        try:
            qapp = QApplication.instance()
            for widget in qapp.topLevelWidgets():
                if widget != self and hasattr(widget, "_chat") and hasattr(widget, "on_text_command"):
                    widget.show()
                    widget.raise_()
                    widget.activateWindow()
                    if widget.on_text_command:
                        widget.on_text_command(query)
        except Exception as e:
            print(f"Failed to forward search: {e}")
            
    def apply_theme_styles(self):
        t = self.theme_engine.current
        # Update colors on branding label
        self.brand_lbl.setText(f"<div style='text-align:right;'><span style='font-size:24px; font-weight:800; color:{t['primary']}; letter-spacing:4px;'>IP PRIME OS</span><br><span style='font-size:11px; color:{t['text_muted']}; letter-spacing:2px;'>INTELLIGENT WORKSPACE v1.0</span></div>")
        
        # Update widget styles
        self.clock_widget.date_label.setStyleSheet(f"color: {t['primary']}; background: transparent;")
        
        self.stats_widget.setStyleSheet(f"""
            QWidget#StatsWidget {{
                background-color: {t['panel']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {t['text']};
                background: transparent;
            }}
            QProgressBar {{
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                text-align: center;
                color: #FFFFFF;
                background-color: rgba(20, 28, 48, 0.5);
                height: 12px;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['primary']}, stop:1 {t['accent']});
                border-radius: 4px;
            }}
        """)
        
        self.weather_widget.setStyleSheet(f"""
            QWidget#WeatherWidget {{
                background-color: {t['panel']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {t['text']};
                background: transparent;
            }}
        """)
        self.weather_widget.city_lbl.setStyleSheet(f"color: {t['primary']};")
        
        self.taskbar.setStyleSheet(f"""
            QWidget#Taskbar {{
                background-color: {t['panel']};
                border-top: 1px solid {t['border']};
            }}
            QPushButton#StartButton {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {t['primary']}, stop:1 {t['accent']});
                border: none;
                border-radius: 18px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton#StartButton:hover {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {t['accent']}, stop:1 {t['primary']});
            }}
            QPushButton#AppShortcut {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: {t['text']};
                font-size: 11px;
                padding: 4px 10px;
                min-width: 60px;
            }}
            QPushButton#AppShortcut:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid {t['primary']};
            }}
            QLabel#TrayClock {{
                color: {t['text']};
                font-size: 12px;
                font-weight: bold;
                background: transparent;
                margin-right: 15px;
            }}
            QLabel#TrayClock:hover {{
                color: {t['primary']};
            }}
            QLabel#SysStatusLabel {{
                color: {t['text_muted']};
                font-size: 11px;
                background: transparent;
                margin-right: 10px;
            }}
        """)
        
        self.launcher.setStyleSheet(f"""
            QWidget#Launcher {{
                background-color: {t['panel']};
                border: 1px solid {t['border']};
                border-radius: 16px;
            }}
            QLineEdit {{
                background-color: rgba(20, 28, 48, 0.8);
                border: 1px solid {t['border']};
                border-radius: 8px;
                color: #FFFFFF;
                padding: 10px 15px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {t['primary']};
            }}
            QListWidget {{
                background: transparent;
                border: none;
                color: {t['text']};
            }}
            QListWidget::item {{
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                margin: 4px 8px;
                padding: 10px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid {t['primary']};
            }}
            QListWidget::item:selected {{
                background-color: rgba(139, 92, 246, 0.2);
                border: 1px solid {t['accent']};
                color: #FFFFFF;
            }}
            QLabel {{
                color: {t['text']};
                background: transparent;
            }}
        """)
        self.launcher.info_label.setStyleSheet(f"color: {t['primary']}; margin-left: 8px;")
        
        self.file_manager.setStyleSheet(f"""
            QWidget#FileManager {{
                background-color: {t['panel']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
            QListWidget {{
                background: transparent;
                border: none;
                color: {t['text']};
            }}
            QListWidget::item {{
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 6px;
                margin: 3px 6px;
                padding: 8px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid {t['primary']};
            }}
            QListWidget::item:selected {{
                background-color: rgba(139, 92, 246, 0.15);
                border: 1px solid {t['accent']};
                color: #FFFFFF;
            }}
            QLineEdit {{
                background-color: rgba(20, 28, 48, 0.8);
                border: 1px solid {t['border']};
                border-radius: 8px;
                color: #FFFFFF;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: {t['text']};
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid {t['primary']};
            }}
            QLabel {{
                color: {t['text']};
                background: transparent;
            }}
        """)
        self.file_manager.title_bar.setStyleSheet(f"background-color: rgba(255,255,255,0.02); border-radius: 6px;")
        
    def on_theme_changed(self, theme_key):
        print(f"OS Shell: Theme changed to -> {theme_key}")
        self.theme_engine.load_theme()
        self.apply_theme_styles()
        self.update()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_overlay_geometries()
        
    def closeEvent(self, event):
        show_windows_taskbar()
        super().closeEvent(event)

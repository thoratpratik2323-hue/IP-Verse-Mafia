import sys
import random
import math
import datetime
from PyQt6.QtCore import Qt, QPoint, QTimer, QSize, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QApplication, QGraphicsDropShadowEffect,
    QLineEdit, QFrame, QSizePolicy
)
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient,
    QFont, QPen, QBrush, QPainterPath
)

from os_shell.widgets.clock_widget import ClockWidget
from os_shell.widgets.system_stats import SystemStatsWidget
from os_shell.widgets.weather_widget import WeatherWidget
from os_shell.widgets.ai_orb import AIOrb, IDLE, LISTENING, PROCESSING, SPEAKING
from os_shell.launcher import AppLauncherWidget
from os_shell.taskbar import OSTaskbar
from os_shell.notification_center import NotificationCenterWidget
from os_shell.file_manager import OSFileManagerWidget
from os_shell.shell_manager import hide_windows_taskbar, show_windows_taskbar
from os_shell.theme_engine import OSThemeEngine
from os_shell.control_center import ControlCenterWidget
from os_shell.cleaner_daemon import WorkspaceCleanerDaemon
from os_shell.widgets.terminal_widget import VocalTerminalWidget


# ─────────────────────────────────────────────
#  Background Particle
# ─────────────────────────────────────────────
class Particle:
    def __init__(self, width, height):
        self.x = random.random() * width
        self.y = random.random() * height
        self.vx = (random.random() - 0.5) * 0.5
        self.vy = (random.random() - 0.5) * 0.5
        self.radius = random.random() * 2.5 + 0.5
        self.alpha = random.randint(20, 120)
        self.glow = random.random() > 0.6

    def move(self, width, height):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > width:
            self.vx *= -1
        if self.y < 0 or self.y > height:
            self.vy *= -1


# ─────────────────────────────────────────────
#  Matrix Rain Column
# ─────────────────────────────────────────────
class MatrixColumn:
    def __init__(self, x, height):
        self.x = x
        self.y = random.random() * -height
        self.speed = random.random() * 3 + 1.5
        self.chars = [chr(random.randint(33, 126)) for _ in range(25)]
        self.font_size = random.randint(9, 14)

    def move(self, height):
        self.y += self.speed
        if random.random() < 0.08:
            self.chars.pop(0)
            self.chars.append(chr(random.randint(33, 126)))
        if self.y - (len(self.chars) * self.font_size) > height:
            self.y = random.random() * -100
            self.speed = random.random() * 3 + 1.5


# ─────────────────────────────────────────────
#  Inline AI Command Bar Widget
# ─────────────────────────────────────────────
class AICommandBar(QWidget):
    command_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AICommandBar")
        self.setFixedHeight(56)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        # Pulse indicator dot
        self.dot = QLabel("●", self)
        self.dot.setStyleSheet("color: #00FF88; font-size: 10px; background: transparent;")
        layout.addWidget(self.dot)

        # Input field
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Ask Prime anything... (Press Enter)")
        self.input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #F0F4F8;
                font-size: 15px;
                font-family: 'Outfit', 'Segoe UI', sans-serif;
            }
            QLineEdit::placeholder { color: rgba(255,255,255,0.3); }
        """)
        self.input.returnPressed.connect(self._submit)
        layout.addWidget(self.input, 1)

        # Send button
        self.send_btn = QPushButton("→", self)
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._submit)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #27C8F5,stop:1 #8B5CF6);
                border: none; border-radius: 16px;
                color: white; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background: #27C8F5; }
        """)
        layout.addWidget(self.send_btn)

        # Pulse animation timer
        self._pulse_state = True
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_dot)
        self._pulse_timer.start(800)

    def _pulse_dot(self):
        self._pulse_state = not self._pulse_state
        color = "#00FF88" if self._pulse_state else "#004422"
        self.dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")

    def _submit(self):
        text = self.input.text().strip()
        if text:
            self.command_submitted.emit(text)
            self.input.clear()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 28, 28)
        painter.fillPath(path, QColor(10, 18, 40, 200))
        pen = QPen(QColor(39, 200, 245, 60), 1)
        painter.setPen(pen)
        painter.drawPath(path)


# ─────────────────────────────────────────────
#  Main OS Desktop
# ─────────────────────────────────────────────
class IPPrimeOSDesktop(QMainWindow):
    def __init__(self, face_path="assets/logo.png", ui_facade=None):
        super().__init__()
        self.face_path = face_path
        self.ui_facade = ui_facade
        self.particles = []
        self.matrix_columns = []
        self.wallpaper_style = "plexus"   # stars | matrix | plexus | aurora | none
        self.aurora_pulse = 0.0
        self.launcher = None
        self.theme_engine = OSThemeEngine()
        self._greeting = self._get_greeting()

        self.init_ui()
        self.init_particles()

    # ── Greeting ──────────────────────────────
    def _get_greeting(self):
        h = datetime.datetime.now().hour
        if h < 12:
            return "Good Morning, Pratik"
        elif h < 17:
            return "Good Afternoon, Pratik"
        else:
            return "Good Evening, Pratik"

    # ── UI Bootstrap ──────────────────────────
    def init_ui(self):
        hide_windows_taskbar()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)

        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("OSRoot")
        self.central_widget.setStyleSheet("background: transparent;")
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Workspace
        self.workspace = QWidget(self)
        self.workspace.setStyleSheet("background: transparent;")
        self.main_layout.addWidget(self.workspace, 1)

        # Taskbar
        self.taskbar = OSTaskbar(self)
        self.taskbar.start_clicked.connect(self.toggle_launcher)
        self.taskbar.assistant_clicked.connect(self.trigger_assistant)
        self.taskbar.files_clicked.connect(self.toggle_file_manager)
        self.taskbar.clock_clicked.connect(self.toggle_control_center)
        self.main_layout.addWidget(self.taskbar)

        self.setup_workspace_widgets()

        # Overlays
        self.launcher = AppLauncherWidget(self)
        self.launcher.hide()
        self.launcher.search_triggered.connect(self.on_launcher_search)
        self.launcher.pinned_changed.connect(self.taskbar.reload_shortcuts)

        self.control_center = ControlCenterWidget(self)
        self.control_center.hide()
        self.control_center.notifications_requested.connect(self.show_notifications_and_hide_cc)
        self.control_center.theme_changed.connect(self.on_theme_changed)

        self.vocal_terminal = VocalTerminalWidget(self)
        self.vocal_terminal.show()

        if self.ui_facade and hasattr(self.ui_facade, "_win") and self.ui_facade._win:
            self.ui_facade._win._log_sig.connect(self.write_log_to_terminal)

        self.notification_center = NotificationCenterWidget(self)
        self.notification_center.hide()
        self.notification_center.theme_changed.connect(self.on_theme_changed)

        self.file_manager = OSFileManagerWidget(self)
        self.file_manager.hide()
        self.file_manager.setFixedSize(800, 520)

        # Start workspace cleaner daemon
        self.cleaner_thread = WorkspaceCleanerDaemon(self)
        self.cleaner_thread.start()

        self.update_overlay_geometries()

        # 30 FPS animation
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_background)
        self.anim_timer.start(33)

        self.apply_theme_styles()

    # ── Workspace Layout ──────────────────────
    def setup_workspace_widgets(self):
        outer = QVBoxLayout(self.workspace)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top bar: greeting ──
        greeting_bar = QWidget(self)
        greeting_bar.setStyleSheet("background: transparent;")
        greeting_bar.setFixedHeight(52)
        gb_layout = QHBoxLayout(greeting_bar)
        gb_layout.setContentsMargins(36, 8, 36, 0)

        self.greeting_lbl = QLabel(self._greeting, self)
        self.greeting_lbl.setFont(QFont("Outfit", 17, QFont.Weight.Medium))
        self.greeting_lbl.setStyleSheet("color: rgba(255,255,255,0.70); background: transparent; letter-spacing: 1px;")
        gb_layout.addWidget(self.greeting_lbl)
        gb_layout.addStretch()

        self.brand_lbl = QLabel(self)
        self.brand_lbl.setText(
            "<div style='text-align:right;'>"
            "<span style='font-size:20px; font-weight:800; color:#27C8F5; letter-spacing:4px;'>IP PRIME OS</span>"
            "<br><span style='font-size:10px; color:rgba(136,153,166,0.8); letter-spacing:2px;'>IP VERSE VERIFIED</span>"
            "</div>"
        )
        self.brand_lbl.setStyleSheet("background: transparent;")
        gb_layout.addWidget(self.brand_lbl)
        outer.addWidget(greeting_bar)

        # ── Main row: center space containing only the AI Orb ──
        self.work_layout = QHBoxLayout()
        self.work_layout.setContentsMargins(36, 12, 36, 12)
        self.work_layout.setSpacing(0)

        # Set unused widgets to None to avoid AttributeError
        self.stats_widget = None
        self.weather_widget = None
        self.clock_widget = None
        self.ai_bar = None

        # Center column: AI Orb
        center_col = QVBoxLayout()
        center_col.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.ai_orb = AIOrb(self)
        self.ai_orb.orb_clicked.connect(self._on_orb_click)
        _shadow(self.ai_orb, blur=40, alpha=180)
        center_col.addStretch()
        center_col.addWidget(self.ai_orb, 0, Qt.AlignmentFlag.AlignHCenter)
        center_col.addStretch()
        self.work_layout.addLayout(center_col, 1)

        outer.addLayout(self.work_layout, 1)

    # ── Particles ─────────────────────────────
    def init_particles(self):
        w = self.width() if self.width() > 0 else 1920
        h = self.height() if self.height() > 0 else 1080
        for _ in range(45):
            self.particles.append(Particle(w, h))
        for x in range(0, w, 22):
            self.matrix_columns.append(MatrixColumn(x, h))

    def update_background(self):
        w, h = self.width(), self.height()
        if self.wallpaper_style in ("stars", "plexus"):
            for p in self.particles:
                p.move(w, h)
        elif self.wallpaper_style == "matrix":
            for col in self.matrix_columns:
                col.move(h)
        elif self.wallpaper_style == "aurora":
            self.aurora_pulse += 0.008
        self.update()

    # ── Paint ─────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self.theme_engine.current

        # Deep space background — multi-stop radial
        grad = QRadialGradient(self.width() * 0.5, self.height() * 0.4,
                               max(self.width(), self.height()) * 0.85)
        grad.setColorAt(0.0,  QColor(t["bg"]).lighter(115))
        grad.setColorAt(0.45, QColor(t["bg"]))
        grad.setColorAt(1.0,  QColor("#010207"))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.width(), self.height())

        if self.wallpaper_style in ("stars", "plexus"):
            for p in self.particles:
                c_hex = t["primary"] if p.glow else t["accent"]
                color = QColor(c_hex)
                color.setAlpha(p.alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                if p.glow:
                    gc = QColor(c_hex)
                    gc.setAlpha(int(p.alpha * 0.25))
                    painter.setBrush(QBrush(gc))
                    painter.drawEllipse(QPoint(int(p.x), int(p.y)),
                                        int(p.radius * 3), int(p.radius * 3))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPoint(int(p.x), int(p.y)),
                                    int(p.radius), int(p.radius))

            if self.wallpaper_style == "plexus":
                pts = self.particles
                base_color = QColor(t["primary"])
                pen = QPen(base_color, 0.8, Qt.PenStyle.SolidLine)
                for i in range(len(pts)):
                    for j in range(i + 1, len(pts)):
                        dx = pts[i].x - pts[j].x
                        dy = pts[i].y - pts[j].y
                        dist_sq = dx*dx + dy*dy
                        if dist_sq < 16900:  # 130 * 130 = 16900
                            dist = math.sqrt(dist_sq)
                            alpha = int(65 * (1.0 - dist / 130))
                            base_color.setAlpha(alpha)
                            pen.setColor(base_color)
                            painter.setPen(pen)
                            painter.drawLine(QPoint(int(pts[i].x), int(pts[i].y)),
                                             QPoint(int(pts[j].x), int(pts[j].y)))

        elif self.wallpaper_style == "matrix":
            for col in self.matrix_columns:
                font = QFont("Consolas", col.font_size)
                painter.setFont(font)
                y_off = 0
                for i, ch in enumerate(col.chars):
                    cy = col.y - y_off
                    if 0 < cy < self.height():
                        a = int(255 * (1.0 - i / len(col.chars)))
                        color = QColor(255, 255, 255, a) if i == 0 else QColor(0, 255, 70, a)
                        painter.setPen(color)
                        painter.drawText(int(col.x), int(cy), ch)
                    y_off += col.font_size
        elif self.wallpaper_style == "aurora":
            # Dark base background
            painter.fillRect(self.rect(), QColor("#080a10"))
            
            # Aurora Layer 1: Neon Cyan Glow shifting
            x1 = self.width() * (0.35 + 0.15 * math.sin(self.aurora_pulse))
            y1 = self.height() * (0.4 + 0.1 * math.cos(self.aurora_pulse * 1.3))
            grad1 = QRadialGradient(x1, y1, self.width() * 0.6)
            grad1.setColorAt(0.0, QColor(96, 205, 255, 30))  # Translucent cyan
            grad1.setColorAt(0.5, QColor(96, 205, 255, 6))
            grad1.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(grad1))
            painter.drawRect(self.rect())
            
            # Aurora Layer 2: Cobalt/Violet Glow shifting
            x2 = self.width() * (0.65 + 0.15 * math.cos(self.aurora_pulse * 0.8))
            y2 = self.height() * (0.3 + 0.12 * math.sin(self.aurora_pulse * 1.1))
            grad2 = QRadialGradient(x2, y2, self.width() * 0.55)
            grad2.setColorAt(0.0, QColor(139, 92, 246, 24))  # Translucent purple
            grad2.setColorAt(0.5, QColor(139, 92, 246, 4))
            grad2.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(grad2))
            painter.drawRect(self.rect())
            
            # Aurora Layer 3: Deep Emerald Glow shifting
            x3 = self.width() * (0.5 + 0.1 * math.sin(self.aurora_pulse * 1.5))
            y3 = self.height() * (0.75 + 0.12 * math.cos(self.aurora_pulse * 0.9))
            grad3 = QRadialGradient(x3, y3, self.width() * 0.5)
            grad3.setColorAt(0.0, QColor(16, 185, 129, 15))  # Translucent green
            grad3.setColorAt(0.6, QColor(16, 185, 129, 2))
            grad3.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(grad3))
            painter.drawRect(self.rect())

    # ── Overlay Toggles ───────────────────────
    def toggle_launcher(self):
        if self.notification_center.isVisible():
            self.notification_center.hide()
        if self.control_center.isVisible():
            self.control_center.hide()
        if self.launcher.isVisible():
            self.launcher.hide()
        else:
            self.update_overlay_geometries()
            self.launcher.show()
            self.launcher.raise_()
            self.launcher.search_bar.setFocus()

    def toggle_notification_center(self):
        if self.launcher.isVisible():
            self.launcher.hide()
        if self.control_center.isVisible():
            self.control_center.hide()
        if self.notification_center.isVisible():
            self.notification_center.hide()
        else:
            self.update_overlay_geometries()
            self.notification_center.show()
            self.notification_center.raise_()

    def toggle_control_center(self):
        if self.launcher.isVisible():
            self.launcher.hide()
        if self.notification_center.isVisible():
            self.notification_center.hide()
        if self.control_center.isVisible():
            self.control_center.hide()
        else:
            self.update_overlay_geometries()
            self.control_center.show()
            self.control_center.raise_()

    def show_notifications_and_hide_cc(self):
        self.control_center.hide()
        self.toggle_notification_center()

    def write_log_to_terminal(self, text):
        if hasattr(self, "vocal_terminal") and self.vocal_terminal:
            self.vocal_terminal.append_text(text)

    def toggle_file_manager(self):
        if self.file_manager.isVisible():
            self.file_manager.hide()
        else:
            fw, fh = self.file_manager.width(), self.file_manager.height()
            self.file_manager.setGeometry(
                (self.width() - fw) // 2,
                (self.workspace.height() - fh) // 2,
                fw, fh
            )
            self.file_manager.show()
            self.file_manager.raise_()

    def update_overlay_geometries(self):
        t_top = self.taskbar.geometry().top()
        self.launcher.setGeometry(10, t_top - 510, 380, 500)
        self.notification_center.setGeometry(self.width() - 330, 0, 330, t_top)
        self.control_center.setGeometry(self.width() - 390, t_top - 360, 380, 350)
        self.vocal_terminal.setGeometry(15, t_top - 235, 380, 220)

    # ── AI Command handling ───────────────────
    def on_ai_command(self, text):
        """Forward typed command directly to the Saturday AI assistant."""
        self.set_orb_state(PROCESSING)
        try:
            qapp = QApplication.instance()
            for widget in qapp.topLevelWidgets():
                if widget is not self and hasattr(widget, "on_text_command"):
                    # Silently forward command in the background — no popup!
                    widget.on_text_command(text)
                    return
        except Exception as e:
            print(f"[AI Bar] Forward failed: {e}")
        # If no handler found, return to idle
        QTimer.singleShot(3000, lambda: self.set_orb_state(IDLE))

    def _on_orb_click(self):
        """Orb clicked — toggle listening state and wake assistant."""
        if self.ui_facade:
            # Toggling the system's muted state triggers listening dynamically
            self.ui_facade.muted = not self.ui_facade.muted
            if not self.ui_facade.muted and self.ai_bar:
                self.ai_bar.input.setFocus()
        else:
            # Fallback to local toggle if ui_facade is missing
            if self.ai_orb.state == IDLE:
                self.set_orb_state(LISTENING)
                if self.ai_bar:
                    self.ai_bar.input.setFocus()
            else:
                self.set_orb_state(IDLE)

    def set_orb_state(self, state: str):
        """Public API — call this from any system hook to update orb visuals."""
        if hasattr(self, "ai_orb"):
            self.ai_orb.set_state(state)

    def trigger_assistant(self):
        """Trigger voice assistant (microphone toggle) silently."""
        if self.ui_facade:
            self.ui_facade.muted = not self.ui_facade.muted
        else:
            try:
                qapp = QApplication.instance()
                for widget in qapp.topLevelWidgets():
                    if widget is not self and hasattr(widget, "on_text_command"):
                        # If no ui_facade, just toggle mute of SimpleMainWindow directly if possible
                        if hasattr(widget, "_toggle_mute"):
                            widget._toggle_mute()
            except Exception as e:
                print(f"[OS Shell] Assistant toggle failed: {e}")

    def on_launcher_search(self, query):
        self.on_ai_command(query)

    # ── Theme ─────────────────────────────────
    def apply_theme_styles(self):
        t = self.theme_engine.current

        self.greeting_lbl.setStyleSheet("color: rgba(255,255,255,0.70); background: transparent; letter-spacing:1px;")
        self.brand_lbl.setText(
            f"<div style='text-align:right;'>"
            f"<span style='font-size:20px; font-weight:800; color:{t['primary']}; letter-spacing:4px;'>IP PRIME OS</span>"
            f"<br><span style='font-size:10px; color:{t['text_muted']}; letter-spacing:2px;'>IP VERSE VERIFIED</span>"
            f"</div>"
        )
        if self.clock_widget:
            self.clock_widget.date_label.setStyleSheet(f"color: {t['primary']}; background: transparent;")

        if self.stats_widget:
            _apply_panel_style(self.stats_widget, "StatsWidget", t, extras=f"""
                QProgressBar {{
                    border: 1px solid rgba(255,255,255,0.08); border-radius:5px;
                    text-align:center; color:#FFF;
                    background-color: rgba(20,28,48,0.5); height:12px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {t['primary']},stop:1 {t['accent']});
                    border-radius:4px;
                }}
            """)
        if self.weather_widget:
            _apply_panel_style(self.weather_widget, "WeatherWidget", t)
            self.weather_widget.city_lbl.setStyleSheet(f"color: {t['primary']};")

        self.taskbar.setStyleSheet(f"""
            QWidget#Taskbar {{
                background-color: {t['panel']};
                border-top: 1px solid {t['border']};
            }}
            QPushButton#StartButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {t['primary']},stop:1 {t['accent']});
                border:none; border-radius:18px; color:#FFF; font-weight:bold; font-size:14px;
            }}
            QPushButton#StartButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {t['accent']},stop:1 {t['primary']});
            }}
            QPushButton#AppShortcut {{
                background: rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
                border-radius:6px; color:{t['text']}; font-size:11px; padding:4px 10px; min-width:60px;
            }}
            QPushButton#AppShortcut:hover {{
                background: rgba(255,255,255,0.12); border:1px solid {t['primary']};
            }}
            QLabel#TrayClock {{
                color:{t['text']}; font-size:12px; font-weight:bold;
                background:transparent; margin-right:15px;
            }}
            QLabel#TrayClock:hover {{ color:{t['primary']}; }}
            QLabel#SysStatusLabel {{
                color:{t['text_muted']}; font-size:11px; background:transparent; margin-right:10px;
            }}
        """)

        self.launcher.setStyleSheet(f"""
            #Launcher {{
                background:{t['panel']}; border:1px solid {t['border']}; border-radius:16px;
            }}
            QLineEdit {{
                background:rgba(20,28,48,0.8); border:1px solid {t['border']};
                border-radius:8px; color:#FFF; padding:10px 15px; font-size:14px;
            }}
            QLineEdit:focus {{ border:1px solid {t['primary']}; }}
            QListWidget {{ background:transparent; border:none; color:{t['text']}; }}
            QListWidget::item {{
                background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05);
                border-radius:6px; margin:4px 8px; padding:10px;
            }}
            QListWidget::item:hover {{
                background:rgba(255,255,255,0.08); border:1px solid {t['primary']};
            }}
            QListWidget::item:selected {{
                background:rgba(139,92,246,0.2); border:1px solid {t['accent']}; color:#FFF;
            }}
            QLabel {{ color:{t['text']}; background:transparent; }}
        """)
        self.launcher.info_label.setStyleSheet(f"color:{t['primary']}; margin-left:8px;")

        self.file_manager.setStyleSheet(f"""
            #FileManager {{
                background:{t['panel']}; border:1px solid {t['border']}; border-radius:12px;
            }}
            QListWidget {{ background:transparent; border:none; color:{t['text']}; }}
            QListWidget::item {{
                background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.04);
                border-radius:6px; margin:3px 6px; padding:8px;
            }}
            QListWidget::item:hover {{
                background:rgba(255,255,255,0.08); border:1px solid {t['primary']};
            }}
            QListWidget::item:selected {{
                background:rgba(139,92,246,0.15); border:1px solid {t['accent']}; color:#FFF;
            }}
            QLineEdit {{
                background:rgba(20,28,48,0.8); border:1px solid {t['border']};
                border-radius:8px; color:#FFF; padding:6px 12px; font-size:13px;
            }}
            QPushButton {{
                background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
                border-radius:6px; color:{t['text']}; padding:6px 12px; font-size:12px;
            }}
            QPushButton:hover {{ background:rgba(255,255,255,0.12); border:1px solid {t['primary']}; }}
            QLabel {{ color:{t['text']}; background:transparent; }}
        """)
        self.file_manager.title_bar.setStyleSheet("background:rgba(255,255,255,0.02); border-radius:6px;")

    def on_theme_changed(self, theme_key):
        self.theme_engine.load_theme()
        self.apply_theme_styles()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_overlay_geometries()

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()
        
        # Check Ctrl + Shift modifiers
        if (modifiers & Qt.KeyboardModifier.ControlModifier) and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            if key == Qt.Key.Key_P:
                self.toggle_launcher()
                event.accept()
                return
            elif key == Qt.Key.Key_L:
                self.toggle_control_center()
                event.accept()
                return
            elif key == Qt.Key.Key_T:
                if hasattr(self, "vocal_terminal") and self.vocal_terminal:
                    if self.vocal_terminal.isVisible():
                        self.vocal_terminal.hide()
                    else:
                        self.vocal_terminal.show()
                        self.vocal_terminal.raise_()
                event.accept()
                return
            elif key == Qt.Key.Key_C:
                if hasattr(self, "control_center") and self.control_center:
                    self.toggle_control_center()
                event.accept()
                return
        
        # F1 -> Launcher
        if key == Qt.Key.Key_F1:
            self.toggle_launcher()
            event.accept()
            return
            
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "cleaner_thread") and self.cleaner_thread:
            self.cleaner_thread.stop()
            self.cleaner_thread.wait()
        show_windows_taskbar()
        super().closeEvent(event)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def _shadow(widget, blur=20, alpha=160, offset_y=4):
    s = QGraphicsDropShadowEffect(widget)
    s.setBlurRadius(blur)
    s.setColor(QColor(0, 0, 0, alpha))
    s.setOffset(0, offset_y)
    widget.setGraphicsEffect(s)


def _apply_panel_style(widget, obj_name, t, extras=""):
    widget.setStyleSheet(f"""
        QWidget#{obj_name} {{
            background-color: {t['panel']};
            border: 1px solid {t['border']};
            border-radius: 14px;
        }}
        QLabel {{ color: {t['text']}; background: transparent; }}
        {extras}
    """)

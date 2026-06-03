from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen
from actions.pomodoro import PomodoroTimer

class PomodoroPanel(QDialog):
    tick_sig = pyqtSignal(int)
    complete_sig = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(360, 420)
        
        self.timer = PomodoroTimer()
        self.tick_sig.connect(self._on_tick)
        self.complete_sig.connect(self._on_complete)
        
        self._init_ui()

    def _init_ui(self):
        container = QWidget(self)
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container {
                background: rgba(15, 23, 42, 0.94);
                border: 2px solid rgba(239, 68, 68, 0.4);
                border-radius: 18px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title block
        title_lay = QHBoxLayout()
        title_lbl = QLabel("FOCUS TIMER 🍅")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #EF4444; letter-spacing: 0.5px; background: transparent;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.3);
                border: 1px solid #EF4444;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        title_lay.addWidget(title_lbl)
        title_lay.addStretch()
        title_lay.addWidget(close_btn)
        layout.addLayout(title_lay)

        # Circular Visualizer Widget
        self.circle_widget = PomodoroCircleWidget(self)
        self.circle_widget.setFixedSize(180, 180)
        layout.addWidget(self.circle_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Presets Buttons
        preset_lay = QHBoxLayout()
        preset_lay.setSpacing(10)
        
        presets = [("15m", 15), ("25m", 25), ("50m", 50)]
        for label, mins in presets:
            btn = QPushButton(label)
            btn.setFixedSize(65, 30)
            btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #E2E8F0;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background: rgba(239, 68, 68, 0.1);
                    border: 1px solid rgba(239, 68, 68, 0.3);
                }
            """)
            btn.clicked.connect(lambda checked, m=mins: self._set_preset(m))
            preset_lay.addWidget(btn)
            
        layout.addLayout(preset_lay)

        # Control Buttons
        ctrl_lay = QHBoxLayout()
        
        self.start_btn = QPushButton("START FOCUS")
        self.start_btn.setFixedHeight(38)
        self.start_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.3);
                border: 1px solid #EF4444;
            }
        """)
        self.start_btn.clicked.connect(self._toggle_timer)
        
        ctrl_lay.addWidget(self.start_btn)
        layout.addLayout(ctrl_lay)

        # Ambient Option Label
        self.ambient_lbl = QLabel("Ambient: Off | blacklisted apps are monitored.")
        self.ambient_lbl.setFont(QFont("Segoe UI", 8))
        self.ambient_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        self.ambient_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.ambient_lbl)

        # Full layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
        
        self._current_preset_mins = 25
        self._update_circle(self._current_preset_mins * 60)

    def _set_preset(self, mins):
        if self.timer.is_running:
            return
        self._current_preset_mins = mins
        self._update_circle(mins * 60)

    def _update_circle(self, secs):
        self.circle_widget.set_time(secs, self._current_preset_mins * 60)

    def _toggle_timer(self):
        if self.timer.is_running:
            self.timer.stop()
            self.start_btn.setText("START FOCUS")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(239, 68, 68, 0.15);
                    color: #EF4444;
                    border: 1px solid rgba(239, 68, 68, 0.4);
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background: rgba(239, 68, 68, 0.3);
                    border: 1px solid #EF4444;
                }
            """)
            self._update_circle(self._current_preset_mins * 60)
        else:
            self.timer.start(
                self._current_preset_mins,
                self.parent(),
                on_tick=self.tick_sig.emit,
                on_complete=self.complete_sig.emit
            )
            self.start_btn.setText("PAUSE FOCUS")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.15);
                    color: #E2E8F0;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.25);
                    border: 1px solid #E2E8F0;
                }
            """)

    def _on_tick(self, remaining):
        self._update_circle(remaining)

    def _on_complete(self):
        self.start_btn.setText("START FOCUS")
        self._update_circle(self._current_preset_mins * 60)


class PomodoroCircleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.remaining = 25 * 60
        self.total = 25 * 60

    def set_time(self, remaining, total):
        self.remaining = remaining
        self.total = total
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        side = min(width, height)
        
        # Draw background track
        pen_track = QPen(QColor(239, 68, 68, 30))
        pen_track.setWidth(8)
        painter.setPen(pen_track)
        painter.drawEllipse(10, 10, side - 20, side - 20)
        
        # Draw active progress arc
        progress = float(self.remaining) / float(max(self.total, 1))
        span_angle = -int(progress * 360 * 16)
        start_angle = 90 * 16
        
        pen_arc = QPen(QColor(239, 68, 68, 220))
        pen_arc.setWidth(8)
        pen_arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_arc)
        painter.drawArc(10, 10, side - 20, side - 20, start_angle, span_angle)
        
        # Draw time text in the center
        mins = self.remaining // 60
        secs = self.remaining % 60
        time_str = f"{mins:02d}:{secs:02d}"
        
        painter.setPen(QColor(226, 232, 240))
        painter.setFont(QFont("Consolas", 24, QFont.Weight.Bold))
        painter.drawText(0, 0, width, height, Qt.AlignmentFlag.AlignCenter, time_str)

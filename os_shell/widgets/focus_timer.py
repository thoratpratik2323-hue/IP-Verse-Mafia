"""
os_shell/widgets/focus_timer.py — Pomodoro Focus Timer HUD.
Floating draggable widget with ring progress, 25-min work / 5-min break cycles.
Triggered by Ctrl+Shift+F or Command Palette "focus start".
"""

import math
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath


WORK_SECONDS = 25 * 60
BREAK_SECONDS = 5 * 60


class _RingCanvas(QWidget):
    """Draws the circular progress ring."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.progress = 1.0      # 1.0 = full ring, 0.0 = empty
        self.is_break = False

    def set_progress(self, value: float, is_break: bool = False):
        self.progress = max(0.0, min(1.0, value))
        self.is_break = is_break
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy, r = 60, 60, 48
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)

        # Background ring
        pen = QPen(QColor(255, 255, 255, 25), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)

        # Progress arc
        color = QColor("#10b981") if self.is_break else QColor("#06b6d4")
        pen2 = QPen(color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen2)
        span = int(self.progress * 360 * 16)
        painter.drawArc(rect, 90 * 16, -span)

        # Dot at progress tip
        angle_deg = 90 - self.progress * 360
        angle_rad = math.radians(angle_deg)
        dx = math.cos(angle_rad) * r
        dy = -math.sin(angle_rad) * r
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx + dx - 5, cy + dy - 5, 10, 10))


class FocusTimerWidget(QWidget):
    """Draggable floating Pomodoro timer HUD."""
    session_done = pyqtSignal(str)   # emits "work" or "break" when done

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(160, 210)

        self._total = WORK_SECONDS
        self._remaining = WORK_SECONDS
        self._is_break = False
        self._running = False
        self._cycle = 1
        self._drag_pos = None

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Background card
        self._card = QWidget(self)
        self._card.setStyleSheet("""
            QWidget {
                background: rgba(10, 18, 35, 0.92);
                border: 1px solid rgba(6, 182, 212, 0.35);
                border-radius: 18px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(6, 182, 212, 100))
        shadow.setOffset(0, 4)
        self._card.setGraphicsEffect(shadow)
        self._card.setGeometry(0, 0, 160, 210)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)

        # Mode label
        self._mode_lbl = QLabel("🎯 FOCUS")
        self._mode_lbl.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        self._mode_lbl.setStyleSheet("color: rgba(6,182,212,0.9); background: transparent; border: none;")
        self._mode_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._mode_lbl)

        # Ring
        self._ring = _RingCanvas()
        card_layout.addWidget(self._ring, alignment=Qt.AlignmentFlag.AlignCenter)

        # Timer label (drawn on top of ring)
        self._time_lbl = QLabel("25:00")
        self._time_lbl.setFont(QFont("Outfit", 16, QFont.Weight.Bold))
        self._time_lbl.setStyleSheet("color: #f8fafc; background: transparent; border: none;")
        self._time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_lbl.setGeometry(20, 55, 120, 40)
        self._time_lbl.setParent(self._card)

        # Cycle counter
        self._cycle_lbl = QLabel("Cycle 1")
        self._cycle_lbl.setFont(QFont("Outfit", 9))
        self._cycle_lbl.setStyleSheet("color: rgba(255,255,255,0.45); background: transparent; border: none;")
        self._cycle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._cycle_lbl)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._start_btn = QPushButton("▶")
        self._stop_btn = QPushButton("⏹")
        self._close_btn = QPushButton("✕")

        for btn, tip in [(self._start_btn, "Start/Pause"), (self._stop_btn, "Reset"), (self._close_btn, "Close")]:
            btn.setToolTip(tip)
            btn.setFixedSize(36, 28)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.10);
                    border: 1px solid rgba(255,255,255,0.18);
                    border-radius: 7px;
                    color: white;
                    font-size: 12px;
                }
                QPushButton:hover { background: rgba(6,182,212,0.25); }
            """)
            btn_row.addWidget(btn)

        self._start_btn.clicked.connect(self._toggle)
        self._stop_btn.clicked.connect(self._reset)
        self._close_btn.clicked.connect(self.hide)
        card_layout.addLayout(btn_row)

        self._update_display()

    # ── Logic ─────────────────────────────────────────────
    def _toggle(self):
        if self._running:
            self._timer.stop()
            self._running = False
            self._start_btn.setText("▶")
        else:
            self._timer.start()
            self._running = True
            self._start_btn.setText("⏸")

    def _reset(self):
        self._timer.stop()
        self._running = False
        self._is_break = False
        self._remaining = WORK_SECONDS
        self._total = WORK_SECONDS
        self._start_btn.setText("▶")
        self._update_display()

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            self._running = False
            done_type = "break" if self._is_break else "work"
            self.session_done.emit(done_type)
            # Auto-switch to break/work
            self._is_break = not self._is_break
            if not self._is_break:
                self._cycle += 1
            self._total = BREAK_SECONDS if self._is_break else WORK_SECONDS
            self._remaining = self._total
            self._start_btn.setText("▶")
        self._update_display()

    def _update_display(self):
        mins = self._remaining // 60
        secs = self._remaining % 60
        self._time_lbl.setText(f"{mins:02d}:{secs:02d}")
        progress = self._remaining / self._total if self._total > 0 else 1.0
        self._ring.set_progress(progress, self._is_break)
        self._mode_lbl.setText("☕ BREAK" if self._is_break else "🎯 FOCUS")
        self._cycle_lbl.setText(f"Cycle {self._cycle}")

    def start_focus(self):
        """Public method to start a fresh work session."""
        self._reset()
        self.show()
        self.raise_()
        self._toggle()

    # ── Drag ─────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

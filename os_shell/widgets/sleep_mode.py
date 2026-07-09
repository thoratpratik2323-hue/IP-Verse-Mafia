"""
os_shell/widgets/sleep_mode.py — IP Prime Sleep Mode overlay.
After 30 min of inactivity, dims the screen and enters sleep.
Wake word or mouse click brings it back.
"""

import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QColor, QFont, QPainter, QLinearGradient, QKeyEvent


class SleepModeOverlay(QWidget):
    """Full-screen sleep mode overlay with clock and wake hint."""
    wake_requested = pyqtSignal()   # Emitted when user wakes IP Prime

    INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000   # 30 minutes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._sleeping = False
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._setup_ui()
        self.hide()

        # Inactivity timer
        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setInterval(self.INACTIVITY_TIMEOUT_MS)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.timeout.connect(self.enter_sleep)
        self._inactivity_timer.start()

        # Clock update
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        self._time_lbl = QLabel("00:00")
        self._time_lbl.setFont(QFont("Outfit", 72, QFont.Weight.Thin))
        self._time_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.85); background: transparent;")
        self._time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont("Outfit", 18, QFont.Weight.Light))
        self._date_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45); background: transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._hint_lbl = QLabel("💤  IP Prime is sleeping…  Click or press any key to wake")
        self._hint_lbl.setFont(QFont("Outfit", 12))
        self._hint_lbl.setStyleSheet("color: rgba(6, 182, 212, 0.55); background: transparent;")
        self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        layout.addWidget(self._time_lbl)
        layout.addWidget(self._date_lbl)
        layout.addSpacing(40)
        layout.addWidget(self._hint_lbl)
        layout.addStretch()

    def _update_clock(self):
        now = datetime.datetime.now()
        self._time_lbl.setText(now.strftime("%H:%M"))
        self._date_lbl.setText(now.strftime("%A, %d %B %Y"))

    def reset_inactivity(self):
        """Call this on every user interaction to reset the 30-min timer."""
        if not self._sleeping:
            self._inactivity_timer.start()

    def enter_sleep(self):
        """Fade in the sleep overlay."""
        if self._sleeping:
            return
        self._sleeping = True
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self._update_clock()
        self._clock_timer.start()

        anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim.setDuration(1500)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.start()
        self._anim = anim   # keep reference

    def wake_up(self):
        """Fade out the sleep overlay."""
        if not self._sleeping:
            return
        self._sleeping = False
        self._clock_timer.stop()

        anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim.setDuration(800)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self.hide)
        anim.start()
        self._anim = anim

        self._inactivity_timer.start()   # Restart countdown
        self.wake_requested.emit()

    def is_sleeping(self) -> bool:
        return self._sleeping

    def paintEvent(self, event):
        if not self._sleeping:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(2, 6, 18, 245))
        grad.setColorAt(0.5, QColor(5, 10, 30, 250))
        grad.setColorAt(1.0, QColor(2, 6, 18, 245))
        painter.fillRect(self.rect(), grad)

    def mousePressEvent(self, event):
        self.wake_up()

    def keyPressEvent(self, event: QKeyEvent):
        self.wake_up()

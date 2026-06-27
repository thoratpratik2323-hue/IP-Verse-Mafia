import datetime
from PyQt6.QtCore import Qt, QTime, QDate, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPainterPath

class ClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        # ── Big time label ──
        self.time_label = QLabel(self)
        self.time_label.setFont(QFont("Outfit", 62, QFont.Weight.Bold))
        self.time_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; letter-spacing: -2px;"
        )
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.time_label)

        # ── AM/PM + seconds row ──
        sub_row = QHBoxLayout()
        sub_row.setContentsMargins(0, 0, 0, 0)
        sub_row.setSpacing(8)
        sub_row.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.ampm_label = QLabel(self)
        self.ampm_label.setFont(QFont("Outfit", 16, QFont.Weight.Medium))
        self.ampm_label.setStyleSheet("color: #27C8F5; background: transparent; letter-spacing: 2px;")
        sub_row.addWidget(self.ampm_label)

        self.sec_label = QLabel(self)
        self.sec_label.setFont(QFont("Outfit", 16, QFont.Weight.Light))
        self.sec_label.setStyleSheet("color: rgba(255,255,255,0.4); background: transparent;")
        sub_row.addWidget(self.sec_label)

        layout.addLayout(sub_row)

        # ── Date label ──
        self.date_label = QLabel(self)
        self.date_label.setFont(QFont("Outfit", 13, QFont.Weight.Medium))
        self.date_label.setStyleSheet("color: #27C8F5; background: transparent; letter-spacing: 1px;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.date_label)

        # ── Day / week strip ──
        self.day_label = QLabel(self)
        self.day_label.setFont(QFont("Outfit", 10, QFont.Weight.Light))
        self.day_label.setStyleSheet("color: rgba(255,255,255,0.35); background: transparent; letter-spacing: 3px;")
        self.day_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.day_label)

        # Timer — 1 second tick
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_date)
        self.timer.start(1000)
        self.update_time_date()

    def update_time_date(self):
        now = datetime.datetime.now()
        hour12 = now.strftime("%I:%M")
        ampm   = now.strftime("%p")
        secs   = now.strftime(":%S")
        date   = now.strftime("%A, %B %d")
        year   = now.strftime("%Y")
        week   = f"WEEK {now.strftime('%V')} · {year}"

        self.time_label.setText(hour12)
        self.ampm_label.setText(ampm)
        self.sec_label.setText(secs)
        self.date_label.setText(date)
        self.day_label.setText(week)

    def set_font_family(self, family):
        self.time_label.setFont(QFont(family, 62, QFont.Weight.Bold))
        self.date_label.setFont(QFont(family, 13, QFont.Weight.Medium))

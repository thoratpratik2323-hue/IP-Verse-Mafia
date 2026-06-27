import sys
from PyQt6.QtCore import Qt, QTime, QDate, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont, QColor

class ClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(2)
        self.setLayout(layout)
        
        # Time label
        self.time_label = QLabel(self)
        self.time_label.setFont(QFont("Outfit", 48, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.time_label)
        
        # Date label
        self.date_label = QLabel(self)
        self.date_label.setFont(QFont("Outfit", 14, QFont.Weight.Medium))
        self.date_label.setStyleSheet("color: #27C8F5; background: transparent;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.date_label)
        
        # Start timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_date)
        self.timer.start(1000)
        
        # Initial update
        self.update_time_date()
        
    def update_time_date(self):
        current_time = QTime.currentTime().toString("hh:mm A")
        current_date = QDate.currentDate().toString("dddd, MMMM dd, yyyy")
        
        self.time_label.setText(current_time)
        self.date_label.setText(current_date)
        
    def set_font_family(self, family):
        self.time_label.setFont(QFont(family, 48, QFont.Weight.Bold))
        self.date_label.setFont(QFont(family, 14, QFont.Weight.Medium))

import sys
import psutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtGui import QFont

class SystemStatsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        # Semi-transparent glass container styling
        self.setObjectName("StatsWidget")
        self.setStyleSheet("""
            QWidget#StatsWidget {
                background-color: rgba(8, 14, 28, 0.6);
                border: 1px solid rgba(39, 200, 245, 0.15);
                border-radius: 12px;
            }
            QLabel {
                color: #F0F4F8;
                background: transparent;
            }
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                text-align: center;
                color: #FFFFFF;
                background-color: rgba(20, 28, 48, 0.5);
                height: 12px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #27C8F5, stop:1 #8B5CF6);
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # Header
        header = QLabel("System Status", self)
        header.setFont(QFont("Outfit", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #27C8F5; font-weight: bold;")
        layout.addWidget(header)
        
        # CPU Info
        cpu_layout = QHBoxLayout()
        cpu_label = QLabel("CPU:", self)
        cpu_label.setFont(QFont("Outfit", 10))
        self.cpu_bar = QProgressBar(self)
        self.cpu_bar.setRange(0, 100)
        cpu_layout.addWidget(cpu_label)
        cpu_layout.addWidget(self.cpu_bar)
        layout.addLayout(cpu_layout)
        
        # RAM Info
        ram_layout = QHBoxLayout()
        ram_label = QLabel("RAM:", self)
        ram_label.setFont(QFont("Outfit", 10))
        self.ram_bar = QProgressBar(self)
        self.ram_bar.setRange(0, 100)
        ram_layout.addWidget(ram_label)
        ram_layout.addWidget(self.ram_bar)
        layout.addLayout(ram_layout)
        
        # Disk Info
        disk_layout = QHBoxLayout()
        disk_label = QLabel("Disk:", self)
        disk_label.setFont(QFont("Outfit", 10))
        self.disk_bar = QProgressBar(self)
        self.disk_bar.setRange(0, 100)
        disk_layout.addWidget(disk_label)
        disk_layout.addWidget(self.disk_bar)
        layout.addLayout(disk_layout)
        
        # Update Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)
        
        # Initial check
        self.update_stats()
        
    def update_stats(self):
        cpu_pct = int(psutil.cpu_percent())
        ram_pct = int(psutil.virtual_memory().percent)
        disk_pct = int(psutil.disk_usage('/').percent)
        
        self.cpu_bar.setValue(cpu_pct)
        self.cpu_bar.setFormat(f"{cpu_pct}%")
        
        self.ram_bar.setValue(ram_pct)
        self.ram_bar.setFormat(f"{ram_pct}%")
        
        self.disk_bar.setValue(disk_pct)
        self.disk_bar.setFormat(f"{disk_pct}%")

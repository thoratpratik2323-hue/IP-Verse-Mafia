import sys
from PyQt6.QtCore import Qt, QTime, QDate, QTimer, pyqtSignal, QPoint
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QFrame
)
from PyQt6.QtGui import QFont, QColor

class OSTaskbar(QWidget):
    # Signals
    start_clicked = pyqtSignal()
    assistant_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setFixedHeight(48)
        self.setObjectName("Taskbar")
        self.setStyleSheet("""
            QWidget#Taskbar {
                background-color: rgba(8, 14, 28, 0.95);
                border-top: 1px solid rgba(39, 200, 245, 0.2);
            }
            QPushButton#StartButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #27C8F5, stop:1 #8B5CF6);
                border: none;
                border-radius: 18px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#StartButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8B5CF6, stop:1 #27C8F5);
            }
            QPushButton#AppShortcut {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #F0F4F8;
                font-size: 11px;
                padding: 4px 10px;
                min-width: 60px;
            }
            QPushButton#AppShortcut:hover {
                background-color: rgba(39, 200, 245, 0.15);
                border: 1px solid rgba(39, 200, 245, 0.3);
            }
            QLabel#TrayClock {
                color: #F0F4F8;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
                margin-right: 15px;
            }
            QLabel#SysStatusLabel {
                color: #8899A6;
                font-size: 11px;
                background: transparent;
                margin-right: 10px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # Start button / Prime Orb trigger
        self.start_btn = QPushButton("IP", self)
        self.start_btn.setObjectName("StartButton")
        self.start_btn.setFixedSize(36, 36)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        layout.addWidget(self.start_btn)
        
        # Separator line
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.1); max-height: 24px;")
        layout.addWidget(sep)
        
        # App Shortcuts
        self.shortcut_browser = QPushButton("Browser", self)
        self.shortcut_browser.setObjectName("AppShortcut")
        self.shortcut_browser.clicked.connect(lambda: self.launch_app("explorer.exe", "https://google.com"))
        layout.addWidget(self.shortcut_browser)
        
        self.shortcut_files = QPushButton("Files", self)
        self.shortcut_files.setObjectName("AppShortcut")
        self.shortcut_files.clicked.connect(lambda: self.launch_app("explorer.exe"))
        layout.addWidget(self.shortcut_files)

        self.shortcut_cmd = QPushButton("Terminal", self)
        self.shortcut_cmd.setObjectName("AppShortcut")
        self.shortcut_cmd.clicked.connect(lambda: self.launch_app("cmd.exe"))
        layout.addWidget(self.shortcut_cmd)
        
        # Mic / Assistant quick trigger
        self.mic_btn = QPushButton("🎙️ Ask Prime", self)
        self.mic_btn.setObjectName("AppShortcut")
        self.mic_btn.setStyleSheet("""
            QPushButton#AppShortcut {
                color: #27C8F5;
                font-weight: bold;
                border: 1px solid rgba(39, 200, 245, 0.3);
            }
        """)
        self.mic_btn.clicked.connect(self.assistant_clicked.emit)
        layout.addWidget(self.mic_btn)
        
        # Spacer
        layout.addStretch()
        
        # System status text
        self.status_lbl = QLabel(self)
        self.status_lbl.setObjectName("SysStatusLabel")
        layout.addWidget(self.status_lbl)
        
        # Tray Clock
        self.clock_lbl = QLabel(self)
        self.clock_lbl.setObjectName("TrayClock")
        layout.addWidget(self.clock_lbl)
        
        # Timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_tray)
        self.timer.start(1000)
        
        self.update_tray()
        
    def update_tray(self):
        current_time = QTime.currentTime().toString("hh:mm A")
        self.clock_lbl.setText(current_time)
        
        # System summary
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.status_lbl.setText(f"CPU: {int(cpu)}% | RAM: {int(ram)}%")
        
    def launch_app(self, app_name, arg=None):
        import subprocess
        try:
            if arg:
                subprocess.Popen([app_name, arg])
            else:
                subprocess.Popen(app_name)
        except Exception as e:
            print(f"Failed to launch shortcut: {e}")

import sys
import subprocess
from PyQt6.QtCore import Qt, QTime, QDate, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPainterPath

class OSTaskbar(QWidget):
    start_clicked     = pyqtSignal()
    assistant_clicked = pyqtSignal()
    files_clicked     = pyqtSignal()
    clock_clicked     = pyqtSignal()
    orb_state_changed = pyqtSignal(str)   # forwards orb state to desktop

    def __init__(self, parent=None):
        super().__init__(parent)
        self._wifi_status = "📶 Connected"
        self._bt_status = "ᛒ Active"
        self._tick_count = 0
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(52)
        self.setObjectName("Taskbar")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(6)

        # ── IP Orb (Start) ──
        self.start_btn = QPushButton("IP", self)
        self.start_btn.setObjectName("StartButton")
        self.start_btn.setFixedSize(38, 38)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setFont(QFont("Outfit", 12, QFont.Weight.Bold))
        self.start_btn.setStyleSheet("""
            QPushButton#StartButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #27C8F5,stop:1 #8B5CF6);
                border: none; border-radius: 19px;
                color: #fff; font-weight: 800;
            }
            QPushButton#StartButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #8B5CF6,stop:1 #27C8F5);
            }
        """)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        layout.addWidget(self.start_btn)

        # ── Separator ──
        # ── Shortcuts Layout Container ──
        self.shortcuts_container = QWidget(self)
        self.shortcuts_container.setStyleSheet("background: transparent; border: none;")
        self.shortcuts_layout = QHBoxLayout(self.shortcuts_container)
        self.shortcuts_layout.setContentsMargins(0, 0, 0, 0)
        self.shortcuts_layout.setSpacing(8)
        layout.addWidget(self.shortcuts_container)

        layout.addWidget(_sep(self))
        
        self.reload_shortcuts()

        # ── Spacer ──
        layout.addStretch()

        # ── System status ──
        self.status_lbl = QLabel(self)
        self.status_lbl.setObjectName("SysStatusLabel")
        self.status_lbl.setFont(QFont("Outfit", 10))
        self.status_lbl.setStyleSheet("color: rgba(136,153,166,0.8); background: transparent; margin-right: 8px;")
        layout.addWidget(self.status_lbl)

        # ── WiFi Button ──
        self.wifi_btn = QPushButton(self._wifi_status, self)
        self.wifi_btn.setObjectName("TrayWifi")
        self.wifi_btn.setFont(QFont("Outfit", 10))
        self.wifi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wifi_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #27C8F5;
                padding: 2px 6px; margin-right: 4px;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(39, 200, 245, 0.12);
                border-radius: 4px;
            }
        """)
        self.wifi_btn.clicked.connect(lambda: self.launch("ms-availablenetworks:"))
        layout.addWidget(self.wifi_btn)

        # ── Bluetooth Button ──
        self.bt_btn = QPushButton(self._bt_status, self)
        self.bt_btn.setObjectName("TrayBluetooth")
        self.bt_btn.setFont(QFont("Outfit", 10))
        self.bt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bt_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #8B5CF6;
                padding: 2px 6px; margin-right: 8px;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(139, 92, 246, 0.12);
                border-radius: 4px;
            }
        """)
        self.bt_btn.clicked.connect(lambda: self.launch("ms-settings:bluetooth"))
        layout.addWidget(self.bt_btn)

        layout.addWidget(_sep(self))

        # ── Tray Clock (click → Control Center) ──
        self.clock_lbl = QLabel(self)
        self.clock_lbl.setObjectName("TrayClock")
        self.clock_lbl.setFont(QFont("Outfit", 11, QFont.Weight.Bold))
        self.clock_lbl.setStyleSheet("""
            QLabel { color: #E8EEF8; background: transparent;
                     padding: 0 14px; letter-spacing: 0.5px; }
            QLabel:hover { color: #27C8F5; }
        """)
        self.clock_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clock_lbl.mousePressEvent = lambda _: self.clock_clicked.emit()
        layout.addWidget(self.clock_lbl)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_tray)
        self.timer.start(1000)
        self.update_tray()

    # ── Tray update ─────────────────────────
    def update_tray(self):
        import psutil, datetime
        t   = datetime.datetime.now().strftime("%I:%M %p")
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        # Perform network checks asynchronously every 5 ticks (seconds)
        if self._tick_count % 5 == 0:
            import threading
            def bg_network_checks():
                # WiFi Check
                import socket
                try:
                    socket.setdefaulttimeout(1.0)
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(("8.8.8.8", 53))
                    s.close()
                    self._wifi_status = "📶 Connected"
                except Exception:
                    self._wifi_status = "📶 Disconnected"

                # Bluetooth Check
                try:
                    import subprocess
                    # Query bthserv without popping CMD window console
                    out = subprocess.check_output("sc query bthserv", shell=True, creationflags=0x08000000).decode()
                    if "RUNNING" in out:
                        self._bt_status = "ᛒ Active"
                    else:
                        self._bt_status = "ᛒ Off"
                except Exception:
                    self._bt_status = "ᛒ Off"

            threading.Thread(target=bg_network_checks, daemon=True).start()

        self._tick_count += 1
        self.clock_lbl.setText(f"  {t}  ")
        
        # Display icons alongside CPU & RAM metrics
        self.status_lbl.setText(f"CPU {int(cpu)}%  •  RAM {int(ram)}%")
        self.wifi_btn.setText(self._wifi_status)
        self.bt_btn.setText(self._bt_status)

    def launch(self, app, arg=None):
        import os
        try:
            if app == "msedge":
                # Try opening Edge or fallback to default web browser via URL
                try:
                    os.startfile("msedge.exe")
                except Exception:
                    os.startfile("https://www.google.com")
            else:
                os.startfile(app)
        except Exception as e:
            # Fallback to cmd-based 'start' command for protocol matching
            try:
                import subprocess
                subprocess.Popen(f"start {app}", shell=True,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            except Exception as e2:
                print(f"[Taskbar] Launch failed: {e} | Fallback: {e2}")

    def reload_shortcuts(self):
        # Clear existing shortcuts
        while self.shortcuts_layout.count():
            item = self.shortcuts_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Load from config
        import json
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent
        path = base_dir / "config" / "pinned_apps.json"
        
        pinned = []
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    pinned = json.load(f)
            except Exception:
                pass
        
        if not pinned:
            # Default fallback pinned
            pinned = [
                {"name": "Browser", "cmd": "msedge", "icon": "🌐"},
                {"name": "Files", "cmd": "files", "icon": "📁"},
                {"name": "Terminal", "cmd": "wt.exe", "icon": "💻"},
                {"name": "Notes", "cmd": "notepad.exe", "icon": "📝"},
                {"name": "Settings", "cmd": "ms-settings:", "icon": "⚙️"}
            ]

        # Re-create shortcut buttons (icons only!)
        for app in pinned:
            icon_char = app.get("icon", "🚀")
            cmd = app.get("cmd", "")
            name = app.get("name", "")
            
            btn = QPushButton(icon_char, self)
            btn.setObjectName("AppShortcut")
            btn.setToolTip(name)
            btn.setFixedSize(36, 36)
            btn.setFont(QFont("Outfit", 14)) # Large emoji icon
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton#AppShortcut {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 8px;
                    color: #FFFFFF;
                }
                QPushButton#AppShortcut:hover {
                    background: rgba(96, 205, 255, 0.15);
                    border: 1px solid rgba(96, 205, 255, 0.45);
                }
            """)
            
            # Connect execution slot
            if cmd == "files":
                btn.clicked.connect(self.files_clicked.emit)
            else:
                # Capture variables in closure using default args
                btn.clicked.connect(lambda checked=False, c=cmd: self.launch(c))
                
            self.shortcuts_layout.addWidget(btn)

    # ── Custom paint — glassmorphism bar ────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Glass background
        painter.fillRect(self.rect(), QColor(6, 12, 28, 220))
        # Top accent line
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(39, 200, 245, 0))
        grad.setColorAt(0.3, QColor(39, 200, 245, 140))
        grad.setColorAt(0.7, QColor(139, 92, 246, 140))
        grad.setColorAt(1.0, QColor(139, 92, 246, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawRect(0, 0, self.width(), 1)


def _sep(parent):
    f = QFrame(parent)
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet("color: rgba(255,255,255,0.08); max-height: 26px;")
    return f

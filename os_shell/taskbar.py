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
        layout.addWidget(_sep(self))

        # ── Shortcuts ──
        shortcuts = [
            ("🌐 Browser", lambda: self.launch("msedge")),
            ("📁 Files",   self.files_clicked.emit),
            ("⌨️  Terminal", lambda: self.launch("wt.exe")),
            ("📝 Notes",   lambda: self.launch("notepad.exe")),
            ("⚙️  Settings",lambda: self.launch("ms-settings:")),
        ]
        for label, fn in shortcuts:
            btn = QPushButton(label, self)
            btn.setObjectName("AppShortcut")
            btn.setFont(QFont("Outfit", 10))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton#AppShortcut {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.09);
                    border-radius: 7px; color: #D0D8E8;
                    font-size: 11px; padding: 4px 12px;
                }
                QPushButton#AppShortcut:hover {
                    background: rgba(39,200,245,0.12);
                    border: 1px solid rgba(39,200,245,0.35);
                    color: #fff;
                }
            """)
            btn.clicked.connect(fn)
            layout.addWidget(btn)

        layout.addWidget(_sep(self))

        # ── Spacer ──
        layout.addStretch()

        # ── System status ──
        self.status_lbl = QLabel(self)
        self.status_lbl.setObjectName("SysStatusLabel")
        self.status_lbl.setFont(QFont("Outfit", 10))
        self.status_lbl.setStyleSheet("color: rgba(136,153,166,0.9); background: transparent; margin-right: 8px;")
        layout.addWidget(self.status_lbl)

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
        self.clock_lbl.setText(f"  {t}  ")
        self.status_lbl.setText(f"CPU {int(cpu)}%  •  RAM {int(ram)}%")

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

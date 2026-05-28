import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from actions.spotify_helper import spotify_dj_mode, execute_spotify_command

class SpotifyPanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(380, 260)
        self._init_ui()

    def _init_ui(self):
        container = QWidget(self)
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container {
                background: rgba(15, 23, 42, 0.95);
                border: 2px solid rgba(29, 185, 84, 0.4);
                border-radius: 18px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Title block
        title_lay = QHBoxLayout()
        title_lbl = QLabel("SPOTIFY AI CONTROLLER 🎵")
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #1DB954; letter-spacing: 0.5px; background: transparent;")
        
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

        # DJ Mode / Mood Selection Block
        mood_lay = QHBoxLayout()
        mood_lbl = QLabel("Select Mood:")
        mood_lbl.setFont(QFont("Segoe UI", 9))
        mood_lbl.setStyleSheet("color: #E2E8F0; background: transparent;")
        
        self.mood_combo = QComboBox()
        self.mood_combo.addItems(["auto", "focused", "chill", "happy", "sad", "stressed", "excited"])
        self.mood_combo.setStyleSheet("""
            QComboBox {
                background: rgba(5, 5, 10, 0.6);
                border: 1px solid rgba(29, 185, 84, 0.3);
                border-radius: 6px;
                color: #E2E8F0;
                padding: 4px 10px;
                min-width: 100px;
            }
        """)
        
        dj_btn = QPushButton("DJ MODE")
        dj_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        dj_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dj_btn.setStyleSheet("""
            QPushButton {
                background: rgba(29, 185, 84, 0.15);
                color: #1DB954;
                border: 1px solid rgba(29, 185, 84, 0.4);
                border-radius: 8px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: rgba(29, 185, 84, 0.3);
                border: 1px solid #1DB954;
            }
        """)
        dj_btn.clicked.connect(self._run_dj_mode)
        
        mood_lay.addWidget(mood_lbl)
        mood_lay.addWidget(self.mood_combo)
        mood_lay.addWidget(dj_btn)
        layout.addLayout(mood_lay)

        # Media Control Buttons
        ctrl_lay = QHBoxLayout()
        ctrl_lay.setSpacing(10)
        
        actions = [
            ("⏮", "previous"),
            ("⏸", "pause"),
            ("▶", "play"),
            ("⏭", "next")
        ]
        
        for icon, act in actions:
            btn = QPushButton(icon)
            btn.setFixedSize(50, 40)
            btn.setFont(QFont("Segoe UI", 12))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #E2E8F0;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.15);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
            """)
            btn.clicked.connect(lambda checked, a=act: self._media_cmd(a))
            ctrl_lay.addWidget(btn)
            
        layout.addLayout(ctrl_lay)
        
        # Info text
        self.info_lbl = QLabel("Click DJ Mode to play mood-based music.")
        self.info_lbl.setFont(QFont("Segoe UI", 8))
        self.info_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        self.info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_lbl)

        # Full layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def _run_dj_mode(self):
        mood = self.mood_combo.currentText()
        res = spotify_dj_mode(mood=mood)
        self.info_lbl.setText(f"Playing {mood} music on Spotify desktop...")
        parent = self.parent()
        if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
            parent.ip_ray.speak(f"Playing {mood} playlist, bhai! Let's code!")
            parent.write_log(res)

    def _media_cmd(self, cmd):
        execute_spotify_command(cmd)
        self.info_lbl.setText(f"Sent control command: {cmd.upper()}")

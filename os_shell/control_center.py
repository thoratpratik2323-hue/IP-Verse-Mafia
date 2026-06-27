import os
import sys
import subprocess
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QButtonGroup
)
from PyQt6.QtGui import QFont, QColor

from os_shell.theme_engine import OSThemeEngine

# Volume management using pycaw (pre-installed)
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

class ControlCenterWidget(QFrame):
    theme_changed = pyqtSignal(str)
    notifications_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_engine = OSThemeEngine()
        self.dnd_enabled = self.get_dnd_enabled()
        self.current_profile = "balanced"
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("ControlCenter")
        self.update_style()
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        self.setLayout(main_layout)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Control Center", self)
        title.setFont(QFont("Outfit", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #60cdff; background: transparent;")
        header.addWidget(title)
        
        close_btn = QPushButton("✕", self)
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8899A6;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        main_layout.addLayout(header)
        
        # Quick Settings Grid / Toggle Buttons
        toggles_layout = QHBoxLayout()
        toggles_layout.setSpacing(10)
        
        # DND Button
        self.dnd_btn = QPushButton(self)
        self.dnd_btn.setCheckable(True)
        self.dnd_btn.setChecked(self.dnd_enabled)
        self.dnd_btn.setFixedSize(80, 50)
        self.dnd_btn.clicked.connect(self.toggle_dnd)
        toggles_layout.addWidget(self.dnd_btn)
        
        # WiFi Status Indicator Shortcut
        self.wifi_btn = QPushButton("📶 WiFi\nPanel", self)
        self.wifi_btn.setFixedSize(80, 50)
        self.wifi_btn.setFont(QFont("Outfit", 9))
        self.wifi_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background: rgba(96, 205, 255, 0.15);
                border: 1px solid #60cdff;
            }
        """)
        self.wifi_btn.clicked.connect(lambda: os.startfile("ms-availablenetworks:"))
        toggles_layout.addWidget(self.wifi_btn)

        # Bluetooth Status Indicator Shortcut
        self.bt_btn = QPushButton("ᛒ BT\nPanel", self)
        self.bt_btn.setFixedSize(80, 50)
        self.bt_btn.setFont(QFont("Outfit", 9))
        self.bt_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background: rgba(96, 205, 255, 0.15);
                border: 1px solid #60cdff;
            }
        """)
        self.bt_btn.clicked.connect(lambda: os.startfile("ms-settings:bluetooth"))
        toggles_layout.addWidget(self.bt_btn)
        
        main_layout.addLayout(toggles_layout)
        
        # Power / Performance Profiles (Quiet, Balanced, Performance)
        profiles_frame = QFrame(self)
        profiles_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 8px;")
        profiles_lay = QVBoxLayout(profiles_frame)
        profiles_lay.setContentsMargins(8, 8, 8, 8)
        profiles_lay.setSpacing(6)
        
        prof_lbl = QLabel("Performance Profile", self)
        prof_lbl.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        prof_lbl.setStyleSheet("color: #9CA3AF; border: none; background: transparent;")
        profiles_lay.addWidget(prof_lbl)
        
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(6)
        
        self.quiet_btn = QPushButton("🍃 Quiet", self)
        self.bal_btn = QPushButton("⚖️ Balanced", self)
        self.perf_btn = QPushButton("⚡ Performance", self)
        
        for btn in (self.quiet_btn, self.bal_btn, self.perf_btn):
            btn.setCheckable(True)
            btn.setFont(QFont("Outfit", 8))
            btn.setFixedHeight(28)
            btn_lay.addWidget(btn)
            
        self.profile_group = QButtonGroup(self)
        self.profile_group.addButton(self.quiet_btn)
        self.profile_group.addButton(self.bal_btn)
        self.profile_group.addButton(self.perf_btn)
        self.bal_btn.setChecked(True)
        
        self.quiet_btn.clicked.connect(lambda: self.set_profile("quiet"))
        self.bal_btn.clicked.connect(lambda: self.set_profile("balanced"))
        self.perf_btn.clicked.connect(lambda: self.set_profile("performance"))
        
        profiles_lay.addLayout(btn_lay)
        main_layout.addWidget(profiles_frame)
        
        # Volume & Brightness Sliders Block
        sliders_frame = QFrame(self)
        sliders_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 8px;")
        sliders_lay = QVBoxLayout(sliders_frame)
        sliders_lay.setContentsMargins(8, 8, 8, 8)
        sliders_lay.setSpacing(8)
        
        # Volume Slider
        vol_lay = QHBoxLayout()
        self.vol_lbl = QLabel("🔊 Volume: 50%", self)
        self.vol_lbl.setFont(QFont("Outfit", 9))
        self.vol_lbl.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
        vol_lay.addWidget(self.vol_lbl)
        sliders_lay.addLayout(vol_lay)
        
        self.vol_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self.get_system_volume())
        self.vol_slider.valueChanged.connect(self.on_volume_changed)
        self.vol_slider.setStyleSheet(self.get_slider_style())
        self.vol_lbl.setText(f"🔊 Volume: {self.vol_slider.value()}%")
        sliders_lay.addWidget(self.vol_slider)
        
        # Brightness Slider
        br_lay = QHBoxLayout()
        self.br_lbl = QLabel("☀️ Brightness: 75%", self)
        self.br_lbl.setFont(QFont("Outfit", 9))
        self.br_lbl.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
        br_lay.addWidget(self.br_lbl)
        sliders_lay.addLayout(br_lay)
        
        self.br_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.br_slider.setRange(0, 100)
        self.br_slider.setValue(self.get_system_brightness())
        self.br_slider.valueChanged.connect(self.on_brightness_changed)
        self.br_slider.setStyleSheet(self.get_slider_style())
        self.br_lbl.setText(f"☀️ Brightness: {self.br_slider.value()}%")
        sliders_lay.addWidget(self.br_slider)
        
        main_layout.addWidget(sliders_frame)
        
        # Bottom controls: Notifications trigger
        bottom_lay = QHBoxLayout()
        self.notif_btn = QPushButton("🔔 Notifications & Calendar", self)
        self.notif_btn.setFont(QFont("Outfit", 9, QFont.Weight.Medium))
        self.notif_btn.setFixedHeight(30)
        self.notif_btn.setStyleSheet("""
            QPushButton {
                background: rgba(96, 205, 255, 0.1);
                border: 1px solid rgba(96, 205, 255, 0.25);
                border-radius: 8px;
                color: #60cdff;
            }
            QPushButton:hover {
                background: rgba(96, 205, 255, 0.2);
                border: 1px solid #60cdff;
                color: #FFFFFF;
            }
        """)
        self.notif_btn.clicked.connect(self.notifications_requested.emit)
        bottom_lay.addWidget(self.notif_btn)
        main_layout.addLayout(bottom_lay)
        
        self.update_dnd_style()
        self.update_profiles_style()

    def update_style(self):
        t = self.theme_engine.current
        self.setStyleSheet(f"""
            QWidget#ControlCenter {{
                background-color: {t['panel']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
        """)
        
    def get_slider_style(self):
        return """
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #60cdff;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #0078d4;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #60cdff;
                border: 2px solid #FFFFFF;
            }
        """
        
    def toggle_dnd(self):
        self.dnd_enabled = not self.dnd_enabled
        self.set_dnd_enabled(self.dnd_enabled)
        self.update_dnd_style()
        
    def update_dnd_style(self):
        if self.dnd_enabled:
            self.dnd_btn.setText("🌙 DND\nON")
            self.dnd_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(96, 205, 255, 0.2);
                    border: 1px solid #60cdff;
                    border-radius: 8px;
                    color: #60cdff;
                    font-weight: bold;
                }
            """)
        else:
            self.dnd_btn.setText("🌙 DND\nOFF")
            self.dnd_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                }
            """)
            
    def set_profile(self, profile):
        self.current_profile = profile
        self.update_profiles_style()
        
        # 1. Update system process priority
        try:
            import psutil
            p = psutil.Process(os.getpid())
            if profile == "quiet":
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            elif profile == "balanced":
                p.nice(psutil.NORMAL_PRIORITY_CLASS)
            elif profile == "performance":
                p.nice(psutil.HIGH_PRIORITY_CLASS)
        except Exception:
            pass
            
        # 2. Update active powercfg scheme
        guids = {
            "quiet": "a1841308-3541-4fab-bc81-f71556f20b4a",
            "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
            "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        }
        guid = guids.get(profile)
        if guid:
            subprocess.Popen(["powercfg", "/setactive", guid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
    def update_profiles_style(self):
        active_style = """
            QPushButton {
                background: rgba(96, 205, 255, 0.2);
                border: 1px solid #60cdff;
                border-radius: 6px;
                color: #FFFFFF;
                font-weight: bold;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                color: #8899A6;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
            }
        """
        self.quiet_btn.setStyleSheet(active_style if self.current_profile == "quiet" else inactive_style)
        self.bal_btn.setStyleSheet(active_style if self.current_profile == "balanced" else inactive_style)
        self.perf_btn.setStyleSheet(active_style if self.current_profile == "performance" else inactive_style)

    # Volume slider handler
    def on_volume_changed(self, value):
        self.vol_lbl.setText(f"🔊 Volume: {value}%")
        self.set_system_volume(value)
        
    def get_system_volume(self) -> int:
        if HAS_PYCAW:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                return int(volume.GetMasterVolumeLevelScalar() * 100)
            except Exception:
                pass
        return 50
        
    def set_system_volume(self, value):
        if HAS_PYCAW:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(float(value) / 100.0, None)
            except Exception:
                pass

    # Brightness slider handler
    def on_brightness_changed(self, value):
        self.br_lbl.setText(f"☀️ Brightness: {value}%")
        self.set_system_brightness(value)
        
    def get_system_brightness(self) -> int:
        try:
            cmd = "(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightness).CurrentBrightness"
            out = subprocess.check_output(["powershell", "-Command", cmd], text=True, stderr=subprocess.DEVNULL)
            return int(out.strip())
        except Exception:
            return 75
            
    def set_system_brightness(self, value):
        try:
            cmd = f"(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {int(value)})"
            subprocess.Popen(["powershell", "-Command", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # Persistence helpers for DND
    def set_dnd_enabled(self, enabled):
        import json
        config_path = self.theme_engine.CONFIG_DIR / "dnd_enabled.json"
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({"dnd_enabled": enabled}, f)
        except Exception:
            pass

    def get_dnd_enabled(self) -> bool:
        import json
        config_path = self.theme_engine.CONFIG_DIR / "dnd_enabled.json"
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get("dnd_enabled", False)
        except Exception:
            pass
        return False

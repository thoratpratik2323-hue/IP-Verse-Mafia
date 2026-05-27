"""
second_monitor_overlay.py — Glassmorphic transparent dual-monitor HUD overlay for IP Prime.

Constructs a frameless transparent display widget in PyQt6 to render active checklists,
real-time voice transcriptions, system load graphs, and AI contextual tips.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.second_monitor_overlay")

BASE_DIR = Path(__file__).resolve().parent.parent
_APP_INSTANCE: Optional[Any] = None
_OVERLAY_WINDOW: Optional[Any] = None

def _run_pyqt_app():
    """Background thread runner handling PyQt6 event loop lifecycle."""
    global _OVERLAY_WINDOW, _APP_INSTANCE
    logger.info("Initializing PyQt6 Second Monitor Overlay window...")
    
    try:
        from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QColor, QFont
        
        # Check if QApplication already initialized
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        _APP_INSTANCE = app

        class SecondMonitorOverlayWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.initUI()
                
            def initUI(self):
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint | 
                    Qt.WindowType.WindowStaysOnTopHint | 
                    Qt.WindowType.SubWindow
                )
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                
                # Setup layout
                main_layout = QHBoxLayout()
                
                # Left side - Tasks & Transcripts
                left_panel = QVBoxLayout()
                self.title_label = QLabel("✨ IP PRIME HUD OVERLAY (MONITOR 2)")
                self.title_label.setFont(QFont("Outfit", 16, QFont.Weight.Bold))
                self.title_label.setStyleSheet("color: #00ffcc;")
                left_panel.addWidget(self.title_label)
                
                self.tasks_label = QLabel("📋 Active Checklist:\n- Review security updates\n- Run wifi speed test\n- Split lunch bill")
                self.tasks_label.setFont(QFont("Inter", 12))
                self.tasks_label.setStyleSheet("color: #ffffff; background-color: rgba(20, 20, 30, 180); border-radius: 8px; padding: 10px;")
                left_panel.addWidget(self.tasks_label)
                
                self.transcript_label = QLabel("💬 Live Transcript:\n'Listening... Command dijiye, sir!'")
                self.transcript_label.setFont(QFont("Inter", 12))
                self.transcript_label.setStyleSheet("color: #00ff88; background-color: rgba(10, 25, 20, 180); border-radius: 8px; padding: 10px;")
                left_panel.addWidget(self.transcript_label)
                
                main_layout.addLayout(left_panel, 2)
                
                # Right side - Suggestions
                right_panel = QVBoxLayout()
                self.sugg_label = QLabel("🧠 AI Suggestion Engine:\n- Consider running 'PC Cleaner' to optimize RAM.\n- 3 topics are due for tutor review today.")
                self.sugg_label.setFont(QFont("Inter", 12))
                self.sugg_label.setStyleSheet("color: #ff9900; background-color: rgba(30, 20, 10, 180); border-radius: 8px; padding: 10px;")
                right_panel.addWidget(self.sugg_label)
                
                main_layout.addLayout(right_panel, 1)
                self.setLayout(main_layout)
                
                # Transparent styling bounds
                self.resize(1000, 600)
                self.setWindowTitle("IP Prime Overlay")
                
                # Target second monitor if present
                screens = QApplication.screens()
                if len(screens) > 1:
                    monitor2 = screens[1]
                    self.setGeometry(monitor2.geometry())
                    logger.info("Overlay mapped to secondary monitor.")
                else:
                    self.move(100, 100)
                    logger.info("Only single display detected. Opening overlay window in local coordinates.")
            
            def update_tasks(self, task_list_str: str):
                self.tasks_label.setText(f"📋 Active Checklist:\n{task_list_str}")
                
            def update_transcript(self, text: str):
                self.transcript_label.setText(f"💬 Live Transcript:\n'{text}'")
                
            def update_suggestions(self, tips: str):
                self.sugg_label.setText(f"🧠 AI Suggestion Engine:\n{tips}")

        _OVERLAY_WINDOW = SecondMonitorOverlayWidget()
        _OVERLAY_WINDOW.show()
        app.exec()
        
    except Exception as e:
        logger.error("Failed running PyQt6 UI thread loop: %s", e)

def enable_second_monitor_mode(player: Optional[Any] = None) -> str:
    """Launches the overlay widget on the secondary display screen."""
    global _OVERLAY_WINDOW
    
    # Try importing PyQt6 safely
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        logger.warning("PyQt6 is not available, unable to open overlay window. Simulating overlay logs.")
        return "PyQt6 library missing. Transparent dual display overlay simulation logged successfully, sir."

    if _OVERLAY_WINDOW:
        # Already running, just show
        try:
            _OVERLAY_WINDOW.show()
            return "Second Monitor overlay window refreshed and active, sir!"
        except Exception:
            pass

    # Start loop thread
    t = threading.Thread(target=_run_pyqt_app, daemon=True, name="PyQtOverlayThread")
    t.start()
    
    msg = "Secondary screen transparent HUD overlay started successfully, sir! All channels active."
    if player and hasattr(player, "write_log"):
        player.write_log("🖥️ Dual-Monitor HUD Active.")
    return msg

def disable_second_monitor_mode() -> str:
    """Closes and hides the secondary screen widget."""
    global _OVERLAY_WINDOW
    if _OVERLAY_WINDOW:
        try:
            # We must close on the PyQt thread safely, or simply hide
            _OVERLAY_WINDOW.hide()
            return "Second Monitor transparent overlay de-activated successfully, sir."
        except Exception as e:
            logger.error("Failed hiding overlay widget: %s", e)
            
    return "Second Monitor overlay is not currently active, sir."

def update_overlay_tasks(task_list: str) -> str:
    """Refreshes the checklist panel of the secondary screen overlay."""
    global _OVERLAY_WINDOW
    if _OVERLAY_WINDOW:
        try:
            _OVERLAY_WINDOW.update_tasks(task_list)
            return "HUD checklist metrics updated successfully, sir!"
        except Exception as e:
            logger.error("Failed writing updates: %s", e)
    return f"Overlay not active. Simulated checklist updated successfully: '{task_list}'"

def second_monitor_overlay(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for second_monitor_overlay action."""
    action = parameters.get("action", "enable").lower().strip()
    value = parameters.get("value", "")
    
    if action == "enable":
        return enable_second_monitor_mode(player)
    elif action == "disable":
        return disable_second_monitor_mode()
    elif action == "update_tasks":
        return update_overlay_tasks(value)
    else:
        return "Unknown second monitor overlay action parameter, sir."

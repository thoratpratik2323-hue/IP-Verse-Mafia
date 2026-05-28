"""
actions/git_gui.py — Custom interactive PyQt6 widget for the Git Autopilot Commit Synthesizer.

This is a premium action module for the IP Prime personal assistant suite.
"""

import time
import threading
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QScrollArea
)
from PyQt6.QtGui import QFont
from actions.git_autopilot import GitAutopilot

PANEL_DARK = "rgba(4, 7, 14, 0.95)"
BORDER_COLOR = "rgba(0, 240, 255, 0.45)"  # Cyber cyan border for git
TEXT_MED = "#E2E8F0"

class GitAutopilotPanel(QFrame):
    """Floating glassmorphic Git Autopilot panel."""
    
    diff_analyzed = pyqtSignal(str) # commit message
    commit_completed = pyqtSignal(bool) # success state
    clean_detected = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(540, 420)
        self.setStyleSheet(
            f"background: {PANEL_DARK};"
            f"border: 2px solid {BORDER_COLOR};"
            f"border-radius: 16px;"
        )
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        
        self.autopilot = GitAutopilot()
        
        # Connect signals for threading
        self.diff_analyzed.connect(self.on_diff_analyzed)
        self.commit_completed.connect(self.on_commit_completed)
        self.clean_detected.connect(self.on_clean)
        
        # Setup Layout
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 16, 16, 16)
        self.lay.setSpacing(12)
        
        # Title bar
        title_lay = QHBoxLayout()
        self.title_lbl = QLabel("🐙 GIT AUTOPILOT CO-PILOT")
        self.title_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #00f0ff; background: transparent; border: none;")
        title_lay.addWidget(self.title_lbl)
        title_lay.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet(
            "background: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid #EF4444; border-radius: 12px;"
        )
        self.close_btn.clicked.connect(self.hide)
        title_lay.addWidget(self.close_btn)
        self.lay.addLayout(title_lay)
        
        # Description
        desc = QLabel(
            "Autonomously scan unstaged workspace files, generate compliant Conventional Commit messages using Gemini, and commit code with a click or voice command."
        )
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        desc.setWordWrap(True)
        self.lay.addWidget(desc)
        
        # Diff summary display
        self.status_lbl = QLabel("Porcelain changes detected:")
        self.status_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
        self.lay.addWidget(self.status_lbl)
        
        self.diff_scroll = QScrollArea()
        self.diff_scroll.setWidgetResizable(True)
        self.diff_scroll.setFixedHeight(110)
        self.diff_scroll.setStyleSheet("QScrollArea { border: 1px solid rgba(0, 240, 255, 0.15); border-radius: 8px; background: transparent; }")
        
        self.diff_summary_lbl = QLabel("No changes scanned yet. Click 'Scan Diff' to begin.")
        self.diff_summary_lbl.setFont(QFont("Consolas", 8))
        self.diff_summary_lbl.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
        self.diff_summary_lbl.setWordWrap(True)
        self.diff_scroll.setWidget(self.diff_summary_lbl)
        self.lay.addWidget(self.diff_scroll)
        
        # Commit message entry
        commit_lbl = QLabel("Synthesized Commit Message:")
        commit_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        commit_lbl.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
        self.lay.addWidget(commit_lbl)
        
        self.commit_msg_edit = QTextEdit()
        self.commit_msg_edit.setFixedHeight(48)
        self.commit_msg_edit.setPlaceholderText("Commit message will be synthesized here...")
        self.commit_msg_edit.setStyleSheet(
            "QTextEdit { background: rgba(15, 23, 42, 0.6); color: #00f0ff; border: 1px solid rgba(0, 240, 255, 0.2); "
            "border-radius: 8px; padding: 6px; font-family: 'Consolas'; font-size: 11px; }"
        )
        self.lay.addWidget(self.commit_msg_edit)
        
        # Actions
        btns_lay = QHBoxLayout()
        self.scan_btn = QPushButton("🔍 Scan & Synthesize")
        self.scan_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.scan_btn.setStyleSheet(
            "background: rgba(0, 240, 255, 0.15); color: #00f0ff; border: 1px solid #00f0ff; "
            "border-radius: 6px; padding: 8px;"
        )
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self.scan_and_synthesize)
        btns_lay.addWidget(self.scan_btn)
        
        self.commit_btn = QPushButton("🚀 Stage & Commit")
        self.commit_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.commit_btn.setStyleSheet(
            "background: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid #10B981; "
            "border-radius: 6px; padding: 8px;"
        )
        self.commit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.commit_btn.clicked.connect(self.stage_and_commit)
        self.commit_btn.setEnabled(False)
        btns_lay.addWidget(self.commit_btn)
        
        self.lay.addLayout(btns_lay)
        
        # Status footer
        self.log_lbl = QLabel("Autopilot system online.")
        self.log_lbl.setFont(QFont("Segoe UI", 8))
        self.log_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        self.lay.addWidget(self.log_lbl)
        
    def scan_and_synthesize(self):
        self.scan_btn.setEnabled(False)
        self.log_lbl.setText("Scanning repository for unstaged changes...")
        self.diff_summary_lbl.setText("Querying repository status...")
        
        def run_thread():
            summary = self.autopilot.get_status_summary()
            diff = self.autopilot.get_git_diff()
            
            if not summary:
                # Safely update GUI
                def gui_idle():
                    self.diff_summary_lbl.setText("No unstaged modifications detected in active workspace!")
                    self.commit_msg_edit.setPlainText("chore: no changes to commit")
                    self.scan_btn.setEnabled(True)
                    self.commit_btn.setEnabled(False)
                    self.log_lbl.setText("Workspace clean.")
                self.clean_detected.emit()
                return
                
            # Synthesize commit message using Gemini
            msg = self.autopilot.generate_commit_message(diff)
            
            # Vocalize message synthesis
            parent = self.parent()
            if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
                parent.ip_ray.speak(f"Synthesized conventional commit: {msg}")
                
            self.diff_analyzed.emit(msg)
            
        threading.Thread(target=run_thread, daemon=True).start()

    # Qt slot mappings
    def on_diff_analyzed(self, msg: str):
        self.commit_msg_edit.setPlainText(msg)
        summary = self.autopilot.get_status_summary()
        self.diff_summary_lbl.setText(summary)
        self.scan_btn.setEnabled(True)
        self.commit_btn.setEnabled(True)
        self.log_lbl.setText("Gemini synthesis complete. Review and commit.")
        
    def on_clean(self):
        self.diff_summary_lbl.setText("No unstaged modifications detected in active workspace!")
        self.commit_msg_edit.setPlainText("chore: no changes to commit")
        self.scan_btn.setEnabled(True)
        self.commit_btn.setEnabled(False)
        self.log_lbl.setText("Workspace clean.")

    def stage_and_commit(self):
        msg = self.commit_msg_edit.toPlainText().strip()
        if not msg:
            self.log_lbl.setText("Error: Commit message cannot be empty!")
            return
            
        self.commit_btn.setEnabled(False)
        self.log_lbl.setText("Running git add and commit...")
        
        def run_thread():
            success = self.autopilot.stage_and_commit(msg)
            
            # Vocalize commit success
            parent = self.parent()
            if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
                if success:
                    parent.ip_ray.speak("Changes staged and committed successfully to main branch!")
                else:
                    parent.ip_ray.speak("Git commit operation failed, sir. Please check local logs.")
                    
            self.commit_completed.emit(success)
            
        threading.Thread(target=run_thread, daemon=True).start()
        
    def on_commit_completed(self, success: bool):
        if success:
            self.log_lbl.setText("Changes staged and committed successfully!")
            self.diff_summary_lbl.setText("Working tree clean.")
            self.commit_msg_edit.clear()
            self.commit_btn.setEnabled(False)
        else:
            self.log_lbl.setText("Git commit failed. Review stderr logs.")
            self.commit_btn.setEnabled(True)

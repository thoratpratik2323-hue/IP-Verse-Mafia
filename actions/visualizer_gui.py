"""
actions/visualizer_gui.py — Custom interactive PyQt6 widget for the Code Visualizer Sandbox.

This is a premium action module for the IP Prime personal assistant suite.
"""

import time
import random
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from actions.code_visualizer import CodeVisualizer

# Theme constants mapping matching ui_core C class
CYAN = "#0369A1"
TEXT_MED = "#E2E8F0"
PANEL_DARK = "rgba(4, 7, 14, 0.95)"
BORDER_COLOR = "rgba(3, 105, 161, 0.45)"

class ArrayCanvas(QWidget):
    """Custom canvas that draws the animated sorting/searching bars."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.array = [20, 50, 15, 80, 45, 90, 30, 75, 60, 40]
        self.compare_indices = []
        self.swap_occurred = False
        self.sorted_indices = []
        self.low_pointer = -1
        self.high_pointer = -1
        self.mid_pointer = -1
        
    def set_frame(self, frame: dict, is_search: bool = False):
        """Updates the canvas data representation and schedules a repaint."""
        self.array = frame.get("array", self.array)
        if not is_search:
            self.compare_indices = frame.get("compare", [])
            self.swap_occurred = frame.get("swap", False)
            self.sorted_indices = frame.get("sorted_indices", [])
            self.low_pointer = -1
            self.high_pointer = -1
            self.mid_pointer = -1
        else:
            self.compare_indices = []
            self.swap_occurred = False
            self.sorted_indices = []
            self.low_pointer = frame.get("low", -1)
            self.high_pointer = frame.get("high", -1)
            self.mid_pointer = frame.get("mid", -1)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        n = len(self.array)
        
        # Calculate bar geometry
        spacing = 6
        bar_w = int((w - (spacing * (n + 1))) / n)
        max_val = max(self.array) if self.array else 100
        
        for i, val in enumerate(self.array):
            bar_h = int((val / max_val) * (h - 60))
            x = spacing + i * (bar_w + spacing)
            y = h - bar_h - 30
            
            # Default bar color (electric cyan gradient feel)
            color = QColor("#0284C7")  # Cyber sky blue
            
            # Color overrides based on algorithm execution state
            if i in self.compare_indices:
                if self.swap_occurred:
                    color = QColor("#EF4444")  # Swap active (Red alert)
                else:
                    color = QColor("#F59E0B")  # Comparing (Amber yellow)
            elif i in self.sorted_indices:
                color = QColor("#10B981")  # Fully sorted (Emerald green)
                
            # Search pointer overrides
            if i == self.mid_pointer:
                color = QColor("#8B5CF6")  # Mid pointer (Indigo purple)
            elif i == self.low_pointer or i == self.high_pointer:
                color = QColor("#EC4899")  # Low/High bounds (Pink)
                
            # Draw glowing bar
            painter.setPen(QPen(QColor(BORDER_COLOR), 1))
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(x, y, bar_w, bar_h, 4, 4)
            
            # Draw numerical value label under each bar
            painter.setPen(QPen(QColor(TEXT_MED)))
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.drawText(x, h - 10, f"{val}")
            
        painter.end()


class SandboxPanel(QFrame):
    """Floating glassmorphic algorithm visualizer panel."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(540, 360)
        self.setStyleSheet(
            f"background: {PANEL_DARK};"
            f"border: 2px solid {BORDER_COLOR};"
            f"border-radius: 16px;"
        )
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        
        # Algorithmic states
        self.frames = []
        self.current_frame_idx = 0
        self.is_playing = False
        self.is_search_mode = False
        
        # Setup UI layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        
        # Title bar
        title_lay = QHBoxLayout()
        self.title_lbl = QLabel("◈ ALGORITHM SANDBOX")
        self.title_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet(f"color: #27C8F5; background: transparent; border: none;")
        title_lay.addWidget(self.title_lbl)
        title_lay.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet(
            "background: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid #EF4444; border-radius: 12px;"
        )
        self.close_btn.clicked.connect(self.hide)
        title_lay.addWidget(self.close_btn)
        lay.addLayout(title_lay)
        
        # Code Canvas
        self.canvas = ArrayCanvas(self)
        self.canvas.setStyleSheet("background: rgba(2, 4, 8, 0.45); border: 1px solid rgba(3, 105, 161, 0.18); border-radius: 8px;")
        lay.addWidget(self.canvas)
        
        # Explanatory text banner
        self.info_banner = QLabel("Select an algorithm to begin visual learning.")
        self.info_banner.setFont(QFont("Consolas", 8))
        self.info_banner.setStyleSheet(f"color: {TEXT_MED}; background: transparent; border: none;")
        self.info_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.info_banner)
        
        # Controls Row 1: Algorithmic triggers
        algo_lay = QHBoxLayout()
        self.bubble_btn = QPushButton("Bubble Sort")
        self.select_btn = QPushButton("Selection Sort")
        self.search_btn = QPushButton("Binary Search")
        
        for btn in (self.bubble_btn, self.select_btn, self.search_btn):
            btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            btn.setStyleSheet(
                "background: rgba(30, 41, 59, 0.35); color: #27C8F5; "
                "border: 1px solid rgba(3, 105, 161, 0.35); border-radius: 6px; padding: 4px 8px;"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            algo_lay.addWidget(btn)
            
        self.bubble_btn.clicked.connect(lambda: self.load_algorithm("bubble"))
        self.select_btn.clicked.connect(lambda: self.load_algorithm("selection"))
        self.search_btn.clicked.connect(lambda: self.load_algorithm("search"))
        lay.addLayout(algo_lay)
        
        # Controls Row 2: Playback actions
        play_lay = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.step_btn = QPushButton("↳ Step")
        self.reset_btn = QPushButton("↺ Reset")
        
        for btn in (self.play_btn, self.step_btn, self.reset_btn):
            btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            btn.setStyleSheet(
                "background: rgba(3, 105, 161, 0.15); color: #E2E8F0; "
                "border: 1px solid rgba(3, 105, 161, 0.25); border-radius: 6px; padding: 4px 10px;"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            play_lay.addWidget(btn)
            
        self.play_btn.clicked.connect(self.toggle_play)
        self.step_btn.clicked.connect(self.step_frame)
        self.reset_btn.clicked.connect(self.reset_algorithm)
        lay.addLayout(play_lay)
        
        # Timer for play loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.play_step)
        
    def load_algorithm(self, name: str):
        """Generates frame list and triggers visualizer loading state."""
        self.timer.stop()
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        
        arr = [random.randint(15, 95) for _ in range(10)]
        self.is_search_mode = False
        
        if name == "bubble":
            self.frames = CodeVisualizer.bubble_sort(arr)
            self.title_lbl.setText("◈ SANDBOX: BUBBLE SORT")
            self.info_banner.setText("Bubble Sort: Comparing adjacent items and swapping.")
        elif name == "selection":
            self.frames = CodeVisualizer.selection_sort(arr)
            self.title_lbl.setText("◈ SANDBOX: SELECTION SORT")
            self.info_banner.setText("Selection Sort: Scanning for the absolute minimum and swapping.")
        elif name == "search":
            self.is_search_mode = True
            sorted_arr = sorted(arr)
            target = sorted_arr[random.randint(2, 7)]
            self.frames = CodeVisualizer.binary_search(sorted_arr, target)
            self.title_lbl.setText(f"◈ SANDBOX: BINARY SEARCH (Target: {target})")
            self.info_banner.setText(f"Binary Search: Halving the search range to locate target {target}.")
            
        self.current_frame_idx = 0
        if self.frames:
            self.canvas.set_frame(self.frames[0], is_search=self.is_search_mode)
            
    def step_frame(self):
        """Steps forward a single frame manually."""
        if not self.frames:
            return
            
        if self.current_frame_idx < len(self.frames) - 1:
            self.current_frame_idx += 1
            frame = self.frames[self.current_frame_idx]
            self.canvas.set_frame(frame, is_search=self.is_search_mode)
            
            # Dynamic updates to info banner
            if not self.is_search_mode:
                comp = frame.get("compare", [])
                sw = frame.get("swap", False)
                if comp:
                    action = "Swapping" if sw else "Comparing"
                    self.info_banner.setText(f"Step {self.current_frame_idx}: {action} index {comp[0]} and {comp[1]}.")
            else:
                self.info_banner.setText(
                    f"Step {self.current_frame_idx}: Low={frame['low']}, High={frame['high']}, Mid={frame['mid']}. "
                    f"Found={frame['found']}"
                )
        else:
            self.timer.stop()
            self.is_playing = False
            self.play_btn.setText("▶ Play")
            self.info_banner.setText("Algorithm execution complete! Click Reset to restart.")
            
            # Auto-trigger coding habit on algorithm completion
            try:
                from actions.habits_engine import check_coding_habit
                check_coding_habit()
            except Exception:
                pass
            
    def toggle_play(self):
        """Starts or pauses the animation timer loop."""
        if not self.frames:
            return
            
        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            self.play_btn.setText("▶ Play")
        else:
            self.timer.start(400)  # Smooth 400ms tick interval
            self.is_playing = True
            self.play_btn.setText("⏸ Pause")
            
    def play_step(self):
        self.step_frame()
        
    def reset_algorithm(self):
        """Resets the loaded algorithm back to the initial state."""
        self.timer.stop()
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.current_frame_idx = 0
        if self.frames:
            self.canvas.set_frame(self.frames[0], is_search=self.is_search_mode)
            self.info_banner.setText("Visualizer reset. Click Play or Step to walk through.")

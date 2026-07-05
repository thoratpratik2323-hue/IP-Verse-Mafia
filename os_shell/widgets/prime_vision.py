import os
import json
import threading
import time
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtGui import QFont, QImage, QPixmap

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

from google import genai
from google.genai import types
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"
TEMP_DIR = BASE_DIR / "memory"

class PrimeVisionWidget(QWidget):
    """
    👁️ Prime Vision Web Camera interface.
    Streams local webcam frames in real-time and integrates with Gemini Vision
    to analyze objects, read text, or recognize the user.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.desktop = parent
        self.setStyleSheet("background: transparent; border: none;")
        
        self.cap = None
        self.is_running = False
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Live camera display label
        self.feed_lbl = QLabel(self)
        self.feed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_lbl.setFixedSize(400, 260)
        self.feed_lbl.setStyleSheet("""
            QLabel {
                background-color: rgba(5, 12, 14, 0.85);
                border: 1px solid rgba(0, 200, 255, 0.15);
                border-radius: 8px;
                color: #B4CDD4;
            }
        """)
        self.feed_lbl.setText("👁️ Prime Camera Feed Offline")
        layout.addWidget(self.feed_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.snap_btn = QPushButton("📸 Take Snapshot", self)
        self.snap_btn.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        self.snap_btn.setStyleSheet(self._btn_style("#00f5ff", "#008b99"))
        self.snap_btn.clicked.connect(self._take_snapshot)
        btn_layout.addWidget(self.snap_btn)
        
        self.ocr_btn = QPushButton("🔍 Scan Text (OCR)", self)
        self.ocr_btn.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        self.ocr_btn.setStyleSheet(self._btn_style("#10b981", "#059669"))
        self.ocr_btn.clicked.connect(self._run_ocr)
        btn_layout.addWidget(self.ocr_btn)
        
        layout.addLayout(btn_layout)
        
        # Description text editor output
        self.output_box = QTextEdit(self)
        self.output_box.setReadOnly(True)
        self.output_box.setFont(QFont("JetBrains Mono", 9))
        self.output_box.setPlaceholderText("Analysis outputs will display here, Sir...")
        self.output_box.setStyleSheet("""
            QTextEdit {
                background-color: rgba(5, 12, 14, 0.75);
                border: 1px solid rgba(0, 200, 255, 0.12);
                border-radius: 8px;
                color: #e1f0f5;
            }
        """)
        layout.addWidget(self.output_box, 1)
        
        # Timer for frame updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        
    def _btn_style(self, start_color, end_color):
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {start_color}, stop:1 {end_color});
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: white;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
            QPushButton:pressed {{
                opacity: 0.7;
            }}
        """
        
    def start_camera(self):
        if not _CV2_AVAILABLE:
            self.feed_lbl.setText("Error: OpenCV (cv2) is not installed.")
            return
            
        if self.is_running:
            return
            
        # Initialize camera in a background thread to prevent GUI lockup
        def init():
            try:
                # Try camera index 0 with DSHOW backend on Windows
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    # Fallback to default backend
                    self.cap = cv2.VideoCapture(0)
                
                if self.cap.isOpened():
                    self.is_running = True
                    self.timer.start(33) # ~30 FPS
                else:
                    self.feed_lbl.setText("No web camera detected.")
            except Exception as e:
                self.feed_lbl.setText(f"Camera error: {e}")
                
        threading.Thread(target=init, daemon=True).start()
        
    def stop_camera(self):
        self.timer.stop()
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.feed_lbl.setText("👁️ Prime Camera Feed Offline")
        
    def _update_frame(self):
        if not self.is_running or not self.cap:
            return
            
        ret, frame = self.cap.read()
        if ret:
            # Resize frame to fit label aspect ratio
            frame = cv2.resize(frame, (400, 260))
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Create QImage and QPixmap
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.feed_lbl.setPixmap(QPixmap.fromImage(q_img))
            
    def _take_snapshot(self):
        self._analyze_camera("Describe what you see in this camera frame. Be brief and direct.")
        
    def _run_ocr(self):
        self._analyze_camera("Read and extract all visible text from this frame. Output only the transcribed text.")
        
    def _analyze_camera(self, prompt):
        if not self.is_running or not self.cap:
            self.output_box.setPlainText("Please start the camera feed first, Sir.")
            return
            
        ret, frame = self.cap.read()
        if not ret:
            self.output_box.setPlainText("Failed to capture frame from camera stream.")
            return
            
        self.output_box.setPlainText("Capturing snapshot... Analyzing with Gemini Vision...")
        
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        temp_path = TEMP_DIR / "temp_camera.jpg"
        
        # Save snapshot
        cv2.imwrite(str(temp_path), frame)
        
        def worker():
            try:
                # Load API key
                with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                    api_key = json.load(f)["gemini_api_key"]
                
                client = genai.Client(api_key=api_key)
                image = Image.open(temp_path)
                
                system_instruction = """You are IP PRIME's Multimodal Camera Assistant. 
You will be provided with a web camera snapshot and a query.
Analyze the image with absolute precision. Answer the query clearly and concisely."""
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[image, prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2
                    )
                )
                
                analysis_text = response.text.strip()
                self.output_box.setPlainText(analysis_text)
                
                # Cleanup temp file
                image.close()
                if temp_path.exists():
                    os.remove(temp_path)
                    
                # Speak response out loud!
                if hasattr(self.desktop, "ui_facade") and self.desktop.ui_facade:
                    # Look up prime instance to speak
                    from PyQt6.QtWidgets import QApplication
                    for widget in QApplication.topLevelWidgets():
                        if hasattr(widget, "agent") and widget.agent:
                            widget.agent.speak(analysis_text)
                            break
            except Exception as e:
                self.output_box.setPlainText(f"Error during vision analysis: {e}")
                if temp_path.exists():
                    try: os.remove(temp_path)
                    except Exception: pass
                    
        threading.Thread(target=worker, daemon=True).start()

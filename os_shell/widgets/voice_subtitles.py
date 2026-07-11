"""
os_shell/widgets/voice_subtitles.py — Active Speech Subtitles Panel.
Sequentially highlights spoken words in cyan, keeping user in sync with voice output.
"""
from __future__ import annotations
import re
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont, QPainter


class VoiceSubtitlesWidget(QWidget):
    """
    Glassmorphic subtitle overlay anchored above the bottom center of the screen.
    Flashes word-by-word highlights when the system talks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        self.words: list[str] = []
        self.word_idx = 0
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_word)
        
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        
        # Container styling
        self.setStyleSheet("""
            QWidget {
                background: rgba(8, 14, 30, 0.93);
                border: 1px solid rgba(6, 182, 212, 0.40);
                border-radius: 12px;
            }
        """)
        
        # Cyan neon drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(6, 182, 212, 70))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

        self.label = QLabel(self)
        self.label.setFont(QFont("Outfit", 12))
        self.label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

    def show_speech(self, text: str):
        """Prepares and starts word-by-word subtitle highlighting."""
        # Clean text
        clean = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        clean = re.sub(r'\[.*?\]', '', clean)
        clean = re.sub(r'[*#_\-`]', '', clean)
        
        self.words = [w for w in clean.split() if w.strip()]
        if not self.words:
            self.hide()
            return
            
        self.word_idx = 0
        self.show()
        self.raise_()
        
        # Calculate interval dynamically based on word length (average 260ms per word)
        self._update_text()
        self._start_word_timer()

    def _start_word_timer(self):
        if self.word_idx < len(self.words):
            word = self.words[self.word_idx]
            # Give longer words slightly more time
            duration = max(180, min(500, len(word) * 45))
            self._timer.start(duration)
        else:
            # Done speaking, hide subtitles after a brief pause
            QTimer.singleShot(1000, self.hide)

    def _advance_word(self):
        self._timer.stop()
        self.word_idx += 1
        if self.word_idx < len(self.words):
            self._update_text()
            self._start_word_timer()
        else:
            self._update_text()
            QTimer.singleShot(1200, self.hide)

    def _update_text(self):
        formatted = []
        # Display window of 8 words around current word for readability
        start = max(0, self.word_idx - 4)
        end = min(len(self.words), self.word_idx + 5)
        
        for i in range(start, end):
            word = self.words[i]
            if i == self.word_idx:
                formatted.append(f"<font color='#00f0ff'><b>{word}</b></font>")
            else:
                formatted.append(f"<font color='#8899a6'>{word}</font>")
                
        prefix = "... " if start > 0 else ""
        suffix = " ..." if end < len(self.words) else ""
        self.label.setText(prefix + " ".join(formatted) + suffix)
        
        # Reposition and resize to text bounding size
        self.adjustSize()
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            # Center horizontally, place slightly above bottom stats panel (h - 130)
            self.setGeometry((pw - self.width()) // 2, ph - 140, self.width(), self.height())

"""
os_shell/widgets/media_hud.py — Glassmorphic Universal Media Control HUD.
Universal media key controls with clean aesthetic visuals.
"""
from __future__ import annotations
import sys
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

class MediaControlHUD(QWidget):
    """
    Yosemite glassmorphic overlay widget that displays current track details,
    a pulsing progress bar, spinning vinyl animation, and controls system media.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 100)
        
        self.track_title = "No Track Playing"
        self.track_artist = "Standing By"
        self.is_playing = False
        self.progress = 0.0 # 0.0 to 100.0
        self.disc_rotation = 0.0
        
        # UI Labels
        self.title_lbl = QLabel(self.track_title, self)
        self.title_lbl.setFont(QFont("Outfit", 11, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #ffffff; background: transparent;")
        self.title_lbl.setFixedWidth(170)
        self.title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.artist_lbl = QLabel(self.track_artist, self)
        self.artist_lbl.setFont(QFont("Outfit", 9))
        self.artist_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        self.artist_lbl.setFixedWidth(170)
        self.artist_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Position labels
        self.title_lbl.move(95, 18)
        self.artist_lbl.move(95, 38)
        
        # Control Buttons Rectangles (for custom click handling)
        self.prev_btn_rect = QRectF(95, 62, 22, 22)
        self.play_btn_rect = QRectF(130, 60, 26, 26)
        self.next_btn_rect = QRectF(170, 62, 22, 22)
        
        # Animation & Progress Timer (60 fps for smooth disc rotation and progress)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def set_track_info(self, title: str, artist: str):
        """Update track information and start animations."""
        self.track_title = title[:24] + "..." if len(title) > 24 else title
        self.track_artist = artist[:24] + "..." if len(artist) > 24 else artist
        self.title_lbl.setText(self.track_title)
        self.artist_lbl.setText(self.track_artist)
        self.is_playing = True
        self.progress = 0.0
        self.update()

    def _tick(self):
        if self.is_playing:
            # Advance rotation
            self.disc_rotation += 2.0
            if self.disc_rotation >= 360.0:
                self.disc_rotation -= 360.0
            
            # Advance track progress bar
            self.progress += 0.05
            if self.progress >= 100.0:
                self.progress = 0.0
            
            self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            if self.prev_btn_rect.contains(pos):
                self._trigger_media_key("prevtrack")
            elif self.play_btn_rect.contains(pos):
                self.is_playing = not self.is_playing
                self._trigger_media_key("playpause")
            elif self.next_btn_rect.contains(pos):
                self._trigger_media_key("nexttrack")

    def _trigger_media_key(self, key: str):
        if _PYAUTOGUI:
            try:
                pyautogui.press(key)
            except Exception as e:
                print(f"[Media HUD] Failed to press media key '{key}': {e}")
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Glassmorphic Background Card
        p.setPen(QPen(QColor(255, 255, 255, 20), 1.2))
        p.setBrush(QBrush(QColor(15, 23, 42, 170))) # Yosemite dark slate glass
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 12.0, 12.0)
        
        # 2. Draw Vinyl Spinning Record
        p.save()
        # Translate to vinyl center
        p.translate(45, 50)
        p.rotate(self.disc_rotation)
        
        # Outer Vinyl Edge
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.setBrush(QBrush(QColor(30, 30, 30)))
        p.drawEllipse(QRectF(-32, -32, 64, 64))
        
        # Grooves
        p.setPen(QPen(QColor(255, 255, 255, 15), 1))
        p.drawEllipse(QRectF(-24, -24, 48, 48))
        p.drawEllipse(QRectF(-16, -16, 32, 32))
        
        # Center Label (glowing cyan / purple gradient)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(6, 182, 212))) # Cyan label center
        p.drawEllipse(QRectF(-8, -8, 16, 16))
        
        # Center Spindle Hole
        p.setBrush(QBrush(QColor(15, 23, 42)))
        p.drawEllipse(QRectF(-2, -2, 4, 4))
        
        p.restore()
        
        # 3. Draw Track Progress Bar
        bar_y = 90
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 15))) # Background channel
        p.drawRoundedRect(QRectF(15, bar_y, 270, 3), 1.5, 1.5)
        
        if self.is_playing:
            # Active glowing cyan progress line
            p.setBrush(QBrush(QColor(6, 182, 212)))
            fill_w = int(270 * (self.progress / 100.0))
            p.drawRoundedRect(QRectF(15, bar_y, fill_w, 3), 1.5, 1.5)
            
        # 4. Draw Media Controls (Prev, Play, Next icons)
        # Prev Button
        p.setPen(QPen(QColor(255, 255, 255, 220), 2))
        p.setBrush(QBrush(QColor(255, 255, 255, 220)))
        px, py = self.prev_btn_rect.x(), self.prev_btn_rect.y()
        p.drawPolygon(
            [QPointF(px + 10, py + 5), QPointF(px + 2, py + 11), QPointF(px + 10, py + 17)]
        )
        p.drawPolygon(
            [QPointF(px + 18, py + 5), QPointF(px + 10, py + 11), QPointF(px + 18, py + 17)]
        )
        p.drawLine(QPointF(px + 2, py + 5), QPointF(px + 2, py + 17))
        
        # Play / Pause Button
        px, py = self.play_btn_rect.x(), self.play_btn_rect.y()
        if self.is_playing:
            # Draw Pause symbol (two bars)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(6, 182, 212))) # Glowing cyan pause bars
            p.drawRect(QRectF(px + 7, py + 5, 4, 16))
            p.drawRect(QRectF(px + 15, py + 5, 4, 16))
        else:
            # Draw Play triangle
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 220)))
            p.drawPolygon(
                [QPointF(px + 7, py + 4), QPointF(px + 21, py + 13), QPointF(px + 7, py + 22)]
            )
            
        # Next Button
        px, py = self.next_btn_rect.x(), self.next_btn_rect.y()
        p.setPen(QPen(QColor(255, 255, 255, 220), 2))
        p.setBrush(QBrush(QColor(255, 255, 255, 220)))
        p.drawPolygon(
            [QPointF(px + 12, py + 5), QPointF(px + 20, py + 11), QPointF(px + 12, py + 17)]
        )
        p.drawPolygon(
            [QPointF(px + 4, py + 5), QPointF(px + 12, py + 11), QPointF(px + 4, py + 17)]
        )
        p.drawLine(QPointF(px + 20, py + 5), QPointF(px + 20, py + 17))

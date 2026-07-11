"""
os_shell/widgets/screen_crop.py — Multimodal Eyes crop overlay.
Captures screen regions and forwards them to AI vision analysis.
"""
from __future__ import annotations
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QCursor

class ScreenCropOverlay(QWidget):
    """
    Transparent full-screen overlay for drag-and-drop screen crop.
    Draws a dim mask and highlights the selection box with pulsing neon borders.
    """
    def __init__(self, screen_pixmap: QPixmap, parent_desktop):
        super().__init__()
        self.pixmap = screen_pixmap
        self.parent_desktop = parent_desktop
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Set full screen dimensions
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.is_dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.position().toPoint()
            self.end_pos = self.start_pos
            self.is_dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.end_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.end_pos = event.position().toPoint()
            self.update()
            
            # Calculate final rect
            rect = QRect(self.start_pos, self.end_pos).normalized()
            self.close()
            
            if rect.width() > 10 and rect.height() > 10:
                self.crop_and_submit(rect)
            else:
                self.parent_desktop.notif_center.add_notification(
                    "👁️", "Crop Cancelled", "Selection area too small.", color="#ef4444"
                )

    def crop_and_submit(self, rect: QRect):
        try:
            cropped = self.pixmap.copy(rect)
            
            save_dir = Path("data")
            save_dir.mkdir(exist_ok=True)
            crop_path = save_dir / "crop_snap.png"
            
            # Remove existing snapshot if present
            if crop_path.exists():
                try: os.remove(str(crop_path))
                except: pass
                
            cropped.save(str(crop_path), "PNG")
            
            # Notify user
            self.parent_desktop.notif_center.add_notification(
                "📸", "Region Captured!", "Sending cropped region to Prime Visual Core...", color="#a855f7"
            )
            
            # Submit to AI vision pipeline
            abs_path = crop_path.resolve()
            self.parent_desktop._send_to_ai(f"explain this cropped screenshot at {abs_path.as_posix()}")
            
        except Exception as e:
            print(f"[ScreenCrop] Crop failed: {e}")
            self.parent_desktop.notif_center.add_notification(
                "❌", "Capture Failed", f"Crop error: {e}", color="#ef4444"
            )

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Draw the clean captured screen background
        p.drawPixmap(0, 0, self.pixmap)
        
        # Calculate selection rect
        rect = QRect(self.start_pos, self.end_pos).normalized()
        
        # 2. Draw dim translucent mask outside selection
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 140)))
        
        # Top strip
        p.drawRect(0, 0, self.width(), rect.top())
        # Bottom strip
        p.drawRect(0, rect.bottom(), self.width(), self.height() - rect.bottom())
        # Left strip next to selection
        p.drawRect(0, rect.top(), rect.left(), rect.height())
        # Right strip next to selection
        p.drawRect(rect.right(), rect.top(), self.width() - rect.right(), rect.height())
        
        if not rect.isEmpty():
            # 3. Draw neon cyan glowing selection border
            neon_cyan = QColor(6, 182, 212, 230)
            p.setPen(QPen(neon_cyan, 2.5, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, 4.0, 4.0)
            
            # 4. Draw neon purple target corner marks
            neon_purple = QColor(139, 92, 246, 255)
            p.setPen(QPen(neon_purple, 4.0))
            
            l, t, r, b = rect.left(), rect.top(), rect.right(), rect.bottom()
            tick = 15
            
            # Top-left corner
            p.drawLine(l, t, l + tick, t)
            p.drawLine(l, t, l, t + tick)
            
            # Top-right corner
            p.drawLine(r, t, r - tick, t)
            p.drawLine(r, t, r, t + tick)
            
            # Bottom-left corner
            p.drawLine(l, b, l + tick, b)
            p.drawLine(l, b, l, b - tick)
            
            # Bottom-right corner
            p.drawLine(r, b, r - tick, b)
            p.drawLine(r, b, r, b - tick)

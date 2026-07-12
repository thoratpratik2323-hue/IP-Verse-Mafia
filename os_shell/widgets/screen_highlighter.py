"""
os_shell/widgets/screen_highlighter.py — Intelligent Screen Highlighting Overlay.
Captures screen, performs OCR, matches query, and flashes neon target boxes on top of UI.
"""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtWidgets import QWidget, QApplication, QMainWindow
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont

try:
    import pytesseract
    from PIL import Image
    _OCR_OK = True
except ImportError:
    _OCR_OK = False

class ScreenHighlightBox(QWidget):
    """Glowing neon overlay box that draws on top of a specific screen coordinate."""
    def __init__(self, x: int, y: int, w: int, h: int, duration: float = 4.0, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        
        # Expand geometry slightly for glow effect padding
        padding = 10
        self.target_x = x
        self.target_y = y
        self.target_w = w
        self.target_h = h
        
        self.setGeometry(x - padding, y - padding, w + padding * 2, h + padding * 2)
        
        self.tick = 0
        self.max_ticks = int(duration * 60)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)
        self.timer.start(16) # ~60 fps

    def _step(self):
        self.tick += 1
        if self.tick >= self.max_ticks:
            self.timer.stop()
            self.close()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        progress = self.tick / self.max_ticks
        opacity = int(220 * (1.0 - progress))
        
        # Draw pulsing neon border
        color = QColor(6, 182, 212, opacity) # Electric cyan
        p.setPen(QPen(color, 2.5, Qt.PenStyle.SolidLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        
        # Draw bounding rect
        p.drawRoundedRect(
            QRectF(10, 10, self.target_w, self.target_h),
            6.0, 6.0
        )
        
        # Draw target corners
        corner_color = QColor(139, 92, 246, opacity) # Purple corner ticks
        p.setPen(QPen(corner_color, 3.5))
        
        # Top-left corner
        p.drawLine(10, 10, 20, 10)
        p.drawLine(10, 10, 10, 20)
        
        # Top-right corner
        p.drawLine(self.target_w + 10, 10, self.target_w, 10)
        p.drawLine(self.target_w + 10, 10, self.target_w + 10, 20)
        
        # Bottom-left corner
        p.drawLine(10, self.target_h + 10, 20, self.target_h + 10)
        p.drawLine(10, self.target_h + 10, 10, self.target_h)
        
        # Bottom-right corner
        p.drawLine(self.target_w + 10, self.target_h + 10, self.target_w, self.target_h + 10)
        p.drawLine(self.target_w + 10, self.target_h + 10, self.target_w + 10, self.target_h)

def highlight_text_on_screen(query: str) -> str:
    """Takes screen grab, runs local OCR, matches query, and flashes target box on UI thread."""
    try:
        app = QApplication.instance()
        if not app:
            return "Application not running."
            
        # Find desktop window to temporarily hide it
        desktop = None
        for w in QApplication.topLevelWidgets():
            if w.inherits("QMainWindow") or w.__class__.__name__ == "IPPrimeOSDesktop":
                desktop = w
                break
                
        temp_img_path = os.path.join(os.environ.get("TEMP", "."), "ip_prime_ocr_grab.png")
        if os.path.exists(temp_img_path):
            try: os.remove(temp_img_path)
            except: pass
            
        def _job():
            try:
                if desktop:
                    desktop.hide()
                    QApplication.processEvents()
                    # Sleep slightly to let the window manager process hide animation
                    time.sleep(0.15)
                    
                screen = QApplication.primaryScreen()
                if screen:
                    pix = screen.grabWindow(0)
                    pix.save(temp_img_path, "PNG")
                    
                if desktop:
                    desktop.show()
                    desktop.raise_()
            except Exception as e:
                print(f"[Highlighter ScreenGrab Error] {e}")
                if desktop:
                    desktop.show()
                
        # Must execute screen grab on main thread to avoid crash
        QTimer.singleShot(0, _job)
        time_counter = 0
        while not os.path.exists(temp_img_path) and time_counter < 30:
            time.sleep(0.1)
            time_counter += 1
            
        if not os.path.exists(temp_img_path):
            return "❌ Failed to capture screen grab for OCR."
            
        # 2. Run OCR & find query
        found_matches = []
        if _OCR_OK:
            try:
                img = Image.open(temp_img_path)
                data = pytesseract.image_to_data(img, output_type='dict')
                
                query_lower = query.lower().strip()
                for i, text in enumerate(data['text']):
                    if query_lower in text.lower().strip():
                        found_matches.append({
                            "x": data['left'][i],
                            "y": data['top'][i],
                            "w": data['width'][i],
                            "h": data['height'][i]
                        })
            except Exception as e:
                print(f"[Highlighter OCR Err] {e}")
                
        # Gemini Vision Fallback if Tesseract failed or found no local matches
        if not found_matches and os.path.exists(temp_img_path):
            try:
                print(f"[Highlighter Fallback] Local OCR returned no matches. Querying Gemini Vision RAG...")
                from actions.prime_utils import UnifiedModelClient
                from google.genai import types as gtypes
                
                try:
                    from actions.autopilot_agent import highlight_swarm_node
                    highlight_swarm_node("Fallback", f"OCR Fallback to Gemini: {query}")
                except:
                    pass
                
                with open(temp_img_path, "rb") as f:
                    img_bytes = f.read()
                
                client = UnifiedModelClient(category="vision")
                prompt = (
                    f"Find the pixel coordinates [x, y, width, height] of the text '{query}' on this screenshot image. "
                    f"Return a JSON object containing keys 'x', 'y', 'w', 'h'. "
                    f"If multiple instances exist, return a JSON object with a list of coordinates under key 'matches'. "
                    f"Return ONLY valid raw JSON, nothing else."
                )
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        gtypes.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                        prompt
                    ]
                )
                
                import re
                import json
                txt = response.text or ""
                match = re.search(r"\{.*\}|\[.*\]", txt, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    if "matches" in parsed and isinstance(parsed["matches"], list):
                        for item in parsed["matches"]:
                            found_matches.append({
                                "x": int(item.get("x", 0)),
                                "y": int(item.get("y", 0)),
                                "w": int(item.get("w", 50)),
                                "h": int(item.get("h", 20))
                            })
                    elif "x" in parsed:
                        found_matches.append({
                            "x": int(parsed.get("x", 0)),
                            "y": int(parsed.get("y", 0)),
                            "w": int(parsed.get("w", 50)),
                            "h": int(parsed.get("h", 20))
                        })
            except Exception as ex:
                print(f"[Highlighter Fallback Error] {ex}")

        # Clean up temp image
        try: os.remove(temp_img_path)
        except: pass
        
        # Diagnostic fallback if no OCR matches found or OCR library missing
        if not found_matches:
            # Simulated match - flash box in the center of the screen to guide user
            screen_geo = QApplication.primaryScreen().geometry()
            cx = screen_geo.width() // 2
            cy = screen_geo.height() // 2
            found_matches.append({
                "x": cx - 100,
                "y": cy - 40,
                "w": 200,
                "h": 80
            })
            msg = f"⚠️ OCR match not found on screen. Flashed a central scan marker instead, sir."
        else:
            msg = f"✅ Flashed highlight overlays for {len(found_matches)} matches of '{query}'."
            
        # 3. Spawn overlays on UI thread
        def _trigger_highlights():
            if not hasattr(app, "_active_highlights"):
                app._active_highlights = []
            for match in found_matches:
                box = ScreenHighlightBox(match["x"], match["y"], match["w"], match["h"])
                app._active_highlights.append(box)
                box.show()
                box.destroyed.connect(lambda: app._active_highlights.remove(box) if box in app._active_highlights else None)
                
        QTimer.singleShot(0, _trigger_highlights)
        return msg
        
    except Exception as e:
        return f"❌ Screen highlighting error: {e}"

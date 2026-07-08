import sys
import time
import threading
import shutil
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QTextEdit, QMessageBox, QSplitter
)
from PyQt6.QtGui import QFont, QColor, QPixmap

# Styles map corresponding to NainiPix aesthetic presets
NAINIPIX_PRESETS = {
    "🌌 Cyberpunk Future": {
        "prefix": "In a futuristic cyberpunk city with neon lights, high-tech details, glowing holograms, synthwave aesthetic, 8k resolution, detailed, ",
        "suffix": ""
    },
    "🌄 Warm Vintage": {
        "prefix": "Vintage film style photography, warm sun-drenched lighting, nostalgia, fine grain, cinematic retro look, 35mm lens, ",
        "suffix": ""
    },
    "🌸 Aesthetic Anime": {
        "prefix": "Gorgeous clean aesthetic anime key art illustration, highly detailed, beautiful lighting, vibrant color palette, Makoto Shinkai style, ",
        "suffix": ""
    },
    "👾 Retro Pixel Art": {
        "prefix": "Charming 16-bit retro pixel art design, vibrant game asset style, pixel grid, nostalgic, ",
        "suffix": ""
    },
    "💎 3D Glassmorphism": {
        "prefix": "Premium 3D render, glossy frosted glass glassmorphism style elements, translucent textures, vibrant mesh gradient background, clean studio lighting, high resolution, ",
        "suffix": ""
    },
    "📸 Portrait Cinematic": {
        "prefix": "Cinematic professional photography, high-end dramatic lighting, shallow depth of field, blurred background, crisp focus, photorealistic 8k, ",
        "suffix": ""
    },
    "✨ Normal (No Style)": {
        "prefix": "",
        "suffix": ""
    }
}

class NainiPixStudioWidget(QWidget):
    generation_finished = pyqtSignal(bool, str) # success, filepath/error
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.desktop = parent
        self.generated_image_path = None
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("NainiPixStudio")
        self.setStyleSheet("""
            QWidget#NainiPixStudio {
                background-color: rgba(15, 23, 42, 0.45);
                border-radius: 12px;
            }
            QLabel {
                color: #f1f5f9;
                background: transparent;
            }
            QComboBox {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: white;
                font-family: 'Outfit';
                font-size: 11px;
                padding: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: white;
                selection-background-color: #4f46e5;
            }
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: white;
                font-family: 'Outfit';
                font-size: 12px;
                padding: 6px;
            }
            QPushButton {
                border-radius: 6px;
                font-family: 'Outfit';
                font-size: 11px;
                font-weight: bold;
                padding: 6px 12px;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Splitter to separate Controls and Preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Left Panel: Controls ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Style Title
        title_lbl = QLabel("✨ NainiPix AI Studio", self)
        title_lbl.setFont(QFont("Outfit", 14, QFont.Weight.ExtraBold))
        title_lbl.setStyleSheet("color: #a855f7;")
        left_layout.addWidget(title_lbl)
        
        desc_lbl = QLabel("Generate premium styled artwork using AI presets", self)
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        left_layout.addWidget(desc_lbl)
        
        # Presets selector
        left_layout.addWidget(QLabel("Select Aesthetic Preset:", self))
        self.preset_combo = QComboBox(self)
        self.preset_combo.addItems(list(NAINIPIX_PRESETS.keys()))
        self.preset_combo.setCurrentText("🌌 Cyberpunk Future")
        left_layout.addWidget(self.preset_combo)
        
        # Prompt box
        left_layout.addWidget(QLabel("Prompt Description:", self))
        self.prompt_edit = QTextEdit(self)
        self.prompt_edit.setPlaceholderText("Describe your masterpiece here... e.g. A solitary astronaut looking at a neon butterfly")
        left_layout.addWidget(self.prompt_edit)
        
        # Options row: Ratio and Provider
        opts_layout = QHBoxLayout()
        
        ratio_box = QVBoxLayout()
        ratio_box.addWidget(QLabel("Aspect Ratio:", self))
        self.ratio_combo = QComboBox(self)
        self.ratio_combo.addItems(["1:1", "16:9", "9:16", "4:3", "3:4"])
        ratio_box.addWidget(self.ratio_combo)
        opts_layout.addLayout(ratio_box)
        
        prov_box = QVBoxLayout()
        prov_box.addWidget(QLabel("API Provider:", self))
        self.prov_combo = QComboBox(self)
        self.prov_combo.addItems(["Auto", "Replicate (Flux)", "Ideogram", "Pollinations (Free)"])
        prov_box.addWidget(self.prov_combo)
        opts_layout.addLayout(prov_box)
        
        left_layout.addLayout(opts_layout)
        
        # Generate Button
        self.gen_btn = QPushButton("🎨 Generate Artwork", self)
        self.gen_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #ec4899);
                color: white;
                border: none;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:disabled {
                background: #475569;
                color: #94a3b8;
            }
        """)
        self.gen_btn.clicked.connect(self.start_generation)
        left_layout.addWidget(self.gen_btn)
        
        splitter.addWidget(left_widget)
        
        # --- Right Panel: Preview Area ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        # Large preview image placeholder
        self.preview_lbl = QLabel(self)
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.4);
                border: 2px dashed rgba(168, 85, 247, 0.3);
                border-radius: 8px;
            }
        """)
        self.preview_lbl.setText("🎨\nYour AI masterpiece\nwill appear here")
        self.preview_lbl.setFont(QFont("Outfit", 12, QFont.Weight.Medium))
        right_layout.addWidget(self.preview_lbl, 1)
        
        # Image actions
        actions_layout = QHBoxLayout()
        
        self.wall_btn = QPushButton("🌄 Set as Wallpaper", self)
        self.wall_btn.setEnabled(False)
        self.wall_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(6, 182, 212, 0.2);
                border: 1px solid rgba(6, 182, 212, 0.4);
                color: #22d3ee;
            }
            QPushButton:hover {
                background-color: rgba(6, 182, 212, 0.3);
            }
        """)
        self.wall_btn.clicked.connect(self.set_as_wallpaper)
        actions_layout.addWidget(self.wall_btn)
        
        self.save_as_btn = QPushButton("💾 Export Image", self)
        self.save_as_btn.setEnabled(False)
        self.save_as_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #e2e8f0;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.save_as_btn.clicked.connect(self.export_image)
        actions_layout.addWidget(self.save_as_btn)
        
        right_layout.addLayout(actions_layout)
        
        splitter.addWidget(right_widget)
        
        # Set splitter properties
        splitter.setSizes([320, 420])
        main_layout.addWidget(splitter)
        
        # Connect generation finished signal
        self.generation_finished.connect(self.on_generation_finished)
        
    def start_generation(self):
        user_prompt = self.prompt_edit.toPlainText().strip()
        if not user_prompt:
            QMessageBox.warning(self, "Empty Prompt", "Please enter a prompt description first, sir!")
            return
            
        # Compile preset styling
        preset_key = self.preset_combo.currentText()
        preset = NAINIPIX_PRESETS.get(preset_key, {"prefix": "", "suffix": ""})
        
        full_prompt = f"{preset['prefix']}{user_prompt}{preset['suffix']}"
        aspect_ratio = self.ratio_combo.currentText()
        provider = self.prov_combo.currentText().split("(")[0].strip().lower() # 'auto', 'replicate', 'ideogram', 'pollinations'
        
        # Disable controls during generation
        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("🧬 Generating Art...")
        self.preview_lbl.setText("⚡\nSynthesizing neural pathways...\nPlease wait, sir.")
        
        # Run inside thread to prevent freezing
        def run_thread():
            try:
                from actions.image_generator import _load_keys, _generate_replicate, _generate_ideogram, _generate_pollinations, EXPORTS_DIR
                
                # Check keys
                keys = _load_keys()
                img_data = None
                selected_prov = "pollinations"
                
                if provider == "replicate" and keys["replicate"]:
                    img_data = _generate_replicate(full_prompt, aspect_ratio, keys["replicate"])
                    selected_prov = "replicate"
                elif provider == "ideogram" and keys["ideogram"]:
                    img_data = _generate_ideogram(full_prompt, aspect_ratio, keys["ideogram"])
                    selected_prov = "ideogram"
                elif provider == "pollinations":
                    img_data = _generate_pollinations(full_prompt, aspect_ratio)
                    selected_prov = "pollinations"
                else:
                    # Auto select
                    if keys["replicate"]:
                        img_data = _generate_replicate(full_prompt, aspect_ratio, keys["replicate"])
                        selected_prov = "replicate"
                    elif keys["ideogram"]:
                        img_data = _generate_ideogram(full_prompt, aspect_ratio, keys["ideogram"])
                        selected_prov = "ideogram"
                    else:
                        img_data = _generate_pollinations(full_prompt, aspect_ratio)
                        selected_prov = "pollinations"
                        
                if img_data:
                    # Save image
                    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
                    filename = f"nainipix_{int(time.time())}.png"
                    full_path = EXPORTS_DIR / filename
                    with open(full_path, "wb") as f:
                        f.write(img_data)
                    self.generation_finished.emit(True, str(full_path))
                else:
                    self.generation_finished.emit(False, "Failed to generate image data. Please check connection.")
            except Exception as e:
                self.generation_finished.emit(False, str(e))
                
        threading.Thread(target=run_thread, daemon=True).start()
        
    def on_generation_finished(self, success, result):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("🎨 Generate Artwork")
        
        if success:
            self.generated_image_path = result
            pixmap = QPixmap(result)
            if not pixmap.isNull():
                # Scale pixmap to fit preview area nicely
                scaled = pixmap.scaled(self.preview_lbl.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_lbl.setPixmap(scaled)
                self.wall_btn.setEnabled(True)
                self.save_as_btn.setEnabled(True)
                # If player/desktop is present, log it
                if self.desktop and hasattr(self.desktop, "write_log"):
                    self.desktop.write_log(f"IP Prime: Generated image successfully! Saved to: {result}")
            else:
                self.preview_lbl.setText("✗\nError rendering\ngenerated image.")
        else:
            QMessageBox.critical(self, "Generation Failed", f"Failed to generate image, sir:\n{result}")
            self.preview_lbl.setText("🎨\nYour AI masterpiece\nwill appear here")
            
    def set_as_wallpaper(self):
        if not self.generated_image_path:
            return
            
        if self.desktop and hasattr(self.desktop, "set_wallpaper_direct"):
            ok = self.desktop.set_wallpaper_direct(self.generated_image_path)
            if ok:
                QMessageBox.information(self, "Wallpaper Updated", "Awesome, sir! The generated art is now your desktop wallpaper.")
            else:
                QMessageBox.critical(self, "Failed Set Wallpaper", "Could not set desktop wallpaper, sir.")
        else:
            QMessageBox.warning(self, "Not Supported", "Desktop wallpaper manager is not active in this session.")
            
    def export_image(self):
        if not self.generated_image_path:
            return
            
        from PyQt6.QtWidgets import QFileDialog
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Export NainiPix Artwork", "art_masterpiece.png", "Images (*.png)"
        )
        if dest_path:
            try:
                shutil.copy(self.generated_image_path, dest_path)
                QMessageBox.information(self, "Image Exported", f"Successfully exported to:\n{dest_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to copy file: {e}")
                
    def resizeEvent(self, event):
        if self.generated_image_path:
            pixmap = QPixmap(self.generated_image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.preview_lbl.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_lbl.setPixmap(scaled)
        super().resizeEvent(event)

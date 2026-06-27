import sys
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QCalendarWidget, QComboBox, QScrollArea, QFrame
)
from PyQt6.QtGui import QFont, QColor

from os_shell.theme_engine import OSThemeEngine, THEMES

class NotificationCenterWidget(QFrame):
    # Signals
    theme_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_engine = OSThemeEngine()
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("NotificationCenter")
        self.update_style()
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 20, 15, 15)
        main_layout.setSpacing(15)
        self.setLayout(main_layout)
        
        # Header layout
        header_lay = QHBoxLayout()
        title = QLabel("Control Center", self)
        title.setFont(QFont("Outfit", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #27C8F5; background: transparent;")
        header_lay.addWidget(title)
        
        close_btn = QPushButton("✕", self)
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8899A6;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header_lay.addWidget(close_btn)
        main_layout.addLayout(header_lay)
        
        # Scroll Area for contents
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setContentsMargins(0, 0, 0, 0)
        scroll_lay.setSpacing(15)
        
        # Section 1: Theme Switcher
        theme_box = QFrame(self)
        theme_box.setStyleSheet("background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;")
        theme_lay = QVBoxLayout(theme_box)
        theme_lay.setContentsMargins(10, 10, 10, 10)
        
        theme_lbl = QLabel("Desktop Theme", self)
        theme_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        theme_lbl.setStyleSheet("color: #27C8F5; border: none; background: transparent;")
        theme_lay.addWidget(theme_lbl)
        
        self.theme_combo = QComboBox(self)
        for key, val in THEMES.items():
            self.theme_combo.addItem(val["name"], key)
            
        # Select current theme
        idx = self.theme_combo.findData(self.theme_engine.current_theme_key)
        if idx != -1:
            self.theme_combo.setCurrentIndex(idx)
            
        self.theme_combo.currentIndexChanged.connect(self.on_theme_select)
        theme_lay.addWidget(self.theme_combo)

        # Section 1b: Wallpaper Presets
        wp_lbl = QLabel("Wallpaper Style", self)
        wp_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        wp_lbl.setStyleSheet("color: #27C8F5; border: none; background: transparent; margin-top: 10px;")
        theme_lay.addWidget(wp_lbl)

        self.wp_combo = QComboBox(self)
        self.wp_combo.addItem("Star Field", "stars")
        self.wp_combo.addItem("Matrix Rain", "matrix")
        self.wp_combo.addItem("Plexus Net", "plexus")
        self.wp_combo.addItem("Static Gradient", "none")

        if hasattr(self.parent(), "wallpaper_style"):
            idx = self.wp_combo.findData(self.parent().wallpaper_style)
            if idx != -1:
                self.wp_combo.setCurrentIndex(idx)

        self.wp_combo.currentIndexChanged.connect(self.on_wallpaper_select)
        theme_lay.addWidget(self.wp_combo)

        # Style Combo Boxes
        combo_style = """
            QComboBox {
                background-color: rgba(20, 28, 48, 0.8);
                border: 1px solid rgba(39, 200, 245, 0.2);
                border-radius: 6px;
                color: #FFFFFF;
                padding: 6px 12px;
                min-width: 200px;
            }
            QComboBox QAbstractItemView {
                background-color: #080E1C;
                color: #FFFFFF;
                selection-background-color: #27C8F5;
            }
        """
        self.theme_combo.setStyleSheet(combo_style)
        self.wp_combo.setStyleSheet(combo_style)
        scroll_lay.addWidget(theme_box)
        
        # Section 2: Calendar widget
        cal_box = QFrame(self)
        cal_box.setStyleSheet("background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;")
        cal_lay = QVBoxLayout(cal_box)
        cal_lay.setContentsMargins(5, 10, 5, 10)
        
        cal_lbl = QLabel("Calendar", self)
        cal_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        cal_lbl.setStyleSheet("color: #27C8F5; border: none; background: transparent; margin-left: 5px;")
        cal_lay.addWidget(cal_lbl)
        
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet("""
            QCalendarWidget QWidget {
                alternate-background-color: rgba(8, 14, 28, 0.5);
                background-color: rgba(6, 12, 26, 0.9);
                color: #FFFFFF;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #FFFFFF;
                selection-background-color: #27C8F5;
                selection-color: #000000;
            }
        """)
        cal_lay.addWidget(self.calendar)
        scroll_lay.addWidget(cal_box)
        
        # Section 3: AI Quick Sticky Notes
        note_box = QFrame(self)
        note_box.setStyleSheet("background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;")
        note_lay = QVBoxLayout(note_box)
        note_lay.setContentsMargins(10, 10, 10, 10)
        
        note_lbl = QLabel("OS Scratchpad", self)
        note_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        note_lbl.setStyleSheet("color: #27C8F5; border: none; background: transparent;")
        note_lay.addWidget(note_lbl)
        
        self.notes = QTextEdit(self)
        self.notes.setPlaceholderText("Type quick notes here...")
        self.notes.setStyleSheet("""
            QTextEdit {
                background-color: rgba(20, 28, 48, 0.6);
                border: 1px solid rgba(39, 200, 245, 0.15);
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 12px;
            }
        """)
        self.notes.setFixedHeight(120)
        note_lay.addWidget(self.notes)
        scroll_lay.addWidget(note_box)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Load cached scratchpad notes if any
        self.load_scratchpad()
        self.notes.textChanged.connect(self.save_scratchpad)
        
    def update_style(self):
        t = self.theme_engine.current
        self.setStyleSheet(f"""
            #NotificationCenter {{
                background-color: {t['panel']};
                border-left: 1px solid {t['border']};
            }}
        """)
        
    def on_theme_select(self, index):
        theme_key = self.theme_combo.itemData(index)
        self.theme_engine.save_theme(theme_key)
        self.update_style()
        self.theme_changed.emit(theme_key)
        
    def on_wallpaper_select(self, index):
        wp_style = self.wp_combo.itemData(index)
        if hasattr(self.parent(), "wallpaper_style"):
            self.parent().wallpaper_style = wp_style
        
    def save_scratchpad(self):
        import json
        config_path = self.theme_engine.CONFIG_DIR / "os_scratchpad.json"
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({"notes": self.notes.toPlainText()}, f)
        except Exception:
            pass
            
    def load_scratchpad(self):
        import json
        config_path = self.theme_engine.CONFIG_DIR / "os_scratchpad.json"
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notes.setPlainText(data.get("notes", ""))
        except Exception:
            pass

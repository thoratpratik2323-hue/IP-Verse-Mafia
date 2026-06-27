import os
import json
from pathlib import Path
from PyQt6.QtGui import QColor

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
THEME_FILE = CONFIG_DIR / "os_theme.json"

# Theme Palettes
THEMES = {
    "windows": {
        "name": "Fluent Windows",
        "bg": "#10121a",
        "panel": "rgba(32, 35, 48, 0.90)",
        "border": "rgba(96, 205, 255, 0.22)",
        "primary": "#60cdff",
        "accent": "#0078d4",
        "text": "#F3F4F6",
        "text_muted": "#9CA3AF"
    },
    "cobalt": {
        "name": "Cobalt Blue",
        "bg": "#040810",
        "panel": "rgba(8, 14, 28, 0.94)",
        "border": "rgba(39, 200, 245, 0.2)",
        "primary": "#27C8F5",
        "accent": "#8B5CF6",
        "text": "#F0F4F8",
        "text_muted": "#8899A6"
    },
    "neon": {
        "name": "Electric Cyan",
        "bg": "#02020a",
        "panel": "rgba(2, 6, 18, 0.95)",
        "border": "rgba(0, 240, 255, 0.25)",
        "primary": "#00f0ff",
        "accent": "#f43f5e",
        "text": "#FFFFFF",
        "text_muted": "#64748B"
    },
    "emerald": {
        "name": "Emerald Green",
        "bg": "#020a05",
        "panel": "rgba(4, 18, 10, 0.94)",
        "border": "rgba(16, 185, 129, 0.2)",
        "primary": "#10B981",
        "accent": "#10B981",
        "text": "#ECFDF5",
        "text_muted": "#6EE7B7"
    },
    "purple": {
        "name": "Aether Purple",
        "bg": "#080014",
        "panel": "rgba(12, 6, 24, 0.94)",
        "border": "rgba(217, 70, 239, 0.2)",
        "primary": "#D946EF",
        "accent": "#00f0ff",
        "text": "#FDF4FF",
        "text_muted": "#C084FC"
    },
    "obsidian": {
        "name": "Obsidian Dark",
        "bg": "#09090b",
        "panel": "rgba(18, 18, 24, 0.96)",
        "border": "rgba(255, 255, 255, 0.08)",
        "primary": "#E4E4E7",
        "accent": "#F43F5E",
        "text": "#FAFAFA",
        "text_muted": "#71717A"
    }
}

class OSThemeEngine:
    CONFIG_DIR = CONFIG_DIR
    
    def __init__(self):
        self.current_theme_key = "windows"
        self.load_theme()
        
    def load_theme(self):
        try:
            if THEME_FILE.exists():
                with open(THEME_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    key = data.get("theme_key", "windows")
                    if key in THEMES:
                        self.current_theme_key = key
        except Exception as e:
            print(f"Failed to load OS theme: {e}")
            
    def save_theme(self, theme_key):
        if theme_key not in THEMES:
            return
        self.current_theme_key = theme_key
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(THEME_FILE, 'w', encoding='utf-8') as f:
                json.dump({"theme_key": theme_key}, f, indent=4)
        except Exception as e:
            print(f"Failed to save OS theme: {e}")
            
    @property
    def current(self):
        return THEMES[self.current_theme_key]
        
    def get_stylesheet(self, component_name):
        t = self.current
        if component_name == "panel":
            return f"""
                background-color: {t['panel']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            """
        elif component_name == "button":
            return f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid {t['border']};
                    border-radius: 6px;
                    color: {t['text']};
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.12);
                    border: 1px solid {t['primary']};
                }}
            """
        return ""

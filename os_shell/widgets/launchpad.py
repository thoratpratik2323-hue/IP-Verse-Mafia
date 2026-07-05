import sys
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QScrollArea
)
from PyQt6.QtGui import QFont, QColor

class LaunchpadItem(QWidget):
    def __init__(self, key, name, emoji, callback, parent=None):
        super().__init__(parent)
        self.key = key
        self.name = name
        self.callback = callback
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        
        # Brand styling mapping
        styles = {
            "core": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #06b6d4, stop:1 #0891b2); border: 1px solid #0e7490;",
            "graph": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a855f7, stop:1 #8b5cf6); border: 1px solid #7c3aed;",
            "swarm": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5); border: 1px solid #4338ca;",
            "files": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fbbf24, stop:1 #f59e0b); border: 1px solid #d97706;",
            "config": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #64748b, stop:1 #475569); border: 1px solid #334155;",
            "notes": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fef08a, stop:1 #eab308); border: 1px solid #ca8a04;",
            "editor": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669); border: 1px solid #047857;",
            "tasks": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ec4899, stop:1 #db2777); border: 1px solid #be185d;",
            "calc": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f97316, stop:1 #ea580c); border: 1px solid #c2410c;",
            "youtube": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff4b4b, stop:1 #cc0000); border: 1px solid #990000;",
            "whatsapp": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #25d366, stop:1 #128c7e); border: 1px solid #075e54;",
            "instagram": "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f09433, stop:0.5 #dc2743, stop:1 #bc1888); border: 1px solid #8a3ab9;",
            "shell": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e293b, stop:1 #0f172a); border: 1px solid #020617;",
            "autopilot": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00f5ff, stop:1 #008b99); border: 1px solid #005f66;",
            "vision": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ec4899, stop:1 #a855f7); border: 1px solid #7c3aed;",
            "nainipix": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #a855f7); border: 1px solid #8a3ab9;",
            "cobra_web": "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #06b6d4); border: 1px solid #059669;"
        }
        bg_style = styles.get(key, "background-color: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.18);")
        
        # Large Emoji Button
        self.btn = QPushButton(emoji, self)
        self.btn.setFixedSize(70, 70)
        self.btn.setStyleSheet(f"""
            QPushButton {{
                {bg_style}
                border-radius: 20px;
                font-size: 32px;
                color: white;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        self.btn.clicked.connect(self._on_click)
        
        # Label
        self.lbl = QLabel(name, self)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-family: 'Outfit';
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
        """)
        
        layout.addWidget(self.btn)
        layout.addWidget(self.lbl)
        
    def _on_click(self):
        self.callback(self.key)

class LaunchpadOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.desktop = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Semi-transparent background
        self.setStyleSheet("""
            LaunchpadOverlay {
                background-color: rgba(10, 15, 30, 0.9);
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(25)
        
        # Header / Close Button
        header = QHBoxLayout()
        header.addStretch()
        
        # Search Bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search Apps...")
        self.search_bar.setFixedSize(300, 30)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 15px;
                padding: 6px 12px;
                color: white;
                font-family: 'Outfit';
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: rgba(255, 255, 255, 0.4);
                background-color: rgba(255, 255, 255, 0.18);
            }
        """)
        self.search_bar.textChanged.connect(self._filter_apps)
        
        # Center the search bar in header
        header.addStretch()
        header.addWidget(self.search_bar)
        header.addStretch()
        
        close_btn = QPushButton("✕", self)
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 15px;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(244, 63, 94, 0.7);
            }
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        
        main_layout.addLayout(header)
        
        # App Grid Scroll Area
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(35)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        self.scroll.setWidget(self.grid_widget)
        
        main_layout.addWidget(self.scroll)
        
        # Populate apps
        self.all_apps = [
            ("core", "Neural Core", "🧬"),
            ("graph", "Mind Graph", "🧠"),
            ("swarm", "Swarm Deck", "💻"),
            ("autopilot", "Autopilot Coder", "🤖"),
            ("vision", "Prime Vision", "👁️"),
            ("files", "Workspace Files", "📁"),
            ("config", "Control Center", "⚙️"),
            ("notes", "Sticky Note", "📝"),
            ("editor", "Code Editor", "✍️"),
            ("tasks", "Task Manager", "📊"),
            ("calc", "Calculator", "🧮"),
            ("youtube", "YouTube", "📺"),
            ("whatsapp", "WhatsApp", "💬"),
            ("instagram", "Instagram", "📸"),
            ("nainipix", "NainiPix Studio", "🎨"),
            ("cobra_web", "Cobra AI 2.0", "🐍"),
            ("shell", "Terminal", "🖥️")
        ]
        
        self.items = []
        self._populate_grid()
        
    def _populate_grid(self, filter_text=""):
        # Clear layout
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
            
        self.items.clear()
        
        # Filtered list
        filtered = [app for app in self.all_apps if filter_text in app[1].lower()]
        
        # Arrange in a grid of 5 columns
        cols = 5
        for index, (key, name, emoji) in enumerate(filtered):
            row = index // cols
            col = index % cols
            item = LaunchpadItem(key, name, emoji, self._launch_app, self)
            self.grid_layout.addWidget(item, row, col, Qt.AlignmentFlag.AlignCenter)
            self.items.append(item)
            
    def _filter_apps(self, text):
        self._populate_grid(text.lower().strip())
        
    def _launch_app(self, key):
        self.hide()
        if self.desktop:
            # Show/toggle the window corresponding to key
            win = self.desktop.windows.get(key)
            if win:
                win.show_window()
                win.raise_()
                
    def mousePressEvent(self, event):
        # Close on background click
        if event.pos().y() > 80:  # avoid closing when clicking search bar area
            # check if click is on grid widget directly
            child = self.childAt(event.pos())
            if child is None or child == self.grid_widget or child == self.scroll:
                self.hide()
        super().mousePressEvent(event)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        super().keyPressEvent(event)
        
    def resizeEvent(self, event):
        # Always cover parent
        if self.parentWidget():
            self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())
        super().resizeEvent(event)

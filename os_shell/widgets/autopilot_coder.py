import random
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QListWidget, QSplitter
from PyQt6.QtGui import QFont, QColor

# Realistic code snippets for typing simulation
CODE_SNIPPETS = [
    # Python API Endpoint
    "import os\nimport sys\nimport requests\nfrom fastapi import FastAPI, HTTPException\n\napp = FastAPI(title='IP Prime OS Autopilot')\n\n@app.get('/api/status')\ndef get_status():\n    return {\n        'status': 'healthy',\n        'agent': 'Autopilot Coder',\n        'load': '0.12'\n    }",
    
    # PyQt Glass Window Definition
    "class GlassWindow(QWidget):\n    def __init__(self, title, parent=None):\n        super().__init__(parent)\n        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)\n        self.setStyleSheet('background: transparent; border: none;')\n        \n        # Initialize main layout\n        layout = QVBoxLayout(self)\n        self.titlebar = WindowTitleBar(title, self)\n        layout.addWidget(self.titlebar)",
    
    # HTML Layout template
    "<!DOCTYPE html>\n<html lang='en'>\n<head>\n    <meta charset='UTF-8'>\n    <title>IP Prime UI</title>\n    <link rel='stylesheet' href='style.css'>\n</head>\n<body>\n    <div class='central-orb' id='orb'>\n        <div class='pulsing-nucleus'></div>\n    </div>\n</body>\n</html>",
    
    # CSS Glassmorphism Stylesheet
    ".glass-panel {\n    background: rgba(10, 24, 27, 0.75);\n    border: 1px solid rgba(0, 200, 255, 0.18);\n    border-radius: 12px;\n    backdrop-filter: blur(20px);\n    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);\n    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);\n}",
    
    # Python Swarm Executor Thread
    "class SwarmExecutor(threading.Thread):\n    def __init__(self, tasks):\n        super().__init__(daemon=True)\n        self.queue = queue.Queue()\n        self.active = True\n        \n    def run(self):\n        while self.active:\n            task = self.queue.get()\n            self.execute_task(task)\n            self.queue.task_done()"
]

class AutopilotCoderWidget(QWidget):
    """
    Futuristic Agent Autopilot Coder visualizer.
    Triggers automatically when the Coder Agent starts writing code,
    simulating live typing animations and active directory modifications.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        
        # State variables
        self.active_file = "untitled.py"
        self.current_snippet = ""
        self.char_idx = 0
        self.cursor_visible = True
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header Status Panel
        self.header_panel = QWidget(self)
        self.header_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(5, 12, 14, 0.65);
                border: 1px solid rgba(0, 200, 255, 0.12);
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        h_layout = QHBoxLayout(self.header_panel)
        h_layout.setContentsMargins(12, 8, 12, 8)
        
        self.status_lbl = QLabel("🤖 AUTOPILOT CODER: IDLE", self.header_panel)
        self.status_lbl.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color: #9CA3AF;")
        
        self.file_lbl = QLabel("File: --", self.header_panel)
        self.file_lbl.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
        self.file_lbl.setStyleSheet("color: #60CDFF;")
        
        h_layout.addWidget(self.status_lbl)
        h_layout.addStretch()
        h_layout.addWidget(self.file_lbl)
        layout.addWidget(self.header_panel)
        
        # Splitter for Code editor and Folder Tree list
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setStyleSheet("QSplitter::handle { background-color: rgba(0, 200, 255, 0.08); }")
        
        # 1. Simulated Text Code Editor
        self.editor = QTextEdit(self)
        self.editor.setReadOnly(True)
        self.editor.setFont(QFont("JetBrains Mono", 10))
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: rgba(5, 12, 14, 0.85);
                border: 1px solid rgba(0, 200, 255, 0.15);
                border-radius: 8px;
                color: #00F5A0;
                line-height: 1.4;
            }
        """)
        splitter.addWidget(self.editor)
        
        # 2. File modification activity log / tree view
        self.tree_list = QListWidget(self)
        self.tree_list.setFont(QFont("JetBrains Mono", 9))
        self.tree_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(5, 12, 14, 0.85);
                border: 1px solid rgba(0, 200, 255, 0.15);
                border-radius: 8px;
                color: #B4CDD4;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            }
        """)
        splitter.addWidget(self.tree_list)
        splitter.setSizes([320, 160])
        layout.addWidget(splitter)
        
        # Initialize default tree layout
        self.tree_list.addItem("📁 projects/")
        self.tree_list.addItem("└── 📁 src/")
        
        # Timers
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self._type_character)
        
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self._toggle_cursor)
        self.cursor_timer.start(500)
        
    def start_coding_session(self, filename: str):
        """Triggers simulated typing animation for a given file."""
        self.active_file = filename
        self.file_lbl.setText(f"File: {filename}")
        self.status_lbl.setText("🤖 AUTOPILOT CODER: WRITING CODE...")
        self.status_lbl.setStyleSheet("color: #00F5A0;")
        
        # Choose a random code snippet
        self.current_snippet = random.choice(CODE_SNIPPETS)
        self.char_idx = 0
        self.editor.clear()
        
        # Append to active folders listing
        folder = "src"
        if "." in filename:
            ext = filename.split(".")[-1]
            if ext in ["html", "css"]:
                folder = "templates"
        
        # Add to folders list if not exists
        folder_str = f"    ├── 📁 {folder}/"
        file_str = f"    │   └── 📄 {filename} [WRITING...]"
        
        items = [self.tree_list.item(i).text() for i in range(self.tree_list.count())]
        if folder_str not in items:
            self.tree_list.addItem(folder_str)
        self.tree_list.addItem(file_str)
        self.tree_list.scrollToBottom()
        
        # Start typing timer with randomized intervals (simulates real human typing)
        self.typing_timer.start(random.randint(15, 35))
        
    def stop_coding_session(self):
        """Stops the typing session and resets to idle status."""
        self.typing_timer.stop()
        self.status_lbl.setText("🤖 AUTOPILOT CODER: IDLE")
        self.status_lbl.setStyleSheet("color: #9CA3AF;")
        
        # Mark the active file as completed in the tree
        count = self.tree_list.count()
        if count > 0:
            last_item = self.tree_list.item(count - 1)
            txt = last_item.text()
            if "[WRITING...]" in txt:
                last_item.setText(txt.replace("[WRITING...]", "[COMPLETED] ✅"))
                
    def _type_character(self):
        if self.char_idx < len(self.current_snippet):
            # Read next character
            char = self.current_snippet[self.char_idx]
            self.char_idx += 1
            
            # Update editor text
            cursor = "█" if self.cursor_visible else ""
            self.editor.setPlainText(self.current_snippet[:self.char_idx] + cursor)
            
            # Scroll to bottom
            v_bar = self.editor.verticalScrollBar()
            v_bar.setValue(v_bar.maximum())
            
            # Slightly randomize typing speed for realistic look
            if char in ["\n", ".", "{", "}"]:
                self.typing_timer.setInterval(random.randint(150, 300)) # Pause on lines or blocks
            else:
                self.typing_timer.setInterval(random.randint(15, 45))
        else:
            self.stop_coding_session()
            
    def _toggle_cursor(self):
        self.cursor_visible = not self.cursor_visible
        if not self.typing_timer.isActive():
            cursor = "█" if self.cursor_visible else ""
            self.editor.setPlainText(self.current_snippet[:self.char_idx] + cursor)

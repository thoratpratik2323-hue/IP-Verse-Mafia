from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit
from PyQt6.QtGui import QFont, QColor

class VocalTerminalWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("VocalTerminal")
        self.setFixedSize(380, 220)
        
        # Cyberpunk Fluent Acrylic Style
        self.setStyleSheet("""
            QFrame#VocalTerminal {
                background-color: rgba(6, 10, 18, 0.88);
                border: 1px solid rgba(57, 255, 20, 0.25);
                border-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # Header
        header = QHBoxLayout()
        title = QLabel(">_ VOCAL TERMINAL", self)
        title.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #39FF14; background: transparent;")
        header.addWidget(title)
        
        status = QLabel("[ MONITORING ]", self)
        status.setFont(QFont("Consolas", 8))
        status.setStyleSheet("color: rgba(57, 255, 20, 0.6); background: transparent;")
        header.addStretch()
        header.addWidget(status)
        layout.addLayout(header)
        
        # Console Display Text Edit
        self.console = QTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 9))
        self.console.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.console.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.console.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: #39FF14;
                line-height: 1.2;
            }
        """)
        layout.addWidget(self.console)
        
        self.append_text("System shell ready. Listening for logs...")
        
    def append_text(self, text: str):
        if not text or not text.strip():
            return
        
        # Remove markdown/HTML styles if any
        clean_text = text.replace("<b>", "").replace("</b>", "").replace("<br>", "\n")
        
        self.console.append(f">> {clean_text}")
        
        # Auto-scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Prevent text buffer bloat
        doc = self.console.document()
        if doc.blockCount() > 150:
            cursor = self.console.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar() # removes newline

import os
import sys
import subprocess
from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QLineEdit, QSplitter, QFrame, QInputDialog
)
from PyQt6.QtGui import QFont, QIcon

class OSFileManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dir = Path(os.path.expanduser("~"))
        self.history = []
        self._drag_pos = None
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("FileManager")
        self.setStyleSheet("""
            QWidget#FileManager {
                background-color: rgba(8, 14, 28, 0.98);
                border: 1px solid rgba(39, 200, 245, 0.3);
                border-radius: 12px;
            }
            QListWidget {
                background: transparent;
                border: none;
                color: #F0F4F8;
            }
            QListWidget::item {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 6px;
                margin: 3px 6px;
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: rgba(39, 200, 245, 0.08);
                border: 1px solid rgba(39, 200, 245, 0.25);
            }
            QListWidget::item:selected {
                background-color: rgba(139, 92, 246, 0.15);
                border: 1px solid rgba(139, 92, 246, 0.4);
                color: #FFFFFF;
            }
            QLineEdit {
                background-color: rgba(20, 28, 48, 0.8);
                border: 1px solid rgba(39, 200, 245, 0.2);
                border-radius: 8px;
                color: #FFFFFF;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #F0F4F8;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(39, 200, 245, 0.15);
                border: 1px solid #27C8F5;
            }
            QLabel {
                color: #F0F4F8;
                background: transparent;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)
        
        # Draggable Title Bar
        self.title_bar = QFrame(self)
        self.title_bar.setFixedHeight(32)
        self.title_bar.setStyleSheet("background-color: rgba(255,255,255,0.02); border-radius: 6px;")
        title_lay = QHBoxLayout(self.title_bar)
        title_lay.setContentsMargins(10, 0, 10, 0)
        
        title_lbl = QLabel("File Explorer", self)
        title_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #27C8F5;")
        title_lay.addWidget(title_lbl)
        title_lay.addStretch()
        
        close_btn = QPushButton("✕", self)
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8899A6;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        close_btn.clicked.connect(self.hide)
        title_lay.addWidget(close_btn)
        
        main_layout.addWidget(self.title_bar)
        
        # Header Controls (Back, Path edit, Search)
        hdr_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("← Back", self)
        self.back_btn.clicked.connect(self.navigate_back)
        hdr_layout.addWidget(self.back_btn)
        
        self.path_edit = QLineEdit(self)
        self.path_edit.setText(str(self.current_dir))
        self.path_edit.returnPressed.connect(self.navigate_to_edit_path)
        hdr_layout.addWidget(self.path_edit, 1)
        
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Filter files...")
        self.search_edit.textChanged.connect(self.filter_current_view)
        self.search_edit.setFixedWidth(180)
        hdr_layout.addWidget(self.search_edit)
        
        main_layout.addLayout(hdr_layout)
        
        # Main Splitter (Sidebar | Main explorer pane)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setStyleSheet("QSplitter::handle { background-color: rgba(255,255,255,0.05); }")
        
        # Sidebar Quick Access
        sidebar_frame = QFrame(self)
        sidebar_frame.setStyleSheet("background-color: rgba(0,0,0,0.15); border-radius: 8px;")
        sidebar_lay = QVBoxLayout(sidebar_frame)
        sidebar_lay.setContentsMargins(5, 5, 5, 5)
        
        sidebar_title = QLabel("Quick Access", self)
        sidebar_title.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        sidebar_title.setStyleSheet("color: #27C8F5; margin: 5px;")
        sidebar_lay.addWidget(sidebar_title)
        
        self.sidebar_list = QListWidget(self)
        self.sidebar_list.itemClicked.connect(self.on_sidebar_click)
        self.populate_sidebar()
        sidebar_lay.addWidget(self.sidebar_list)
        
        splitter.addWidget(sidebar_frame)
        
        # Main Explorer Pane
        explorer_frame = QFrame(self)
        explorer_lay = QVBoxLayout(explorer_frame)
        explorer_lay.setContentsMargins(0, 0, 0, 0)
        
        self.files_list = QListWidget(self)
        self.files_list.itemDoubleClicked.connect(self.on_item_double_click)
        explorer_lay.addWidget(self.files_list)
        
        splitter.addWidget(explorer_frame)
        
        # Set splitter sizes (25% sidebar, 75% explorer)
        splitter.setSizes([120, 480])
        main_layout.addWidget(splitter, 1)

    # ── Draggable Window events ──────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on the title bar frame or child label
            child = self.childAt(event.position().toPoint())
            if child in [self.title_bar] or (child and child.parent() == self.title_bar):
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        
        # Footer Actions (AI, Rename, Delete, etc.)
        footer_layout = QHBoxLayout()
        
        self.open_btn = QPushButton("Open File", self)
        self.open_btn.clicked.connect(self.open_selected_item)
        footer_layout.addWidget(self.open_btn)
        
        self.rename_btn = QPushButton("Rename", self)
        self.rename_btn.clicked.connect(self.rename_selected_item)
        footer_layout.addWidget(self.rename_btn)
        
        self.delete_btn = QPushButton("Delete", self)
        self.delete_btn.setStyleSheet("QPushButton:hover { border: 1px solid #EF4444; }")
        self.delete_btn.clicked.connect(self.delete_selected_item)
        footer_layout.addWidget(self.delete_btn)
        
        footer_layout.addStretch()
        
        self.ai_btn = QPushButton("🤖 Ask Prime", self)
        self.ai_btn.setStyleSheet("""
            QPushButton {
                color: #27C8F5;
                font-weight: bold;
                border: 1px solid rgba(39, 200, 245, 0.3);
            }
        """)
        self.ai_btn.clicked.connect(self.ask_prime_about_file)
        footer_layout.addWidget(self.ai_btn)
        
        main_layout.addLayout(footer_layout)
        
        # Initial scan
        self.scan_directory(self.current_dir)
        
    def populate_sidebar(self):
        # Add basic quick directories
        quick_dirs = [
            {"name": "🏠 Home", "path": os.path.expanduser("~")},
            {"name": "🖥️ Desktop", "path": os.path.join(os.path.expanduser("~"), "Desktop")},
            {"name": "📥 Downloads", "path": os.path.join(os.path.expanduser("~"), "Downloads")},
            {"name": "📄 Documents", "path": os.path.join(os.path.expanduser("~"), "Documents")},
            {"name": "💿 C:\\ Drive", "path": "C:\\"}
        ]
        
        # Add D drive if it exists
        if os.path.exists("D:\\"):
            quick_dirs.append({"name": "💿 D:\\ Drive", "path": "D:\\"})
            
        for d in quick_dirs:
            if os.path.exists(d["path"]):
                item = QListWidgetItem(d["name"])
                item.setData(Qt.ItemDataRole.UserRole, d["path"])
                self.sidebar_list.addItem(item)
                
    def scan_directory(self, path):
        path = Path(path)
        if not path.exists() or not path.is_dir():
            return
            
        self.current_dir = path
        self.path_edit.setText(str(path))
        self.files_list.clear()
        
        # Back btn enabled state
        self.back_btn.setEnabled(len(self.history) > 0 or path.parent != path)
        
        try:
            items = list(os.scandir(path))
            # Sort: folders first, then files
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for entry in items:
                prefix = "📁 " if entry.is_dir() else "📄 "
                item = QListWidgetItem(f"{prefix}{entry.name}")
                item.setData(Qt.ItemDataRole.UserRole, entry.path)
                self.files_list.addItem(item)
        except Exception as e:
            # Add error item
            item = QListWidgetItem(f"❌ Access Denied: {e}")
            self.files_list.addItem(item)
            
    def navigate_to_edit_path(self):
        new_path = self.path_edit.text()
        if os.path.exists(new_path) and os.path.isdir(new_path):
            self.history.append(self.current_dir)
            self.scan_directory(new_path)
            
    def filter_current_view(self, query):
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            # Match text after icon/prefix
            name = item.text()[2:]
            item.setHidden(query.lower() not in name.lower())
            
    def on_sidebar_click(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        self.history.append(self.current_dir)
        self.scan_directory(path)
        
    def on_item_double_click(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path is None:
            return
            
        if os.path.isdir(path):
            self.history.append(self.current_dir)
            self.scan_directory(path)
        else:
            self.open_file(path)
            
    def navigate_back(self):
        if self.history:
            prev = self.history.pop()
            self.scan_directory(prev)
        else:
            parent = self.current_dir.parent
            if parent != self.current_dir:
                self.scan_directory(parent)
                
    def open_selected_item(self):
        selected = self.files_list.selectedItems()
        if selected:
            path = selected[0].data(Qt.ItemDataRole.UserRole)
            if path:
                if os.path.isdir(path):
                    self.history.append(self.current_dir)
                    self.scan_directory(path)
                else:
                    self.open_file(path)
                    
    def open_file(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            print(f"Failed to open file: {e}")
            
    def rename_selected_item(self):
        selected = self.files_list.selectedItems()
        if not selected:
            return
        path = Path(selected[0].data(Qt.ItemDataRole.UserRole))
        if not path.exists():
            return
            
        new_name, ok = QInputDialog.getText(self, "Rename Item", "Enter new name:", text=path.name)
        if ok and new_name.strip():
            new_path = path.parent / new_name.strip()
            try:
                os.rename(path, new_path)
                self.scan_directory(self.current_dir)
            except Exception as e:
                print(f"Rename failed: {e}")
                
    def delete_selected_item(self):
        selected = self.files_list.selectedItems()
        if not selected:
            return
        path = Path(selected[0].data(Qt.ItemDataRole.UserRole))
        if not path.exists():
            return
            
        # Standard confirmation
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{path.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.scan_directory(self.current_dir)
            except Exception as e:
                print(f"Delete failed: {e}")
                
    def ask_prime_about_file(self):
        selected = self.files_list.selectedItems()
        if not selected:
            return
        path = selected[0].data(Qt.ItemDataRole.UserRole)
        if not path or os.path.isdir(path):
            return
            
        # Get relative path or name
        file_name = Path(path).name
        query = f"Give me details and explain this file: {file_name}"
        
        # Forward query to assistant
        try:
            from PyQt6.QtWidgets import QApplication
            qapp = QApplication.instance()
            for widget in qapp.topLevelWidgets():
                if hasattr(widget, "show") and hasattr(widget, "on_text_command") and hasattr(widget, "_chat"):
                    widget.show()
                    widget.raise_()
                    widget.activateWindow()
                    if widget.on_text_command:
                        widget.on_text_command(query)
        except Exception as e:
            print(f"Failed to forward file query to assistant: {e}")

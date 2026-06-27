import os
import sys
import logging
from pathlib import Path
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QGridLayout, QScrollArea, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QFont, QIcon, QColor

class AppLauncherWidget(QWidget):
    # Signals
    app_launched = pyqtSignal(str)
    search_triggered = pyqtSignal(str)  # Send query to assistant if not an app
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.apps = []
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("Launcher")
        self.setStyleSheet("""
            QWidget#Launcher {
                background-color: rgba(6, 12, 26, 0.96);
                border: 1px solid rgba(39, 200, 245, 0.25);
                border-radius: 16px;
            }
            QLineEdit {
                background-color: rgba(20, 28, 48, 0.8);
                border: 1px solid rgba(39, 200, 245, 0.3);
                border-radius: 8px;
                color: #FFFFFF;
                padding: 10px 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #27C8F5;
            }
            QListWidget {
                background: transparent;
                border: none;
                color: #F0F4F8;
            }
            QListWidget::item {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                margin: 4px 8px;
                padding: 10px;
            }
            QListWidget::item:hover {
                background-color: rgba(39, 200, 245, 0.1);
                border: 1px solid rgba(39, 200, 245, 0.3);
            }
            QListWidget::item:selected {
                background-color: rgba(139, 92, 246, 0.2);
                border: 1px solid rgba(139, 92, 246, 0.5);
                color: #FFFFFF;
            }
            QLabel {
                color: #F0F4F8;
                background: transparent;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        self.setLayout(main_layout)
        
        # Search Bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search apps or ask Prime (e.g. 'tell me a joke')...")
        self.search_bar.textChanged.connect(self.filter_apps)
        self.search_bar.returnPressed.connect(self.handle_execution)
        main_layout.addWidget(self.search_bar)
        
        # Label Info
        self.info_label = QLabel("Applications", self)
        self.info_label.setFont(QFont("Outfit", 12, QFont.Weight.Bold))
        self.info_label.setStyleSheet("color: #27C8F5; margin-left: 8px;")
        main_layout.addWidget(self.info_label)
        
        # Apps List
        self.apps_list = QListWidget(self)
        self.apps_list.itemDoubleClicked.connect(self.launch_selected_item)
        main_layout.addWidget(self.apps_list)
        
        # Load local apps dynamically
        self.scan_installed_apps()
        self.populate_list(self.apps)
        
    def scan_installed_apps(self):
        """Scans Windows Start Menu for shortcut links."""
        self.apps = []
        
        # Built-in fallback apps
        fallback_apps = [
            {"name": "Command Prompt", "path": "cmd.exe"},
            {"name": "PowerShell", "path": "powershell.exe"},
            {"name": "Notepad", "path": "notepad.exe"},
            {"name": "Calculator", "path": "calc.exe"},
            {"name": "Paint", "path": "mspaint.exe"},
            {"name": "Task Manager", "path": "taskmgr.exe"},
            {"name": "Registry Editor", "path": "regedit.exe"},
            {"name": "File Explorer", "path": "explorer.exe"}
        ]
        self.apps.extend(fallback_apps)
        
        # Common Windows start menu paths
        start_menu_paths = [
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        ]
        
        scanned_names = set(app["name"].lower() for app in self.apps)
        
        for path in start_menu_paths:
            if path.exists() and path.is_dir():
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith(".lnk"):
                            app_name = file[:-4]  # Remove .lnk
                            if app_name.lower() not in scanned_names:
                                full_path = os.path.join(root, file)
                                self.apps.append({"name": app_name, "path": full_path})
                                scanned_names.add(app_name.lower())
                                
        # Sort alphabetically
        self.apps.sort(key=lambda x: x["name"].lower())
        
    def populate_list(self, app_list):
        self.apps_list.clear()
        for app in app_list:
            item = QListWidgetItem(app["name"])
            item.setData(Qt.ItemDataRole.UserRole, app["path"])
            # We can associate a default icon, or query from executable
            self.apps_list.addItem(item)
            
    def filter_apps(self, query):
        if not query.strip():
            self.populate_list(self.apps)
            return
            
        filtered = [app for app in self.apps if query.lower() in app["name"].lower()]
        self.populate_list(filtered)
        
    def handle_execution(self):
        query = self.search_bar.text().strip()
        if not query:
            return
            
        # Check if first matching app name equals the query exactly or starts with it
        items = [self.apps_list.item(i) for i in range(self.apps_list.count())]
        exact_match = None
        for item in items:
            if item.text().lower() == query.lower():
                exact_match = item
                break
                
        if exact_match:
            self.launch_item(exact_match)
        elif self.apps_list.count() > 0:
            # Launch first filtered app
            self.launch_item(self.apps_list.item(0))
        else:
            # Query is not an app name, treat as voice/text assistant prompt
            self.search_triggered.emit(query)
            self.search_bar.clear()
            self.close()
            
    def launch_selected_item(self, item):
        self.launch_item(item)
        
    def launch_item(self, item):
        app_name = item.text()
        app_path = item.data(Qt.ItemDataRole.UserRole)
        
        logging.info(f"OS Launcher: Launching {app_name} from {app_path}")
        try:
            os.startfile(app_path)
            self.app_launched.emit(app_name)
        except Exception as e:
            logging.error(f"Failed to launch app {app_name}: {e}")
            
        self.search_bar.clear()
        self.close()

import os
import sys
import logging
from pathlib import Path
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QGridLayout, QScrollArea, QGraphicsOpacityEffect,
    QFrame
)
from PyQt6.QtGui import QFont, QIcon, QColor

class AppLauncherWidget(QFrame):
    # Signals
    app_launched = pyqtSignal(str)
    search_triggered = pyqtSignal(str)  # Send query to assistant if not an app
    pinned_changed = pyqtSignal()
    
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
        self.apps_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.apps_list.customContextMenuRequested.connect(self.show_context_menu)
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

    def show_context_menu(self, pos):
        item = self.apps_list.itemAt(pos)
        if not item:
            return
        
        app_name = item.text()
        app_path = item.data(Qt.ItemDataRole.UserRole)
        
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #10121a;
                border: 1px solid rgba(96, 205, 255, 0.25);
                border-radius: 8px;
                color: #F3F4F6;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(96, 205, 255, 0.15);
                color: #60cdff;
            }
        """)
        
        pinned = self._load_pinned_apps()
        is_pinned = any(p["name"].lower() == app_name.lower() or p["cmd"].lower() == app_path.lower() for p in pinned)
        
        if is_pinned:
            action = menu.addAction("📌 Unpin from Taskbar")
            action.triggered.connect(lambda: self.unpin_app(app_name, app_path))
        else:
            action = menu.addAction("📌 Pin to Taskbar")
            action.triggered.connect(lambda: self.pin_app(app_name, app_path))
            
        menu.exec(self.apps_list.mapToGlobal(pos))

    def pin_app(self, name, path):
        pinned = self._load_pinned_apps()
        # Deduplicate
        if any(p["name"].lower() == name.lower() or p["cmd"].lower() == path.lower() for p in pinned):
            return
            
        # Detect appropriate emoji icon based on name
        icon = "🚀"
        name_lower = name.lower()
        if "chrome" in name_lower or "browser" in name_lower or "edge" in name_lower or "firefox" in name_lower:
            icon = "🌐"
        elif "file" in name_lower or "explorer" in name_lower or "folder" in name_lower:
            icon = "📁"
        elif "cmd" in name_lower or "terminal" in name_lower or "powershell" in name_lower or "bash" in name_lower:
            icon = "💻"
        elif "note" in name_lower or "editor" in name_lower or "write" in name_lower or "word" in name_lower:
            icon = "📝"
        elif "setting" in name_lower or "control" in name_lower or "config" in name_lower:
            icon = "⚙️"
        elif "music" in name_lower or "spotify" in name_lower or "player" in name_lower:
            icon = "🎵"
        elif "calc" in name_lower:
            icon = "🧮"
        elif "paint" in name_lower or "draw" in name_lower:
            icon = "🎨"
            
        pinned.append({"name": name, "cmd": path, "icon": icon})
        self._save_pinned_apps(pinned)
        self.pinned_changed.emit()

    def unpin_app(self, name, path):
        pinned = self._load_pinned_apps()
        pinned = [p for p in pinned if p["name"].lower() != name.lower() and p["cmd"].lower() != path.lower()]
        self._save_pinned_apps(pinned)
        self.pinned_changed.emit()

    def _get_pinned_file_path(self):
        import json
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent
        config_dir = base_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "pinned_apps.json"

    def _load_pinned_apps(self):
        import json
        path = self._get_pinned_file_path()
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Fallback default
        default_pinned = [
            {"name": "Browser", "cmd": "msedge", "icon": "🌐"},
            {"name": "Files", "cmd": "files", "icon": "📁"},
            {"name": "Terminal", "cmd": "wt.exe", "icon": "💻"},
            {"name": "Notes", "cmd": "notepad.exe", "icon": "📝"},
            {"name": "Settings", "cmd": "ms-settings:", "icon": "⚙️"}
        ]
        self._save_pinned_apps(default_pinned)
        return default_pinned

    def _save_pinned_apps(self, data):
        import json
        path = self._get_pinned_file_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save pinned apps: {e}")

"""
os_shell/widgets/kanban_hud.py — Glassmorphic Kanban Task Board HUD.
A clean, premium widget to view and manage active goals and tasks.
"""
from __future__ import annotations
import json
from pathlib import Path
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea, QCheckBox
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent

GOALS_PATH = Path("memory/goals.json")

class KanbanTaskBoardHUD(QWidget):
    """
    Glassmorphic floating widget displaying Pratik's active project goals/tasks
    with checklist controls to toggle progress.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 240)
        
        self.tasks: list[dict] = []
        self._load_tasks()
        
        # Header Label
        self.header_lbl = QLabel("IP PRIME KANBAN", self)
        self.header_lbl.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        self.header_lbl.setStyleSheet("color: #06b6d4; background: transparent; letter-spacing: 1px;")
        self.header_lbl.move(18, 15)
        
        # Scroll Area for Task List
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.FrameShape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.move(10, 45)
        self.scroll.resize(280, 180)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout_tasks = QVBoxLayout(self.container)
        self.layout_tasks.setContentsMargins(5, 5, 5, 5)
        self.layout_tasks.setSpacing(10)
        self.scroll.setWidget(self.container)
        
        self.refresh_ui()

        # File Watcher for Real-time Sync
        from PyQt6.QtCore import QFileSystemWatcher
        self.watcher = QFileSystemWatcher(self)
        if not GOALS_PATH.exists():
            self._save_tasks()
        self.watcher.addPath(str(GOALS_PATH))
        self.watcher.fileChanged.connect(self._on_file_changed)

    def _load_tasks(self):
        """Loads tasks from goals.json with fallback default goals."""
        try:
            if GOALS_PATH.exists():
                self.tasks = json.loads(GOALS_PATH.read_text(encoding="utf-8"))
            else:
                self.tasks = [
                    {"id": 1, "title": "Build IP Prime companion app", "status": "active", "progress": 10},
                    {"id": 2, "title": "Implement multi-agent swarm", "status": "active", "progress": 30},
                    {"id": 3, "title": "Refactor audio buffer loops", "status": "done", "progress": 100},
                    {"id": 4, "title": "Integrate visual screen crop tool", "status": "done", "progress": 100}
                ]
                self._save_tasks()
        except Exception:
            self.tasks = []

    def _save_tasks(self):
        try:
            GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
            GOALS_PATH.write_text(json.dumps(self.tasks, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Kanban HUD] Failed to save tasks: {e}")

    def refresh_ui(self):
        # Clear layout
        while self.layout_tasks.count():
            child = self.layout_tasks.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Rebuild task list rows
        for t in self.tasks:
            row = QWidget()
            row.setFixedHeight(34)
            row.setStyleSheet("background: rgba(255, 255, 255, 5); border-radius: 6px;")
            
            h_layout = QHBoxLayout(row)
            h_layout.setContentsMargins(8, 0, 8, 0)
            h_layout.setSpacing(8)
            
            # Checkbox control
            cb = QCheckBox()
            cb.setChecked(t.get("status") == "done")
            cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 14px;
                    height: 14px;
                    border: 1px solid rgba(255, 255, 255, 40);
                    border-radius: 3px;
                    background: transparent;
                }
                QCheckBox::indicator:checked {
                    background-color: #10b981;
                    border-color: #10b981;
                }
            """)
            cb.stateChanged.connect(lambda state, task_id=t["id"]: self.toggle_task(task_id, state))
            h_layout.addWidget(cb)
            
            # Task Title Label
            lbl = QLabel(t["title"])
            lbl.setFont(QFont("Outfit", 9))
            if t.get("status") == "done":
                lbl.setStyleSheet("color: #64748b; text-decoration: line-through; background: transparent;")
            else:
                lbl.setStyleSheet("color: #e2e8f0; background: transparent;")
            h_layout.addWidget(lbl, 1)
            
            # Status Badge
            badge = QLabel()
            badge.setFont(QFont("Outfit", 7, QFont.Weight.Bold))
            badge.setContentsMargins(6, 2, 6, 2)
            if t.get("status") == "done":
                badge.setText("DONE")
                badge.setStyleSheet("color: #10b981; background: rgba(16, 185, 129, 20); border-radius: 4px; padding: 2px;")
            else:
                progress = t.get("progress", 0)
                if progress > 0:
                    badge.setText("DOING")
                    badge.setStyleSheet("color: #a855f7; background: rgba(168, 85, 247, 20); border-radius: 4px; padding: 2px;")
                else:
                    badge.setText("TODO")
                    badge.setStyleSheet("color: #06b6d4; background: rgba(6, 182, 212, 20); border-radius: 4px; padding: 2px;")
            h_layout.addWidget(badge)
            
            self.layout_tasks.addWidget(row)
            
        self.layout_tasks.addStretch()

    def _on_file_changed(self):
        self._load_tasks()
        self.refresh_ui()

    def toggle_task(self, task_id: int, state: int):
        """Update task progress dynamically."""
        self.watcher.blockSignals(True)
        for t in self.tasks:
            if t["id"] == task_id:
                if state == 2: # Checked
                    t["status"] = "done"
                    t["progress"] = 100
                else: # Unchecked
                    t["status"] = "active"
                    t["progress"] = 0
                break
        self._save_tasks()
        self.watcher.blockSignals(False)
        # Non-blocking single shot UI refresh to allow checkbox state animation to render
        from PyQt6.QtCore import QTimer as QtTimer
        QtTimer.singleShot(100, self.refresh_ui)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw translucent glassmorphic panel
        p.setPen(QPen(QColor(255, 255, 255, 20), 1.2))
        p.setBrush(QBrush(QColor(15, 23, 42, 170)))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 12.0, 12.0)

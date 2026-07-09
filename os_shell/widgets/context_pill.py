"""
os_shell/widgets/context_pill.py — Active Context Indicator Pill.
Shows current AI persona, active project, and running task count.
Sits in the top-right corner of the desktop, always visible.
"""

from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont


class ContextPill(QWidget):
    """
    Top-right pill badge showing:
      ⚡ [Persona]  |  [Project]  |  [N tasks]
    Updates every 3 seconds. Clicking it cycles personas.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._persona     = "IP Prime OS"
        self._project     = "General"
        self._task_count  = 0

        self._build_ui()

        # Refresh task count every 3s
        self._timer = QTimer(self)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self._refresh_tasks)
        self._timer.start()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        self.setStyleSheet("""
            QWidget {
                background: rgba(8, 14, 30, 0.88);
                border: 1px solid rgba(6, 182, 212, 0.35);
                border-radius: 14px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(6, 182, 212, 60))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        dot = QLabel("⚡")
        dot.setFont(QFont("Segoe UI Emoji", 9))
        dot.setStyleSheet("background: transparent; color: #06b6d4;")
        layout.addWidget(dot)

        self._persona_lbl = QLabel(self._persona)
        self._persona_lbl.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        self._persona_lbl.setStyleSheet("color: #06b6d4; background: transparent;")
        layout.addWidget(self._persona_lbl)

        sep1 = QLabel("·")
        sep1.setStyleSheet("color: rgba(255,255,255,0.25); background: transparent;")
        sep1.setFont(QFont("Outfit", 9))
        layout.addWidget(sep1)

        self._project_lbl = QLabel(self._project)
        self._project_lbl.setFont(QFont("Outfit", 9))
        self._project_lbl.setStyleSheet("color: rgba(255,255,255,0.65); background: transparent;")
        layout.addWidget(self._project_lbl)

        sep2 = QLabel("·")
        sep2.setStyleSheet("color: rgba(255,255,255,0.25); background: transparent;")
        sep2.setFont(QFont("Outfit", 9))
        layout.addWidget(sep2)

        self._tasks_lbl = QLabel("0 tasks")
        self._tasks_lbl.setFont(QFont("JetBrains Mono", 8))
        self._tasks_lbl.setStyleSheet("color: rgba(255,255,255,0.40); background: transparent;")
        layout.addWidget(self._tasks_lbl)

        self.adjustSize()

    def set_persona(self, name: str):
        self._persona = name
        self._persona_lbl.setText(name)
        self.adjustSize()

    def set_project(self, name: str):
        self._project = name
        self._project_lbl.setText(name)
        self.adjustSize()

    def set_task_count(self, count: int):
        self._task_count = count
        color = "#f59e0b" if count > 0 else "rgba(255,255,255,0.40)"
        text  = f"{count} task{'s' if count != 1 else ''} running" if count else "idle"
        self._tasks_lbl.setText(text)
        self._tasks_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        self.adjustSize()

    def _refresh_tasks(self):
        """Try to read live task count from TaskQueue."""
        try:
            from core.task_queue_manager import TaskQueue
            running = len([j for j in TaskQueue.all_jobs()
                           if getattr(j, "status", "") == "running"])
            self.set_task_count(running)
        except Exception:
            pass

    def anchor_top_right(self, parent_width: int, margin: int = 16):
        """Position this pill in the top-right corner."""
        self.adjustSize()
        x = parent_width - self.width() - margin
        self.move(x, margin)

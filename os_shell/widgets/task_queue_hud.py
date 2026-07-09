"""
os_shell/widgets/task_queue_hud.py — Background Job Queue HUD.
Shows active/queued/done background tasks in a floating panel.
Integrates with core.task_queue_manager.TaskQueue.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont


_STATUS_ICON = {
    "queued":    ("⏳", "#fbbf24"),
    "running":   ("🔄", "#06b6d4"),
    "done":      ("✅", "#10b981"),
    "failed":    ("❌", "#ef4444"),
    "cancelled": ("🚫", "#6b7280"),
}


class JobCard(QFrame):
    """Single job card in the queue list."""

    def __init__(self, job_dict: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        status = job_dict.get("status", "queued")
        icon, color = _STATUS_ICON.get(status, ("❓", "#ffffff"))

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(20)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        name_lbl = QLabel(job_dict.get("name", "Unknown Task")[:40])
        name_lbl.setFont(QFont("Outfit", 10))
        name_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        layout.addWidget(name_lbl, 1)

        status_lbl = QLabel(status.upper())
        status_lbl.setFont(QFont("JetBrains Mono", 8))
        status_lbl.setStyleSheet(
            f"color: {color}; background: rgba(255,255,255,0.05); "
            f"border: 1px solid {color}40; border-radius: 4px; padding: 2px 6px;"
        )
        layout.addWidget(status_lbl)


class TaskQueueHUD(QWidget):
    """Floating panel showing live background job queue."""
    closed = pyqtSignal()

    def __init__(self, task_queue=None, parent=None):
        super().__init__(parent)
        self._queue = task_queue
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(360)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(6, 182, 212, 80))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        self._setup_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1500)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start()

        self.hide()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget(self)
        self._container.setStyleSheet("""
            QWidget {
                background: rgba(10, 18, 35, 0.96);
                border: 1px solid rgba(6, 182, 212, 0.35);
                border-radius: 14px;
            }
        """)
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(14, 14, 14, 14)
        container_layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("⚡ Background Tasks")
        title.setFont(QFont("Outfit", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #06b6d4; background: transparent; border: none;")
        hdr.addWidget(title)
        hdr.addStretch()

        self._summary_lbl = QLabel("Idle")
        self._summary_lbl.setFont(QFont("JetBrains Mono", 8))
        self._summary_lbl.setStyleSheet("color: rgba(255,255,255,0.4); background: transparent; border: none;")
        hdr.addWidget(self._summary_lbl)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; color:rgba(255,255,255,0.35); font-size:11px; }"
            "QPushButton:hover { color:#f87171; }"
        )
        close_btn.clicked.connect(self.toggle)
        hdr.addWidget(close_btn)
        container_layout.addLayout(hdr)

        # Job list scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMaximumHeight(300)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)

        self._empty_lbl = QLabel("No background tasks running")
        self._empty_lbl.setFont(QFont("Outfit", 10))
        self._empty_lbl.setStyleSheet("color: rgba(255,255,255,0.25); background: transparent;")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_layout.addWidget(self._empty_lbl)

        self._scroll.setWidget(self._list_widget)
        container_layout.addWidget(self._scroll)

        # Footer
        footer = QHBoxLayout()
        clear_btn = QPushButton("🧹 Clear Done")
        clear_btn.setFont(QFont("Outfit", 9))
        clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                color: rgba(255,255,255,0.5);
                padding: 4px 10px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.12); color: white; }
        """)
        clear_btn.clicked.connect(self._clear_done)
        footer.addWidget(clear_btn)
        footer.addStretch()
        container_layout.addLayout(footer)

        outer.addWidget(self._container)

    def refresh(self):
        """Update the job list from the queue."""
        if not self._queue or not self.isVisible():
            return

        jobs = self._queue.all_jobs()
        # Update summary
        active = sum(1 for j in jobs if j.status.value in ("queued", "running"))
        self._summary_lbl.setText(f"{active} active" if active else "Idle")

        # Rebuild list
        for i in reversed(range(self._list_layout.count())):
            w = self._list_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        if not jobs:
            self._list_layout.addWidget(self._empty_lbl)
            self._empty_lbl.show()
        else:
            self._empty_lbl.hide()
            for job in reversed(jobs):
                card = JobCard(job.to_dict(), self._list_widget)
                self._list_layout.addWidget(card)

        # Auto-resize
        job_count = max(1, len(jobs))
        self.setFixedHeight(min(80 + job_count * 52, 420))

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.refresh()

    def _clear_done(self):
        if self._queue:
            self._queue.clear_done()
            self.refresh()

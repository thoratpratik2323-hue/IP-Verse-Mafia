"""
os_shell/widgets/file_organizer.py — Smart File Organizer.
Scans Desktop + Downloads. Shows preview of what will be moved.
Organizes into: Images, Videos, Documents, Code, Archives, Others.
Triggered by: "organize files", "clean desktop", or Command Palette.
"""

import shutil
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QFont


CATEGORIES = {
    "🖼️ Images":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"],
    "🎬 Videos":    [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
    "🎵 Audio":     [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "📄 Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".csv"],
    "💻 Code":      [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml", ".sh", ".bat", ".java", ".cpp", ".c", ".rs", ".go"],
    "🗜️ Archives":  [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
}


def _categorize(suffix: str) -> str:
    for cat, exts in CATEGORIES.items():
        if suffix.lower() in exts:
            return cat
    return "📦 Others"


def _scan_dirs() -> list[dict]:
    """Scan Desktop and Downloads for organizable files."""
    home = Path.home()
    scan_paths = [home / "Desktop", home / "Downloads"]
    files = []
    for base in scan_paths:
        if base.exists():
            for f in base.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    cat = _categorize(f.suffix)
                    files.append({"path": f, "category": cat, "source_dir": base})
    return files


class _OrganizerThread(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(int)

    def __init__(self, files: list[dict]):
        super().__init__()
        self._files = files

    def run(self):
        moved = 0
        for i, item in enumerate(self._files):
            try:
                src: Path = item["path"]
                dest_dir: Path = item["source_dir"] / item["category"].split(" ", 1)[-1]
                dest_dir.mkdir(exist_ok=True)
                dest = dest_dir / src.name
                if not dest.exists():
                    shutil.move(str(src), str(dest))
                    moved += 1
                pct = int((i + 1) / len(self._files) * 100)
                self.progress.emit(pct, src.name)
            except Exception as e:
                self.progress.emit(0, f"Error: {e}")
        self.done.emit(moved)


class FileOrganizerWidget(QWidget):
    """Glass overlay for the Smart File Organizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 520)
        self._files = []
        self._thread = None
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self._card = QWidget(self)
        self._card.setGeometry(0, 0, 480, 520)
        self._card.setStyleSheet("""
            QWidget {
                background: rgba(10, 18, 35, 0.96);
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 18px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(245, 158, 11, 80))
        shadow.setOffset(0, 6)
        self._card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("🗂️ Smart File Organizer")
        title.setFont(QFont("Outfit", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #f59e0b; background: transparent; border: none;")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("QPushButton { background:transparent; border:none; color:rgba(255,255,255,0.5); font-size:16px; } QPushButton:hover { color:#f87171; }")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # Scan info
        self._info_lbl = QLabel("Scans: Desktop + Downloads")
        self._info_lbl.setFont(QFont("Outfit", 10))
        self._info_lbl.setStyleSheet("color: rgba(255,255,255,0.5); background: transparent; border: none;")
        layout.addWidget(self._info_lbl)

        # File list
        self._list = QListWidget()
        self._list.setFont(QFont("Outfit", 10))
        self._list.setStyleSheet("""
            QListWidget { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; color: #f8fafc; outline: none; }
            QListWidget::item { padding: 6px 10px; border-radius: 6px; }
            QListWidget::item:selected { background: rgba(245,158,11,0.2); }
        """)
        layout.addWidget(self._list)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.08); border-radius: 3px; border: none; }
            QProgressBar::chunk { background: #f59e0b; border-radius: 3px; }
        """)
        self._progress.hide()
        layout.addWidget(self._progress)

        # Status label
        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont("Outfit", 9))
        self._status_lbl.setStyleSheet("color: rgba(255,255,255,0.5); background: transparent; border: none;")
        layout.addWidget(self._status_lbl)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._scan_btn = QPushButton("🔍 Scan")
        self._organize_btn = QPushButton("✅ Organize Now")
        self._organize_btn.setEnabled(False)

        for btn in [self._scan_btn, self._organize_btn]:
            btn.setFont(QFont("Outfit", 11, QFont.Weight.Medium))
            btn.setFixedHeight(38)
            btn_row.addWidget(btn)

        self._scan_btn.setStyleSheet("""
            QPushButton { background: rgba(6,182,212,0.15); border: 1px solid rgba(6,182,212,0.4);
                border-radius: 10px; color: #06b6d4; }
            QPushButton:hover { background: rgba(6,182,212,0.28); }
        """)
        self._organize_btn.setStyleSheet("""
            QPushButton { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.4);
                border-radius: 10px; color: #f59e0b; }
            QPushButton:hover { background: rgba(245,158,11,0.28); }
            QPushButton:disabled { opacity: 0.4; }
        """)

        self._scan_btn.clicked.connect(self._do_scan)
        self._organize_btn.clicked.connect(self._do_organize)
        layout.addLayout(btn_row)

    def _do_scan(self):
        self._list.clear()
        self._status_lbl.setText("Scanning…")
        self._files = _scan_dirs()
        cat_counts: dict[str, int] = {}
        for item in self._files:
            cat = item["category"]
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for cat, count in sorted(cat_counts.items()):
            it = QListWidgetItem(f"{cat}  —  {count} file{'s' if count > 1 else ''}")
            self._list.addItem(it)
        self._status_lbl.setText(f"Found {len(self._files)} files to organize")
        self._organize_btn.setEnabled(len(self._files) > 0)

    def _do_organize(self):
        if not self._files:
            return
        self._organize_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self._progress.show()
        self._progress.setValue(0)
        self._thread = _OrganizerThread(self._files)
        self._thread.progress.connect(self._on_progress)
        self._thread.done.connect(self._on_done)
        self._thread.start()

    def _on_progress(self, pct: int, name: str):
        self._progress.setValue(pct)
        self._status_lbl.setText(f"Moving: {name[:40]}…")

    def _on_done(self, moved: int):
        self._progress.setValue(100)
        self._status_lbl.setText(f"✅ Done! Moved {moved} files.")
        self._scan_btn.setEnabled(True)
        self._files = []
        self._organize_btn.setEnabled(False)

    def open(self):
        if self.parent():
            p = self.parent()
            self.move((p.width() - self.width()) // 2, (p.height() - self.height()) // 2)
        self.show()
        self.raise_()
        self._do_scan()

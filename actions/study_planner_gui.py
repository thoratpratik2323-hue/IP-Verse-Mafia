import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QCheckBox, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from actions.study_planner import generate_study_plan, load_study_plan, save_study_plan

class StudyPlannerPanel(QDialog):
    plan_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(480, 520)
        self.plan_ready.connect(self._on_plan_ready)
        self._init_ui()

    def _init_ui(self):
        container = QWidget(self)
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container {
                background: rgba(15, 23, 42, 0.95);
                border: 2px solid rgba(59, 130, 246, 0.4);
                border-radius: 18px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Title block
        title_lay = QHBoxLayout()
        title_lbl = QLabel("STUDY PLANNER 📅")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #3B82F6; letter-spacing: 0.5px; background: transparent;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.3);
                border: 1px solid #EF4444;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        title_lay.addWidget(title_lbl)
        title_lay.addStretch()
        title_lay.addWidget(close_btn)
        layout.addLayout(title_lay)

        # Topic & Date Inputs
        input_lay = QVBoxLayout()
        input_lay.setSpacing(8)
        
        self.topics_input = QLineEdit()
        self.topics_input.setPlaceholderText("Enter topics (e.g. System Design, OS, Network)")
        self.topics_input.setStyleSheet("""
            QLineEdit {
                background: rgba(5, 5, 10, 0.6);
                border: 1px solid rgba(59, 130, 246, 0.25);
                border-radius: 8px;
                color: #F1F5F9;
                font-size: 10px;
                padding: 6px;
            }
        """)
        input_lay.addWidget(self.topics_input)
        
        date_lay = QHBoxLayout()
        date_lbl = QLabel("Exam Date (YYYY-MM-DD):")
        date_lbl.setFont(QFont("Segoe UI", 8))
        date_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("2026-06-15")
        self.date_input.setStyleSheet("""
            QLineEdit {
                background: rgba(5, 5, 10, 0.6);
                border: 1px solid rgba(59, 130, 246, 0.25);
                border-radius: 8px;
                color: #F1F5F9;
                font-size: 10px;
                padding: 6px;
                max-width: 120px;
            }
        """)
        
        date_lay.addWidget(date_lbl)
        date_lay.addWidget(self.date_input)
        input_lay.addLayout(date_lay)
        layout.addLayout(input_lay)

        # Generate Button
        gen_btn = QPushButton("GENERATE DAY-WISE STUDY PLAN")
        gen_btn.setFixedHeight(36)
        gen_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.15);
                color: #3B82F6;
                border: 1px solid rgba(59, 130, 246, 0.4);
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.3);
                border: 1px solid #3B82F6;
            }
        """)
        gen_btn.clicked.connect(self._generate_plan)
        layout.addWidget(gen_btn)

        # Scroll Area for plan checklist
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background: rgba(5, 5, 10, 0.6);
                border: 1px solid rgba(59, 130, 246, 0.15);
                border-radius: 10px;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        # Full layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
        
        self._load_active_plan()

    def _generate_plan(self):
        topics = self.topics_input.text()
        exam_date = self.date_input.text()
        if not topics or not exam_date:
            return
            
        # Clear checklist
        self._clear_layout(self.scroll_layout)
        loading_lbl = QLabel("Creating plan... Please wait, bhai!")
        loading_lbl.setStyleSheet("color: #3B82F6;")
        self.scroll_layout.insertWidget(0, loading_lbl)
        
        def run_bg():
            res = generate_study_plan(topics, exam_date, self.parent())
            self.plan_ready.emit(res)
            
        threading.Thread(target=run_bg, daemon=True).start()

    def _on_plan_ready(self, msg):
        self._load_active_plan()
        parent = self.parent()
        if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
            parent.ip_ray.speak("Aapka dynamic day-wise study schedule set kar diya hai, bhai!")

    def _load_active_plan(self):
        self._clear_layout(self.scroll_layout)
        plan = load_study_plan()
        if not plan:
            lbl = QLabel("No active study plan. Generate one above!")
            lbl.setStyleSheet("color: #64748B; font-style: italic;")
            self.scroll_layout.insertWidget(0, lbl)
            self.scroll_layout.addStretch()
            return
            
        schedule = plan.get("schedule", [])
        for idx, day in enumerate(schedule):
            cb = QCheckBox(f"{day.get('date')} | {day.get('topic')}\n» {day.get('task')}")
            cb.setFont(QFont("Segoe UI", 8))
            cb.setStyleSheet("""
                QCheckBox {
                    color: #E2E8F0;
                    spacing: 8px;
                    padding: 4px;
                }
                QCheckBox::indicator {
                    width: 14px; height: 14px;
                }
            """)
            cb.setChecked(day.get("completed", False))
            # Wire checkbox change event
            cb.stateChanged.connect(lambda state, i=idx: self._toggle_task(i, state))
            self.scroll_layout.insertWidget(idx, cb)
            
        self.scroll_layout.addStretch()

    def _toggle_task(self, idx, state):
        plan = load_study_plan()
        if plan:
            schedule = plan.get("schedule", [])
            if 0 <= idx < len(schedule):
                schedule[idx]["completed"] = (state == 2)  # Qt.CheckState.Checked is 2
                plan["schedule"] = schedule
                save_study_plan(plan)

    def _clear_layout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

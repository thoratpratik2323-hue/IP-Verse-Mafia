"""
actions/viva_gui.py — Custom interactive PyQt6 widget for the Voice Viva Technical Prep Examiner.

This is a premium action module for the IP Prime personal assistant suite.
"""

import time
import threading
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QComboBox, QTextEdit, QScrollArea
)
from PyQt6.QtGui import QFont
from actions.viva_prep import VivaExaminer

PANEL_DARK = "rgba(4, 7, 14, 0.95)"
BORDER_COLOR = "rgba(16, 185, 129, 0.45)"  # Emerald green vibe for exams
TEXT_MED = "#E2E8F0"

class VivaPanel(QFrame):
    """Floating glassmorphic Viva Prep mock examiner panel."""
    
    # Signals to communicate with the main live loop
    viva_started = pyqtSignal(str) # topic
    viva_ended = pyqtSignal()
    q_generated = pyqtSignal(str)
    scorecard_done = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(540, 420)
        self.setStyleSheet(
            f"background: {PANEL_DARK};"
            f"border: 2px solid {BORDER_COLOR};"
            f"border-radius: 16px;"
        )
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        
        self.examiner = None
        self.is_active = False
        self.topic = "Python Basics"
        
        # Connect internal signals for safe threading UI updates
        self.q_generated.connect(self.on_q_generated)
        self.scorecard_done.connect(self.on_scorecard_done)
        
        # Setup Layout
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 16, 16, 16)
        self.lay.setSpacing(12)
        
        # Title bar
        title_lay = QHBoxLayout()
        self.title_lbl = QLabel("🏆 VIVA VOICE EXAMINER")
        self.title_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #10B981; background: transparent; border: none;")
        title_lay.addWidget(self.title_lbl)
        title_lay.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet(
            "background: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid #EF4444; border-radius: 12px;"
        )
        self.close_btn.clicked.connect(self.hide)
        title_lay.addWidget(self.close_btn)
        self.lay.addLayout(title_lay)
        
        # Build Setup Page & Exam Page in a dynamic layout switching
        self.setup_widget = QWidget()
        self.setup_lay = QVBoxLayout(self.setup_widget)
        self.setup_lay.setContentsMargins(0, 0, 0, 0)
        self.setup_lay.setSpacing(15)
        
        desc = QLabel(
            "Prepare for your technical interviews & viva! Our AI Examiner will ask "
            "conceptual questions verbally. Speak your answer or type it to get dynamic buddy grading."
        )
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        desc.setWordWrap(True)
        self.setup_lay.addWidget(desc)
        
        topic_lay = QHBoxLayout()
        topic_lbl = QLabel("Select Topic:")
        topic_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        topic_lbl.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
        topic_lay.addWidget(topic_lbl)
        
        self.topic_combo = QComboBox()
        self.topic_combo.addItems(["Python Basics", "Algorithms & DS", "Web Development", "Git & GitHub"])
        self.topic_combo.setStyleSheet(
            "QComboBox { background: rgba(30, 41, 59, 0.5); color: #E2E8F0; border: 1px solid rgba(16, 185, 129, 0.3); "
            "border-radius: 6px; padding: 4px 8px; } QComboBox::drop-down { border: none; }"
        )
        topic_lay.addWidget(self.topic_combo)
        self.setup_lay.addLayout(topic_lay)
        
        self.start_btn = QPushButton("🚀 Start Viva Session")
        self.start_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.start_btn.setStyleSheet(
            "background: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid #10B981; "
            "border-radius: 8px; padding: 8px;"
        )
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_viva)
        self.setup_lay.addWidget(self.start_btn)
        
        self.lay.addWidget(self.setup_widget)
        
        # Exam Widget
        self.exam_widget = QWidget()
        self.exam_lay = QVBoxLayout(self.exam_widget)
        self.exam_lay.setContentsMargins(0, 0, 0, 0)
        self.exam_lay.setSpacing(10)
        self.exam_widget.hide()
        
        self.status_lbl = QLabel("Question 1 of 3")
        self.status_lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color: #34D399; background: transparent; border: none;")
        self.exam_lay.addWidget(self.status_lbl)
        
        self.question_lbl = QLabel("Generating technical question...")
        self.question_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.question_lbl.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
        self.question_lbl.setWordWrap(True)
        self.exam_lay.addWidget(self.question_lbl)
        
        self.ans_input = QTextEdit()
        self.ans_input.setPlaceholderText("Type your answer here, or click the mic to speak to Gemini Live...")
        self.ans_input.setStyleSheet(
            "QTextEdit { background: rgba(15, 23, 42, 0.6); color: #E2E8F0; border: 1px solid rgba(16, 185, 129, 0.2); "
            "border-radius: 8px; padding: 8px; }"
        )
        self.exam_lay.addWidget(self.ans_input)
        
        actions_lay = QHBoxLayout()
        self.voice_indicator = QLabel("🎤 MIC READY (Speak to answer)")
        self.voice_indicator.setFont(QFont("Consolas", 8))
        self.voice_indicator.setStyleSheet("color: #64748B; background: transparent; border: none;")
        actions_lay.addWidget(self.voice_indicator)
        actions_lay.addStretch()
        
        self.submit_btn = QPushButton("Submit Answer ↳")
        self.submit_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.submit_btn.setStyleSheet(
            "background: rgba(16, 185, 129, 0.25); color: #34D399; border: 1px solid #34D399; "
            "border-radius: 6px; padding: 6px 12px;"
        )
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.clicked.connect(self.submit_answer)
        actions_lay.addWidget(self.submit_btn)
        
        self.exam_lay.addLayout(actions_lay)
        
        self.feedback_lbl = QLabel("")
        self.feedback_lbl.setFont(QFont("Segoe UI", 9))
        self.feedback_lbl.setStyleSheet("color: #F59E0B; background: transparent; border: none;")
        self.feedback_lbl.setWordWrap(True)
        self.exam_lay.addWidget(self.feedback_lbl)
        
        self.lay.addWidget(self.exam_widget)
        
        # Report Widget
        self.report_widget = QWidget()
        self.report_lay = QVBoxLayout(self.report_widget)
        self.report_lay.setContentsMargins(0, 0, 0, 0)
        self.report_lay.setSpacing(10)
        self.report_widget.hide()
        
        self.score_lbl = QLabel("🏆 Final Score: 85/100")
        self.score_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.score_lbl.setStyleSheet("color: #10B981; background: transparent; border: none;")
        self.score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.report_lay.addWidget(self.score_lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid rgba(16, 185, 129, 0.15); border-radius: 8px; background: transparent; }")
        
        self.report_content = QLabel("Detailed scorecard saved in your Second Brain!")
        self.report_content.setFont(QFont("Segoe UI", 9))
        self.report_content.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
        self.report_content.setWordWrap(True)
        scroll.setWidget(self.report_content)
        self.report_lay.addWidget(scroll)
        
        self.done_btn = QPushButton("Finish & Save Checklist")
        self.done_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.done_btn.setStyleSheet(
            "background: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid #10B981; "
            "border-radius: 8px; padding: 8px;"
        )
        self.done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done_btn.clicked.connect(self.finish_viva)
        self.report_lay.addWidget(self.done_btn)
        
        self.lay.addWidget(self.report_widget)

    def start_viva(self):
        self.topic = self.topic_combo.currentText()
        self.examiner = VivaExaminer(topic=self.topic)
        self.is_active = True
        
        # Switch screens
        self.setup_widget.hide()
        self.exam_widget.show()
        self.report_widget.hide()
        
        self.viva_started.emit(self.topic)
        
        # Generate first question
        self.next_question()
        
    def next_question(self):
        if self.examiner.current_q_idx < self.examiner.total_questions:
            self.status_lbl.setText(f"Question {self.examiner.current_q_idx + 1} of {self.examiner.total_questions}")
            
            # Start question in a separate thread so Gemini doesn't freeze the GUI
            self.submit_btn.setEnabled(False)
            self.question_lbl.setText("Generating technical question...")
            
            def run_gen():
                q = self.examiner.generate_question()
                self.q_generated.emit(q)
                        
            threading.Thread(target=run_gen, daemon=True).start()
        else:
            self.show_scorecard()

    def on_q_generated(self, q: str):
        self.question_lbl.setText(q)
        self.ans_input.clear()
        self.submit_btn.setEnabled(True)
        
        # Vocalize question via main live loop hook
        parent = self.parent()
        if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
            parent.ip_ray.speak(q)

    def submit_answer(self, user_ans: str = ""):
        if not user_ans:
            user_ans = self.ans_input.toPlainText().strip()
            
        if not user_ans:
            self.feedback_lbl.setText("Sir, please enter or speak an answer first!")
            return
            
        self.submit_btn.setEnabled(False)
        self.feedback_lbl.setText("AI Examiner is grading your answer...")
        
        def run_grade():
            res = self.examiner.grade_answer(user_ans)
            
            # Vocalize examiner feedback
            parent = self.parent()
            if parent and hasattr(parent, "ip_ray") and parent.ip_ray:
                parent.ip_ray.speak(f"{res.get('feedback', '')}. Scorecard update logged.")
                
            def gui_done():
                self.feedback_lbl.setText(f"Grade: {res.get('grade', 0)}/100\nFeedback: {res.get('feedback', '')}")
                time.sleep(2.5)  # Let user read it
                self.next_question()
                
            threading.Thread(target=gui_done, daemon=True).start()
            
        threading.Thread(target=run_grade, daemon=True).start()

    def show_scorecard(self):
        self.is_active = False
        self.exam_widget.hide()
        self.report_widget.show()
        
        final_score = int(self.examiner.score / self.examiner.total_questions) if self.examiner.total_questions else 0
        self.score_lbl.setText(f"🏆 Final Score: {final_score}/100")
        
        # Save to file
        self.report_content.setText("Generating final roadmap assessment scorecard...")
        
        def run_scorecard():
            scorecard = self.examiner.generate_scorecard()
            self.scorecard_done.emit(scorecard)
            
        threading.Thread(target=run_scorecard, daemon=True).start()

    def on_scorecard_done(self, scorecard: str):
        final_score = int(self.examiner.score / self.examiner.total_questions) if self.examiner.total_questions else 0
        summary = "Congratulations Pratik Sir!\n\nYour exam details:\n"
        for i, turn in enumerate(self.examiner.history, 1):
            summary += f"• Q{i}: {turn['q'][:50]}... ({turn['grade']}/100)\n"
        summary += "\nFull AI report and CS study roadmap saved to c:/Users/thora/Documents/SecondBrain/viva_scorecard.md"
        self.report_content.setText(summary)

    def finish_viva(self):
        # Auto-tick CS Roadmap habit
        try:
            from actions.habits_engine import check_study_habit
            check_study_habit()
        except Exception:
            pass
            
        self.exam_widget.hide()
        self.report_widget.hide()
        self.setup_widget.show()
        self.hide()
        self.viva_ended.emit()

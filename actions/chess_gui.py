"""
chess_gui.py — PyQt6 HUD Chess Board Overlay for IP Prime

Features:
- Interactive chess board with piece highlighting
- Threaded AI calculation for smooth UI
- Move history with algebraic notation
- Game statistics and difficulty adjustment
- Hinglish commentary system
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QComboBox, QTextEdit, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush
import chess
import threading
from typing import Optional
from actions.chess_partner import get_ai_move, generate_hinglish_commentary, get_game_stats

# Unicode chess pieces mapping
PIECE_UNICODE = {
    'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚',
    'p': '♙', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔'
}


class AIWorker(QThread):
    """Worker thread for AI move calculation to prevent UI freezing."""
    move_ready = pyqtSignal(chess.Move, str)  # Emits (move, commentary)
    error_occurred = pyqtSignal(str)

    def __init__(self, board: chess.Board, difficulty: str):
        super().__init__()
        self.board = board.copy()
        self.difficulty = difficulty

    def run(self):
        """Run the AI calculation in a separate thread."""
        try:
            ai_move = get_ai_move(self.board, self.difficulty, time_limit=3.0)
            comment = generate_hinglish_commentary(self.board, ai_move)
            self.move_ready.emit(ai_move, comment)
        except Exception as e:
            self.error_occurred.emit(f"AI Error: {str(e)}")

class ChessBoardWidget(QWidget):
    move_played = pyqtSignal(str) # Emits UCI move string like "e2e4"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.board: chess.Board = chess.Board()
        self.selected_square: Optional[int] = None
        self.highlighted_squares: list[int] = []
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_user_turn: bool = True

    def set_board(self, board: chess.Board) -> None:
        """Update the board and reset highlighting."""
        self.board = board
        self.selected_square = None
        self.highlighted_squares = []
        self.update()

    def set_user_turn(self, turn: bool) -> None:
        """Enable/disable user input."""
        self.is_user_turn = turn
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        sq_size = min(width, height) // 8

        # Offset to center the board if needed
        offset_x = (width - sq_size * 8) // 2
        offset_y = (height - sq_size * 8) // 2

        # Draw grid
        for row in range(8):
            for col in range(8):
                x = offset_x + col * sq_size
                y = offset_y + row * sq_size

                # Square colors: cobalt cyber theme
                is_light = (row + col) % 2 == 0
                if is_light:
                    brush = QBrush(QColor(15, 23, 42, 230)) # Dark slate-blue
                else:
                    brush = QBrush(QColor(30, 41, 59, 180)) # Slightly lighter slate

                painter.fillRect(x, y, sq_size, sq_size, brush)
                
                # Draw subtle grid lines
                painter.setPen(QPen(QColor(6, 182, 212, 30), 1))
                painter.drawRect(x, y, sq_size, sq_size)

        # Highlight selected square
        if self.selected_square is not None:
            col = chess.square_file(self.selected_square)
            row = 7 - chess.square_rank(self.selected_square)
            x = offset_x + col * sq_size
            y = offset_y + row * sq_size
            painter.setPen(QPen(QColor(16, 185, 129, 220), 2)) # Glowing green border
            painter.setBrush(QBrush(QColor(16, 185, 129, 40)))
            painter.drawRect(x, y, sq_size, sq_size)

        # Highlight legal moves destination squares
        for sq in self.highlighted_squares:
            col = chess.square_file(sq)
            row = 7 - chess.square_rank(sq)
            x = offset_x + col * sq_size + sq_size // 2
            y = offset_y + row * sq_size + sq_size // 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(39, 200, 245, 150))) # Cyan dot
            painter.drawEllipse(x - 6, y - 6, 12, 12)

        # Draw pieces
        font = QFont("Segoe UI Symbol", 28)
        font.setBold(True)
        painter.setFont(font)

        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece:
                col = chess.square_file(sq)
                row = 7 - chess.square_rank(sq)
                x = offset_x + col * sq_size
                y = offset_y + row * sq_size

                symbol = PIECE_UNICODE.get(piece.symbol())
                if symbol:
                    # White pieces: glowing Cyan/White
                    if piece.color == chess.WHITE:
                        painter.setPen(QColor(39, 200, 245)) # Cyan
                    # Black pieces: soft neon Purple/Rose
                    else:
                        painter.setPen(QColor(244, 63, 94)) # Rose/Purple
                    
                    painter.drawText(x, y, sq_size, sq_size, Qt.AlignmentFlag.AlignCenter, symbol)

    def mousePressEvent(self, event):
        if not self.is_user_turn:
            return

        width = self.width()
        height = self.height()
        sq_size = min(width, height) // 8
        offset_x = (width - sq_size * 8) // 2
        offset_y = (height - sq_size * 8) // 2

        pos = event.position()
        col = int((pos.x() - offset_x) // sq_size)
        row = int((pos.y() - offset_y) // sq_size)

        if 0 <= col < 8 and 0 <= row < 8:
            clicked_sq = chess.square(col, 7 - row)
            
            # If a square was already selected and clicked square is in legal destinations
            if self.selected_square is not None and clicked_sq in self.highlighted_squares:
                # Find the legal move
                move = None
                # Check normal move or promotion
                for m in self.board.legal_moves:
                    if m.from_square == self.selected_square and m.to_square == clicked_sq:
                        move = m
                        break
                
                if move:
                    self.move_played.emit(move.uci())
                    self.selected_square = None
                    self.highlighted_squares = []
                    self.update()
                    return

            # Otherwise, select white pieces
            piece = self.board.piece_at(clicked_sq)
            if piece and piece.color == chess.WHITE:
                self.selected_square = clicked_sq
                # Generate legal destination squares for this piece
                self.highlighted_squares = [
                    m.to_square for m in self.board.legal_moves 
                    if m.from_square == clicked_sq
                ]
            else:
                self.selected_square = None
                self.highlighted_squares = []
                
            self.update()


class ChessPanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(800, 500)

        self.board: chess.Board = chess.Board()
        self.difficulty: str = "Medium"
        self.ai_worker: Optional[AIWorker] = None
        self.move_history: list[str] = []
        self._init_ui()

    def _init_ui(self):
        container = QWidget(self)
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container {
                background: rgba(10, 15, 30, 0.96);
                border: 2px solid rgba(39, 200, 245, 0.4);
                border-radius: 18px;
            }
        """)

        # Main Layout
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Header Section
        header = QHBoxLayout()
        title = QLabel("CHESS PARTNER ⚔️")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #27C8F5; letter-spacing: 0.5px; background: transparent;")

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

        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Content Section (Board on left, Logs/Controls on right)
        content = QHBoxLayout()
        content.setSpacing(15)

        # Left Column: Chess Board
        self.board_widget = ChessBoardWidget(self)
        self.board_widget.setFixedSize(380, 380)
        self.board_widget.move_played.connect(self._on_user_move)
        content.addWidget(self.board_widget)

        # Right Column: Side Info Panel
        side_panel = QVBoxLayout()
        side_panel.setSpacing(10)

        # Turn info
        self.turn_lbl = QLabel("Your Turn (White)")
        self.turn_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.turn_lbl.setStyleSheet("color: #10B981; background: transparent;")
        side_panel.addWidget(self.turn_lbl)

        # Game Stats
        self.stats_lbl = QLabel("Move: 0 | Material: W8 vs B8")
        self.stats_lbl.setFont(QFont("Segoe UI", 8))
        self.stats_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        side_panel.addWidget(self.stats_lbl)

        # Commentary & Logs Log
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setFont(QFont("Consolas", 9))
        self.log_widget.setStyleSheet("""
            QTextEdit {
                background: rgba(5, 10, 20, 0.7);
                border: 1px solid rgba(6, 182, 212, 0.25);
                border-radius: 8px;
                color: #E2E8F0;
                padding: 6px;
            }
        """)
        self.log_widget.append("Welcome Pratik Sir! White plays first.")
        side_panel.addWidget(self.log_widget)

        # Controls (Difficulty & Reset)
        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.diff_box = QComboBox()
        self.diff_box.addItems(["Easy", "Medium", "Hard"])
        self.diff_box.setCurrentText("Medium")
        self.diff_box.setCursor(Qt.CursorShape.PointingHandCursor)
        self.diff_box.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: #F8FAFC;
                padding: 4px 10px;
            }
            QComboBox::drop-down { border: none; }
        """)
        self.diff_box.currentTextChanged.connect(self._on_diff_changed)

        new_game_btn = QPushButton("NEW GAME 🔄")
        new_game_btn.setFixedHeight(30)
        new_game_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        new_game_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_game_btn.setStyleSheet("""
            QPushButton {
                background: rgba(39, 200, 245, 0.15);
                color: #27C8F5;
                border: 1px solid rgba(39, 200, 245, 0.35);
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(39, 200, 245, 0.3);
                border: 1px solid #27C8F5;
            }
        """)
        new_game_btn.clicked.connect(self._restart_game)

        controls.addWidget(self.diff_box)
        controls.addWidget(new_game_btn)
        side_panel.addLayout(controls)

        content.addLayout(side_panel)
        layout.addLayout(content)

        # Main window placement layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def _on_diff_changed(self, text: str) -> None:
        self.difficulty = text
        self.log_widget.append(f"<font color='#94A3B8'>SYS: Difficulty changed to {text}.</font>")

    def _restart_game(self) -> None:
        """Reset the board and start a new game."""
        # Kill any running AI worker
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.quit()
            self.ai_worker.wait()
        
        self.board = chess.Board()
        self.move_history = []
        self.board_widget.set_board(self.board)
        self.board_widget.set_user_turn(True)
        self.turn_lbl.setText("Your Turn (White)")
        self.turn_lbl.setStyleSheet("color: #10B981; background: transparent;")
        self.log_widget.clear()
        self.log_widget.append("<font color='#27C8F5'><b>Welcome Pratik Sir! White plays first.</b></font>")
        self._update_stats()

    def _on_user_move(self, uci_move: str) -> None:
        """Handle user move."""
        try:
            move = chess.Move.from_uci(uci_move)
            
            # Generate commentary
            comment = generate_hinglish_commentary(self.board, move)
            san_move = self.board.san(move)
            self.move_history.append(f"{len(self.move_history)//2 + 1}. {san_move}")
            
            self.log_widget.append(f"<b style='color: #27C8F5'>You:</b> {uci_move} ({san_move})")
            self.log_widget.append(f"<font color='#e0a82e'><i>Buddy: {comment}</i></font>")
            
            self.board.push(move)
            self.board_widget.set_board(self.board)

            if self.board.is_game_over():
                self._handle_game_over()
                return

            # Start AI move in background thread
            self.board_widget.set_user_turn(False)
            self.turn_lbl.setText("IP Prime Thinking...")
            self.turn_lbl.setStyleSheet("color: #F59E0B; background: transparent;")
            
            self.ai_worker = AIWorker(self.board, self.difficulty)
            self.ai_worker.move_ready.connect(self._on_ai_move_ready)
            self.ai_worker.error_occurred.connect(self._on_ai_error)
            self.ai_worker.start()
            
        except Exception as e:
            self.log_widget.append(f"<font color='#EF4444'>Error: {str(e)}</font>")

    @pyqtSlot(chess.Move, str)
    def _on_ai_move_ready(self, ai_move: chess.Move, comment: str) -> None:
        """Handle AI move completion."""
        try:
            san_move = self.board.san(ai_move)
            self.move_history.append(san_move)
            
            self.log_widget.append(f"<b style='color: #EC4899'>Buddy:</b> {ai_move.uci()} ({san_move})")
            self.log_widget.append(f"<font color='#e0a82e'><i>{comment}</i></font>")
            
            # Speak comment if parent has ip_ray for speak function
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, "ip_ray") and parent_win.ip_ray:
                clean_comment = comment.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
                parent_win.ip_ray.speak(clean_comment)

            self.board.push(ai_move)
            self.board_widget.set_board(self.board)
            self._update_stats()
        except Exception as e:
            self.log_widget.append(f"<font color='#EF4444'>Error processing AI move: {str(e)}</font>")

        if self.board.is_game_over():
            self._handle_game_over()
            return

        self.board_widget.set_user_turn(True)
        self.turn_lbl.setText("Your Turn (White)")
        self.turn_lbl.setStyleSheet("color: #10B981; background: transparent;")

    @pyqtSlot(str)
    def _on_ai_error(self, error_msg: str) -> None:
        """Handle AI error."""
        self.log_widget.append(f"<font color='#EF4444'>{error_msg}</font>")
        self.board_widget.set_user_turn(True)
        self.turn_lbl.setText("Your Turn (White)")
        self.turn_lbl.setStyleSheet("color: #10B981; background: transparent;")

    def _handle_game_over(self) -> None:
        """Handle end of game scenarios."""
        result = "Game Over!"
        if self.board.is_checkmate():
            if self.board.turn == chess.WHITE:
                result = "🎉 Buddy Wins! Checkmate."
                self.turn_lbl.setStyleSheet("color: #EC4899; background: transparent;")
            else:
                result = "🏆 Pratik Sir Wins! Checkmate."
                self.turn_lbl.setStyleSheet("color: #10B981; background: transparent;")
        elif self.board.is_stalemate():
            result = "⚔️ Draw! Stalemate."
            self.turn_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        elif self.board.is_insufficient_material():
            result = "⚔️ Draw! Insufficient material."
            self.turn_lbl.setStyleSheet("color: #94A3B8; background: transparent;")

        self.turn_lbl.setText(result)
        self.log_widget.append(f"<b style='color: #F59E0B'>{result}</b>")
        self.board_widget.set_user_turn(False)

    def _update_stats(self) -> None:
        """Update game statistics display."""
        stats = get_game_stats(self.board)
        info = f"Move: {stats['move_count']} | Material: W{stats['white_material']} vs B{stats['black_material']}"
        self.stats_lbl.setText(info)

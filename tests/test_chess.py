import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import chess

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from actions.chess_partner import (
    evaluate_board, minimax, get_ai_move, 
    generate_hinglish_commentary, get_game_stats
)
from actions.chess_gui import AIWorker, ChessBoardWidget, ChessPanel

class TestChessPartner(unittest.TestCase):

    def setUp(self):
        self.board = chess.Board()

    def test_evaluate_board(self):
        # Initial board evaluation should be close to 0 (equal)
        eval_score = evaluate_board(self.board)
        self.assertIsInstance(eval_score, int)
        
        # Checkmate white should be extremely negative for white
        checkmate_board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        self.assertTrue(checkmate_board.is_checkmate())
        self.assertEqual(evaluate_board(checkmate_board), -99999)

    def test_minimax_and_ai_move(self):
        # AI move should be a valid legal move
        move = get_ai_move(self.board, difficulty="Easy", time_limit=1.0)
        self.assertIn(move, self.board.legal_moves)
        
        # Medium difficulty
        move_med = get_ai_move(self.board, difficulty="Medium", time_limit=1.0)
        self.assertIn(move_med, self.board.legal_moves)

    def test_commentary_generation(self):
        # Standard first moves
        move = chess.Move.from_uci("e2e4")
        comment = generate_hinglish_commentary(self.board, move)
        self.assertIsInstance(comment, str)
        self.assertTrue(len(comment) > 0)

    def test_game_stats(self):
        stats = get_game_stats(self.board)
        self.assertEqual(stats["white_material"], 15)
        self.assertEqual(stats["black_material"], 15)
        self.assertEqual(stats["move_count"], 0)

    @patch("actions.chess_gui.AIWorker.start")
    def test_gui_components(self, mock_start):
        # Initialize PyQt Application
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])

        # Test widget initialization
        board_widget = ChessBoardWidget()
        self.assertIsNotNone(board_widget.board)
        self.assertTrue(board_widget.is_user_turn)

        # Test setting board
        new_board = chess.Board()
        board_widget.set_board(new_board)
        self.assertEqual(board_widget.board, new_board)

        # Test ChessPanel dialog
        panel = ChessPanel()
        self.assertEqual(panel.difficulty, "Medium")
        self.assertIsNotNone(panel.board_widget)
        
        # Test difficulty changed slot
        panel._on_diff_changed("Hard")
        self.assertEqual(panel.difficulty, "Hard")
        
        # Test restart game
        panel._restart_game()
        self.assertEqual(panel.difficulty, "Hard")
        self.assertEqual(len(panel.move_history), 0)

        # Test user move trigger (e2e4 is legal for White from starting board)
        panel._on_user_move("e2e4")
        self.assertEqual(panel.board.piece_at(chess.E4).symbol(), "P")

if __name__ == "__main__":
    unittest.main()

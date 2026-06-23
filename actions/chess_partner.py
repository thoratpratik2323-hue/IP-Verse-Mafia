"""
chess_partner.py — IP Prime Chess Partner Engine & AI

Provides Minimax search with Alpha-Beta pruning, transposition tables,
board evaluation, and contextual Hinglish commentary.

Features:
- Alpha-beta pruning with transposition table maching
- Positional piece tables for better evaluation
- Move ordering optimization (captures, checks first)
- Difficulty-based search depth
- Hinglish commentary system
"""

import chess
import random
import time
from typing import Optional, Tuple, Dict
from collections import defaultdict

# Piece values
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Positional tables (from white perspective, reversed for black)
PAWN_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

ROOK_TABLE = [
      0,  0,  0,  0,  0,  0,  0,  0,
      5, 10, 10, 10, 10, 10, 10,  5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
      0,  0,  0,  5,  5,  0,  0,  0
]

QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  5,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

KING_TABLE = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]


# Transposition Table for memoization
class TranspositionTable:
    """Stores board evaluations to avoid re-evaluating identical positions."""
    
    def __init__(self):
        self.table: Dict[str, Tuple[int, int, int]] = {}  # hash -> (eval, depth, flag)
    
    def store(self, board_hash: str, eval_score: int, depth: int, flag: int):
        """Store evaluation. flag: 0=lower, 1=exact, 2=upper"""
        if board_hash not in self.table or self.table[board_hash][1] < depth:
            self.table[board_hash] = (eval_score, depth, flag)
    
    def lookup(self, board_hash: str, depth: int) -> Optional[int]:
        """Retrieve evaluation if available."""
        if board_hash in self.table:
            stored_eval, stored_depth, _ = self.table[board_hash]
            if stored_depth >= depth:
                return stored_eval
        return None
    
    def clear(self):
        """Clear the table."""
        self.table.clear()
    
    def size(self) -> int:
        return len(self.table)


# Global transposition table instance
TRANSPOSITION_TABLE = TranspositionTable()



def evaluate_board(board: chess.Board) -> int:
    """
    Evaluates board from White's perspective (positive for White, negative for Black).
    Includes material, positional bonuses, piece mobility, and endgame evaluations.
    """
    if board.is_checkmate():
        return -99999 if board.turn == chess.WHITE else 99999
    
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    
    # Material + Positional evaluation
    for sq in board.pieces(chess.PAWN, chess.WHITE):
        score += PIECE_VALUES[chess.PAWN] + PAWN_TABLE[chess.square_mirror(sq)]
    for sq in board.pieces(chess.KNIGHT, chess.WHITE):
        score += PIECE_VALUES[chess.KNIGHT] + KNIGHT_TABLE[chess.square_mirror(sq)]
    for sq in board.pieces(chess.BISHOP, chess.WHITE):
        score += PIECE_VALUES[chess.BISHOP] + BISHOP_TABLE[chess.square_mirror(sq)]
    for sq in board.pieces(chess.ROOK, chess.WHITE):
        score += PIECE_VALUES[chess.ROOK] + ROOK_TABLE[chess.square_mirror(sq)]
    for sq in board.pieces(chess.QUEEN, chess.WHITE):
        score += PIECE_VALUES[chess.QUEEN] + QUEEN_TABLE[chess.square_mirror(sq)]
    for sq in board.pieces(chess.KING, chess.WHITE):
        score += PIECE_VALUES[chess.KING] + KING_TABLE[chess.square_mirror(sq)]

    for sq in board.pieces(chess.PAWN, chess.BLACK):
        score -= PIECE_VALUES[chess.PAWN] + PAWN_TABLE[sq]
    for sq in board.pieces(chess.KNIGHT, chess.BLACK):
        score -= PIECE_VALUES[chess.KNIGHT] + KNIGHT_TABLE[sq]
    for sq in board.pieces(chess.BISHOP, chess.BLACK):
        score -= PIECE_VALUES[chess.BISHOP] + BISHOP_TABLE[sq]
    for sq in board.pieces(chess.ROOK, chess.BLACK):
        score -= PIECE_VALUES[chess.ROOK] + ROOK_TABLE[sq]
    for sq in board.pieces(chess.QUEEN, chess.BLACK):
        score -= PIECE_VALUES[chess.QUEEN] + QUEEN_TABLE[sq]
    for sq in board.pieces(chess.KING, chess.BLACK):
        score -= PIECE_VALUES[chess.KING] + KING_TABLE[sq]

    # Bonus for piece mobility
    legal_move_count = len(list(board.legal_moves))
    if board.turn == chess.WHITE:
        score += legal_move_count * 2  # Slight bonus for more options
    else:
        score -= legal_move_count * 2

    # Endgame bonuses (encourage pawn advancement & king activity)
    total_material = sum(len(list(board.pieces(pt, True))) + len(list(board.pieces(pt, False))) 
                         for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN])
    is_endgame = total_material <= 8
    
    if is_endgame:
        # In endgame, passed pawns are more valuable
        for sq in board.pieces(chess.PAWN, chess.WHITE):
            if board.is_pseudo_legal(chess.Move(sq, sq + 8)):
                rank = chess.square_rank(sq)
                score += 50 * (rank + 1)  # Bonus increases with advancement
        
        for sq in board.pieces(chess.PAWN, chess.BLACK):
            if board.is_pseudo_legal(chess.Move(sq, sq - 8)):
                rank = 7 - chess.square_rank(sq)
                score -= 50 * (rank + 1)

    return score


def minimax(board: chess.Board, depth: int, alpha: int, beta: int, maximizing: bool, 
            start_time: float, time_limit: float = 5.0) -> Tuple[int, Optional[chess.Move]]:
    """
    Alpha-beta pruning minimax algorithm with transposition table support.
    
    Args:
        board: Current chess board state
        depth: Remaining search depth
        alpha: Alpha value for pruning
        beta: Beta value for pruning
        maximizing: True if maximizing player's turn
        start_time: Time when search started
        time_limit: Maximum time in seconds
    
    Returns:
        Tuple of (best_evaluation, best_move)
    """
    # Check time limit
    if time.time() - start_time > time_limit:
        return evaluate_board(board), None
    
    # Check transposition table
    board_hash = board.fen()
    cached_eval = TRANSPOSITION_TABLE.lookup(board_hash, depth)
    if cached_eval is not None:
        return cached_eval, None

    if depth == 0 or board.is_game_over():
        score = evaluate_board(board)
        TRANSPOSITION_TABLE.store(board_hash, score, depth, 1)  # Exact flag
        return score, None

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return evaluate_board(board), None
    
    # Move ordering: prioritize captures and checks for better pruning
    legal_moves.sort(key=lambda m: (board.is_capture(m), board.gives_check(m)), reverse=True)

    best_move = None
    if maximizing:
        max_eval = -999999
        for move in legal_moves:
            board.push(move)
            val, _ = minimax(board, depth - 1, alpha, beta, False, start_time, time_limit)
            board.pop()
            if val > max_eval:
                max_eval = val
                best_move = move
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        TRANSPOSITION_TABLE.store(board_hash, max_eval, depth, 1)
        return max_eval, best_move
    else:
        min_eval = 999999
        for move in legal_moves:
            board.push(move)
            val, _ = minimax(board, depth - 1, alpha, beta, True, start_time, time_limit)
            board.pop()
            if val < min_eval:
                min_eval = val
                best_move = move
            beta = min(beta, val)
            if beta <= alpha:
                break
        TRANSPOSITION_TABLE.store(board_hash, min_eval, depth, 1)
        return min_eval, best_move


def get_ai_move(board: chess.Board, difficulty: str = "Medium", time_limit: float = 3.0) -> chess.Move:
    """
    Returns the best move calculated by iterative deepening minimax with alpha-beta pruning.
    
    Args:
        board: Current chess board state
        difficulty: "Easy", "Medium", or "Hard"
        time_limit: Maximum search time in seconds
    
    Returns:
        Best chess move found
    """
    start_time = time.time()
    best_move_overall = None
    
    if difficulty == "Easy":
        # Easy: 40% random moves, otherwise shallow search
        if random.random() < 0.4:
            return random.choice(list(board.legal_moves))
        max_depth = 1
    elif difficulty == "Medium":
        max_depth = 3
    else:  # Hard
        max_depth = 4

    # Iterative deepening: search progressively deeper until time runs out
    for depth in range(1, max_depth + 1):
        try:
            _, move = minimax(board, depth, -999999, 999999, board.turn == chess.WHITE, 
                            start_time, time_limit)
            if move:
                best_move_overall = move
            
            # Check if we've used enough time
            if time.time() - start_time > time_limit * 0.8:
                break
        except:
            break

    if best_move_overall is None:
        best_move_overall = random.choice(list(board.legal_moves))
    
    return best_move_overall


# Commentary generator
H_COMMENTARY_CAPTURES = [
    "Oho, piece uda diya sir ne!",
    "Bhai, capture mast tha!",
    "Chalo ek aur piece gaya.",
    "Kya baat hai Pratik Sir! Acha attack hai.",
    "Dikha na? Piece lapet le!",
    "Nice khela, bhai!"
]

H_COMMENTARY_CHECKS = [
    "Arre, check! Ab bachiye, sir.",
    "Ouch! Check laga diya.",
    "Check hai sir, dhyaan se!",
    "Bhai, king ko bachana padega.",
    "Ek din Check, Check, Check... Hehe!",
]

H_COMMENTARY_AI_MOVES = [
    "Mera turn! Ab dekho ye move.",
    "Chalo maine bhi chal diya, sir.",
    "Hum bhi kam nahi hain, Pratik Sir!",
    "Tension mat lo sir, match tight hoga.",
    "Aapki strategy achi hai, par ye dekho!",
    "Boom! Masterpiece move!",
    "Check out this beauty!"
]

H_COMMENTARY_PROMOTION = [
    "Wah, pawn to Queen ban gaya!",
    "Bhai sahab! Promotion ho gaya!",
    "Ek naya Queen aagya battlefield mein!"
]

H_COMMENTARY_BLUNDER = [
    "Oops! Ye move kaatil nikla.",
    "Teri to jam gai ab!",
    "Mistake kar diya bhai?"
]


def get_game_stats(board: chess.Board) -> dict:
    """Returns dictionary with game statistics."""
    return {
        "white_material": sum(len(list(board.pieces(pt, True))) 
                             for pt in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]),
        "black_material": sum(len(list(board.pieces(pt, False))) 
                             for pt in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]),
        "fullmove_number": board.fullmove_number,
        "move_count": len(board.move_stack)
    }


def generate_hinglish_commentary(board: chess.Board, move: chess.Move) -> str:
    """
    Generates context-aware Hinglish commentary about the move just played.
    Takes into account the position, move type, and game state.
    """
    is_capture = board.is_capture(move)
    board.push(move)
    is_check = board.is_check()
    is_mate = board.is_checkmate()
    is_promo = move.promotion is not None
    is_stalemate = board.is_stalemate()
    board.pop()

    if is_mate:
        return "Checkmate! Khel khatam ho gaya sir! Bahut hi shandar game tha. 🏆"
    if is_stalemate:
        return "Draw by stalemate! Interesting endgame, bhai."
    if is_promo:
        return random.choice(H_COMMENTARY_PROMOTION)
    if is_check:
        return random.choice(H_COMMENTARY_CHECKS)
    if is_capture:
        return random.choice(H_COMMENTARY_CAPTURES)

    # General AI move comment
    return random.choice(H_COMMENTARY_AI_MOVES)

"""
AI engine supporting Stockfish with 3 difficulty levels, plus Minimax fallback and Hidden Queen tactics.
"""
import os
import random
from typing import Optional, Tuple, List
from .board import Board, Move, square_to_algebraic, algebraic_to_square
from .piece import Piece

# Try importing the official Stockfish wrapper
try:
    from stockfish import Stockfish
    STOCKFISH_AVAILABLE = True
except ImportError:
    STOCKFISH_AVAILABLE = False


# Difficulty configuration
DIFFICULTY_LEVELS = {
    'easy': {
        'name': 'Easy (Casual)',
        'skill_level': 1,
        'depth': 2,
        'minimax_depth': 1,
        'blunder_chance': 0.20
    },
    'medium': {
        'name': 'Medium (Club Player)',
        'skill_level': 8,
        'depth': 6,
        'minimax_depth': 2,
        'blunder_chance': 0.0
    },
    'hard': {
        'name': 'Hard (Grandmaster Stockfish)',
        'skill_level': 20,
        'depth': 12,
        'minimax_depth': 3,
        'blunder_chance': 0.0
    }
}

# Piece values in centipawns
PIECE_VALUES = {
    'pawn': 100,
    'knight': 320,
    'bishop': 330,
    'rook': 500,
    'queen': 900,
    'king': 20000
}


class ChessAI:
    def __init__(self, color: str = 'black', difficulty: str = 'medium',
                 depth: Optional[int] = None, stockfish_path: Optional[str] = None):
        self.color = color
        self.difficulty = difficulty
        self.custom_depth = depth
        self.stockfish = None
        self._init_stockfish(stockfish_path)

    def _init_stockfish(self, custom_path: Optional[str] = None):
        if not STOCKFISH_AVAILABLE:
            return

        # Check candidate paths for stockfish executable
        candidates = []
        if custom_path:
            candidates.append(custom_path)

        curr_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates.extend([
            os.path.join(curr_dir, 'stockfish', 'stockfish.exe'),
            os.path.join(curr_dir, 'stockfish', 'stockfish'),
            'stockfish',
            'stockfish.exe'
        ])

        for path in candidates:
            if os.path.exists(path) or path in ['stockfish', 'stockfish.exe']:
                try:
                    cfg = DIFFICULTY_LEVELS.get(self.difficulty, DIFFICULTY_LEVELS['medium'])
                    sf = Stockfish(
                        path=path,
                        depth=cfg['depth'],
                        parameters={
                            "Skill Level": cfg['skill_level'],
                            "Threads": 2,
                            "Minimum Thinking Time": 10
                        }
                    )
                    self.stockfish = sf
                    return
                except Exception:
                    continue

    def set_difficulty(self, level: str):
        """Update difficulty level (easy, medium, hard)."""
        if level in DIFFICULTY_LEVELS:
            self.difficulty = level
            cfg = DIFFICULTY_LEVELS[level]
            if self.stockfish:
                try:
                    self.stockfish.set_skill_level(cfg['skill_level'])
                    self.stockfish.set_depth(cfg['depth'])
                except Exception:
                    pass

    def choose_hidden_queen_pawn(self, board: Board) -> str:
        """Intelligently choose a strong pawn to designate as the hidden queen."""
        candidate_ids = [f"{self.color}-pawn-{i}" for i in range(1, 9)]
        # Central pawns (d & e files) have highest tactical reach for a surprise Queen
        weights = [1.0, 1.2, 2.2, 3.5, 3.5, 2.2, 1.2, 1.0]
        return random.choices(candidate_ids, weights=weights, k=1)[0]

    def get_best_move(self, board: Board) -> Optional[Move]:
        """Find the best move using Stockfish, tactical Hidden Queen surprise, or Minimax fallback."""
        legal_moves = board.get_legal_moves(self.color)
        if not legal_moves:
            return None

        cfg = DIFFICULTY_LEVELS.get(self.difficulty, DIFFICULTY_LEVELS['medium'])

        # 1. Easy mode: small chance to play a random legal quiet move (casual beginner play)
        if cfg['blunder_chance'] > 0 and random.random() < cfg['blunder_chance']:
            quiet_moves = [m for m in legal_moves if not m.captured_piece]
            if quiet_moves:
                return random.choice(quiet_moves)

        # 2. Tactical Hidden Queen Opportunity:
        # Stockfish sees unrevealed hidden queen as a normal pawn, so it won't know
        # about lethal queen-slider attacks. Check if the Hidden Queen can execute a winning blow!
        hq_tactical_move = self._find_hidden_queen_tactic(board, legal_moves)
        if hq_tactical_move:
            return hq_tactical_move

        # 3. Stockfish Engine Move
        if self.stockfish:
            try:
                fen = board.to_fen()
                self.stockfish.set_fen_position(fen)
                best_uci = self.stockfish.get_best_move()
                if best_uci:
                    matched_move = self._match_uci_move(best_uci, legal_moves)
                    if matched_move:
                        return matched_move
            except Exception:
                pass

        # 4. Built-in Minimax Fallback
        depth = cfg['minimax_depth']
        is_maximizing = (self.color == 'white')
        _, best_move = self._minimax(board, depth, -float('inf'), float('inf'), is_maximizing)
        return best_move or random.choice(legal_moves)

    def _find_hidden_queen_tactic(self, board: Board, legal_moves: List[Move]) -> Optional[Move]:
        """Identify if a surprise Hidden Queen move delivers checkmate or wins a high-value piece."""
        hq_revealing_moves = [m for m in legal_moves if m.reveals_hidden_queen]
        if not hq_revealing_moves:
            return None

        # Check for immediate checkmate with hidden queen
        for m in hq_revealing_moves:
            if m.san.endswith('#'):
                return m

        # Check for capturing Queen or Rook with surprise attack
        best_capture = None
        max_capture_val = 0
        for m in hq_revealing_moves:
            if m.captured_piece:
                val = PIECE_VALUES.get(m.captured_piece.piece_type, 0)
                if val >= 500 and val > max_capture_val:  # Queen (900) or Rook (500)
                    max_capture_val = val
                    best_capture = m

        return best_capture

    def _match_uci_move(self, uci: str, legal_moves: List[Move]) -> Optional[Move]:
        """Convert UCI string (e.g. 'e7e5', 'a7a8q') to our legal Move object."""
        if len(uci) < 4:
            return None
        from_sq = algebraic_to_square(uci[:2])
        to_sq = algebraic_to_square(uci[2:4])
        promo = None
        if len(uci) >= 5:
            promo_char = uci[4].lower()
            promo_map = {'q': 'queen', 'r': 'rook', 'b': 'bishop', 'n': 'knight'}
            promo = promo_map.get(promo_char, 'queen')

        candidates = [m for m in legal_moves if m.from_sq == from_sq and m.to_sq == to_sq]
        if not candidates:
            return None

        if promo:
            for m in candidates:
                if m.promotion_choice == promo:
                    return m

        return candidates[0]

    def _minimax(self, board: Board, depth: int, alpha: float, beta: float, is_maximizing: bool) -> Tuple[float, Optional[Move]]:
        is_over, _ = board.is_game_over()
        if depth == 0 or is_over:
            return self._evaluate_board(board), None

        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return self._evaluate_board(board), None

        def move_score(m: Move) -> int:
            score = 0
            if m.captured_piece:
                score += PIECE_VALUES.get(m.captured_piece.piece_type, 0)
            if m.reveals_hidden_queen:
                score += 400
            return score

        legal_moves.sort(key=move_score, reverse=True)
        best_move = legal_moves[0]

        if is_maximizing:
            max_eval = -float('inf')
            for move in legal_moves:
                board.make_move(move)
                eval_score, _ = self._minimax(board, depth - 1, alpha, beta, False)
                board.undo_move()
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in legal_moves:
                board.make_move(move)
                eval_score, _ = self._minimax(board, depth - 1, alpha, beta, True)
                board.undo_move()
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def _evaluate_board(self, board: Board) -> int:
        if board.is_checkmate():
            return -99999 if board.turn == 'white' else 99999
        if board.is_stalemate() or board.is_threefold_repetition() or board.is_fifty_move_rule():
            return 0

        score = 0
        for r in range(8):
            for c in range(8):
                p = board.grid[r][c]
                if not p:
                    continue
                val = 950 if p.is_hidden_queen and not p.is_revealed else PIECE_VALUES.get(p.piece_type, 0)
                score += val if p.color == 'white' else -val
        return score

"""
Unit tests for the Python Hidden Queen Chess engine.
Includes tests for all standard FIDE rules and Hidden Queen mechanics:
- Move generation, piece movement, disambiguation
- Castling & castling rights revocation
- En passant
- Promotion choices
- Check, checkmate, stalemate
- Threefold repetition
- 50-move rule
- Insufficient material
- Hidden queen secrecy, queen movement, and reveal mechanics
"""
import pytest
from chess_engine.board import Board, Move, square_to_algebraic, algebraic_to_square
from chess_engine.piece import Piece
from chess_engine.ai import ChessAI


def test_algebraic_conversions():
    assert square_to_algebraic(7, 4) == 'e1'
    assert square_to_algebraic(0, 4) == 'e8'
    assert square_to_algebraic(4, 3) == 'd4'
    assert algebraic_to_square('e1') == (7, 4)
    assert algebraic_to_square('e8') == (0, 4)
    assert algebraic_to_square('d4') == (4, 3)


def test_initial_board_setup():
    board = Board()
    assert board.turn == 'white'
    white_pieces = sum(1 for r in range(8) for c in range(8) if board.grid[r][c] and board.grid[r][c].color == 'white')
    black_pieces = sum(1 for r in range(8) for c in range(8) if board.grid[r][c] and board.grid[r][c].color == 'black')
    assert white_pieces == 16
    assert black_pieces == 16
    moves = board.get_legal_moves()
    assert len(moves) == 20


def test_pawn_double_push_and_single_push():
    board = Board()
    e2 = algebraic_to_square('e2')
    e4 = algebraic_to_square('e4')
    move = next(m for m in board.get_legal_moves() if m.from_sq == e2 and m.to_sq == e4)
    assert board.make_move(move) is True
    assert board.en_passant_target == algebraic_to_square('e3')
    assert board.turn == 'black'

    e7 = algebraic_to_square('e7')
    e5 = algebraic_to_square('e5')
    move_black = next(m for m in board.get_legal_moves() if m.from_sq == e7 and m.to_sq == e5)
    assert board.make_move(move_black) is True
    assert board.en_passant_target == algebraic_to_square('e6')
    assert board.turn == 'white'


def test_en_passant():
    board = Board()
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('e4')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('a6')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('e5')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('d5')))
    assert board.en_passant_target == algebraic_to_square('d6')

    ep_move = next((m for m in board.get_legal_moves() if m.is_en_passant), None)
    assert ep_move is not None
    assert ep_move.to_sq == algebraic_to_square('d6')
    board.make_move(ep_move)
    d5_sq = algebraic_to_square('d5')
    assert board.grid[d5_sq[0]][d5_sq[1]] is None


def test_castling_kingside_and_queenside():
    board = Board()
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('e4')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('e5')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('Nf3')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('Nc6')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('Bc4')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('Bc5')))

    castle_move = next((m for m in board.get_legal_moves() if m.is_castling and m.to_sq[1] == 6), None)
    assert castle_move is not None
    board.make_move(castle_move)
    assert board.grid[7][6] is not None and board.grid[7][6].piece_type == 'king'
    assert board.grid[7][5] is not None and board.grid[7][5].piece_type == 'rook'
    assert board.castling_rights['white']['K'] is False
    assert board.castling_rights['white']['Q'] is False


def test_castling_rights_revocation_on_rook_capture():
    board = Board()
    # If black captures white's h1 rook, white loses kingside castling
    # Clear white pieces except king and rooks
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.grid[7][4] = Piece('white', 'king', 'white-king')
    board.grid[7][7] = Piece('white', 'rook', 'white-rook-2')
    board.grid[7][0] = Piece('white', 'rook', 'white-rook-1')
    board.grid[0][4] = Piece('black', 'king', 'black-king')
    board.grid[5][6] = Piece('black', 'knight', 'black-knight-1')  # g3 knight attacks h1
    board.turn = 'black'

    capture_move = next(m for m in board.get_legal_moves('black') if m.to_sq == (7, 7))
    board.make_move(capture_move)
    assert board.castling_rights['white']['K'] is False
    assert board.castling_rights['white']['Q'] is True


def test_checkmate_scholars_mate():
    board = Board()
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('e4')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('e5')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('Qh5')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('Nc6')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('Bc4')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('Nf6')))
    mate_move = next(m for m in board.get_legal_moves() if m.san.startswith('Qxf7'))
    board.make_move(mate_move)

    assert board.is_checkmate() is True
    is_over, reason = board.is_game_over()
    assert is_over is True
    assert "White wins" in reason


def test_stalemate():
    # Setup classic stalemate position:
    # Black king on a8, White king on c7, White queen on b6
    board = Board()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.grid[0][0] = Piece('black', 'king', 'black-king')  # a8
    board.grid[1][2] = Piece('white', 'king', 'white-king')  # c7
    board.grid[2][1] = Piece('white', 'queen', 'white-queen')  # b6
    board.turn = 'black'

    assert board.is_in_check('black') is False
    assert len(board.get_legal_moves('black')) == 0
    assert board.is_stalemate() is True
    is_over, reason = board.is_game_over()
    assert is_over is True
    assert "Draw by Stalemate" in reason


def test_threefold_repetition():
    board = Board()
    # 1. Nf3 Nf6 2. Ng1 Ng8 (repetition 1)
    # 3. Nf3 Nf6 4. Ng1 Ng8 (repetition 2 - 3 occurrences of initial position!)
    moves_sequence = ['Nf3', 'Nf6', 'Ng1', 'Ng8', 'Nf3', 'Nf6', 'Ng1', 'Ng8']
    for san in moves_sequence:
        m = next(move for move in board.get_legal_moves() if move.san == san)
        board.make_move(m)

    assert board.is_threefold_repetition() is True
    is_over, reason = board.is_game_over()
    assert is_over is True
    assert "Threefold Repetition" in reason


def test_fifty_move_rule():
    board = Board()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.grid[0][4] = Piece('black', 'king', 'black-king')
    board.grid[7][4] = Piece('white', 'king', 'white-king')
    board.halfmove_clock = 100

    assert board.is_fifty_move_rule() is True
    is_over, reason = board.is_game_over()
    assert is_over is True
    assert "50-Move Rule" in reason


def test_insufficient_material():
    board = Board()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.grid[0][4] = Piece('black', 'king', 'black-king')
    board.grid[7][4] = Piece('white', 'king', 'white-king')

    # King vs King
    assert board.is_insufficient_material() is True
    is_over, reason = board.is_game_over()
    assert is_over is True
    assert "Insufficient Material" in reason

    # King + Bishop vs King
    board.grid[7][2] = Piece('white', 'bishop', 'white-bishop-1')
    assert board.is_insufficient_material() is True

    # King + Knight vs King
    board.grid[7][2] = Piece('white', 'knight', 'white-knight-1')
    assert board.is_insufficient_material() is True

    # King + Pawn vs King (sufficient material because pawn can promote)
    board.grid[7][2] = Piece('white', 'pawn', 'white-pawn-1')
    assert board.is_insufficient_material() is False

    # King + Hidden Queen (unrevealed pawn) vs King (sufficient because it's secretly a queen)
    board.grid[7][2] = Piece('white', 'pawn', 'white-pawn-1', is_hidden_queen=True)
    assert board.is_insufficient_material() is False


def test_hidden_queen_normal_pawn_move_stays_hidden():
    board = Board()
    board.set_hidden_queen('white', 'white-pawn-5')  # e2
    pawn = board.grid[6][4]
    assert pawn.is_hidden_queen is True
    assert pawn.is_revealed is False
    assert pawn.display_type == 'pawn'

    move = next(m for m in board.get_legal_moves() if m.from_sq == (6, 4) and m.to_sq == (4, 4))
    assert move.reveals_hidden_queen is False
    board.make_move(move)

    assert pawn.is_revealed is False
    assert pawn.display_type == 'pawn'


def test_hidden_queen_queen_move_reveals():
    board = Board()
    board.set_hidden_queen('white', 'white-pawn-5')
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('d4')))
    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('d5')))

    hq_moves = [m for m in board.get_legal_moves() if m.from_sq == (6, 4) and m.to_sq == (5, 3)]
    assert len(hq_moves) == 1
    queen_move = hq_moves[0]
    assert queen_move.reveals_hidden_queen is True

    board.make_move(queen_move)
    pawn = board.grid[5][3]
    assert pawn.is_revealed is True
    assert pawn.display_type == 'queen'


def test_hidden_queen_slider_moves_multiple_squares():
    board = Board()
    board.set_hidden_queen('white', 'white-pawn-5')  # e2
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.grid[0][4] = Piece('black', 'king', 'black-king')
    board.grid[7][4] = Piece('white', 'king', 'white-king')
    hq = Piece('white', 'pawn', 'white-pawn-1', is_hidden_queen=True)
    board.grid[4][4] = hq  # e4

    moves = board.get_legal_moves('white')
    h_moves = [m for m in moves if m.from_sq == (4, 4) and m.to_sq[0] == 4]
    assert len(h_moves) == 7
    assert all(m.reveals_hidden_queen for m in h_moves)


def test_ai_selection_and_move():
    board = Board()
    ai = ChessAI(color='black', depth=2)
    chosen_pawn = ai.choose_hidden_queen_pawn(board)
    assert chosen_pawn.startswith('black-pawn-')
    board.set_hidden_queen('black', chosen_pawn)

    board.make_move(next(m for m in board.get_legal_moves() if m.san.startswith('e4')))

    ai_move = ai.get_best_move(board)
    assert ai_move is not None
    assert ai_move.piece.color == 'black'
    assert board.make_move(ai_move) is True
    assert board.turn == 'white'


def test_stockfish_difficulty_levels():
    board = Board()
    for diff in ['easy', 'medium', 'hard']:
        ai = ChessAI(color='black', difficulty=diff)
        assert ai.difficulty == diff
        # In start position after e4, verify AI calculates a valid move
        test_board = Board()
        test_board.make_move(next(m for m in test_board.get_legal_moves() if m.san.startswith('e4')))
        move = ai.get_best_move(test_board)
        assert move is not None
        assert move.piece.color == 'black'


def test_hidden_queen_vs_normal_pawn_promotion():
    board = Board()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.grid[0][4] = Piece('black', 'king', 'black-king')
    board.grid[7][4] = Piece('white', 'king', 'white-king')

    # 1. Normal white pawn on a7
    normal_pawn = Piece('white', 'pawn', 'white-pawn-1')
    board.grid[1][0] = normal_pawn  # a7
    normal_moves = [m for m in board.get_legal_moves('white') if m.from_sq == (1, 0) and m.to_sq == (0, 0)]
    # Normal pawn must have 4 promotion options: Queen, Rook, Bishop, Knight
    assert len(normal_moves) == 4
    promos = {m.promotion_choice for m in normal_moves}
    assert promos == {'queen', 'rook', 'bishop', 'knight'}

    # 2. Hidden Queen on h7
    hq_pawn = Piece('white', 'pawn', 'white-pawn-8', is_hidden_queen=True)
    board.grid[1][7] = hq_pawn  # h7
    hq_moves = [m for m in board.get_legal_moves('white') if m.from_sq == (1, 7) and m.to_sq == (0, 7)]
    # Hidden queen MUST ONLY be able to promote to a Queen!
    assert len(hq_moves) == 1
    assert hq_moves[0].promotion_choice == 'queen'
    assert hq_moves[0].reveals_hidden_queen is True



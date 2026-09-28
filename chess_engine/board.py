"""
Full Chess engine logic with all standard FIDE rules and Hidden Queen mechanics.
Includes:
- Full legal move generation (castling, en passant, promotion)
- Precise castling rights tracking (king/rook moves and captures)
- Check, Checkmate, and Stalemate
- Threefold Repetition detection
- 50-Move Rule
- Insufficient Material detection
- Move history, undo, and SAN notation with disambiguation
"""
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Set
from .piece import Piece


def square_to_algebraic(row: int, col: int) -> str:
    """Convert (row, col) (0-7, 0-7) to algebraic notation, e.g. (7, 4) -> 'e1'"""
    file_char = chr(ord('a') + col)
    rank_char = str(8 - row)
    return f"{file_char}{rank_char}"


def algebraic_to_square(alg: str) -> Tuple[int, int]:
    """Convert algebraic notation like 'e4' to (row, col)"""
    col = ord(alg[0].lower()) - ord('a')
    row = 8 - int(alg[1])
    return row, col


@dataclass
class Move:
    from_sq: Tuple[int, int]
    to_sq: Tuple[int, int]
    piece: Piece
    captured_piece: Optional[Piece] = None
    is_castling: bool = False
    is_en_passant: bool = False
    promotion_choice: Optional[str] = None
    reveals_hidden_queen: bool = False
    san: str = ""

    def __repr__(self) -> str:
        hq_flag = " (HQ Revealed!)" if self.reveals_hidden_queen else ""
        return f"{self.san or f'{square_to_algebraic(*self.from_sq)}->{square_to_algebraic(*self.to_sq)}'}{hq_flag}"


class Board:
    def __init__(self):
        self.grid: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self.turn: str = 'white'  # 'white' or 'black'
        self.en_passant_target: Optional[Tuple[int, int]] = None
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1

        # Castling rights: True if eligible
        self.castling_rights: Dict[str, Dict[str, bool]] = {
            'white': {'K': True, 'Q': True},
            'black': {'K': True, 'Q': True}
        }

        # Hidden queen IDs
        self.white_hidden_queen_pawn_id: Optional[str] = None
        self.black_hidden_queen_pawn_id: Optional[str] = None

        # Position history for threefold repetition
        self.position_history: Dict[tuple, int] = {}
        self.move_history: List[Tuple[Move, dict]] = []

        self.setup_standard_board()

    def setup_standard_board(self):
        """Initialize standard chess pieces."""
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.turn = 'white'
        self.en_passant_target = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.castling_rights = {
            'white': {'K': True, 'Q': True},
            'black': {'K': True, 'Q': True}
        }
        self.move_history.clear()
        self.position_history.clear()

        # Black major pieces (Rank 8, row 0)
        back_rank = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']
        for col, p_type in enumerate(back_rank):
            p_id = f"black-{p_type}-{col+1 if p_type in ['rook', 'knight', 'bishop'] else ''}".rstrip('-')
            self.grid[0][col] = Piece('black', p_type, p_id)

        # Black pawns (Rank 7, row 1)
        for col in range(8):
            self.grid[1][col] = Piece('black', 'pawn', f"black-pawn-{col+1}")

        # White pawns (Rank 2, row 6)
        for col in range(8):
            self.grid[6][col] = Piece('white', 'pawn', f"white-pawn-{col+1}")

        # White major pieces (Rank 1, row 7)
        for col, p_type in enumerate(back_rank):
            p_id = f"white-{p_type}-{col+1 if p_type in ['rook', 'knight', 'bishop'] else ''}".rstrip('-')
            self.grid[7][col] = Piece('white', p_type, p_id)

        # Record initial position signature
        self.position_history[self.get_position_signature()] = 1

    def set_hidden_queen(self, color: str, pawn_id: str):
        """Designate a pawn as the secret Hidden Queen."""
        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if piece and piece.color == color and piece.piece_type == 'pawn':
                    if piece.id == pawn_id:
                        piece.is_hidden_queen = True
                        piece.is_revealed = False
                        if color == 'white':
                            self.white_hidden_queen_pawn_id = pawn_id
                        else:
                            self.black_hidden_queen_pawn_id = pawn_id
                        # Update position signature after designation
                        self.position_history.clear()
                        self.position_history[self.get_position_signature()] = 1
                        return

    def get_piece(self, row: int, col: int) -> Optional[Piece]:
        if 0 <= row < 8 and 0 <= col < 8:
            return self.grid[row][col]
        return None

    def find_king(self, color: str) -> Optional[Tuple[int, int]]:
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p and p.color == color and p.piece_type == 'king':
                    return r, c
        return None

    def to_fen(self) -> str:
        """Generate FEN string for Stockfish and position analysis."""
        rows = []
        for r in range(8):
            empty = 0
            row_str = ""
            for c in range(8):
                p = self.grid[r][c]
                if p is None:
                    empty += 1
                else:
                    if empty > 0:
                        row_str += str(empty)
                        empty = 0
                    char = p.display_type[0].upper() if p.display_type != 'knight' else 'N'
                    row_str += char if p.color == 'white' else char.lower()
            if empty > 0:
                row_str += str(empty)
            rows.append(row_str)
        placement = "/".join(rows)

        active = 'w' if self.turn == 'white' else 'b'

        castling = ""
        if self.castling_rights['white']['K']:
            castling += 'K'
        if self.castling_rights['white']['Q']:
            castling += 'Q'
        if self.castling_rights['black']['K']:
            castling += 'k'
        if self.castling_rights['black']['Q']:
            castling += 'q'
        if not castling:
            castling = '-'

        ep = square_to_algebraic(*self.en_passant_target) if self.en_passant_target else '-'

        return f"{placement} {active} {castling} {ep} {self.halfmove_clock} {self.fullmove_number}"

    def get_position_signature(self) -> tuple:
        """Hashable signature representing the exact FIDE position state."""
        board_tuple = tuple(
            tuple(
                (p.color, p.display_type, p.is_hidden_queen and not p.is_revealed) if p else None
                for p in row
            )
            for row in self.grid
        )
        castling_tuple = (
            self.castling_rights['white']['K'],
            self.castling_rights['white']['Q'],
            self.castling_rights['black']['K'],
            self.castling_rights['black']['Q']
        )
        return (board_tuple, self.turn, castling_tuple, self.en_passant_target)

    def is_valid_normal_pawn_move(self, piece: Piece, from_sq: Tuple[int, int], to_sq: Tuple[int, int],
                                  captured: Optional[Piece], is_ep: bool) -> bool:
        """Returns True if the move strictly conforms to standard pawn rules."""
        fr, fc = from_sq
        tr, tc = to_sq
        direction = -1 if piece.color == 'white' else 1
        start_rank = 6 if piece.color == 'white' else 1

        # Standard 1 square forward move
        if fc == tc and tr == fr + direction and captured is None:
            return True

        # Standard 2 squares forward from start rank
        if fc == tc and fr == start_rank and tr == fr + (2 * direction) and captured is None:
            mid_sq = self.grid[fr + direction][fc]
            if mid_sq is None:
                return True

        # Standard 1 square diagonal capture or en passant
        if abs(fc - tc) == 1 and tr == fr + direction:
            if captured is not None and captured.color != piece.color:
                return True
            if is_ep:
                return True

        return False

    def is_square_attacked(self, row: int, col: int, by_color: str) -> bool:
        """Returns True if (row, col) is attacked by any piece of `by_color`."""
        # 1. Pawn attacks (from perspective of attacking color)
        pawn_dir = 1 if by_color == 'white' else -1
        for dc in [-1, 1]:
            pr, pc = row + pawn_dir, col + dc
            if 0 <= pr < 8 and 0 <= pc < 8:
                p = self.grid[pr][pc]
                if p and p.color == by_color and p.piece_type == 'pawn':
                    return True

        # 2. Knight attacks
        knight_offsets = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                          (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, dc in knight_offsets:
            nr, nc = row + dr, col + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                p = self.grid[nr][nc]
                if p and p.color == by_color and p.piece_type == 'knight':
                    return True

        # 3. King attacks
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                kr, kc = row + dr, col + dc
                if 0 <= kr < 8 and 0 <= kc < 8:
                    p = self.grid[kr][kc]
                    if p and p.color == by_color and p.piece_type == 'king':
                        return True

        # 4. Straight rays (Rook, Queen, Hidden Queen)
        straight_dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in straight_dirs:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                p = self.grid[r][c]
                if p:
                    if p.color == by_color:
                        if p.piece_type in ['rook', 'queen'] or p.is_hidden_queen:
                            return True
                    break
                r += dr
                c += dc

        # 5. Diagonal rays (Bishop, Queen, Hidden Queen)
        diag_dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in diag_dirs:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                p = self.grid[r][c]
                if p:
                    if p.color == by_color:
                        if p.piece_type in ['bishop', 'queen'] or p.is_hidden_queen:
                            return True
                    break
                r += dr
                c += dc

        return False

    def is_in_check(self, color: str) -> bool:
        king_pos = self.find_king(color)
        if not king_pos:
            return False
        opponent = 'black' if color == 'white' else 'white'
        return self.is_square_attacked(king_pos[0], king_pos[1], opponent)

    def get_pseudo_legal_moves_for_piece(self, r: int, c: int) -> List[Move]:
        piece = self.grid[r][c]
        if not piece:
            return []

        moves: List[Move] = []
        eff_type = piece.effective_type

        # 1. Normal Pawn
        if eff_type == 'pawn':
            direction = -1 if piece.color == 'white' else 1
            start_rank = 6 if piece.color == 'white' else 1
            promo_rank = 0 if piece.color == 'white' else 7

            # Forward 1
            nr, nc = r + direction, c
            if 0 <= nr < 8 and self.grid[nr][nc] is None:
                if nr == promo_rank:
                    for promo in ['queen', 'rook', 'bishop', 'knight']:
                        moves.append(Move((r, c), (nr, nc), piece, promotion_choice=promo))
                else:
                    moves.append(Move((r, c), (nr, nc), piece))

                # Forward 2 from start
                if r == start_rank:
                    nnr = r + (2 * direction)
                    if self.grid[nnr][nc] is None:
                        moves.append(Move((r, c), (nnr, nc), piece))

            # Diagonal captures
            for dc in [-1, 1]:
                nr, nc = r + direction, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.grid[nr][nc]
                    if target and target.color != piece.color:
                        if nr == promo_rank:
                            for promo in ['queen', 'rook', 'bishop', 'knight']:
                                moves.append(Move((r, c), (nr, nc), piece, captured_piece=target, promotion_choice=promo))
                        else:
                            moves.append(Move((r, c), (nr, nc), piece, captured_piece=target))
                    # En passant
                    elif self.en_passant_target == (nr, nc):
                        ep_pawn_row = r
                        ep_pawn_col = nc
                        ep_captured = self.grid[ep_pawn_row][ep_pawn_col]
                        moves.append(Move((r, c), (nr, nc), piece, captured_piece=ep_captured, is_en_passant=True))

        # 2. Knight
        elif eff_type == 'knight':
            knight_offsets = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                              (1, -2), (1, 2), (2, -1), (2, 1)]
            for dr, dc in knight_offsets:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.grid[nr][nc]
                    if target is None:
                        moves.append(Move((r, c), (nr, nc), piece))
                    elif target.color != piece.color:
                        moves.append(Move((r, c), (nr, nc), piece, captured_piece=target))

        # 3. King
        elif eff_type == 'king':
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        target = self.grid[nr][nc]
                        if target is None:
                            moves.append(Move((r, c), (nr, nc), piece))
                        elif target.color != piece.color:
                            moves.append(Move((r, c), (nr, nc), piece, captured_piece=target))

            # Castling (using self.castling_rights)
            if not self.is_in_check(piece.color):
                opponent = 'black' if piece.color == 'white' else 'white'
                rights = self.castling_rights[piece.color]

                # Kingside: e-file to g-file (cols 4 to 6)
                if rights['K']:
                    rook_ks = self.grid[r][7]
                    if rook_ks and rook_ks.piece_type == 'rook':
                        if self.grid[r][5] is None and self.grid[r][6] is None:
                            if not self.is_square_attacked(r, 5, opponent) and not self.is_square_attacked(r, 6, opponent):
                                moves.append(Move((r, c), (r, 6), piece, is_castling=True))

                # Queenside: e-file to c-file (cols 4 to 2)
                if rights['Q']:
                    rook_qs = self.grid[r][0]
                    if rook_qs and rook_qs.piece_type == 'rook':
                        if self.grid[r][1] is None and self.grid[r][2] is None and self.grid[r][3] is None:
                            if not self.is_square_attacked(r, 3, opponent) and not self.is_square_attacked(r, 2, opponent):
                                moves.append(Move((r, c), (r, 2), piece, is_castling=True))

        # 4. Sliding pieces: Rook, Bishop, Queen, or Hidden Queen
        if eff_type in ['rook', 'bishop', 'queen']:
            directions = []
            if eff_type in ['rook', 'queen']:
                directions.extend([(-1, 0), (1, 0), (0, -1), (0, 1)])
            if eff_type in ['bishop', 'queen']:
                directions.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])

            promo_rank = 0 if piece.color == 'white' else 7

            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    target = self.grid[nr][nc]
                    if target is None:
                        reveals = False
                        if piece.is_hidden_queen and not piece.is_revealed:
                            reveals = not self.is_valid_normal_pawn_move(piece, (r, c), (nr, nc), None, False)

                        # If reaching promotion rank as hidden queen, only queen is allowed
                        if piece.is_hidden_queen and nr == promo_rank:
                            moves.append(Move((r, c), (nr, nc), piece, reveals_hidden_queen=True, promotion_choice='queen'))
                        else:
                            moves.append(Move((r, c), (nr, nc), piece, reveals_hidden_queen=reveals))
                    else:
                        if target.color != piece.color:
                            reveals = False
                            if piece.is_hidden_queen and not piece.is_revealed:
                                reveals = not self.is_valid_normal_pawn_move(piece, (r, c), (nr, nc), target, False)

                            # If reaching promotion rank as hidden queen, only queen is allowed
                            if piece.is_hidden_queen and nr == promo_rank:
                                moves.append(Move((r, c), (nr, nc), piece, captured_piece=target,
                                                  reveals_hidden_queen=True, promotion_choice='queen'))
                            else:
                                moves.append(Move((r, c), (nr, nc), piece, captured_piece=target, reveals_hidden_queen=reveals))
                        break
                    nr += dr
                    nc += dc

            # If hidden queen, also check if standard en passant is available
            if piece.is_hidden_queen and not piece.is_revealed and self.en_passant_target:
                direction = -1 if piece.color == 'white' else 1
                for dc in [-1, 1]:
                    if (r + direction, c + dc) == self.en_passant_target:
                        ep_captured = self.grid[r][c + dc]
                        moves.append(Move((r, c), self.en_passant_target, piece,
                                          captured_piece=ep_captured, is_en_passant=True,
                                          reveals_hidden_queen=False))

        return moves

    def get_legal_moves(self, color: Optional[str] = None) -> List[Move]:
        """Generate all strictly legal moves for `color` (defaults to current turn)."""
        active_color = color or self.turn
        legal_moves: List[Move] = []

        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if piece and piece.color == active_color:
                    pseudo_moves = self.get_pseudo_legal_moves_for_piece(r, c)
                    for move in pseudo_moves:
                        if self._is_move_safe_for_king(move, active_color):
                            legal_moves.append(move)

        # Compute SAN notation for all legal moves with disambiguation
        for move in legal_moves:
            move.san = self._compute_san(move, legal_moves)

        return legal_moves

    def _is_move_safe_for_king(self, move: Move, color: str) -> bool:
        """Test if making this move leaves the king in check."""
        self._apply_raw_move(move)
        in_check = self.is_in_check(color)
        self._undo_raw_move(move)
        return not in_check

    def _apply_raw_move(self, move: Move):
        """Low-level move application without validation or history (for search/safety)."""
        fr, fc = move.from_sq
        tr, tc = move.to_sq
        piece = self.grid[fr][fc]
        self.grid[fr][fc] = None

        if move.is_en_passant:
            self.grid[fr][tc] = None

        elif move.is_castling:
            if tc == 6:  # Kingside
                rook = self.grid[fr][7]
                self.grid[fr][7] = None
                self.grid[fr][5] = rook
            elif tc == 2:  # Queenside
                rook = self.grid[fr][0]
                self.grid[fr][0] = None
                self.grid[fr][3] = rook

        if move.promotion_choice:
            promoted_piece = Piece(piece.color, move.promotion_choice, f"{piece.color}-{move.promotion_choice}-promo")
            promoted_piece.has_moved = True
            self.grid[tr][tc] = promoted_piece
        else:
            self.grid[tr][tc] = piece

    def _undo_raw_move(self, move: Move):
        """Undo raw move applied by _apply_raw_move."""
        fr, fc = move.from_sq
        tr, tc = move.to_sq
        self.grid[fr][fc] = move.piece
        self.grid[tr][tc] = move.captured_piece if not move.is_en_passant else None

        if move.is_en_passant:
            self.grid[fr][tc] = move.captured_piece

        elif move.is_castling:
            if tc == 6:
                rook = self.grid[fr][5]
                self.grid[fr][5] = None
                self.grid[fr][7] = rook
            elif tc == 2:
                rook = self.grid[fr][3]
                self.grid[fr][3] = None
                self.grid[fr][0] = rook

    def make_move(self, move: Move) -> bool:
        """Make a legal move, updating board state, castling rights, clocks, and hidden queen status."""
        fr, fc = move.from_sq
        tr, tc = move.to_sq
        piece = self.grid[fr][fc]
        if not piece:
            return False

        # Save snapshot for undo
        state_snapshot = {
            'en_passant_target': self.en_passant_target,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
            'piece_has_moved': piece.has_moved,
            'piece_is_revealed': piece.is_revealed,
            'castling_rights': {
                'white': dict(self.castling_rights['white']),
                'black': dict(self.castling_rights['black'])
            },
            'turn': self.turn
        }

        # Apply raw move
        self._apply_raw_move(move)

        # Update piece states
        piece.has_moved = True
        if move.reveals_hidden_queen:
            piece.is_revealed = True

        # Update castling rights
        if piece.piece_type == 'king':
            self.castling_rights[piece.color]['K'] = False
            self.castling_rights[piece.color]['Q'] = False

        # If a rook moved or was captured, revoke that side's castling right
        if (fr, fc) == (7, 7) or (tr, tc) == (7, 7):
            self.castling_rights['white']['K'] = False
        if (fr, fc) == (7, 0) or (tr, tc) == (7, 0):
            self.castling_rights['white']['Q'] = False
        if (fr, fc) == (0, 7) or (tr, tc) == (0, 7):
            self.castling_rights['black']['K'] = False
        if (fr, fc) == (0, 0) or (tr, tc) == (0, 0):
            self.castling_rights['black']['Q'] = False

        # En passant target update
        direction = -1 if piece.color == 'white' else 1
        if piece.piece_type == 'pawn' and abs(tr - fr) == 2:
            self.en_passant_target = (fr + direction, fc)
        else:
            self.en_passant_target = None

        # Clock updates (50-move rule: reset on pawn move or capture)
        if piece.piece_type == 'pawn' or move.captured_piece:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if self.turn == 'black':
            self.fullmove_number += 1

        # Switch turn
        self.turn = 'black' if self.turn == 'white' else 'white'

        # Record position history for threefold repetition
        pos_sig = self.get_position_signature()
        self.position_history[pos_sig] = self.position_history.get(pos_sig, 0) + 1

        # Record move history
        self.move_history.append((move, state_snapshot))
        return True

    def undo_move(self) -> Optional[Move]:
        """Undo the last made move."""
        if not self.move_history:
            return None

        # Decrement current position in repetition history
        current_sig = self.get_position_signature()
        if current_sig in self.position_history:
            self.position_history[current_sig] -= 1
            if self.position_history[current_sig] <= 0:
                del self.position_history[current_sig]

        move, state = self.move_history.pop()
        self._undo_raw_move(move)

        # Restore state snapshot
        move.piece.has_moved = state['piece_has_moved']
        move.piece.is_revealed = state['piece_is_revealed']
        self.castling_rights = {
            'white': dict(state['castling_rights']['white']),
            'black': dict(state['castling_rights']['black'])
        }
        self.en_passant_target = state['en_passant_target']
        self.halfmove_clock = state['halfmove_clock']
        self.fullmove_number = state['fullmove_number']
        self.turn = state['turn']

        return move

    def is_checkmate(self) -> bool:
        return self.is_in_check(self.turn) and len(self.get_legal_moves()) == 0

    def is_stalemate(self) -> bool:
        return not self.is_in_check(self.turn) and len(self.get_legal_moves()) == 0

    def is_threefold_repetition(self) -> bool:
        """Returns True if the current position has occurred 3 or more times."""
        current_sig = self.get_position_signature()
        return self.position_history.get(current_sig, 0) >= 3

    def is_fifty_move_rule(self) -> bool:
        """50 moves (100 half-moves) without a pawn move or capture."""
        return self.halfmove_clock >= 100

    def is_insufficient_material(self) -> bool:
        """Returns True if neither player has mating material according to FIDE rules."""
        pieces = []
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p:
                    # If any pawn is an unrevealed hidden queen, it has full queen power!
                    if p.is_hidden_queen:
                        return False
                    pieces.append((p, (r, c)))

        # If any queen, rook, or pawn remains on the board, material is sufficient
        for p, _ in pieces:
            if p.piece_type in ['queen', 'rook', 'pawn']:
                return False

        # Kings only (King vs King)
        if len(pieces) == 2:
            return True

        # King + Minor piece vs King (3 pieces total)
        if len(pieces) == 3:
            minor_pieces = [p for p, _ in pieces if p.piece_type in ['bishop', 'knight']]
            if len(minor_pieces) == 1:
                return True

        # King + Bishop vs King + Bishop with bishops on same color
        if len(pieces) == 4:
            bishops = [(p, sq) for p, sq in pieces if p.piece_type == 'bishop']
            if len(bishops) == 2 and bishops[0][0].color != bishops[1][0].color:
                # Check square color of bishops: (r + c) % 2
                color1 = (bishops[0][1][0] + bishops[0][1][1]) % 2
                color2 = (bishops[1][1][0] + bishops[1][1][1]) % 2
                if color1 == color2:
                    return True

        return False

    def is_game_over(self) -> Tuple[bool, str]:
        """Returns (is_over, reason)."""
        if self.is_checkmate():
            winner = 'Black' if self.turn == 'white' else 'White'
            return True, f"Checkmate! {winner} wins!"
        if self.is_stalemate():
            return True, "Draw by Stalemate!"
        if self.is_threefold_repetition():
            return True, "Draw by Threefold Repetition!"
        if self.is_fifty_move_rule():
            return True, "Draw by 50-Move Rule!"
        if self.is_insufficient_material():
            return True, "Draw by Insufficient Material!"
        return False, ""

    def _compute_san(self, move: Move, legal_moves: List[Move]) -> str:
        """Compute standard algebraic notation for a move with disambiguation."""
        if move.is_castling:
            return "O-O" if move.to_sq[1] == 6 else "O-O-O"

        piece = move.piece
        p_symbol = ""
        if piece.display_type == 'knight':
            p_symbol = "N"
        elif piece.display_type in ['bishop', 'rook', 'queen', 'king']:
            p_symbol = piece.display_type[0].upper()

        to_alg = square_to_algebraic(*move.to_sq)

        # Disambiguation for non-pawns
        disambig = ""
        if piece.display_type != 'pawn':
            ambiguous = [
                m for m in legal_moves
                if m.to_sq == move.to_sq and m.piece.display_type == piece.display_type and m.from_sq != move.from_sq
            ]
            if ambiguous:
                same_file = any(m.from_sq[1] == move.from_sq[1] for m in ambiguous)
                same_rank = any(m.from_sq[0] == move.from_sq[0] for m in ambiguous)
                from_alg = square_to_algebraic(*move.from_sq)
                if not same_file:
                    disambig = from_alg[0]
                elif not same_rank:
                    disambig = from_alg[1]
                else:
                    disambig = from_alg

        if move.captured_piece or move.is_en_passant:
            if piece.display_type == 'pawn':
                san = f"{square_to_algebraic(*move.from_sq)[0]}x{to_alg}"
            else:
                san = f"{p_symbol}{disambig}x{to_alg}"
        else:
            san = f"{p_symbol}{disambig}{to_alg}"

        if move.promotion_choice:
            san += f"={move.promotion_choice[0].upper()}"

        if move.reveals_hidden_queen:
            san += "!"

        # Check / Checkmate suffix
        self._apply_raw_move(move)
        opponent = 'black' if piece.color == 'white' else 'white'
        if self.is_in_check(opponent):
            self.turn = opponent
            opp_moves = self.get_legal_moves(opponent)
            self.turn = piece.color
            if len(opp_moves) == 0:
                san += "#"
            else:
                san += "+"
        self._undo_raw_move(move)

        return san

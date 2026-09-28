"""
Piece representation for Hidden Queen Chess.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Piece:
    color: str          # 'white' or 'black'
    piece_type: str     # 'pawn', 'knight', 'bishop', 'rook', 'queen', 'king'
    id: str             # unique ID, e.g. 'white-pawn-1'
    is_hidden_queen: bool = False
    is_revealed: bool = False
    has_moved: bool = False

    @property
    def display_type(self) -> str:
        """The appearance of the piece to an observer.
        If it's a hidden queen that hasn't been revealed, it displays as a pawn.
        Once revealed, it displays as a queen.
        """
        if self.is_hidden_queen:
            return 'queen' if self.is_revealed else 'pawn'
        return self.piece_type

    @property
    def effective_type(self) -> str:
        """The move capability of the piece.
        A hidden queen can move with queen capabilities.
        """
        if self.is_hidden_queen:
            return 'queen'
        return self.piece_type

    def clone(self) -> 'Piece':
        return Piece(
            color=self.color,
            piece_type=self.piece_type,
            id=self.id,
            is_hidden_queen=self.is_hidden_queen,
            is_revealed=self.is_revealed,
            has_moved=self.has_moved
        )

    def __repr__(self) -> str:
        hq_flag = ""
        if self.is_hidden_queen:
            hq_flag = "(HQ-Rev)" if self.is_revealed else "(HQ-Hidden)"
        return f"{self.color[0].upper()}{self.piece_type[0].upper()}{hq_flag}"

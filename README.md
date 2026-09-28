# Hidden Queen Chess 👑 (Python Edition)

An innovative twist on the classic game of chess built fully with Python, Pygame, and the world-class **Stockfish 19** chess engine!

In **Hidden Queen Chess**, each player secretly designates one of their 8 pawns to be an undercover **Hidden Queen**. The opponent remains unaware of which pawn holds this lethal power until the trap is sprung!

---

## 🎯 Game Concept & Rules

1. **On-Board Secret Designation**:
   - At the beginning of the match, simply **click any of your pawns directly on the chessboard** to designate it as your secret **Hidden Queen**.
   - Your secret queen appears as an ordinary pawn to your opponent.
   - You have a subtle gold crown badge on your own screen so you always know which pawn is yours.

2. **Movement & Stealth**:
   - As long as you make standard pawn moves (single push, initial double push, diagonal pawn capture, en passant), your Hidden Queen remains **in disguise**.
   - At any moment, your Hidden Queen can execute full **Queen moves** (sliding any number of squares horizontally, vertically, or diagonally).

3. **The Reveal**:
   - The moment your Hidden Queen performs a non-pawn move (such as sliding across files/ranks, moving backwards, or moving diagonally to an unoccupied square), its disguise is broken!
   - Its sprite instantly transforms into a full Queen with an announcement and celebratory fanfare!

4. **Complete FIDE Chess Rules**:
   - Castling (kingside and queenside) with strict rights tracking and revocation on King/Rook move or capture.
   - En passant captures.
   - Interactive pawn promotion choice (Queen, Rook, Bishop, Knight).
   - Check, Checkmate, and Stalemate.
   - Threefold Repetition detection.
   - 50-Move Rule.
   - Insufficient Material detection.

---

## ✨ Features

- **🤖 Stockfish 19 Integration with 3 Difficulty Levels**:
  - **Easy (Casual)**: Skill Level 1, depth 2, relaxed play for beginners.
  - **Medium (Club Player)**: Skill Level 8, depth 6, solid positional play.
  - **Hard (Grandmaster Stockfish)**: Skill Level 20, depth 12+, top engine strength.
  - Built-in Minimax fallback if Stockfish binary is not present.
- **🎮 Game Modes**:
  - **Player vs Computer (Stockfish AI)**.
  - **Local 2-Player (PvP)**: Pass-and-play matches.
- **♟️ Direct On-Board Selection**:
  - No pop-up row of pawns! Click any pawn square directly on the board to select your Hidden Queen (with glowing pulsing indicators).
  - "Auto-Pick HQ" button for instant random selection.
- **🎨 Themes & Styles**:
  - **Board Themes**: Ocean Slate, Classic Wood, and Emerald Forest.
  - **Piece Styles**: Alt (Chess.com style) and Standard (Lichess style).
- **⏱️ Chess Clocks**: Integrated 10:00 blitz / rapid clock with active turn highlights.
- **📜 Move History**: Standard Algebraic Notation (SAN) log with auto-scroll.
- **↩️ Undo Move**: Step back moves at any time (undoes both AI and player moves in PvAI).
- **🔊 Procedural Sound Effects**: Crisp audio for moves, captures, checks, game over, and Hidden Queen reveals (generated dynamically without external sound files).

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- `pygame-ce` (Community Edition)
- `stockfish`

### Installation

```bash
git clone https://github.com/mr-zero0/HiddenQueenChess.git
cd HiddenQueenChess
pip install -r requirements.txt
```

### Running the Game

Launch the Python game:

```bash
python main.py
```

### Running Tests

Execute the 16 unit tests:

```bash
pytest test_chess.py -v
```

---

## 📁 Project Architecture

```
HiddenQueenChess/
├── main.py                  # Launcher entrypoint
├── requirements.txt         # Dependencies (pygame-ce, pytest, stockfish)
├── test_chess.py            # Complete test suite (16 tests covering engine, rules, AI)
├── stockfish/               # Official Stockfish 19 executable
│   └── stockfish.exe
├── assets/
│   └── images/              # Chess piece graphics (Alt & Standard sets)
├── chess_engine/            # Pure Python chess engine & AI
│   ├── __init__.py
│   ├── piece.py             # Piece model and Hidden Queen state
│   ├── board.py             # Move generator, FEN, legality, check/checkmate, notation
│   └── ai.py                # Stockfish integration, 3 difficulty levels & Hidden Queen tactics
└── chess_gui/               # Pygame interface
    ├── __init__.py
    ├── assets.py            # Sprite loader, color themes, synthesized audio
    ├── ui_elements.py       # Buttons, clock timers, notifications, move log
    └── game_app.py          # Pygame main loop, on-board HQ selection, rendering
```

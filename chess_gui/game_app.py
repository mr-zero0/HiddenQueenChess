"""
Main Pygame application for Hidden Queen Chess.
Coordinates rendering, user interactions, Stockfish AI moves, game states, and menus.
Includes support for:
- Direct on-board Hidden Queen pawn selection (clicking pawns directly on the board)
- Stockfish AI with 3 difficulty levels (Easy, Medium, Hard)
- Threefold Repetition, Stalemate, 50-Move Rule, Insufficient Material
- Interactive Pawn Promotion selection
"""
import sys
import random
import pygame
from typing import Optional, Tuple, List

from chess_engine.board import Board, Move, square_to_algebraic, algebraic_to_square
from chess_engine.piece import Piece
from chess_engine.ai import ChessAI, DIFFICULTY_LEVELS
from .assets import (
    AssetManager, THEMES, DARK_BG, PANEL_BG, PANEL_BORDER,
    TEXT_WHITE, TEXT_MUTED, ACCENT_BLUE, ACCENT_GREEN, ACCENT_GOLD, ACCENT_RED
)
from .ui_elements import Button, ChessClock, NotificationBanner, MoveLog


class GameApp:
    def __init__(self, images_dir: str = 'assets/images'):
        pygame.init()
        pygame.display.set_caption("Hidden Queen Chess - Python Edition (with Stockfish)")

        self.width = 1040
        self.height = 720
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_large = pygame.font.SysFont("georgia,serif", 24, bold=True)
        self.font_main = pygame.font.SysFont("segoe ui,arial,sans-serif", 15)
        self.font_bold = pygame.font.SysFont("segoe ui,arial,sans-serif", 15, bold=True)
        self.font_small = pygame.font.SysFont("segoe ui,arial,sans-serif", 12)
        self.font_timer = pygame.font.SysFont("consolas,monospace", 22, bold=True)

        # Engine & Assets
        self.board = Board()
        self.assets = AssetManager(images_dir)
        self.difficulty = 'medium'  # 'easy', 'medium', 'hard'
        self.ai = ChessAI(color='black', difficulty=self.difficulty)

        # Game State
        self.game_mode = 'ai'  # 'ai' or 'pvp'
        self.flipped = False
        self.state = 'SELECT_WHITE_HQ'  # 'SELECT_WHITE_HQ', 'SELECT_BLACK_HQ', 'PLAYING', 'SELECT_PROMOTION', 'GAME_OVER'
        self.selected_sq: Optional[Tuple[int, int]] = None
        self.legal_moves_for_selected: List[Move] = []
        self.pending_promotion_moves: List[Move] = []
        self.mouse_pos = (0, 0)
        self.pulse_timer = 0.0

        # Board dimensions
        self.board_offset_x = 35
        self.board_offset_y = 40
        self.square_size = 80
        self.board_size = self.square_size * 8

        # UI Components
        self.chess_clock = ChessClock(600)
        self.notification = NotificationBanner(self.font_bold)
        self.move_log = MoveLog(
            pygame.Rect(710, 215, 300, 230),
            self.font_main,
            self.font_bold
        )

        # AI Move Delay tracking
        self.ai_thinking = False
        self.ai_think_timer = 0.0

        # Buttons
        self._init_buttons()

        # Start game flow
        self.start_new_game()

    def _init_buttons(self):
        btn_w, btn_h = 144, 32
        x1, x2 = 710, 866

        self.btn_new = Button(pygame.Rect(x1, 460, btn_w, btn_h), "New Game", self.font_bold, self.start_new_game)
        self.btn_undo = Button(pygame.Rect(x2, 460, btn_w, btn_h), "Undo Move", self.font_bold, self.undo_move)

        self.btn_mode = Button(pygame.Rect(x1, 500, btn_w, btn_h), "Mode: vs AI", self.font_bold, self.toggle_mode)
        self.btn_diff = Button(pygame.Rect(x2, 500, btn_w, btn_h), "AI: Medium", self.font_bold, self.cycle_difficulty)

        self.btn_flip = Button(pygame.Rect(x1, 540, btn_w, btn_h), "Flip Board", self.font_bold, self.toggle_flip)
        self.btn_auto_hq = Button(pygame.Rect(x2, 540, btn_w, btn_h), "Auto-Pick HQ", self.font_bold, self.auto_pick_hq)

        self.btn_theme = Button(pygame.Rect(x1, 580, btn_w, btn_h), "Theme", self.font_bold, self.cycle_theme)
        self.btn_pieces = Button(pygame.Rect(x2, 580, btn_w, btn_h), "Pieces: Alt", self.font_bold, self.cycle_pieces)

        self.buttons = [
            self.btn_new, self.btn_undo, self.btn_mode, self.btn_diff,
            self.btn_flip, self.btn_auto_hq, self.btn_theme, self.btn_pieces
        ]

    def start_new_game(self):
        self.board = Board()
        self.chess_clock = ChessClock(600)
        self.selected_sq = None
        self.legal_moves_for_selected.clear()
        self.pending_promotion_moves.clear()
        self.move_log.update_moves([])
        self.ai_thinking = False
        self.state = 'SELECT_WHITE_HQ'
        engine_label = "Stockfish" if self.ai.stockfish else "Minimax"
        self.notification.show(f"Click any White pawn on the board to make it your Hidden Queen! ({engine_label})", ACCENT_GOLD, duration=5.0)

    def toggle_flip(self):
        self.flipped = not self.flipped

    def toggle_mode(self):
        self.game_mode = 'pvp' if self.game_mode == 'ai' else 'ai'
        self.btn_mode.text = "Mode: 2-Player" if self.game_mode == 'pvp' else "Mode: vs AI"
        self.notification.show(f"Game Mode: {'2-Player Local' if self.game_mode == 'pvp' else 'Player vs Computer'}", ACCENT_BLUE)
        self.start_new_game()

    def cycle_difficulty(self):
        diff_order = ['easy', 'medium', 'hard']
        curr_idx = diff_order.index(self.difficulty) if self.difficulty in diff_order else 1
        new_diff = diff_order[(curr_idx + 1) % len(diff_order)]
        self.difficulty = new_diff
        self.ai.set_difficulty(new_diff)
        diff_names = {'easy': 'AI: Easy', 'medium': 'AI: Medium', 'hard': 'AI: Hard'}
        self.btn_diff.text = diff_names.get(new_diff, 'AI: Medium')
        self.notification.show(f"Difficulty set to: {DIFFICULTY_LEVELS[new_diff]['name']}", ACCENT_BLUE, 2.5)

    def cycle_theme(self):
        themes = list(THEMES.keys())
        idx = (themes.index(self.assets.theme_name) + 1) % len(themes)
        self.assets.set_theme(themes[idx])
        self.notification.show(f"Theme: {THEMES[themes[idx]]['name']}", ACCENT_BLUE)

    def cycle_pieces(self):
        new_style = 'standard' if self.assets.piece_style == 'alt' else 'alt'
        self.assets.set_piece_style(new_style)
        self.btn_pieces.text = "Pieces: Lichess" if new_style == 'standard' else "Pieces: Alt"
        self.notification.show(f"Piece Style: {self.btn_pieces.text}", ACCENT_BLUE)

    def auto_pick_hq(self):
        """Randomly pick a hidden queen pawn for the current selecting player."""
        if self.state == 'SELECT_WHITE_HQ':
            idx = random.randint(1, 8)
            pawn_id = f"white-pawn-{idx}"
            self.board.set_hidden_queen('white', pawn_id)
            self.assets.sounds.play_reveal()
            self._advance_hq_selection('white', idx)
        elif self.state == 'SELECT_BLACK_HQ':
            idx = random.randint(1, 8)
            pawn_id = f"black-pawn-{idx}"
            self.board.set_hidden_queen('black', pawn_id)
            self.assets.sounds.play_reveal()
            self._advance_hq_selection('black', idx)

    def undo_move(self):
        if self.state not in ['PLAYING', 'GAME_OVER']:
            return
        if self.game_mode == 'ai' and self.board.turn == 'white' and len(self.board.move_history) >= 2:
            self.board.undo_move()
            self.board.undo_move()
        else:
            self.board.undo_move()

        self.selected_sq = None
        self.legal_moves_for_selected.clear()
        self.pending_promotion_moves.clear()
        self.move_log.update_moves(self.board.move_history)
        self.state = 'PLAYING'
        self.notification.show("Move Undone", ACCENT_BLUE, 1.5)

    def sq_to_screen(self, r: int, c: int) -> Tuple[int, int]:
        disp_r = (7 - r) if self.flipped else r
        disp_c = (7 - c) if self.flipped else c
        x = self.board_offset_x + disp_c * self.square_size
        y = self.board_offset_y + disp_r * self.square_size
        return x, y

    def screen_to_sq(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        if not (self.board_offset_x <= x < self.board_offset_x + self.board_size and
                self.board_offset_y <= y < self.board_offset_y + self.board_size):
            return None
        disp_c = (x - self.board_offset_x) // self.square_size
        disp_r = (y - self.board_offset_y) // self.square_size
        r = (7 - disp_r) if self.flipped else disp_r
        c = (7 - disp_c) if self.flipped else disp_c
        return int(r), int(c)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.handle_event(event)

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def handle_event(self, event: pygame.event.Event):
        for btn in self.buttons:
            btn.handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos

        elif event.type == pygame.MOUSEWHEEL:
            if self.move_log.rect.collidepoint(self.mouse_pos):
                self.move_log.handle_scroll(-event.y)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state in ['SELECT_WHITE_HQ', 'SELECT_BLACK_HQ']:
                self.handle_board_hq_click(event.pos)
            elif self.state == 'SELECT_PROMOTION':
                self.handle_promotion_selection_click(event.pos)
            elif self.state == 'PLAYING':
                self.handle_board_click(event.pos)

    def handle_board_hq_click(self, pos: Tuple[int, int]):
        """Directly clicking a pawn square on the board to designate as the hidden queen."""
        sq = self.screen_to_sq(*pos)
        if not sq:
            return

        r, c = sq
        piece = self.board.grid[r][c]
        active_color = 'white' if self.state == 'SELECT_WHITE_HQ' else 'black'
        expected_rank = 6 if active_color == 'white' else 1

        if piece and piece.color == active_color and piece.piece_type == 'pawn' and r == expected_rank:
            pawn_id = f"{active_color}-pawn-{c+1}"
            self.board.set_hidden_queen(active_color, pawn_id)
            self.assets.sounds.play_reveal()
            self._advance_hq_selection(active_color, c + 1)

    def _advance_hq_selection(self, color: str, col_idx: int):
        col_letter = chr(ord('a') + col_idx - 1)
        if color == 'white':
            self.notification.show(f"White's Secret Queen: {col_letter}2 pawn!", ACCENT_GREEN, 2.5)
            if self.game_mode == 'ai':
                ai_pawn = self.ai.choose_hidden_queen_pawn(self.board)
                self.board.set_hidden_queen('black', ai_pawn)
                self.state = 'PLAYING'
                self.chess_clock.is_running = True
                self.notification.show("Game Started! White to move.", ACCENT_GOLD, 3.0)
            else:
                self.state = 'SELECT_BLACK_HQ'
                self.notification.show("Black (Player 2): Click any Black pawn on the board!", ACCENT_GOLD, 4.0)
        else:
            self.notification.show(f"Black's Secret Queen: {col_letter}7 pawn!", ACCENT_GREEN, 2.5)
            self.state = 'PLAYING'
            self.chess_clock.is_running = True
            self.notification.show("Game Started! White to move.", ACCENT_GOLD, 3.0)

    def handle_board_click(self, pos: Tuple[int, int]):
        sq = self.screen_to_sq(*pos)
        if not sq:
            self.selected_sq = None
            self.legal_moves_for_selected.clear()
            return

        r, c = sq
        clicked_piece = self.board.grid[r][c]

        if self.selected_sq:
            matching_moves = [m for m in self.legal_moves_for_selected if m.to_sq == (r, c)]
            if matching_moves:
                if any(m.promotion_choice for m in matching_moves):
                    self.pending_promotion_moves = matching_moves
                    self.state = 'SELECT_PROMOTION'
                    return
                else:
                    self.execute_player_move(matching_moves[0])
                    return

        # Select friendly piece
        if clicked_piece and clicked_piece.color == self.board.turn:
            self.selected_sq = (r, c)
            all_legal = self.board.get_legal_moves()
            self.legal_moves_for_selected = [m for m in all_legal if m.from_sq == (r, c)]
        else:
            self.selected_sq = None
            self.legal_moves_for_selected.clear()

    def handle_promotion_selection_click(self, pos: Tuple[int, int]):
        modal_w, modal_h = 360, 150
        modal_x = self.board_offset_x + (self.board_size - modal_w) // 2
        modal_y = self.board_offset_y + (self.board_size - modal_h) // 2

        card_w, card_h = 65, 65
        start_x = modal_x + 25
        card_y = modal_y + 60
        options = ['queen', 'rook', 'bishop', 'knight']

        for i, opt in enumerate(options):
            card_rect = pygame.Rect(start_x + i * (card_w + 15), card_y, card_w, card_h)
            if card_rect.collidepoint(pos):
                chosen_move = next((m for m in self.pending_promotion_moves if m.promotion_choice == opt), None)
                if chosen_move:
                    self.state = 'PLAYING'
                    self.pending_promotion_moves.clear()
                    self.execute_player_move(chosen_move)
                return

    def execute_player_move(self, move: Move):
        revealed_hq = move.reveals_hidden_queen
        self.board.make_move(move)
        self.selected_sq = None
        self.legal_moves_for_selected.clear()
        self.move_log.update_moves(self.board.move_history)

        # Sound & Announcements
        if revealed_hq:
            self.assets.sounds.play_reveal()
            owner = 'White' if move.piece.color == 'white' else 'Black'
            self.notification.show(f"SURPRISE! {owner}'s Hidden Queen Revealed!", ACCENT_GOLD, 4.0)
        elif move.captured_piece:
            self.assets.sounds.play_capture()
        else:
            self.assets.sounds.play_move()

        if self.board.is_in_check(self.board.turn):
            self.assets.sounds.play_check()
            self.notification.show("CHECK!", ACCENT_RED, 2.0)

        # Check Game Over
        is_over, reason = self.board.is_game_over()
        if is_over:
            self.state = 'GAME_OVER'
            self.chess_clock.is_running = False
            self.assets.sounds.play_game_over()
            self.notification.show(reason, ACCENT_GOLD, 6.0)
            return

        # Trigger AI if vs AI and black's turn
        if self.game_mode == 'ai' and self.board.turn == 'black':
            self.ai_thinking = True
            self.ai_think_timer = 0.25

    def update(self, dt: float):
        self.notification.update(dt)
        self.pulse_timer += dt * 4.0

        if self.state == 'PLAYING':
            self.chess_clock.update(dt, self.board.turn)
            if self.chess_clock.white_time <= 0:
                self.state = 'GAME_OVER'
                self.notification.show("Black wins on time!", ACCENT_GOLD, 6.0)
            elif self.chess_clock.black_time <= 0:
                self.state = 'GAME_OVER'
                self.notification.show("White wins on time!", ACCENT_GOLD, 6.0)

            # AI processing
            if self.ai_thinking:
                self.ai_think_timer -= dt
                if self.ai_think_timer <= 0:
                    self.ai_thinking = False
                    ai_move = self.ai.get_best_move(self.board)
                    if ai_move:
                        self.execute_player_move(ai_move)

    def draw(self):
        self.screen.fill(DARK_BG)

        self.draw_board()
        self.draw_pieces()
        self.draw_highlights()
        self.draw_side_panel()
        self.draw_notifications()

        if self.state == 'SELECT_PROMOTION':
            self.draw_promotion_modal()
        elif self.state == 'GAME_OVER':
            self.draw_game_over_banner()

    def draw_board(self):
        theme = self.assets.get_theme()
        border_rect = pygame.Rect(
            self.board_offset_x - 4,
            self.board_offset_y - 4,
            self.board_size + 8,
            self.board_size + 8
        )
        pygame.draw.rect(self.screen, theme['board_bg'], border_rect, border_radius=6)

        for r in range(8):
            for c in range(8):
                disp_r = (7 - r) if self.flipped else r
                disp_c = (7 - c) if self.flipped else c
                color = theme['light'] if (r + c) % 2 == 0 else theme['dark']
                sq_rect = pygame.Rect(
                    self.board_offset_x + disp_c * self.square_size,
                    self.board_offset_y + disp_r * self.square_size,
                    self.square_size,
                    self.square_size
                )
                pygame.draw.rect(self.screen, color, sq_rect)

        # Coordinate labels
        for i in range(8):
            col_idx = (7 - i) if self.flipped else i
            file_char = chr(ord('a') + col_idx)
            lbl = self.font_small.render(file_char, True, TEXT_MUTED)
            self.screen.blit(lbl, (self.board_offset_x + i * self.square_size + 36, self.board_offset_y + self.board_size + 6))

            row_idx = i if self.flipped else (7 - i)
            rank_char = str(row_idx + 1)
            lbl2 = self.font_small.render(rank_char, True, TEXT_MUTED)
            self.screen.blit(lbl2, (self.board_offset_x - 18, self.board_offset_y + i * self.square_size + 32))

    def draw_highlights(self):
        theme = self.assets.get_theme()

        # On-Board Hidden Queen Selection Highlighting
        if self.state in ['SELECT_WHITE_HQ', 'SELECT_BLACK_HQ']:
            active_rank = 6 if self.state == 'SELECT_WHITE_HQ' else 1
            pulse = int((abs((self.pulse_timer % 2.0) - 1.0)) * 60) + 180  # pulse alpha 180..240

            for c in range(8):
                sx, sy = self.sq_to_screen(active_rank, c)
                sq_rect = pygame.Rect(sx, sy, self.square_size, self.square_size)
                is_hover = sq_rect.collidepoint(self.mouse_pos)

                s = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                fill_color = (241, 196, 15, 90 if is_hover else 40)
                s.fill(fill_color)
                self.screen.blit(s, (sx, sy))

                # Glowing border
                border_color = (*ACCENT_GOLD, pulse if not is_hover else 255)
                border_surf = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                pygame.draw.rect(border_surf, border_color, border_surf.get_rect(), width=4 if is_hover else 2, border_radius=4)
                self.screen.blit(border_surf, (sx, sy))

                # Mini prompt banner over hovered pawn
                if is_hover:
                    tip = self.font_small.render("Pick HQ", True, ACCENT_GOLD)
                    self.screen.blit(tip, (sx + 18, sy + 60))
            return

        # Last move highlight
        if self.board.move_history:
            last_move, _ = self.board.move_history[-1]
            for sq in [last_move.from_sq, last_move.to_sq]:
                x, y = self.sq_to_screen(*sq)
                s = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                s.fill(theme['last_move'])
                self.screen.blit(s, (x, y))

        # King in check highlight
        if self.board.is_in_check(self.board.turn):
            king_sq = self.board.find_king(self.board.turn)
            if king_sq:
                kx, ky = self.sq_to_screen(*king_sq)
                s = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                s.fill(theme['check'])
                self.screen.blit(s, (kx, ky))

        # Selected square highlight & target dots
        if self.selected_sq:
            sx, sy = self.sq_to_screen(*self.selected_sq)
            s = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
            s.fill(theme['highlight'])
            self.screen.blit(s, (sx, sy))

            drawn_targets = set()
            for move in self.legal_moves_for_selected:
                if move.to_sq in drawn_targets:
                    continue
                drawn_targets.add(move.to_sq)

                mx, my = self.sq_to_screen(*move.to_sq)
                dot_surf = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                if move.captured_piece or move.is_en_passant:
                    pygame.draw.circle(dot_surf, (231, 76, 60, 200), (self.square_size // 2, self.square_size // 2), self.square_size // 2 - 4, width=5)
                elif move.reveals_hidden_queen:
                    pygame.draw.circle(dot_surf, (241, 196, 15, 230), (self.square_size // 2, self.square_size // 2), 14)
                else:
                    pygame.draw.circle(dot_surf, (46, 204, 113, 190), (self.square_size // 2, self.square_size // 2), 10)
                self.screen.blit(dot_surf, (mx, my))

    def draw_pieces(self):
        for r in range(8):
            for c in range(8):
                piece = self.board.grid[r][c]
                if piece:
                    x, y = self.sq_to_screen(r, c)
                    img = self.assets.load_piece_image(piece.color, piece.display_type, self.square_size)
                    img_rect = img.get_rect(center=(x + self.square_size // 2, y + self.square_size // 2))
                    self.screen.blit(img, img_rect)

                    # Subtle Badge on own unrevealed hidden queen
                    if piece.is_hidden_queen and not piece.is_revealed:
                        show_badge = (piece.color == 'white') or (self.game_mode == 'pvp' and piece.color == 'black')
                        if show_badge:
                            crown_surf = pygame.Surface((18, 18), pygame.SRCALPHA)
                            pygame.draw.circle(crown_surf, (241, 196, 15, 240), (9, 9), 8)
                            pygame.draw.circle(crown_surf, (20, 20, 20), (9, 9), 8, width=1)
                            q_lbl = self.font_small.render("Q", True, (20, 20, 20))
                            crown_surf.blit(q_lbl, (4, 1))
                            self.screen.blit(crown_surf, (x + self.square_size - 22, y + 4))

    def draw_side_panel(self):
        title_surf = self.font_large.render("HIDDEN QUEEN CHESS", True, TEXT_WHITE)
        self.screen.blit(title_surf, (710, 35))

        engine_name = "Stockfish 19" if self.ai.stockfish else "Minimax Engine"
        diff_name = DIFFICULTY_LEVELS[self.difficulty]['name']
        sub_surf = self.font_small.render(f"{engine_name} • {diff_name}", True, ACCENT_GOLD if self.ai.stockfish else TEXT_MUTED)
        self.screen.blit(sub_surf, (710, 65))

        # Black Clock
        b_active = (self.board.turn == 'black' and self.state == 'PLAYING')
        b_color = ACCENT_BLUE if b_active else PANEL_BORDER
        b_rect = pygame.Rect(710, 95, 300, 50)
        pygame.draw.rect(self.screen, PANEL_BG, b_rect, border_radius=8)
        pygame.draw.rect(self.screen, b_color, b_rect, width=2 if b_active else 1, border_radius=8)

        b_name = f"Black ({'AI: ' + self.difficulty.capitalize() if self.game_mode == 'ai' else 'Player 2'})"
        self.screen.blit(self.font_bold.render(b_name, True, TEXT_WHITE), (722, 108))
        b_time_str = self.chess_clock.format_time(self.chess_clock.black_time)
        b_time_surf = self.font_timer.render(b_time_str, True, ACCENT_GOLD if b_active else TEXT_MUTED)
        self.screen.blit(b_time_surf, (920, 106))

        # White Clock
        w_active = (self.board.turn == 'white' and self.state == 'PLAYING')
        w_color = ACCENT_BLUE if w_active else PANEL_BORDER
        w_rect = pygame.Rect(710, 155, 300, 50)
        pygame.draw.rect(self.screen, PANEL_BG, w_rect, border_radius=8)
        pygame.draw.rect(self.screen, w_color, w_rect, width=2 if w_active else 1, border_radius=8)

        w_name = "White (You)" if self.game_mode == 'ai' else "White (Player 1)"
        self.screen.blit(self.font_bold.render(w_name, True, TEXT_WHITE), (722, 168))
        w_time_str = self.chess_clock.format_time(self.chess_clock.white_time)
        w_time_surf = self.font_timer.render(w_time_str, True, ACCENT_GOLD if w_active else TEXT_MUTED)
        self.screen.blit(w_time_surf, (920, 166))

        # Move Log Widget
        self.move_log.draw(self.screen)

        # Buttons
        for btn in self.buttons:
            btn.draw(self.screen)

    def draw_notifications(self):
        self.notification.draw(self.screen, 710, 625, 300)

    def draw_promotion_modal(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        modal_w, modal_h = 360, 150
        modal_x = self.board_offset_x + (self.board_size - modal_w) // 2
        modal_y = self.board_offset_y + (self.board_size - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)

        pygame.draw.rect(self.screen, PANEL_BG, modal_rect, border_radius=12)
        pygame.draw.rect(self.screen, ACCENT_GOLD, modal_rect, width=3, border_radius=12)

        t_surf = self.font_large.render("Promote Your Pawn", True, ACCENT_GOLD)
        self.screen.blit(t_surf, t_surf.get_rect(center=(modal_rect.centerx, modal_y + 30)))

        card_w, card_h = 65, 65
        start_x = modal_x + 25
        card_y = modal_y + 60
        options = ['queen', 'rook', 'bishop', 'knight']
        active_color = self.board.turn

        for i, opt in enumerate(options):
            card_rect = pygame.Rect(start_x + i * (card_w + 15), card_y, card_w, card_h)
            is_hover = card_rect.collidepoint(self.mouse_pos)
            bg = (45, 55, 75) if is_hover else (35, 42, 56)
            b_col = ACCENT_GOLD if is_hover else PANEL_BORDER

            pygame.draw.rect(self.screen, bg, card_rect, border_radius=8)
            pygame.draw.rect(self.screen, b_col, card_rect, width=2 if is_hover else 1, border_radius=8)

            p_img = self.assets.load_piece_image(active_color, opt, 50)
            img_r = p_img.get_rect(center=card_rect.center)
            self.screen.blit(p_img, img_r)

    def draw_game_over_banner(self):
        banner_w, banner_h = 440, 110
        banner_x = self.board_offset_x + (self.board_size - banner_w) // 2
        banner_y = self.board_offset_y + (self.board_size - banner_h) // 2
        rect = pygame.Rect(banner_x, banner_y, banner_w, banner_h)

        pygame.draw.rect(self.screen, (20, 24, 32, 230), rect, border_radius=10)
        pygame.draw.rect(self.screen, ACCENT_GOLD, rect, width=3, border_radius=10)

        is_over, reason = self.board.is_game_over()
        res_surf = self.font_large.render(reason or "Game Over", True, ACCENT_GOLD)
        self.screen.blit(res_surf, res_surf.get_rect(center=(rect.centerx, rect.y + 35)))

        sub_surf = self.font_main.render("Click 'New Game' to play another match!", True, TEXT_WHITE)
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(rect.centerx, rect.y + 75)))

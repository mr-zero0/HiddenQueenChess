"""
UI Widgets and Components for Pygame Chess: Buttons, Modals, Clocks, Move Log, and Notifications.
"""
import pygame
from typing import Callable, Optional, List, Tuple
from .assets import DARK_BG, PANEL_BG, PANEL_BORDER, TEXT_WHITE, TEXT_MUTED, ACCENT_BLUE, ACCENT_GREEN, ACCENT_GOLD, ACCENT_RED


class Button:
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font,
                 callback: Optional[Callable] = None, bg_color=PANEL_BG,
                 hover_color=ACCENT_BLUE, text_color=TEXT_WHITE, border_color=PANEL_BORDER,
                 border_radius=8, icon: Optional[pygame.Surface] = None):
        self.rect = rect
        self.text = text
        self.font = font
        self.callback = callback
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.border_radius = border_radius
        self.icon = icon
        self.is_hovered = False
        self.is_active = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def draw(self, surface: pygame.Surface):
        color = self.hover_color if self.is_hovered or self.is_active else self.bg_color
        pygame.draw.rect(surface, color, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(surface, self.border_color, self.rect, width=1, border_radius=self.border_radius)

        text_surf = self.font.render(self.text, True, self.text_color)
        total_width = text_surf.get_width() + (self.icon.get_width() + 8 if self.icon else 0)
        start_x = self.rect.centerx - total_width // 2

        if self.icon:
            icon_rect = self.icon.get_rect(midleft=(start_x, self.rect.centery))
            surface.blit(self.icon, icon_rect)
            start_x += self.icon.get_width() + 8

        text_rect = text_surf.get_rect(midleft=(start_x, self.rect.centery))
        surface.blit(text_surf, text_rect)


class ChessClock:
    def __init__(self, initial_seconds: int = 600):  # 10 minutes default
        self.white_time = float(initial_seconds)
        self.black_time = float(initial_seconds)
        self.initial_time = float(initial_seconds)
        self.is_running = False

    def update(self, dt: float, active_turn: str):
        if not self.is_running:
            return
        if active_turn == 'white':
            self.white_time = max(0.0, self.white_time - dt)
        else:
            self.black_time = max(0.0, self.black_time - dt)

    def format_time(self, seconds: float) -> str:
        s = int(seconds)
        minutes = s // 60
        secs = s % 60
        return f"{minutes:02d}:{secs:02d}"


class NotificationBanner:
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.message = ""
        self.color = ACCENT_GOLD
        self.duration = 0.0
        self.max_duration = 3.0

    def show(self, text: str, color=ACCENT_GOLD, duration=3.5):
        self.message = text
        self.color = color
        self.duration = duration
        self.max_duration = duration

    def update(self, dt: float):
        if self.duration > 0:
            self.duration = max(0.0, self.duration - dt)

    def draw(self, surface: pygame.Surface, x: int, y: int, width: int):
        if self.duration <= 0 or not self.message:
            return

        alpha = min(255, int((self.duration / 0.5) * 255)) if self.duration < 0.5 else 255
        banner_surf = pygame.Surface((width, 36), pygame.SRCALPHA)
        banner_rect = banner_surf.get_rect()

        # Background with border
        pygame.draw.rect(banner_surf, (20, 24, 32, alpha), banner_rect, border_radius=8)
        pygame.draw.rect(banner_surf, (*self.color, alpha), banner_rect, width=2, border_radius=8)

        text_surf = self.font.render(self.message, True, self.color)
        text_rect = text_surf.get_rect(center=banner_rect.center)
        banner_surf.blit(text_surf, text_rect)

        surface.blit(banner_surf, (x, y))


class MoveLog:
    def __init__(self, rect: pygame.Rect, font: pygame.font.Font, font_bold: pygame.font.Font):
        self.rect = rect
        self.font = font
        self.font_bold = font_bold
        self.moves: List[Tuple[str, Optional[str]]] = []  # [(white_san, black_san), ...]
        self.scroll_offset = 0
        self.line_height = 24

    def update_moves(self, move_history):
        self.moves.clear()
        current_pair = []
        for move, _ in move_history:
            current_pair.append(move.san)
            if len(current_pair) == 2:
                self.moves.append((current_pair[0], current_pair[1]))
                current_pair = []
        if current_pair:
            self.moves.append((current_pair[0], None))

        # Auto-scroll to bottom
        total_content_height = len(self.moves) * self.line_height
        visible_height = self.rect.height - 35
        if total_content_height > visible_height:
            self.scroll_offset = total_content_height - visible_height
        else:
            self.scroll_offset = 0

    def handle_scroll(self, dy: int):
        self.scroll_offset = max(0, self.scroll_offset + dy * 20)

    def draw(self, surface: pygame.Surface):
        # Panel Background
        pygame.draw.rect(surface, PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, self.rect, width=1, border_radius=8)

        # Header
        header_surf = self.font_bold.render("Move History", True, TEXT_WHITE)
        surface.blit(header_surf, (self.rect.x + 12, self.rect.y + 10))
        pygame.draw.line(surface, PANEL_BORDER, (self.rect.x + 8, self.rect.y + 35),
                         (self.rect.right - 8, self.rect.y + 35))

        # Content area clipping
        content_rect = pygame.Rect(self.rect.x + 12, self.rect.y + 40,
                                   self.rect.width - 24, self.rect.height - 48)
        surface.set_clip(content_rect)

        start_y = content_rect.y - self.scroll_offset
        for i, (w_move, b_move) in enumerate(self.moves):
            y = start_y + (i * self.line_height)
            if y + self.line_height < content_rect.top or y > content_rect.bottom:
                continue

            num_surf = self.font.render(f"{i+1}.", True, TEXT_MUTED)
            surface.blit(num_surf, (content_rect.x, y))

            w_surf = self.font.render(w_move, True, TEXT_WHITE)
            surface.blit(w_surf, (content_rect.x + 40, y))

            if b_move:
                b_surf = self.font.render(b_move, True, TEXT_WHITE)
                surface.blit(b_surf, (content_rect.x + 120, y))

        surface.set_clip(None)

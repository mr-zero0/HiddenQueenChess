"""
Asset loading, scaling, theming, and sound synthesis for Hidden Queen Chess GUI.
"""
import os
import math
import wave
import io
import pygame

# Color palettes
THEMES = {
    'ocean_slate': {
        'name': 'Ocean Slate',
        'light': (120, 155, 185),    # #789bb9
        'dark': (78, 127, 167),      # #4e7fa7
        'highlight': (247, 247, 105, 140),
        'last_move': (205, 210, 106, 120),
        'check': (231, 76, 60, 180),
        'board_bg': (35, 45, 60),
    },
    'classic_wood': {
        'name': 'Classic Wood',
        'light': (240, 217, 181),    # #f0d9b5
        'dark': (181, 136, 99),      # #b58863
        'highlight': (255, 255, 100, 140),
        'last_move': (205, 210, 106, 120),
        'check': (220, 60, 60, 180),
        'board_bg': (40, 30, 20),
    },
    'emerald_forest': {
        'name': 'Emerald Forest',
        'light': (235, 236, 208),
        'dark': (115, 149, 82),
        'highlight': (255, 255, 100, 140),
        'last_move': (186, 202, 68, 120),
        'check': (231, 76, 60, 180),
        'board_bg': (30, 40, 30),
    }
}

DARK_BG = (24, 28, 36)
PANEL_BG = (32, 38, 50)
PANEL_BORDER = (48, 56, 74)
TEXT_WHITE = (240, 244, 248)
TEXT_MUTED = (160, 172, 188)
ACCENT_BLUE = (52, 152, 219)
ACCENT_GREEN = (46, 204, 113)
ACCENT_GOLD = (241, 196, 15)
ACCENT_RED = (231, 76, 60)


def generate_sound(freq_list, duration=0.1, sample_rate=22050, wave_type='sine'):
    """Generate synthesized wav sound without external audio files."""
    try:
        num_samples = int(duration * sample_rate)
        raw_data = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            # Multi-frequency mixing
            val = 0
            for freq, amp in freq_list:
                envelope = math.exp(-3.0 * t / duration)  # decay envelope
                if wave_type == 'sine':
                    val += amp * envelope * math.sin(2.0 * math.pi * freq * t)
                elif wave_type == 'square':
                    s = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
                    val += amp * envelope * s

            val = max(-1.0, min(1.0, val))
            sample = int(val * 32767)
            raw_data.extend(sample.to_bytes(2, byteorder='little', signed=True))

        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(raw_data)
        buf.seek(0)
        return pygame.mixer.Sound(buf)
    except Exception:
        return None


class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.move_sound = generate_sound([(480, 0.4), (240, 0.2)], duration=0.08)
            self.capture_sound = generate_sound([(200, 0.7), (120, 0.5)], duration=0.12)
            self.check_sound = generate_sound([(880, 0.5), (660, 0.3)], duration=0.18)
            self.reveal_sound = generate_sound([(523, 0.4), (659, 0.4), (784, 0.5), (1046, 0.6)], duration=0.35)
            self.game_over_sound = generate_sound([(440, 0.5), (330, 0.5), (220, 0.6)], duration=0.4)
            self.enabled = True
        except Exception:
            self.enabled = False

    def play_move(self):
        if self.enabled and self.move_sound:
            self.move_sound.play()

    def play_capture(self):
        if self.enabled and self.capture_sound:
            self.capture_sound.play()

    def play_check(self):
        if self.enabled and self.check_sound:
            self.check_sound.play()

    def play_reveal(self):
        if self.enabled and self.reveal_sound:
            self.reveal_sound.play()

    def play_game_over(self):
        if self.enabled and self.game_over_sound:
            self.game_over_sound.play()


class AssetManager:
    def __init__(self, images_dir: str = 'assets/images'):
        self.images_dir = images_dir
        self.piece_style = 'alt'  # 'alt' (chesscom) or 'standard' (lichess)
        self.theme_name = 'ocean_slate'
        self.cached_piece_images = {}
        self.square_size = 80
        self.sounds = SoundManager()

    def get_theme(self):
        return THEMES.get(self.theme_name, THEMES['ocean_slate'])

    def set_theme(self, name: str):
        if name in THEMES:
            self.theme_name = name

    def set_piece_style(self, style: str):
        if style in ['alt', 'standard']:
            self.piece_style = style
            self.cached_piece_images.clear()

    def load_piece_image(self, color: str, piece_type: str, square_size: int) -> pygame.Surface:
        """Load and cache a piece sprite."""
        cache_key = (color, piece_type, self.piece_style, square_size)
        if cache_key in self.cached_piece_images:
            return self.cached_piece_images[cache_key]

        suffix = "-alt.png" if self.piece_style == 'alt' else ".png"
        filename = f"{color}-{piece_type}{suffix}"
        filepath = os.path.join(self.images_dir, filename)

        if not os.path.exists(filepath):
            # Fallback to standard if alt doesn't exist
            filepath = os.path.join(self.images_dir, f"{color}-{piece_type}.png")

        if os.path.exists(filepath):
            try:
                img = pygame.image.load(filepath).convert_alpha()
                # Scale smoothly with a small padding so pieces don't touch the borders
                pad = max(4, int(square_size * 0.08))
                target_size = square_size - (pad * 2)
                img = pygame.transform.smoothscale(img, (target_size, target_size))
                self.cached_piece_images[cache_key] = img
                return img
            except Exception as e:
                print(f"Error loading {filepath}: {e}")

        # Fallback procedural surface if file is missing
        surf = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
        color_rgb = (255, 255, 255) if color == 'white' else (40, 40, 40)
        pygame.draw.circle(surf, color_rgb, (square_size // 2, square_size // 2), square_size // 3)
        self.cached_piece_images[cache_key] = surf
        return surf

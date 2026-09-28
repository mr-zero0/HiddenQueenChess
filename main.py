"""
Hidden Queen Chess - Python Edition
Entrypoint for launching the game.
"""
import sys
import os

# Ensure current directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chess_gui.game_app import GameApp


def main():
    print("Launching Hidden Queen Chess...")
    app = GameApp()
    app.run()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Chalkboard: the Animatic's card beside the speaker, drawn in chalk on a green board. Every sketch is inverted to chalk-white and laid over the board.

    python3 build.py FOLDER [--frames]

It runs the Animatic's own engine (podcast-motion-animatic/scripts), with the card layout and the blueprint treatment on a plain board with no grid.
show.json "looks": {"chalkboard": {...}} overrides any of PALETTE below. 16:9 only, like the card layout. Writes variant_chalkboard/.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-motion-animatic' / 'scripts'))
import build as engine
import animatic_cards

engine.KEY = 'chalkboard'
engine.PALETTE = {'layout': 'card', 'blueprint': True, 'grid': False, 'sketch': True, 'paper': '#24382E', 'ink': '#F1F3EC', 'pencil': '#BFCBBB', 'accent': '#F2D16B'}

if __name__ == '__main__':
    if '--ratio' not in sys.argv:
        sys.argv += ['--ratio', '16x9']
    animatic_cards.install(engine)
    engine.kit.main(engine)

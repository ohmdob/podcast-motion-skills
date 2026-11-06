#!/usr/bin/env python3
"""Photo Card: the Animatic's card beside the speaker, with each picture kept in full colour as a framed photograph instead of a pencil sketch.

    python3 build.py FOLDER [--frames]

It runs the Animatic's own engine (podcast-motion-animatic/scripts), with the card layout, colour pictures and a clean editorial type.
show.json "looks": {"photo-card": {...}} overrides any of PALETTE below. 16:9 only, like the card layout. Writes variant_photo_card/.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-motion-animatic' / 'scripts'))
import build as engine
import animatic_cards

engine.KEY = 'photo-card'
engine.PALETTE = {'layout': 'card', 'colour': True, 'sketch': False, 'paper': '#FFFFFF', 'ink': '#15181C', 'pencil': '#5B6470', 'accent': '#E8452C'}
engine.FONTS = [('Mitr', 'Mitr-SemiBold.ttf', '400')]
engine.FONT = 'Mitr-SemiBold.ttf'
engine.FAM = '"Mitr", sans-serif'

if __name__ == '__main__':
    if '--ratio' not in sys.argv:
        sys.argv += ['--ratio', '16x9']
    animatic_cards.install(engine)
    engine.kit.main(engine)

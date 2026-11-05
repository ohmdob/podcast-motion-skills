#!/usr/bin/env python3
"""A paid Precise Edit barely opened a thin closed mouth, so this one is painted: a small open mouth in the portrait's own ink, on skin taken from just below. Free.
    python3 paint_mouth.py BASE.png OUT.png CX CY WIDTH HEIGHT"""
import sys
from PIL import Image, ImageDraw
base, out = sys.argv[1], sys.argv[2]
cx, cy, w, h = [int(v) for v in sys.argv[3:7]]
k, pad = 4, 14
im = Image.open(base).convert('RGB')
bw, bh = w + 2 * pad, h + 2 * pad
lay = Image.new('RGBA', (bw * k, bh * k), (0, 0, 0, 0)); dr = ImageDraw.Draw(lay)
P = lambda pts: [((pad + w * a) * k, (pad + h * b) * k) for a, b in pts]
shape = P([(0, .32), (.5, .1), (1, .26), (.82, .82), (.5, 1), (.2, .84)])
dr.polygon(shape, fill=(84, 34, 34, 255)); dr.line(shape + shape[:1], fill=(38, 22, 20, 255), width=4 * k, joint='curve')
dr.polygon(P([(.16, .3), (.5, .16), (.86, .27), (.74, .46), (.26, .48)]), fill=(250, 246, 240, 255))
skin = im.crop((cx - 96, cy + 36, cx + 96, cy + 54)).resize((192, 64)); im.paste(skin, (cx - 96, cy - 44))
small = lay.resize((bw, bh), Image.LANCZOS); im.paste(small, (cx - w // 2 - pad, cy - h // 2 - pad), small)
im.save(out)

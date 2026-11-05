#!/usr/bin/env python3
"""The film's set, drawn by hand in the blueprint: walls, a viewport with stars sliding past, a console with lights. Run it once to write assets/set.png and assets/set_front.png.
scripted_source.py then loads it as hosts.json's "live" and calls behind() and front() on every drawing."""
import random
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
NEBULA = next(ROOT.glob('episodes/*/clips/*/assets_src/panels/raw/nebula.png'), None)
W, H = 1920, 1080
NAVY, GRID, WALL, LINE, AMBER, TEAL = (10, 26, 51), (19, 42, 78), (46, 88, 140), (156, 196, 228), (255, 181, 71), (70, 200, 220)
VP = (800, 96, 1120, 640); vw, vh = VP[2] - VP[0], VP[3] - VP[1]
random.seed(21)
wob = lambda a=2.0: random.uniform(-a, a)
stars = [(random.uniform(0, vw), random.uniform(0, vh), random.choice((1, 1, 2, 2, 3)), random.uniform(.8, 3)) for _ in range(70)]
LEDS = [(x + 18 + k * 20, 1036, random.choice((AMBER, TEAL))) for x in range(40, W - 40, 150) for k in range(4)]
SIDE = [(x, 300 + k * 44, random.choice((AMBER, TEAL))) for x in (14, 1906) for k in range(12)]
mask = Image.new('L', (vw, vh), 0)
ImageDraw.Draw(mask).polygon([(46, 0), (vw - 46, 0), (vw, 46), (vw, vh - 46), (vw - 46, vh), (46, vh), (0, vh - 46), (0, 46)], fill=255)
sky = Image.blend(Image.new('RGB', (vw, vh), (4, 10, 24)), Image.open(NEBULA).convert('RGB').crop((480, 120, 480 + vw, 120 + vh)), .85) if NEBULA else Image.new('RGB', (vw, vh), (4, 10, 24))


def behind(frame, s):
    vp = sky.copy(); d = ImageDraw.Draw(vp)
    for sx, sy, r, sp in stars:
        x = (sx - s * sp) % vw
        d.ellipse((x - r, sy - r, x + r, sy + r), fill=(235, 245, 255))
    frame.paste(vp, VP[:2], mask)


def front(frame, s):
    d = ImageDraw.Draw(frame); random.seed(1000 + s // 3)
    for x, y, col in LEDS + SIDE:
        if random.random() < .55:
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=col)


if __name__ == '__main__':
    random.seed(22)
    im = Image.new('RGB', (W, H), NAVY); d = ImageDraw.Draw(im)
    for x in range(0, W, 60): d.line((x, 0, x, H), fill=GRID, width=1)
    for y in range(0, H, 60): d.line((0, y, W, y), fill=GRID, width=1)
    def box(x0, y0, x1, y1, col=WALL, w=3):
        pts = [(x0 + wob(), y0 + wob()), (x1 + wob(), y0 + wob()), (x1 + wob(), y1 + wob()), (x0 + wob(), y1 + wob())]
        d.line(pts + pts[:1], fill=col, width=w, joint='curve')
    for b in ((30, 40, 770, 960), (1150, 40, 1890, 960), (70, 80, 300, 230), (1620, 80, 1850, 230)):
        box(*b)
    for y in (20, 34):
        d.line([(x, y + wob(1.2)) for x in range(0, W + 80, 80)], fill=WALL, width=2)
    for x0, x1 in ((30, 770), (1150, 1890)):
        for x in range(x0 + 30, x1, 90):
            for y in (52, 948):
                d.ellipse((x - 4, y - 4, x + 4, y + 4), outline=WALL, width=2)
    for k, col, wd in ((0, LINE, 6), (8, WALL, 3)):
        pts = [(VP[0] + 46 - k, VP[1] - k), (VP[2] - 46 + k, VP[1] - k), (VP[2] + k, VP[1] + 46 - k), (VP[2] + k, VP[3] - 46 + k), (VP[2] - 46 + k, VP[3] + k), (VP[0] + 46 - k, VP[3] + k), (VP[0] - k, VP[3] - 46 + k), (VP[0] - k, VP[1] + 46 - k)]
        d.line(pts + pts[:1], fill=col, width=wd, joint='curve')
    (ROOT / 'assets').mkdir(exist_ok=True); im.save(ROOT / 'assets/set.png')
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    dr.rectangle((0, 972, W, H), fill=(14, 36, 68, 255))
    dr.line([(i, 972 + wob(1.6)) for i in range(-20, W + 260, 120)], fill=LINE + (255,), width=5, joint='curve')
    dr.line([(i, 990 + wob(1.2)) for i in range(-20, W + 260, 120)], fill=WALL + (255,), width=2, joint='curve')
    for x in range(40, W - 40, 150):
        dr.rectangle((x, 1016, x + 98, 1056), outline=WALL + (255,), width=2)
    for x, y in ((690, 893), (1215, 893)):      # low and inside each host's half, so a close-up never catches half a mic
        dr.line([(x, y + 78), (x, 972)], fill=LINE + (255,), width=8)
        dr.ellipse((x - 52, 962, x + 52, 984), fill=(30, 48, 78, 255), outline=LINE + (255,), width=4)
        dr.rounded_rectangle((x - 38, y - 76, x + 38, y + 78), radius=38, fill=(30, 40, 60, 255), outline=LINE + (255,), width=5)
        for k in range(5):
            yy = y - 44 + k * 18; dr.line([(x - 26, yy), (x + 26, yy)], fill=(120, 150, 180, 255), width=3)
        dr.rectangle((x - 40, y + 20, x + 40, y + 34), fill=LINE + (255,))
    ov.save(ROOT / 'assets/set_front.png')
    print('OK: assets/set.png, assets/set_front.png')

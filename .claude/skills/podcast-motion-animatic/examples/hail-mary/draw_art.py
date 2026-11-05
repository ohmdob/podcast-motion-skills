#!/usr/bin/env python3
"""The drawings this film made for free, as worked examples: a sun flipbook, Rocky's walk and happy cycles, a solid ship, a nebula and stars.
    python3 draw_art.py PANELS_FOLDER
Rocky is drawn from memory of the novel's description, not from the film's design. The ship is generic, not the film's.
Folders follow animatic_cards.py: <folder>/x.png is line art, turned into blueprint by the build; raw/x.png is used as drawn."""
import math, random, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ni
P = Path(sys.argv[1]); R = P / 'rocky_frames'; R.mkdir(parents=True, exist_ok=True); RAW = P / 'raw'; RAW.mkdir(exist_ok=True); F = P / 'sun_frames'; F.mkdir(exist_ok=True)
W, H = 1700, 860; INK = (20, 22, 26)
cx, cy, RD, N = 850, 430, 235, 18
def draw_sun(n):
    p = .2 + .8 * n / (N - 1)
    random.seed(100 + n); im = Image.new('RGB', (W, H), (255, 255, 255)); d = ImageDraw.Draw(im)
    def stroke(a, b, w=4, wob=2.5):
        pts = [(a[0] + (b[0] - a[0]) * i / 9 + random.uniform(-wob, wob), a[1] + (b[1] - a[1]) * i / 9 + random.uniform(-wob, wob)) for i in range(10)]
        d.line(pts, fill=INK, width=w, joint='curve')
    sx, sy = cx + RD * (1.9 - 1.6 * p), cy - RD * (1.2 - 1.0 * p); sr = RD * 1.12
    for k in range(3):
        off = random.uniform(0, 6.28); r0 = RD + random.uniform(-3, 3)
        d.line([(cx + (r0 + 3 * math.sin(a * .05 + off)) * math.cos(math.radians(a) + off), cy + (r0 + 3 * math.sin(a * .05 + off)) * math.sin(math.radians(a) + off)) for a in range(0, 375, 5)], fill=INK, width=6 if k == 0 else 3, joint='curve')
    for i in range(20):
        a = 2 * math.pi * i / 20 + .08
        x0, y0 = cx + (RD + 40) * math.cos(a), cy + (RD + 40) * math.sin(a)
        dark = max(0.0, 1 - math.hypot(x0 - sx, y0 - sy) / (RD * 2.4))      # rays near the shadow go first
        base = 175 if i % 2 else 115
        ln = base * (1 - min(1, p * .55 + dark * 1.1))
        if ln > 14:
            stroke((x0, y0), (cx + (RD + 40 + ln) * math.cos(a), cy + (RD + 40 + ln) * math.sin(a)), 7 if ln > 70 else 4, 2)
    inside = lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 < (RD - 5) ** 2
    shade = lambda x, y: (x - sx) ** 2 + (y - sy) ** 2 < sr ** 2
    def hatch(step, slope, w):
        for c in range(-2 * W, 2 * W, step):
            run = []
            for x in range(cx - RD, cx + RD, 6):
                y = slope * x + c
                if inside(x, y) and shade(x, y):
                    run.append((x + random.uniform(-1.5, 1.5), y + random.uniform(-1.5, 1.5)))
                else:
                    if len(run) > 1: d.line(run, fill=INK, width=w)
                    run = []
            if len(run) > 1: d.line(run, fill=INK, width=w)
    hatch(22, 1.0, 4); hatch(28, -.9, 3); hatch(17, .25, 2)
    return im.filter(ImageFilter.GaussianBlur(.5))
for n in range(N):
    im = draw_sun(n); im.save(F / f'f{n:02d}.png')
    if n == 0: im.save(P / 'sun.png')


def rocky(legs, bob, seed):
    random.seed(seed); im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im); wob = lambda a=2.0: random.uniform(-a, a)
    cx, cy = 850, 400 + bob
    def line(pts, w=6):
        d.line([(x + wob(), y + wob()) for x, y in pts], fill=INK, width=w, joint='curve')
    def limb(a, b, w0, w1):
        """A tapered segment: a filled shape with an ink outline, so a leg has weight."""
        dx, dy = b[0] - a[0], b[1] - a[1]; n = math.hypot(dx, dy) or 1; nx, ny = -dy / n, dx / n
        pts = [(a[0] + nx * w0 + wob(), a[1] + ny * w0 + wob()), (b[0] + nx * w1 + wob(), b[1] + ny * w1 + wob()), (b[0] - nx * w1 + wob(), b[1] - ny * w1 + wob()), (a[0] - nx * w0 + wob(), a[1] - ny * w0 + wob())]
        d.polygon(pts, fill='white'); d.line(pts + pts[:1], fill=INK, width=6, joint='curve')
    order = [0, 4, 1, 3, 2]     # the far legs first
    for i in order:
        hx, hy, fx, fy = legs[i]; sx, sy = cx + hx, cy + hy
        out = 1 if fx >= sx else -1
        kx, ky = sx + (fx - sx) * .62 + out * 26, min(sy, fy) - 128 - abs(hx) * .22       # a high knee, like a spider's
        limb((sx, sy), (kx, ky), 21, 14); limb((kx, ky), (fx, fy), 14, 7)
        d.ellipse((kx - 17, ky - 17, kx + 17, ky + 17), fill='white', outline=INK, width=6)
        for a in (-.8, 0, .8):
            line([(fx, fy), (fx + 30 * math.sin(a), fy + 18 * math.cos(a))], 7)
    base = [(-190, 30), (-132, -82), (-20, -132), (112, -98), (192, 18), (128, 104), (-110, 110)]
    outline = []
    for k in range(len(base)):       # a broken, rocky edge
        x0, y0 = base[k]; x1, y1 = base[(k + 1) % len(base)]
        outline.append((cx + x0, cy + y0)); outline.append((cx + (x0 + x1) / 2 + wob(11), cy + (y0 + y1) / 2 + wob(11)))
    d.polygon(outline, fill='white'); d.line(outline + outline[:1], fill=INK, width=9, joint='curve')
    inner = [(cx + x * .46 - 8 + wob(4), cy + y * .46 - 14 + wob(4)) for x, y in base[:5]]
    d.line(inner + inner[:1], fill=INK, width=5, joint='curve')
    for k, q in enumerate(inner):    # plates from the crown out to the edge
        x, y = base[k]; line([q, (cx + x * .97, cy + y * .97)], 5)
    for k in range(38):      # the shaded underside
        x = cx - 150 + k * 8; y0 = cy + 44 + 14 * math.sin(k * .9)
        line([(x, y0), (x + 13, y0 + 44 - abs(k - 19) * 1.1)], 3)
    return im.filter(ImageFilter.GaussianBlur(.5))
HIPS = [(-120, 40), (-62, 76), (2, 88), (66, 76), (124, 40)]; BASE = [-300, -150, 0, 150, 300]
N = 8
for n in range(N):      # walk: the feet swing in turn, one or two lifted at a time
    legs = []
    for i, ((hx, hy), bx) in enumerate(zip(HIPS, BASE)):
        ph = 2 * math.pi * (n / N + i * 2 / 5)
        legs.append((hx, hy, 850 + bx * 1.12 + 48 * math.cos(ph), 700 - 56 * max(0, math.sin(ph))))
    rocky(legs, 7 * math.sin(4 * math.pi * n / N), 10 + n).save(R / f'w{n}.png')
for n in range(6):      # happy: legs thrown up by turns
    legs = []
    for i, ((hx, hy), bx) in enumerate(zip(HIPS, BASE)):
        up = (i + n) % 2 == 0
        legs.append((hx, hy, 850 + bx * (1.5 if up else 1.05), 700 - (330 if up else 0)))
    rocky(legs, -16 if n % 2 else 0, 40 + n).save(R / f'h{n}.png')
Image.open(R / 'w0.png').save(P / 'rocky.png')
# the ship, nose to the right, solid so the nebula passes behind it. A generic long-haul ship, not the film's.
LN, FILL, HI = (223, 243, 255, 255), (16, 40, 74, 255), (255, 181, 71, 255)
sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(sh); random.seed(3); wb = lambda a=2.0: random.uniform(-a, a)
def part(pts, fill=FILL, w=8):
    q = [(x + wb(), y + wb()) for x, y in pts]; d.polygon(q, fill=fill); d.line(q + q[:1], fill=LN, width=w, joint='curve')
cy = 430
part([(405, cy - 58), (345, cy - 92), (345, cy + 92), (405, cy + 58)])     # the nozzle
part([(470, cy - 62), (390, cy - 210), (450, cy - 210), (610, cy - 62)]); part([(470, cy + 62), (390, cy + 210), (450, cy + 210), (610, cy + 62)])     # fins
part([(405, cy - 72), (1060, cy - 72), (1270, cy - 26), (1335, cy), (1270, cy + 26), (1060, cy + 72), (405, cy + 72)])    # the long hull
for x in (620, 860):       # the crew rings
    part([(x - 42, cy - 150), (x + 42, cy - 150), (x + 62, cy), (x + 42, cy + 150), (x - 42, cy + 150), (x - 62, cy)])
    d.line([(x + wb(), cy - 150), (x + wb(), cy + 150)], fill=LN, width=4)
for x in (480, 730, 985, 1100):
    d.line([(x + wb(), cy - 72), (x + wb(), cy + 72)], fill=LN, width=3)
for x in range(1000, 1190, 44):     # the windows
    d.ellipse((x - 11, cy - 34, x + 11, cy - 12), outline=HI, width=5)
d.line([(405, cy + 34), (1200, cy + 34)], fill=HI, width=4)
sh.save(RAW / 'ship_art.png')
# the nebula: soft fractal cloud in teal, violet and a little amber, on black so the build can lay it over the blueprint
rng = np.random.default_rng(5); NW, NH = 2500, 860
def noise(seed):
    r = np.random.default_rng(seed); out = np.zeros((NH // 2, NW // 2), np.float32)
    for s, a in ((90, 1.0), (42, .55), (18, .3), (7, .16)):
        n = ni.gaussian_filter(r.standard_normal((NH // 2, NW // 2)).astype(np.float32), s, mode='wrap'); out += a * n / n.std()
    return (out - out.min()) / np.ptp(out)
def tone(x, lo, hi):
    return np.clip((x - lo) / (hi - lo), 0, 1) ** 1.7
A, B, D = noise(1), noise(2), noise(3)
rgb = np.zeros((NH // 2, NW // 2, 3), np.float32)
for ch, col in ((tone(A, .46, .85), (47, 167, 201)), (tone(B, .5, .86), (138, 91, 214)), (tone(D, .62, .92), (255, 181, 71))):
    rgb += ch[..., None] * np.array(col, np.float32) * .6
Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((NW, NH), Image.BICUBIC).save(RAW / 'nebula.png')
st = Image.new('RGB', (NW, NH), 'black'); d = ImageDraw.Draw(st); random.seed(9)
for _ in range(240):
    x, y, r = random.randint(0, NW), random.randint(0, NH), random.choice((1, 1, 1, 2, 2, 3)); v = random.randint(150, 255)
    d.ellipse((x - r, y - r, x + r, y + r), fill=(v, v, min(255, v + 10)))
    if r == 3:
        d.line((x - 10, y, x + 10, y), fill=(v, v, v), width=1); d.line((x, y - 10, x, y + 10), fill=(v, v, v), width=1)
st.save(RAW / 'stars.png')
print('OK')

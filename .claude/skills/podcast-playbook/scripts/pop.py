"""Pop Studio: the look of variant B, shared by the clip and the full episode.

The medium is a painted TV set. The speakers are cut out in natural colour and stand in front of flat colour fields;
behind each one is a painted arch or disc that springs up on every cut. Words sit on the field, behind the people, and
real objects pop in beside them. The ground changes by chapter, which is what keeps a long episode from feeling like one frame.

    ground     one flat colour per chapter, no gradients
    arches     two more colours from the same palette; they mark who is on screen
    type       Mitr Bold, measured with the real font, so a line can't run off the frame
    objects    photographs cut out with cutout_still.swift
    motion     springs on scale and position only; an element arrives once, then holds while it is read
"""
import html, re
from pathlib import Path
import numpy as np
from PIL import ImageFont
import studio

W, H = 1920, 1080
TOMATO, MANGO, MINT, SKY, PINK = '#FF5A36', '#FFC21A', '#0FB98E', '#1F6FE5', '#FF9EC4'
INK_T, INK_M, INK_G, INK_P = '#2A0E08', '#2A1A00', '#06362B', '#3A0A24'

MINT_P = dict(name='mint', g=MINT, a=MANGO, b=TOMATO, ink=INK_G, hero=INK_G, mark=MANGO, mink=INK_M, flood=MANGO, fink=INK_M)
TOMATO_P = dict(name='tomato', g=TOMATO, a=MANGO, b=PINK, ink=INK_T, hero='#FFFFFF', mark=MANGO, mink=INK_M, flood=MANGO, fink=INK_M)
SKY_P = dict(name='sky', g=SKY, a=MANGO, b=TOMATO, ink='#FFFFFF', hero=MANGO, mark=MANGO, mink=INK_M, flood=MANGO, fink=INK_M)
MANGO_P = dict(name='mango', g=MANGO, a=TOMATO, b=MINT, ink=INK_M, hero=INK_M, mark=TOMATO, mink=INK_T, flood=TOMATO, fink=INK_T)
PINK_P = dict(name='pink', g=PINK, a=TOMATO, b=MANGO, ink=INK_P, hero=INK_P, mark=MANGO, mink=INK_M, flood=TOMATO, fink=INK_T)
CYCLE = [TOMATO_P, SKY_P, MANGO_P, PINK_P, MINT_P]
SPLIT_X = 800     # where the two people divide, in source pixels


def apply_show(show):
    """A show can recolour any palette by name, from looks.pop-studio.palettes in show.json. Keep each ground's ink readable, and judge it on real frames first."""
    global SPLIT_X
    SPLIT_X = show.get('body_split_x', 800)
    over = show.get('looks', {}).get('pop-studio', {}).get('palettes', {})
    for p in CYCLE:
        p.update(over.get(p['name'], {}))

_FONT_DIR = studio.FONTS
FONT_FILES = {700: 'Mitr-Bold.ttf', 600: 'Mitr-SemiBold.ttf'}
_fonts = {}


def measure(text, size, wt=700):
    f = _fonts.setdefault(wt, ImageFont.truetype(str(_FONT_DIR / FONT_FILES[wt]), 200))
    return f.getlength(text) * size / 200


def fit(text, width, base, minimum=60, max_lines=2, wt=700):
    """The largest size at which the text fits. A number stays with its unit."""
    text = re.sub(r'(\d) (?=\S)', '\\1\u00a0', text).replace('≠ ', '≠\u00a0')
    text = text.replace(' ≠', '\n≠')
    if '\n' in text:
        text = re.sub(r'(?<=\S) (?=\d)', '\u00a0', text)
    size = base
    lines = [text]
    while size >= minimum:
        lines = []
        for para in text.split('\n'):
            cur = ''
            for w in para.split(' '):
                t_ = (cur + ' ' + w).strip()
                if measure(t_, size, wt) > width and cur:
                    lines.append(cur)
                    cur = w
                else:
                    cur = t_
            lines.append(cur)
        if len(lines) <= max_lines and all(measure(x, size, wt) <= width for x in lines):
            return size, lines
        size -= 4
    print(f'  does not fit at {minimum}px: {text}')
    return minimum, lines


def e(x):
    return html.escape(x)


CSS = f'''@font-face {{ font-family: "Mitr"; src: url("assets/fonts/Mitr-Bold.ttf") format("truetype"); font-weight: 700; }}
    @font-face {{ font-family: "Mitr"; src: url("assets/fonts/Mitr-SemiBold.ttf") format("truetype"); font-weight: 600; }}
    .ground {{ position: absolute; inset: 0; }}
    .arch {{ position: absolute; opacity: 0; z-index: 1; box-shadow: 0 18px 60px rgba(30,10,0,.16); }}
    .flood {{ position: absolute; width: 4400px; height: 4400px; border-radius: 50%; z-index: 2; transform: scale(0); }}
    .ghost {{ position: absolute; left: 0; right: 0; top: 330px; height: 460px; z-index: 0; overflow: hidden; }}
    .ghost .run {{ position: absolute; left: 0; top: 0; font-family: "Mitr", sans-serif; font-weight: 700; font-size: 320px; line-height: 1.3; white-space: nowrap; }}
    .back {{ position: absolute; inset: 0; z-index: 3; }}
    .cam {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; transform-origin: 0 0; z-index: 5; filter: drop-shadow(14px 8px 22px rgba(30,10,0,.26)); }}
    .cam video {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .front {{ position: absolute; inset: 0; z-index: 9; }}
    .ty {{ position: absolute; font-family: "Mitr", sans-serif; font-weight: 700; line-height: 1.3; white-space: nowrap; overflow: visible; }}
    .ty .in {{ display: inline-block; transform-origin: 0% 60%; }}
    .block {{ transform: rotate(-1.4deg); }} .block .in {{ padding: 2px 34px 8px; border-radius: 26px; }}
    .dot {{ display: inline-block; width: .42em; height: .42em; border-radius: 50%; margin-right: .36em; vertical-align: .12em; }}
    .ob {{ position: absolute; }} .ob .in {{ display: block; transform-origin: 50% 80%; }} .ob img {{ display: block; width: 100%; height: 100%; filter: drop-shadow(0 26px 22px rgba(30,10,0,.32)); }}
    .cur {{ position: absolute; left: -600px; top: 1090px; width: 3120px; height: 3400px; border-radius: 1560px 1560px 0 0; z-index: 30; }}'''

JS = '''
    const rise = (s, t) => tl.fromTo(s, { yPercent: 60, clipPath: "inset(-30% -5% 100% -5%)" }, { yPercent: 0, clipPath: "inset(-30% -5% -30% -5%)", duration: .42, ease: "expo.out" }, t);
    const wipe = (s, t) => tl.fromTo(s, { clipPath: "inset(-30% 100% -30% -5%)" }, { clipPath: "inset(-30% -5% -30% -5%)", duration: .34, ease: "expo.out" }, t);
    const slide = (s, t, dx) => tl.fromTo(s, { x: dx, opacity: 0 }, { x: 0, opacity: 1, duration: .36, ease: "back.out(1.5)" }, t);
    const bye = (s, t) => tl.to(s, { opacity: 0, duration: .15, ease: "power2.in" }, t - .16);
    const popIn = (s, t, r) => tl.fromTo(s, { scale: .35, rotation: r * 3.5, opacity: 0 }, { scale: 1, rotation: r, opacity: 1, duration: .55, ease: "back.out(1.9)" }, t);
    const popOut = (s, t) => tl.to(s, { scale: .7, opacity: 0, duration: .16, ease: "power2.in" }, t - .17);
    const shape = (s, t, p) => { tl.set(s, { ...p, opacity: 1 }, t); tl.fromTo(s, { scale: .9 }, { scale: 1, duration: .42, ease: "back.out(1.6)", immediateRender: false }, t); };
    const none = (s, t) => tl.set(s, { opacity: 0 }, t);
    const flood = (s, t0, t1, cx, cy) => { tl.set(s, { left: cx - 2200, top: cy - 2200 }, Math.max(0, t0 - .01)); tl.fromTo(s, { scale: 0 }, { scale: 1, duration: .46, ease: "expo.out", immediateRender: false }, t0); tl.to(s, { scale: 0, duration: .3, ease: "power3.in" }, t1 - .3); };
    '''


def arch(cx, top, w, colour):
    return dict(left=round(cx - w / 2), top=round(top), width=round(w), height=H + 500 - round(top), borderRadius=f'{round(w / 2)}px {round(w / 2)}px 0px 0px', backgroundColor=colour, transformOrigin='50% 75%')


def disc(cx, cy, d, colour):
    return dict(left=round(cx - d / 2), top=round(cy - d / 2), width=round(d), height=round(d), borderRadius='50%', backgroundColor=colour, transformOrigin='50% 50%')


def solo_target(person, carded):
    """Where the face lands. With a card the speaker moves out to leave the side they face for it; with none they hold the middle of the frame."""
    return {('H', True): 500, ('G', True): 1420, ('H', False): 800, ('G', False): 1100}[(person, carded)]


def layout(kind, who, carded, hf, gf, i, pal, split):
    """One shot's stage: camera (scale, x, y), the point it drifts about, what clips the other person, and the shapes behind."""
    hx, hy = hf
    gx, gy = gf
    if kind == 'W':
        s = 1.11
        x = round(960 - s * (hx + gx) / 2, 1)
        y = round(max(H - H * s, min(140.0, 520 - s * (hy + gy) / 2)), 1)
        ax, ay, bx, by = hx * s + x, hy * s + y, gx * s + x, gy * s + y
        return dict(cam=(s, x, y), about=((hx + gx) / 2, (hy + gy) / 2), clip='none', shapes={
            'A': arch(ax - 40, ay - (300 if who == 'H' else 265), 700, pal['a']), 'Ai': None, 'B': arch(bx + 75, by - (300 if who == 'G' else 265), 700, pal['b'])}, focus=(ax if who == 'H' else bx, ay if who == 'H' else by))
    p = kind[0]
    s = 1.58 if kind.endswith('+') else 1.42
    fx, fy = hf if p == 'H' else gf
    tx = solo_target(p, carded)
    x, y = round(tx - s * fx, 1), round(max(H - H * s, min(40.0, 400 - s * fy)), 1)
    fy_ = fy * s + y
    cx = tx + (-60 if p == 'H' else 100)
    c1, c2 = (pal['a'], pal['b']) if i % 2 == 0 else (pal['b'], pal['a'])
    style = i % 3
    if style == 0:
        shapes = {'A': arch(cx, fy_ - 345, 800, c1), 'Ai': None, 'B': None}
    elif style == 1:
        shapes = {'A': disc(cx, fy_ + 150, 860, c1), 'Ai': None, 'B': None}
    else:
        shapes = {'A': arch(cx, fy_ - 385, 860, c1), 'Ai': arch(cx, fy_ - 250, 590, c2), 'B': None}
    clip = f'inset(-200px {round(W - split)}px -200px -200px)' if p == 'H' else f'inset(-200px -200px -200px {round(split)}px)'
    return dict(cam=(s, x, y), about=(fx, fy), clip=clip, shapes=shapes, focus=(tx, fy_))


def ghost(pfx, title, dur, pal):
    """The chapter's name, huge and tone on tone, drifting behind the people while nobody needs to read anything. It leaves when a card arrives."""
    speed = 26
    unit = measure(title + '   •   ', 320)
    n = int((dur * speed + W) / unit) + 2
    op = .2 if pal['name'] == 'sky' else .13
    run = e((title + '   •   ') * n)
    html_ = f'<div class="ghost" id="{pfx}gh" aria-hidden="true"><div class="run" id="{pfx}gt" style="color:{pal["ink"]};opacity:{op}">{run}</div></div>'
    js = f'tl.fromTo("#{pfx}gt",{{x:0}},{{x:{-round(dur * speed)},duration:{dur},ease:"none"}},0);'
    return html_, js


def layout_v(kind, i, pal, split, hf, gf, tx_=None, ty_=None, top=400):
    """9:16. A speaker is recomposed rather than cropped: the words take the band above the head, the face stays inside the app's safe band (168–1330 px).
    People are kept small enough to leave air around them. A desk across the bottom hides where the cutout ends."""
    if kind == 'W':     # the main camera hides; two cameras take over, one for each person
        return dict(cam=(1.0, 0, 0), about=(0, 0), clip='inset(0px 100% 0px 0px)', focus=(540, 760), shapes={
            'A': dict(arch(275, 560, 510, pal['a']), height=1500), 'Ai': None, 'B': dict(arch(805, 730, 510, pal['b']), height=1400)})
    p = kind[0]
    home = 470 if p == 'H' else 640
    s, tx, ty = {'+': (1.48, tx_ or home, ty_ or 960), '~': (1.12, 800, 1060)}.get(kind[-1], (1.38, tx_ or home, ty_ or 960))
    fx, fy = hf if p == 'H' else gf
    x, y = round(tx - s * fx, 1), round(ty - s * fy, 1)
    cx = tx + (-30 if p == 'H' else 60)
    c1, c2 = (pal['a'], pal['b']) if i % 2 == 0 else (pal['b'], pal['a'])
    style = i % 3
    if style == 0:
        shapes = {'A': dict(arch(cx, ty - top, 760, c1), height=2000), 'Ai': None, 'B': None}
    elif style == 1:
        shapes = {'A': disc(cx, ty + 90, 820, c1), 'Ai': None, 'B': None}
    else:
        shapes = {'A': dict(arch(cx, ty - top - 30, 800, c1), height=2000), 'Ai': dict(arch(cx, ty - top + 100, 560, c2), height=2000), 'B': None}
    clip = f'inset(-200px {round(W - split)}px -200px -200px)' if p == 'H' else f'inset(-200px -200px -200px {round(split)}px)'
    return dict(cam=(s, x, y), about=(fx, fy), clip=clip, shapes=shapes, focus=(tx, ty))


def free_split(occ, f0, f1, hug=None):
    """A vertical line between the two people that stays empty for the whole shot. Returns (x in source px, clean?).
    hug='H' or 'G' sets the line close to that person, which also removes scraps of sofa further away."""
    if occ is None:
        return float(SPLIT_X), True
    f1 = max(f1, f0 + 1)
    cols = occ[f0:f1].max(0)
    xs = np.arange(len(cols)) * 8.0
    lo, hi = int(np.searchsorted(xs, SPLIT_X - 180)), int(np.searchsorted(xs, SPLIT_X + 380))
    seg = cols[lo:hi]
    empty = seg < 8
    best, run, start, best_start = 0, 0, 0, 0
    for k, v in enumerate(empty):
        if v:
            if run == 0:
                start = k
            run += 1
            if run > best:
                best, best_start = run, start
        else:
            run = 0
    if best >= 2:
        if hug == 'H':
            return float(xs[lo + best_start] + min(44, xs[1] * (best - 1))), True
        if hug == 'G':
            return float(xs[lo + best_start + best - 1] - min(44, xs[1] * (best - 1))), True
        return float(xs[lo + best_start + best // 2]), True
    return float(xs[lo + int(np.argmin(seg))]), False


def shots_js(shots, pfx, ghost=False):
    """Hard cuts: the camera jumps, the painted shapes behind spring up, and the person keeps a slow push."""
    out = []
    for s in shots:
        t = s['t']
        d = round(s['end'] - t - .001, 3)
        sc, x, y = s['cam']
        ax, ay = s['about']
        s1 = sc * 1.012
        x1, y1 = x - (s1 - sc) * ax, y - (s1 - sc) * ay
        out.append(f'tl.set("#{pfx}c",{{scale:{sc},x:{x},y:{y},clipPath:"{s["clip"]}"}},{t});tl.to("#{pfx}c",{{scale:{s1:.4f},x:{x1:.1f},y:{y1:.1f},duration:{d},ease:"none"}},{t});')
        if ghost:
            out.append(f'tl.set("#{pfx}gh",{{opacity:{0 if s.get("card") else 1}}},{t});')
        for el in ('A', 'Ai', 'B'):
            sp = s['shapes'][el]
            if sp is None:
                out.append(f'none("#{pfx}{el}",{t});')
            else:
                import json
                out.append(f'shape("#{pfx}{el}",{t},{json.dumps(sp)});')
    return ''.join(out)

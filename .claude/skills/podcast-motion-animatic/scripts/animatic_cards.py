#!/usr/bin/env python3
"""What a producer asked of the Animatic on a real film, built in as options. With none of them set, build.py behaves exactly as it did.

In show.json, "looks": {"animatic": {...}}:
    "layout": "card"     a card beside the speaker, after Pop Studio: a heading, rows that land on their words and stay, and a moving picture, on the side away from whoever is talking. 16:9 only.
    "blueprint": true    pale line on a grid: every sketch is inverted and laid over with screen, so layers never show an edge. Set paper, ink, pencil and accent to suit.
    "grid": false        with blueprint, a plain ground and no grid: a chalkboard, say (podcast-motion-chalkboard)
    "colour": true       card pictures keep their colour and sit as photographs, never sketched or greyed (podcast-motion-photo-card). Set "sketch": false with it
On a card, opts:
    "motion": "arc"      how the picture moves. Built in: still, drop, arc, fly, drift, sway, hop, swarm, flipbook. Works in either layout.
    "frames": "sun"      flipbook: the drawings in assets_src/panels/sun/
    "zoom": 1.2          how far in the picture sits in its window
    "flip": true         mirror the picture, for a nose pointing the wrong way
In paper.json:
    "wide": [[a, b]]     recording seconds that play as a wide two-shot, because the planner only goes wide on long speeches

Every pose is set by hand at six steps a second, the look's own rate, so it stays drawn and never turns smooth.

Your own moves: a moves.py beside paper.json, or tools/animatic_moves.py in the show, with register(h) returning {"name": function}. See examples/hail-mary/moves.py.
A function takes (st, c, id_, a, d, rows) in a 1700×860 space and returns (html, js). `h` is this module.

Pictures that aren't the card's own:
    assets_src/panels/<folder>/x.png   line art, named "<folder>_x"
    assets_src/panels/raw/x.png        used as drawn and never inverted: a nebula, or a solid ship with its own colours
"""
import importlib.util, math, random, shutil
from pathlib import Path
import numpy as np
from PIL import Image

RATE = 6
FW, FH = 1700, 860
SHOT = {'H': (1.12, 0.0, -66.0), 'G': (1.12, -230.4, -66.0)}     # the host holds their side, with room for the card
CARD = {'H': (872, 24, 1024, 1032), 'G': (24, 24, 1024, 1032)}
PAD, IMG_W, IMG_H = 36, 952, 482
SLIDE = ('x:-16,opacity:.35', 'x:-5,opacity:.8', 'x:0,opacity:1')
RISE = ('y:40,opacity:.35', 'y:12,opacity:.8', 'y:0,opacity:1')
LOOK, BOX, RAW, MOVES, ACCENT, BLUE = None, {}, {}, {}, '#D3261F', False


def uses_this(st):
    return st.pal.get('layout') == 'card' or st.pal.get('blueprint') or any(c['opts'].get('motion') for o in st.bf.chs for c in o.cards) or bool(st.paper.get('wide'))


def mix(a, b, u):
    A, B = [tuple(int(h.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) for h in (a, b)]
    return '#%02X%02X%02X' % tuple(round(x + (y - x) * u) for x, y in zip(A, B))


# ------------------------------------------------------------ helpers, also for your own moves
def src(name):
    return f"assets/panels/{'bp_' if BLUE else ''}{name}.jpg"


def raw(name):
    return f'assets/panels/{RAW[name]}'


def center(name):
    x0, y0, x1, y1 = BOX[name]
    return (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0


def poses(sel, a, d, f):
    """One tl.set per drawing. f(seconds in, 0..1) gives the pose as a dict."""
    n = max(2, int(d * RATE))
    out = ''
    for k in range(n):
        t = k / RATE
        p = f(t, k / (n - 1))
        out += f'tl.set("{sel}",{{' + ','.join(f'{key}:{val:.3f}' for key, val in p.items()) + f'}},{a + t:.3f});'
    return out


def img(id_, name, ox=None, oy=None, extra=''):
    o = f'transform-origin:{ox:.0f}px {oy:.0f}px;' if ox is not None else ''
    return f'<img id="{id_}" src="{src(name)}" alt="" style="{o}{extra}" />'


def lerp(a, b, u):
    return a + (b - a) * u


def show(sel, on, t):
    return f'tl.set("{sel}",{{opacity:{1 if on else 0}}},{t:.3f});'


def flip(ids, a, d, pick, rate=RATE):
    """Swap between stacked drawings. pick(step) names the drawing for that step."""
    js, prev = '', None
    for k in range(max(1, int(d * rate))):
        n = pick(k)
        if n != prev:
            if prev is not None:
                js += show(f'#{ids[prev]}', False, a + k / rate)
            js += show(f'#{ids[n]}', True, a + k / rate)
            prev = n
    return js


def stack(id_, names):
    """Drawings piled up, all hidden. Returns (html, {name: element id})."""
    ids = {n: f'{id_}{k}' for k, n in enumerate(names)}
    return ''.join(img(ids[n], n, extra='opacity:0;') for n in names), ids


def stepped(sel, t, frames):
    return ''.join(f'tl.set("{sel}",{{{v}}},{t + k / RATE:.3f});' for k, v in enumerate(frames))


def cells(id_, ox, oy, rx, ry, groups=14, per=16, r0=4, r1=8, seed=13, colour=None):
    """Small round things in clumps, each clump a <g id="{id_}g{n}"> starting hidden."""
    random.seed(seed)
    s = ''
    for g in range(groups):
        s += f'<g id="{id_}g{g}" opacity="0">'
        for _ in range(per):
            th, q = random.uniform(0, 6.283), random.random() ** .5
            x, y, r = ox + rx * q * math.cos(th), oy + ry * q * math.sin(th), random.uniform(r0, r1)
            s += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="none" stroke="{colour or ACCENT}" stroke-width="3"/><circle cx="{x:.0f}" cy="{y:.0f}" r="{r * .35:.1f}" fill="{colour or ACCENT}"/>'
        s += '</g>'
    return s


def svg(body, overflow=False):
    return f'<svg viewBox="0 0 {FW} {FH}" style="position:absolute;inset:0;width:100%;height:100%{";overflow:visible" if overflow else ""}">{body}</svg>'


def accent():
    return ACCENT


# ------------------------------------------------------------ the built-in moves
def _name(c):
    return c['opts'].get('panel') or c['opts'].get('still') or c['opts'].get('obj')


def _pic(c, id_, ox, oy):
    return img(id_, _name(c), ox, oy, 'scale:-1 1;' if c['opts'].get('flip') else '')


def m_still(st, c, id_, a, d, rows):
    ox, oy, *_ = center(_name(c))
    return _pic(c, f'{id_}i', ox, oy), poses(f'#{id_}i', a, d, lambda t, u: dict(scale=lerp(1.0, 1.07, u)))


def m_drop(st, c, id_, a, d, rows):
    """Falls in and bounces. If there's a row, it tips on that word."""
    ox, oy, *_ = center(_name(c))
    tr = (rows[0] - a) if rows else d

    def f(t, u):
        y = -520 * (1 - (t / .34) ** 2) if t < .34 else (-70 * math.sin(math.pi * (t - .34) / .22) if t < .56 else 0)
        return dict(y=y, scale=1.0 + .07 * u, rotation=7 * math.sin((t - tr) * 2 * math.pi / .9) * math.exp(-(t - tr) * .6) if t >= tr else 0.0)
    return _pic(c, f'{id_}i', ox, oy), poses(f'#{id_}i', a, d, f)


def m_arc(st, c, id_, a, d, rows):
    """Thrown from one side to the other, spinning."""
    ox, oy, *_ = center(_name(c))

    def f(t, u):
        return dict(x=lerp(-640, 640, u), y=-240 * math.sin(math.pi * u) + lerp(200, -20, u), scale=.42 + .5 * math.sin(math.pi * min(1, u * 1.05)) ** 1.2, rotation=-30 + 620 * u)
    return _pic(c, f'{id_}i', ox, oy), poses(f'#{id_}i', a, d, f)


def m_fly(st, c, id_, a, d, rows):
    """Crosses the frame, getting faster."""
    ox, oy, *_ = center(_name(c))

    def f(t, u):
        return dict(x=lerp(-1000, 560, u ** 1.5), y=lerp(90, -120, u) + 7 * math.sin(t * 9), scale=lerp(.55, .85, u), rotation=lerp(2, -7, u))
    return _pic(c, f'{id_}i', ox, oy), poses(f'#{id_}i', a, d, f)


def m_drift(st, c, id_, a, d, rows):
    """Floats slowly, turning."""
    ox, oy, *_ = center(_name(c))

    def f(t, u):
        return dict(x=lerp(-170, 170, u), y=18 * math.sin(t * .9), rotation=lerp(-9, 9, u))
    return _pic(c, f'{id_}i', ox, oy), poses(f'#{id_}i', a, d, f)


def m_sway(st, c, id_, a, d, rows):
    """Swings from its top edge, like something on strings."""
    x0, y0, x1, _ = BOX[_name(c)]
    period = c['opts'].get('period', 1.7)

    def f(t, u):
        return dict(x=26 * math.sin(t * math.pi / period), y=18 * math.sin(t * 4 * math.pi / period), rotation=8 * math.sin(t * 2 * math.pi / period))
    return _pic(c, f'{id_}i', (x0 + x1) / 2, y0), poses(f'#{id_}i', a, d, f)


def m_hop(st, c, id_, a, d, rows):
    """Waddles in, in hops, then bounces on the spot from the last row."""
    ox, _, _, _ = center(_name(c))
    y1 = BOX[_name(c)][3]
    tr = (rows[-1] - a) if rows else d
    hops = max(3, int(tr / .55))

    def f(t, u):
        if t < tr:
            w = min(.999, t / tr) * hops
            ph = w % 1
            sq = 1 - .13 * math.cos(math.pi * ph) ** 8
            return dict(x=lerp(-620, 0, w / hops), y=-120 * math.sin(math.pi * ph), scaleY=sq, scaleX=2 - sq, rotation=(7 if int(w) % 2 else -7) * math.sin(math.pi * ph))
        ph = ((t - tr) / .42) % 1
        sq = 1 - .13 * math.cos(math.pi * ph) ** 8
        return dict(x=0, y=-90 * math.sin(math.pi * ph), scaleY=sq, scaleX=2 - sq, rotation=0)
    return _pic(c, f'{id_}i', ox, y1), poses(f'#{id_}i', a, d, f)


def m_swarm(st, c, id_, a, d, rows):
    """Pushes in while small things multiply over the picture and wriggle."""
    name = _name(c)
    ox, oy, w, h = center(name)
    body = f'<div class="lay" id="{id_}A" style="transform-origin:{ox:.0f}px {oy:.0f}px"><img src="{src(name)}" alt="" />{svg(cells(id_ + "a", ox, oy, .42 * w, .34 * h))}</div>'
    js = poses(f'#{id_}A', a, d, lambda t, u: dict(scale=lerp(1.0, 1.3, u)))
    for g in range(14):
        js += show(f'#{id_}ag{g}', True, a + round((g + 1) / 15 * d * .9 * RATE) / RATE)
    for k in range(int(d * RATE)):
        for g in range(0, 14, 2):
            random.seed(g * 97 + k)
            js += f'tl.set("#{id_}ag{g}",{{x:{random.uniform(-5, 5):.1f},y:{random.uniform(-5, 5):.1f}}},{a + k / RATE:.3f});'
    return body, js


def m_flipbook(st, c, id_, a, d, rows):
    """A new drawing three times a second, from a folder of them. The line wobbling between drawings is the point."""
    names = sorted(n for n in BOX if n.startswith(c['opts']['frames'] + '_'))
    if not names:
        raise SystemExit(f"FAIL: flipbook {c['opts']['frames']}: no drawings in assets_src/panels/{c['opts']['frames']}/")
    html_, ids = stack(id_, names)
    total = max(1, int(d * 3))
    return html_.replace('opacity:0;', 'opacity:1;', 1), flip(ids, a, d, lambda k: names[min(len(names) - 1, int(k / total * len(names)))], 3)


BUILT_IN = dict(still=m_still, drop=m_drop, arc=m_arc, fly=m_fly, drift=m_drift, sway=m_sway, hop=m_hop, swarm=m_swarm, flipbook=m_flipbook)


def load_moves(st):
    MOVES.clear()
    MOVES.update(BUILT_IN)
    for f in (st.root / 'moves.py', Path(st.show['root']) / 'tools/animatic_moves.py'):
        if f.exists():
            spec = importlib.util.spec_from_file_location(f'moves_{abs(hash(str(f)))}', f)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            MOVES.update(m.register(__import__(__name__)))


# ------------------------------------------------------------ pictures
def bp(path, out, ink):
    v = np.asarray(Image.open(path).convert('L'), np.float32)
    a = np.clip((255 - v) / 255 * 1.4, 0, 1) ** .8     # a sketch of a photograph is faint: lift it to hold on a dark ground
    Image.fromarray((a[..., None] * np.array(ink, np.float32)).astype(np.uint8)).save(out, quality=92)


def install(look):
    """Wraps the look's own functions. Nothing changes unless the show asks for one of the options above."""
    global LOOK
    LOOK = look
    kit = look.kit
    plan, css0, prepare0, panel0 = kit.Stage.shots, look.css, look.prepare, look.panel

    def reframe(st, o, shots_):
        """Cut exactly on each card's edges and on each change of speaker. The planner holds a shot for at least a second, so a card could land on the wrong framing and hide half a face for up to 0.9 s, and a short line could play over the other host."""
        bf = st.bf
        fps = bf.FPS
        cuts = {0.0, o.dur} | {s['t'] for s in shots_}
        for c in o.cards:
            cuts |= {max(0.0, c['a']), min(o.dur, c['b'])}
        for r in bf.pass1:
            local = bf.src2local(o, r['a'])
            if 0 < local < o.dur:
                cuts.add(local)
        edges = {round(max(0.0, c['a']) * fps) / fps for c in o.cards} | {round(min(o.dur, c['b']) * fps) / fps for c in o.cards}
        marks = []
        for t in sorted({round(t * fps) / fps for t in cuts}):
            if marks and t - marks[-1] < .4 and t not in edges:     # too short to read as a shot, unless a card needs the cut
                continue
            if marks and t - marks[-1] < .4 and marks[-1] not in edges and len(marks) > 1:
                marks[-1] = t
                continue
            marks.append(t)
        if marks[-1] < o.dur:
            marks[-1] = round(o.dur * fps) / fps
        new, last = [], None
        for t0, t1 in zip(marks, marks[1:]):
            mid = (t0 + t1) / 2
            c = next((c for c in o.cards if c['a'] - .02 <= mid < c['b']), None)
            a_, b_ = bf.local2src(o, t0), bf.local2src(o, t1)
            if c:
                who = c['who']
                seg = dict(t=t0, end=t1, kind=who, who=who, f=SHOT[who], card=True)
            else:
                who = bf.speaker(bf.local2src(o, mid)) or last or 'G'
                near = next((s for s in shots_ if s['t'] <= mid < s['end'] and not s.get('card') and s['kind'][0] == who), None)
                seg = dict(t=t0, end=t1, kind=near['kind'] if near else who, who=who, f=near['f'] if near else bf.framing(who, a_, b_), card=False)
            last = who
            if new and not c and t1 - t0 < .6:     # the breath between two cards: hold the shot, or it flashes a close-up
                seg.update(kind=new[-1]['kind'], who=new[-1]['who'], f=new[-1]['f'])
            if new and new[-1]['f'] == seg['f'] and new[-1]['kind'] == seg['kind']:
                new[-1]['end'] = t1
                new[-1]['card'] = new[-1]['card'] or seg['card']
            else:
                new.append(seg)
        return new

    def shots(self, o):
        out = plan(self, o)
        if self.V or not uses_this(self):
            return out
        if self.pal.get('layout') == 'card':
            out = reframe(self, o, out)
        wide = self.paper.get('wide', [])
        for s in out:
            mid = self.bf.local2src(o, (s['t'] + s['end']) / 2)
            if any(a - .1 <= mid <= b + .1 for a, b in wide) and not s.get('card'):
                s['kind'], s['f'] = 'W', (1.0, 0.0, 0.0)
        return out
    kit.Stage.shots = shots

    def css(st):
        base = css0(st)
        if st.V or not uses_this(st):
            return base
        p = st.pal
        grid = (f'background-image: linear-gradient({mix(p["paper"], p["ink"], .1)} 2px, transparent 2px), linear-gradient(90deg, {mix(p["paper"], p["ink"], .1)} 2px, transparent 2px); background-size: 85px 85px; '
                if p.get('grid', True) else '')
        win = (f'.win {{ background-color: {p["paper"]}; {grid}isolation: isolate; }}' if p.get('blueprint')
               else '.win { isolation: isolate; border-radius: 18px; overflow: hidden; }' if p.get('colour') else '.win { isolation: isolate; }')
        blend = 'screen' if p.get('blueprint') else 'multiply'     # colour pictures too: their ground is pure white, so layered drawings show through
        return base + f'''
    {win}
    .win img, .win .lay {{ mix-blend-mode: {blend}; }}
    .win .lay {{ position: absolute; inset: 0; }}
    .sc {{ position: absolute; }} .sc .pop {{ position: absolute; inset: 0; background: {p["paper"]}; }}
    .sca {{ position: absolute; width: {FW}px; height: {FH}px; mix-blend-mode: {blend}; }}
    .bul {{ position: absolute; width: 20px; height: 20px; border-radius: 50%; background: {p["accent"]}; }}'''
    look.css = css

    def prepare(st):
        global ACCENT, BLUE
        prepare0(st)
        if st.V or not uses_this(st):
            return
        ACCENT, BLUE = st.pal['accent'], bool(st.pal.get('blueprint'))
        ink = tuple(int(st.pal['ink'].lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
        d = st.p / 'assets' / 'panels'
        panels = st.root / 'assets_src' / 'panels'
        for f in panels.glob('*/*') if panels.is_dir() else []:
            if f.parent.name in ('old',) or f.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
                continue
            if f.parent.name == 'raw':
                RAW[f.stem] = f'raw_{f.name}'
                shutil.copy(f, d / RAW[f.stem])
                continue
            Image.open(f).convert('RGB').resize((FW, FH)).save(d / f'{f.parent.name}_{f.stem}.jpg', quality=92)
        BOX.clear()
        for f in d.glob('*.jpg'):
            if f.stem.startswith('bp_'):
                continue
            if st.pal.get('colour'):
                rgb = np.asarray(Image.open(f).convert('RGB'), np.float32)
                edge = np.concatenate([rgb[:12].reshape(-1, 3), rgb[-12:].reshape(-1, 3), rgb[:, :12].reshape(-1, 3), rgb[:, -12:].reshape(-1, 3)])
                ground = np.maximum(np.median(edge, axis=0), 1)
                if ground.min() > 150:      # a studio photograph on a pale ground: balance it to white, so it sits on the card with no grey box
                    rgb = np.clip(rgb * 255 / ground, 0, 255)
                rgb = np.where((rgb > 226).all(2, keepdims=True), 255, rgb).astype(np.uint8)     # pale ground to pure white, colour kept
                Image.fromarray(rgb).save(f, quality=93)
                v = np.asarray(Image.fromarray(rgb).convert('L'), np.int16)
            else:
                v = np.asarray(Image.open(f).convert('L'), np.int16)
                v = np.where(v > 226, 255, v).astype(np.uint8)     # pure white, so a moved picture shows no edge
                Image.fromarray(v).save(f, quality=93)
            ys, xs = np.where(v < 170)
            BOX[f.stem] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else (0, 0, FW, FH)
            if BLUE:
                bp(f, d / f'bp_{f.stem}.jpg', ink)
        load_moves(st)
    look.prepare = prepare

    def card_frame(i, w, h, st):
        o = [look.wobble(i + n) * 2.6 for n in range(8)]
        n, c, ink = 46, st.pal['accent'], st.pal['ink']
        lines = f'<path d="M{o[0]:.0f},{o[1]:.0f} L{w + o[2]:.0f},{o[3]:.0f} L{w + o[4]:.0f},{h + o[5]:.0f} L{o[6]:.0f},{h + o[7]:.0f} Z" stroke="{ink}" stroke-width="4" fill="none"/>'
        corners = ''.join(f'<path d="{d}" stroke="{c}" stroke-width="6" fill="none"/>' for d in (f'M-12,{n} L-12,-12 L{n},-12', f'M{w - n},-12 L{w + 12},-12 L{w + 12},{n}', f'M{w + 12},{h - n} L{w + 12},{h + 12} L{w - n},{h + 12}', f'M{n},{h + 12} L-12,{h + 12} L-12,{h - n}'))
        return f'<svg viewBox="0 0 {w} {h}" style="position:absolute;inset:0;width:100%;height:100%;overflow:visible" aria-hidden="true">{lines}{corners}</svg>'

    def run_move(st, c, id_, a, d, rows, name):
        key = c['opts'].get('motion') or 'still'
        if key not in MOVES:
            raise SystemExit(f"FAIL: no move called {key}. Built in: {', '.join(BUILT_IN)}. Your own go in moves.py.")
        return MOVES[key](st, c, id_, a, d, rows)

    def panel(st, c, i, pfx, o=None):
        if st.V or not uses_this(st):
            return panel0(st, c, i, pfx, o)
        name = st.panels.get(id(c)) if hasattr(st, 'panels') else None
        a, b = c['a'], c['b']
        d, id_ = round(b - a, 3), f'{pfx}{i}x'
        rows = st.row_times(c, o) if c['rows'] else []
        if st.pal.get('layout') != 'card':
            if not name or not (c['opts'].get('motion') or st.pal.get('blueprint')):
                return panel0(st, c, i, pfx, o)
            x, y, w, h = look.FRAME[False]
            body, js = run_move(st, c, id_, a, d, rows, name)
            return f'<div id="{pfx}{i}" class="clip pg" data-start="{a}" data-duration="{d}" data-track-index="2"><div class="win" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">{body}</div>{look.frame_lines(st, i)}</div>' + look.caption(st, c, pfx, i, o), js
        # a card beside the host
        who = c['who']
        X, Y, W_, H_ = CARD[who]
        p, font = st.pal, look.FONT
        hot = c['kind'] in ('stat', 'verdict')
        tw = W_ - 2 * PAD
        body, js = run_move(st, c, id_, a, d, rows, name) if name else ('', '')
        if a > .1:     # the card arrives in three drawings. The first is already there, because frame 0 is the thumbnail.
            js += stepped(f'#{id_}p', a, ('scale:.84,rotation:-1.6', 'scale:1.03,rotation:.7', 'scale:1,rotation:0'))
        base = {'verdict': 118, 'stat': 170, 'term': 118}.get(c['kind'], 104) if name else {'stat': 230, 'verdict': 180}.get(c['kind'], 150)
        size, ls = kit.fit_lines(c['title'], tw, base, 62, 2, font)
        lh = int(size * 1.28)
        rsized = [kit.fit_lines(r, tw - 44, 58 if name else 68, 38, 2, font) for r in c['rows']]
        block = lh * len(ls) + 18 + sum(int(rs * 1.36) * len(rl) + 8 for rs, rl in rsized)
        y = Y + PAD + 8 + (0 if name else max(0, (H_ - 2 * PAD - block) // 2))
        pic = ''
        if name:      # the picture takes whatever the words leave
            ih = max(IMG_H, min(H_ - PAD - (PAD + 8 + block + 14), 760))
            k = max(IMG_W / FW, ih / FH) * c['opts'].get('zoom', 1.0)
            pic = f'<div class="win" style="left:{PAD}px;top:{H_ - PAD - ih}px;width:{IMG_W}px;height:{ih}px"><div class="sca" style="left:{(IMG_W - FW) / 2:.0f}px;top:{(ih - FH) / 2:.0f}px;transform:scale({k:.4f});transform-origin:{FW / 2}px {FH / 2}px">{body}</div></div>'
        side = 0 if who == 'G' else X
        h_ = (f'<div id="{pfx}{i}m" class="clip" data-start="{a}" data-duration="{d}" data-track-index="1" style="position:absolute;left:{side}px;top:0;width:{W_ + 24}px;height:1080px;background:{p["paper"]}"></div>'      # keeps the other host fully out of shot: a sliver at the edge reads as a mistake
              f'<div id="{pfx}{i}" class="clip sc" data-start="{a}" data-duration="{d}" data-track-index="2" style="left:{X}px;top:{Y}px;width:{W_}px;height:{H_}px"><div class="pop" id="{id_}p" style="transform-origin:50% 50%">{pic}{card_frame(i, W_, H_, st)}</div></div>')
        for j, ln in enumerate(ls):
            tid = f'{pfx}{i}t{j}'
            h_ += st.text(tid, a, b, ln, X + PAD, y, size, p['accent'] if hot else p['ink'], track=4)
            if a > .1:     # after the card has settled: a title crossing the tilted frame looks wrong on pause
                js += stepped(f'#{tid} .in', a, ('opacity:0', 'opacity:0') + RISE)
            y += lh
        y += 18
        for n, (rs, rl) in enumerate(rsized):
            t0, rh = rows[n], int(rs * 1.36)
            if a > .1:
                t0 = max(t0, round(a + 3 / RATE, 3))
            h_ += f'<div id="{pfx}{i}d{n}" class="clip bul" data-start="{t0}" data-duration="{round(b - t0, 3)}" data-track-index="5" style="left:{X + PAD}px;top:{y + rh // 2 - 8}px"></div>'
            for j, ln in enumerate(rl):
                tid = f'{pfx}{i}r{n}{j}'
                h_ += st.text(tid, t0, b, ln, X + PAD + 44, y, rs, p['ink'], track=4)
                if t0 > .1:
                    js += stepped(f'#{tid} .in', t0, SLIDE)
                y += rh
            y += 8
        return h_, js
    look.panel = panel

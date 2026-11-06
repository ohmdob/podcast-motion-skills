#!/usr/bin/env python3
"""Bento Grid: the footage becomes one rounded tile on a plain canvas, and every card reflows the grid. The speaker's tile shrinks to their half
while the other half fills with tiles of its own: the heading, the picture, and one tile per row, each landing on its word.

    python3 build.py FOLDER [--frames]

FOLDER is an episode or clip that has been through full_edit.py --render. No cutout is needed: the room stays, framed as a tile.
A stat or a verdict takes the accent tile. Faces are never stylised. 16:9 only.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-playbook' / 'scripts'))
import look_kit as kit
import card_stage as cs
from look_kit import e

KEY, BED, GROUND = 'bento', 'b', 'canvas'
PALETTE = {'canvas': '#EFECE6', 'tile': '#FFFFFF', 'ink': '#17191D', 'muted': '#6B7078', 'accent': '#FF5A36', 'blue': '#2E5BFF', 'dark': '#1D1F24', 'soft': '#DCE6FF'}
FONTS = [('Mitr', 'Mitr-SemiBold.ttf', '600')]
FONT = 'Mitr-SemiBold.ttf'
FAM = '"Mitr", sans-serif'
BAND = (0, 820)
M, G, R = 24, 16, 30           # outer margin, gap between tiles, corner radius
FULL = f'inset({M}px {M}px {M}px {M}px round {R}px)'
HALF = {'H': f'inset({M}px {960 + G // 2}px {M}px {M}px round {R}px)', 'G': f'inset({M}px {M}px {M}px {960 + G // 2}px round {R}px)'}
TITLE = {'verdict': 96, 'stat': 150, 'term': 76, 'q': 70, 'take': 74, 'rows': 66}


def css(st):
    p = st.pal
    return f'''.ty {{ font-family: {FAM}; font-weight: 600; }}
    .tilecam {{ position: absolute; inset: 0; clip-path: {FULL}; z-index: 1; }}
    .tile {{ position: absolute; border-radius: {R}px; z-index: 4; overflow: hidden; }}
    .tile .ph {{ position: absolute; inset: 0; background: #fff center/cover no-repeat; }}
    .num {{ position: absolute; left: 30px; top: 22px; font-size: 30px; }}'''


def prepare(st):
    cs.prepare_pictures(st, (1200, 900))
    plain = st.footage

    def framed(pfx, video, media_start, dur):
        return f'<div class="tilecam" id="{pfx}w">{plain(pfx, video, media_start, dur)}</div>'
    st.footage = framed


def tiles(st, c, i, pfx, o=None):
    """The free half of the grid, cut to the card: heading on top, rows along the bottom, the picture in between."""
    p = st.pal
    a, b, k = c['a'], c['b'], c['kind']
    x0 = 960 + G // 2 if c['who'] == 'H' else M
    W, top, bottom = 960 - M - G // 2, M, 1080 - M
    src = cs.picture(st, c)
    rows = c['rows']
    big = k in ('stat', 'verdict')
    bg, ink = {'stat': (p['accent'], '#FFFFFF'), 'verdict': (p['accent'], '#FFFFFF'), 'q': (p['dark'], '#FFFFFF'), 'term': (p['blue'], '#FFFFFF')}.get(k, (p['tile'], p['ink']))
    ts, tl_, tlh = cs.lines(c['title'], W - 90, TITLE.get(k, 70), 44, 3, FONT)
    side_w = (W - G * (len(rows) - 1)) // max(len(rows), 1) - 60
    stack = len(rows) > 1 and not cs.fits(rows, side_w, 30, FONT)     # a run too wide for a tile side by side: stack the row tiles instead
    rl = [cs.lines(r, (W - 160) if stack else side_w, 54 if not stack else 46, 30, 3 if not stack else 1, FONT) for r in rows]
    one_h = [lh * len(ls) + (100 if not stack else 44) for _, ls, lh in rl]
    row_h = (sum(one_h) + G * (len(rows) - 1) if stack else max(one_h)) if rows else 0
    title_h = tlh * len(tl_) + 80
    mid = bottom - top - title_h - (row_h + G if rows else 0) - G
    if not src or mid < 240:
        title_h = bottom - top - (row_h + G if rows else 0)
        mid = 0
    h_, js, k_ = '', '', 0
    d = round(b - a, 3)

    def tile(id_, x, y, w, h, colour, inner, t):
        nonlocal h_, js, k_
        h_ += (f'<div id="{id_}" class="clip tile" data-start="{t}" data-duration="{round(b - t, 3)}" data-track-index="4" '
               f'style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{colour}">{inner}</div>')
        js += f'tl.fromTo("#{id_}",{{scale:.82,y:46,opacity:0}},{{scale:1,y:0,opacity:1,duration:.38,ease:"back.out(1.7)"}},{round(t + (.1 + .07 * k_ if t == a else 0), 2)});'
        js += f'tl.to("#{id_}",{{scale:.92,opacity:0,duration:.18,ease:"power2.in"}},{round(b - .2, 2)});'
        k_ += 1

    ty0 = (title_h - tlh * len(tl_)) / 2
    inner = ''.join(st.text(f'{pfx}{i}t{j}', a, b, ln, 46 if not big else (W - kit.measure(ln, ts, FONT, 600)) / 2, ty0 + j * tlh, ts, ink, track=5) for j, ln in enumerate(tl_))
    tile(f'{pfx}{i}T', x0, top, W, title_h, bg, inner, a)
    y = top + title_h + G
    if mid:
        tile(f'{pfx}{i}P', x0, y, W, mid, p['tile'], f'<div class="ph" style="background-image:url({src})"></div>', a)
        y += mid + G
    if rows:
        times = st.row_times(c, o)
        n = len(rows)
        rw = W if stack else (W - G * (n - 1)) // n
        ry = bottom - row_h
        for r, (rs, ls, lh) in enumerate(rl):
            col = p['soft'] if r % 2 == 0 else p['tile']
            if stack:
                inner = f'<div class="num ty" style="color:{p["blue"]};top:{(one_h[r] - 34) // 2}px">{r + 1:02d}</div>' + cs.block(f'{pfx}{i}r{r}', times[r], b, ls, 100, 22, rs, p['ink'], track=5)
                tile(f'{pfx}{i}R{r}', x0, ry, rw, one_h[r], col, inner, times[r])
                ry += one_h[r] + G
            else:
                inner = f'<div class="num ty" style="color:{p["blue"]}">{r + 1:02d}</div>' + cs.block(f'{pfx}{i}r{r}', times[r], b, ls, 30, 70, rs, p['ink'], track=5)
                tile(f'{pfx}{i}R{r}', x0 + r * (rw + G), ry, rw, row_h, col, inner, times[r])
    return h_, js


def chapter(st, o, shots, k):
    h_, js = '', ''
    wrap = f'#{o.id}w'
    cards = o.cards
    for i, c in enumerate(cards):
        a, b = c['a'], c['b']
        prev = cards[i - 1] if i else None
        if not (prev and a - prev['b'] < .45 and prev['who'] == c['who']):
            js += f'tl.to("{wrap}",{{clipPath:"{HALF[c["who"]]}",duration:.42,ease:"power3.inOut"}},{round(max(a - .12, 0), 2)});'
        nxt = cards[i + 1] if i + 1 < len(cards) else None
        if not (nxt and nxt['a'] - b < .45):
            js += f'tl.to("{wrap}",{{clipPath:"{FULL}",duration:.42,ease:"power3.inOut"}},{round(b - .1, 2)});'
        t_h, t_j = tiles(st, c, i, f'{o.id}c', o)
        h_, js = h_ + t_h, js + t_j
    return h_, js


def cold(st, cards, shots):
    h_, js = '', ''
    for i, c in enumerate(cards):
        js += f'tl.to("#coldw",{{clipPath:"{HALF[c["who"]]}",duration:.3,ease:"power3.inOut"}},{c["a"]});'
        a, b = tiles(st, c, i, 'cc')
        h_, js = h_ + a, js + b
    return h_, js


def grid(st, pfx, heading, rows, dur, small=None):
    """A full grid: the heading in the big tile, the mark and the rows in their own, the accent in a corner."""
    p = st.pal
    h_, js = '', ''
    size, ls, lh = cs.lines(heading, 1100, 140, 64, 2, FONT)
    th = 1080 - 2 * M - (230 + G if rows else 0)
    cells = [('A', M, M, 1240, th, p['dark']), ('B', M + 1240 + G, M, 1920 - 2 * M - 1240 - G, th // 2 - G // 2, p['accent']),
             ('C', M + 1240 + G, M + th // 2 + G // 2, 1920 - 2 * M - 1240 - G, th // 2 - G // 2, p['soft'])]
    for k, (n, x, y, w, h, col) in enumerate(cells):
        h_ += f'<div id="{pfx}{n}" class="tile" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{col}"></div>'
        js += f'tl.fromTo("#{pfx}{n}",{{scale:.8,y:40,opacity:0}},{{scale:1,y:0,opacity:1,duration:.4,ease:"back.out(1.6)"}},{round(.05 + k * .08, 2)});'
    y0 = M + (th - lh * len(ls)) / 2
    for j, ln in enumerate(ls):
        id_ = f'{pfx}l{j}'
        h_ += st.text(id_, 0, dur, ln, M + 70, y0 + j * lh, size, '#FFFFFF', track=5, extra='z-index:5;')
        js += f'rise("#{id_} .in",{round(.3 + j * .12, 2)});'
    if small:
        h_ += st.text(f'{pfx}k', 0, dur, small, M + 1240 + G + 40, M + 40, 40, '#FFFFFF', track=5, extra='z-index:5;')
        js += f'rise("#{pfx}k .in",.45);'
    if rows:
        rw = (1920 - 2 * M - G * (len(rows) - 1)) // len(rows)
        for r, row in enumerate(rows):
            rs, rl, rlh = cs.lines(row, rw - 80, 52, 32, 2, FONT)
            x = M + r * (rw + G)
            h_ += f'<div id="{pfx}r{r}" class="tile" style="left:{x}px;top:{1080 - M - 230}px;width:{rw}px;height:230px;background:{p["tile"]}"></div>'
            h_ += cs.block(f'{pfx}r{r}x', 0, dur, rl, x + 40, 1080 - M - 230 + (230 - rlh * len(rl)) / 2, rs, p['ink'], track=5, extra='z-index:5;')
            js += f'tl.fromTo(["#{pfx}r{r}","#{pfx}r{r}x"],{{y:40,opacity:0}},{{y:0,opacity:1,duration:.36,ease:"back.out(1.6)"}},{round(.5 + r * .1, 2)});'
    return h_, js


def chapter_card(st, o, k):
    return grid(st, f'{o.id}t', o.title, [], st.bf.CH_D)


def title(st):
    return grid(st, 'ti', ' '.join(st.paper.get('title_lines') or [st.paper['title']]), [st.paper['sub']] if st.paper.get('sub') else [], st.bf.TITLE_D, small=st.mark)


def end(st):
    return grid(st, 'en', st.paper.get('title', ''), st.paper.get('end_rows', []), st.bf.END_D, small=st.mark)


def cues(st):
    out = []
    for k, o in enumerate(st.bf.chs):
        out.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .2))
        for c in o.cards:
            out.append(('whoosh_1', o.at + c['a'] - .1, .12))
            if c['kind'] in ('stat', 'verdict'):
                out.append(('pop', o.at + c['a'] + .3, .18))
    out.append(('whoosh_1', st.bf.END_AT, .22))
    return out


if __name__ == '__main__':
    if '--ratio' not in sys.argv:
        sys.argv += ['--ratio', '16x9']
    kit.main(sys.modules[__name__])

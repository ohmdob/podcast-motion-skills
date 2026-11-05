#!/usr/bin/env python3
"""Whiteboard: real footage beside a board, with marker notes and arrows that draw what the guest says.

    python3 build.py FOLDER [--ratio 16x9|9x16|both] [--frames]

FOLDER is an episode or clip that has been through full_edit.py --render. The notes are cards.json; give a card opts.times (recording seconds, one per row) to land each note
on the word that says it. The board only ever holds the guest's own points, and the look uses no pictures, so it costs nothing beyond the voice and transcript.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-playbook' / 'scripts'))
import look_kit as kit
from look_kit import e

KEY, BED, GROUND = 'whiteboard', 'a', 'board'
PALETTE = {'board': '#FBFCFA', 'frame': '#9AA5AB', 'tray': '#6F7B82', 'ink': '#1E2933', 'blue': '#1746C7', 'red': '#D3261F', 'green': '#0B7F56'}
FONTS = [('Itim', 'Itim-Regular.ttf', '400')]
FONT = 'Itim-Regular.ttf'
FAM = '"Itim", sans-serif'
BAND = (0, 820)
BASE = {'verdict': 190, 'stat': 170, 'term': 124, 'q': 104, 'take': 116, 'rows': 92}


def css(st):
    p = st.pal
    return f'''.ty {{ font-family: {FAM}; font-weight: 400; }}
    .bd {{ position: absolute; background: {p['board']}; border: 12px solid {p['frame']}; border-radius: 10px; }}
    .bd::after {{ content: ""; position: absolute; left: 6%; right: 6%; bottom: -12px; height: 12px; background: {p['tray']}; border-radius: 0 0 8px 8px; }}
    .wrap {{ position: absolute; }}
    svg.ink {{ position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }}
    svg.ink path {{ fill: none; stroke-linecap: round; stroke-linejoin: round; }}'''


def wobble(n):
    """A marker never draws a perfect line, and the same n always gives the same line, so a render is repeatable."""
    return ((n * 37) % 11 - 5) / 5


def underline(x, y, w, n=0):
    k, m = wobble(n), wobble(n + 3)
    return f'M{x:.0f},{y + k * 3:.0f} C{x + w * .3:.0f},{y - 7 - m * 3:.0f} {x + w * .62:.0f},{y + 8 + k * 3:.0f} {x + w:.0f},{y + m * 3:.0f}'


def ring(cx, cy, rx, ry, n=0):
    k = wobble(n)
    return (f'M{cx - rx * .15:.0f},{cy - ry - 6:.0f} C{cx + rx * .9:.0f},{cy - ry - 8 * k:.0f} {cx + rx + 12:.0f},{cy + ry * .75:.0f} {cx + rx * .1:.0f},{cy + ry + 4:.0f} '
            f'C{cx - rx * .95:.0f},{cy + ry + 6 * k:.0f} {cx - rx - 12:.0f},{cy - ry * .7:.0f} {cx + rx * .1:.0f},{cy - ry - 9:.0f}')


def arrow_down(x, y0, y1):
    return (f'M{x:.0f},{y0:.0f} Q{x + 22:.0f},{(y0 + y1) / 2:.0f} {x:.0f},{y1:.0f}', f'M{x - 13:.0f},{y1 - 16:.0f} L{x:.0f},{y1:.0f} L{x + 15:.0f},{y1 - 14:.0f}')


def stroke(id_, d, colour, width=9):
    return f'<path id="{id_}" d="{d}" stroke="{colour}" stroke-width="{width}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>'


def measure_card(st, c, WD):
    """Sizes first, so the board can be cut to its content: a tall board with one line on it reads as a blank box."""
    k = c['kind']
    rows = list(c['rows'])
    size, lines = kit.fit_lines(c['title'], WD, int(BASE.get(k, 100) * (.92 if st.V else 1)), 60, 3, FONT)
    lh = int(size * 1.3)
    row_lines = [kit.fit_lines(r, WD - 58, 56 if st.V else 62, 38, 2, FONT) for r in rows]
    row_h = sum(int(rs * 1.34) * len(rl) + 12 for rs, rl in row_lines)
    gap = 36 + (34 if k == 'term' and rows else 0)
    return dict(rows=rows, size=size, lines=lines, lh=lh, row_lines=row_lines, total=lh * len(lines) + (gap + row_h if rows else 26))


def notes(st, c, i, pfx, X, y, WD, m, o=None, hook=False):
    """One card on the board: the heading written on, then each note as its word arrives. Returns (text html, svg paths, js)."""
    p = st.pal
    k = c['kind']
    colour = {'verdict': p['red'], 'stat': p['red'], 'q': p['ink'], 'term': p['blue'], 'take': p['ink']}.get(k, p['blue'])
    size, lines, lh, row_lines, rows = m['size'], m['lines'], m['lh'], m['row_lines'], m['rows']
    a, b = c['a'], c['b']
    h_, paths, js = '', '', ''
    top, widest, last_w = y, 0, 0
    for j, ln in enumerate(lines):
        id_ = f'{pfx}{i}t{j}'
        h_ += st.text(id_, a, b, ln, X, y, size, colour, track=3)
        if not hook:
            js += f'wipe("#{id_} .in",{round(a + .22 + j * .3, 2)},.32);'
        last_w = kit.measure(ln, size, FONT)
        widest = max(widest, last_w)
        y += lh
    t_mark = round(a + .5 + (len(lines) - 1) * .3, 2)
    # One mark per card, and it has to mean something: a ring holds the answer, a line stresses the point, an arrow joins a term to what it means.
    if k in ('stat', 'verdict'):
        id_ = f'{pfx}{i}m'
        paths += stroke(id_, ring(X + widest / 2, (top + y) / 2 + size * .04, min(widest * .62 + 40, WD / 2 + 40), (y - top) / 2 + 10, i), p['blue'] if k == 'verdict' else p['ink'], 8)
        js += f'draw("#{id_}",{t_mark},.46);'
    elif k == 'take':
        paths += stroke(f'{pfx}{i}m', underline(X - 4, y + 2, min(last_w + 12, WD), i), p['blue']) + stroke(f'{pfx}{i}n', underline(X + last_w * .2, y + 18, last_w * .6, i + 1), p['blue'], 7)
        js += f'draw("#{pfx}{i}m",{t_mark},.28);draw("#{pfx}{i}n",{round(t_mark + .26, 2)},.2);'
    else:
        id_ = f'{pfx}{i}m'
        paths += stroke(id_, underline(X - 4, y + 2, min(last_w + 12, WD), i), p['red'] if k == 'q' else p['green'])
        js += f'draw("#{id_}",{t_mark},.3);'
    y += 36
    join = k == 'term' and rows
    if join:
        s_, h2 = arrow_down(X + 18, y - 12, y + 34)
        paths += stroke(f'{pfx}{i}a', s_, p['blue'], 7) + stroke(f'{pfx}{i}b', h2, p['blue'], 7)
        js += f'draw("#{pfx}{i}a",{round(t_mark + .3, 2)},.22);draw("#{pfx}{i}b",{round(t_mark + .5, 2)},.1);'
        y += 8
    times = st.row_times(dict(c, rows=rows), o)
    for r_i, (rs, rl) in enumerate(row_lines):
        t = times[r_i]
        if not (join and r_i == 0):
            dot = f'{pfx}{i}d{r_i}'
            paths += stroke(dot, ring(X + 16, y + rs * .68, 11, 11, r_i), p['green'], 6)
            js += f'draw("#{dot}",{t},.18);'
        for j, ln in enumerate(rl):
            id_ = f'{pfx}{i}r{r_i}{j}'
            h_ += st.text(id_, t, b, ln, X + 58, y, rs, p['ink'], track=4)
            js += f'wipe("#{id_} .in",{round(t + .1, 2)},.3);'
            y += int(rs * 1.34)
        y += 12
    return h_, paths, js


def side_card(st, c, i, pfx, o=None, hook=False):
    """16:9: the board stands on the side away from the speaker, so the face stays clear, and it is only as tall as its notes."""
    bx, bw, pad = (1030, 846, 62) if c['who'] == 'H' else (44, 846, 62)
    X, WD = bx + pad, bw - 2 * pad - 24
    m = measure_card(st, c, WD)
    bh = max(330, min(930, m['total'] + 2 * pad + 24))
    top = max(56, 500 - bh // 2)
    h_, paths, js = notes(st, c, i, pfx, X, top + pad + 12, WD, m, o, hook)
    a, b = c['a'], c['b']
    d = round(b - a, 3)
    dx = 960 if c['who'] == 'H' else -960
    frame = (f'<div id="{pfx}{i}" class="clip wrap" data-start="{a}" data-duration="{d}" data-track-index="2" style="left:0;top:0;width:1920px;height:1080px">'
             f'<div class="bd" id="{pfx}{i}f" style="left:{bx}px;top:{top}px;width:{bw}px;height:{bh}px"></div></div>')
    ink = f'<div id="{pfx}{i}k" class="clip wrap" data-start="{a}" data-duration="{d}" data-track-index="5" style="left:0;top:0;width:1920px;height:1080px"><svg class="ink" id="{pfx}{i}s" viewBox="0 0 1920 1080">{paths}</svg></div>'
    entry = '' if hook else f'tl.fromTo("#{pfx}{i}f",{{x:{dx}}},{{x:0,duration:.36,ease:"power3.out"}},{a});'
    return frame + h_ + ink, entry + js + f'bye("#{pfx}{i}f",{b});'


def chapter(st, o, shots, k):
    if not st.V:
        h_, js = '', ''
        for i, c in enumerate(o.cards):
            a, b = side_card(st, c, i, f'{o.id}c', o)
            h_, js = h_ + a, js + b
        return h_, js
    return board_v(st, o.title, o.cards, o.id, o.dur, o)


def board_v(st, heading, cards, pfx, dur, o=None, hook_first=False):
    """9:16: the board is always there below the footage, carrying the chapter's name when no note is up, so a viewer landing anywhere knows the topic."""
    p = st.pal
    top = st.band[1] - 18
    h_ = f'<div class="bd" style="left:-12px;top:{top}px;width:1104px;height:1300px"></div>'
    h_ += f'<div class="ty" style="left:60px;top:1400px;font-size:46px;color:{p["tray"]}">{e(st.mark)}</div>'
    js = ''
    size, lines = kit.fit_lines(heading, 960, 96, 56, 3, FONT)
    lh = int(size * 1.3)
    y = 880 + (440 - lh * len(lines)) // 2
    hd_ids = []
    for j, ln in enumerate(lines):
        id_ = f'{pfx}hd{j}'
        hd_ids.append(id_)
        h_ += st.text(id_, 0, dur, ln, (1080 - kit.measure(ln, size, FONT)) / 2, y + j * lh, size, p['ink'], track=2)
    paths = ''
    for i, c in enumerate(cards):
        m = measure_card(st, c, 960)
        t_h, t_p, t_j = notes(st, c, i, f'{pfx}c', 60, 850 + max(0, (480 - m['total']) // 2), 960, m, o, hook_first and i == 0)
        h_ += t_h
        paths += t_p
        js += t_j
        js += ''.join(f'tl.set("#{d} .in",{{opacity:0}},{c["a"]});tl.set("#{d} .in",{{opacity:1}},{c["b"]});' for d in hd_ids)
        # marks leave with their note
        js += ''.join(f'tl.set("#{pid}",{{opacity:0}},{c["b"]});' for pid in _ids(t_p))
    h_ += f'<div class="wrap" style="left:0;top:0;width:1080px;height:1920px;z-index:6"><svg class="ink" viewBox="0 0 1080 1920">{paths}</svg></div>'
    return h_, js


def _ids(paths):
    import re
    return re.findall(r'id="([^"]+)"', paths)


def cold(st, cards, shots):
    if st.V:
        return board_v(st, st.mark, cards, 'cc', st.bf.COLD, hook_first=True)
    h_, js = '', ''
    for i, c in enumerate(cards):
        a, b = side_card(st, c, i, 'cc', hook=i == 0)
        h_, js = h_ + a, js + b
    return h_, js


def full_board(st, pfx, heading, rows, dur, small=None):
    p = st.pal
    X = 80 if st.V else 150
    WD = st.W - 160 if st.V else (1180 if rows else 1600)
    size, lines = kit.fit_lines(heading, WD, 150, 64, 3, FONT)
    lh = int(size * 1.3)
    total = lh * len(lines) + (84 if small else 0) + 40 + sum(90 for _ in rows)
    y = (((168 + 1330) // 2) if st.V else st.H // 2) - total // 2
    h_ = f'<div class="bd" style="left:18px;top:18px;width:{st.W - 36}px;height:{st.H - 54}px"></div>'
    js, paths = '', ''
    if small:
        h_ += st.text(f'{pfx}k', 0, dur, small, X, y, 50, p['ink'], track=2)
        js += f'wipe("#{pfx}k .in",.1,.3);'
        y += 84
    for j, ln in enumerate(lines):
        id_ = f'{pfx}l{j}'
        h_ += st.text(id_, 0, dur, ln, X, y, size, p['blue'], track=2)
        js += f'wipe("#{id_} .in",{round(.15 + j * .22, 2)},.34);'
        y += lh
    w_ = max(kit.measure(ln, size, FONT) for ln in lines)
    paths += stroke(f'{pfx}u', underline(X - 4, y + 6, min(w_ + 16, WD), 2), p['red'], 11)
    js += f'draw("#{pfx}u",{round(.3 + len(lines) * .22, 2)},.32);'
    y += 44
    for i, r in enumerate(rows):
        rs, _ = kit.fit_lines(r, WD - 60, 60, 36, 1, FONT)
        id_ = f'{pfx}r{i}'
        t = round(.6 + i * .32, 2)
        h_ += st.text(id_, t, dur, r, X + 56, y, rs, p['ink'], track=3)
        paths += stroke(f'{pfx}d{i}', ring(X + 18, y + rs * .66, 12, 12, i), p['green'], 6)
        js += f'draw("#{pfx}d{i}",{t},.18);wipe("#{id_} .in",{round(t + .1, 2)},.3);'
        y += 90
    h_ += f'<svg class="ink" viewBox="0 0 {st.W} {st.H}">{paths}</svg>'
    return h_, js


def chapter_card(st, o, k):
    return full_board(st, f'{o.id}t', o.title, [], st.bf.CH_D)


def title(st):
    return full_board(st, 'ti', ' '.join(st.paper.get('title_lines') or [st.paper['title']]), [st.paper['sub']] if st.paper.get('sub') else [], st.bf.TITLE_D, small=st.mark)


def end(st):
    return full_board(st, 'en', st.paper.get('title', ''), st.paper.get('end_rows', []), st.bf.END_D, small=st.mark)


def cues(st):
    out = []
    for k, o in enumerate(st.bf.chs):
        out.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .2))
        out += [('pop', o.at + c['a'] + .3, .16) for c in o.cards if c['kind'] in ('stat', 'verdict')]
    out.append(('whoosh_1', st.bf.END_AT, .22))
    return out


if __name__ == '__main__':
    kit.main(sys.modules[__name__])

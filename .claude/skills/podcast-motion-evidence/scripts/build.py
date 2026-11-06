#!/usr/bin/env python3
"""Evidence Board: the speakers in front of a cork wall, with every card pinned up as a polaroid and its rows on sticky notes. When a card is done it shrinks
onto the ledge along the bottom, joined to the last by red string, so the board fills up as the case is made.

    python3 build.py FOLDER [--frames]

FOLDER is an episode or clip that has been through full_edit.py --render, with build/cutout.webm (the speakers alone): this look paints its own wall behind them.
A card with no picture is pinned as an index card. Faces are never stylised: the speakers keep their own picture. 16:9 only.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-playbook' / 'scripts'))
import look_kit as kit
import card_stage as cs
from look_kit import e

KEY, BED, GROUND = 'evidence', 'a', 'cork'
PALETTE = {'cork': '#B9875A', 'wood': '#5B3A22', 'ink': '#20242A', 'note': '#FFE36E', 'note2': '#FFB5C2', 'pin': '#D62828', 'string': '#C1121F', 'card': '#FFFDF7', 'line': '#9DC3E6'}
FONTS = [('Itim', 'Itim-Regular.ttf', '400')]
FONT = 'Itim-Regular.ttf'
FAM = '"Itim", sans-serif'
BAND = (0, 820)
LEDGE = 958
SLOT_W, SLOT_Y = 128, LEDGE + 8


def css(st):
    p = st.pal
    return f'''.ty {{ font-family: {FAM}; font-weight: 400; }}
    .cork {{ position: absolute; inset: 0; z-index: 1; background-color: {p['cork']};
      background-image: radial-gradient(rgba(70,40,15,.22) 1.4px, transparent 2.2px), radial-gradient(rgba(255,236,205,.16) 1.2px, transparent 2px), radial-gradient(ellipse at 30% 20%, rgba(255,255,255,.10), transparent 60%);
      background-size: 9px 9px, 13px 13px, 100% 100%; background-position: 0 0, 5px 7px, 0 0; }}
    .ledge {{ position: absolute; left: 0; top: {LEDGE}px; width: 1920px; height: {1080 - LEDGE}px; z-index: 4; background: linear-gradient({p['wood']}, #3E2715); border-top: 6px solid #8A5A34; }}
    .pol {{ position: absolute; z-index: 6; background: {p['card']}; box-shadow: 0 18px 26px rgba(0,0,0,.35); transform-origin: 0 0; }}
    .pol .ph {{ position: absolute; background: #fff center/cover no-repeat; }}
    .idx {{ background-image: linear-gradient(transparent 63px, {p['line']} 63px, {p['line']} 66px, transparent 66px); background-size: 100% 66px; }}
    .pin {{ position: absolute; width: 38px; height: 38px; border-radius: 50%; background: radial-gradient(circle at 35% 32%, #ff8a8a, {p['pin']} 45%, #7a0d0d); box-shadow: 3px 6px 6px rgba(0,0,0,.4); z-index: 8; }}
    .note {{ position: absolute; z-index: 7; box-shadow: 0 10px 16px rgba(0,0,0,.3); }}
    .thumb {{ position: absolute; z-index: 5; background: {p['card']}; box-shadow: 0 6px 8px rgba(0,0,0,.4); }}
    .thumb .ph {{ position: absolute; left: 8px; top: 8px; right: 8px; bottom: 22px; background: #fff center/cover no-repeat; }}
    svg.str {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; z-index: 6; overflow: visible; }}'''


def prepare(st):
    cs.need_cutout(st)
    cs.prepare_pictures(st, (1120, 840))


def pinned(st, c, i, pfx, o, slot):
    """One card: a polaroid (or an index card), pinned, with its rows on notes below. In its last moment it flies to its slot on the ledge."""
    p = st.pal
    a, b, k = c['a'], c['b'], c['kind']
    x0, w = cs.away(c)
    src = cs.picture(st, c)
    rot = (-3.5, 2.8, -1.8, 3.6)[i % 4]
    PW = 600
    if src:
        ph_w, ph_h = PW - 48, int((PW - 48) * .75)
        ts, tl_, tlh = cs.lines(c['title'], PW - 60, 58 if k not in ('stat', 'verdict') else 76, 34, 2, FONT)
        PH = 24 + ph_h + 26 + tlh * len(tl_) + 22
    else:
        ts, tl_, tlh = cs.lines(c['title'], PW - 90, 120 if k in ('stat', 'verdict') else 76, 44, 3, FONT)
        PH = max(330, 90 + tlh * len(tl_) + 60)
    rows = c['rows']
    notes_h = 250 if rows else 0
    px = x0 + (w - PW) // 2
    py = max(40, min(80, LEDGE - 40 - PH - notes_h))
    d = round(b - a, 3)
    h_ = f'<div id="{pfx}{i}" class="clip pol{"" if src else " idx"}" data-start="{a}" data-duration="{d}" data-track-index="5" style="left:{px}px;top:{py}px;width:{PW}px;height:{PH}px;transform:rotate({rot}deg)">'
    ink = p['pin'] if k in ('stat', 'verdict') else p['ink']
    if src:
        h_ += f'<div class="ph" style="left:24px;top:24px;width:{ph_w}px;height:{ph_h}px;background-image:url({src})"></div>'
        ty = 24 + ph_h + 22
        for j, ln in enumerate(tl_):
            h_ += st.text(f'{pfx}{i}t{j}', a, b, ln, (PW - kit.measure(ln, ts, FONT)) / 2, ty + j * tlh, ts, ink, track=6)
    else:
        ty = (PH - tlh * len(tl_)) / 2
        for j, ln in enumerate(tl_):
            h_ += st.text(f'{pfx}{i}t{j}', a, b, ln, 54, ty + j * tlh, ts, ink, track=6)
    h_ += f'<div class="pin" style="left:{PW // 2 - 19}px;top:-14px"></div></div>'
    js = (f'tl.fromTo("#{pfx}{i}",{{y:-260,rotation:{rot - 14},opacity:0}},{{y:0,rotation:{rot},opacity:1,duration:.34,ease:"back.out(1.6)"}},{a});'
          f'tl.fromTo("#{pfx}{i} .pin",{{scale:2.2,opacity:0}},{{scale:1,opacity:1,duration:.16,ease:"power3.in"}},{round(a + .3, 2)});')
    # rows: sticky notes slapped on below, each on its word
    if rows:
        times = st.row_times(c, o)
        n = len(rows)
        nw = min(600 if n == 1 else 400, (w - 30 * (n - 1)) // n)     # one long row of Thai has no space to break at, so give it room
        nx0 = x0 + (w - (nw * n + 30 * (n - 1))) // 2
        ny = py + PH + 30
        for r, row in enumerate(rows):
            rs, rl, rlh = cs.lines(row, nw - 44, 52, 32, 3, FONT)
            nh = max(170, rlh * len(rl) + 50)
            nr = (2.5, -2, 3, -3)[(i + r) % 4]
            col = p['note'] if (i + r) % 3 else p['note2']
            nid = f'{pfx}{i}n{r}'
            h_ += f'<div id="{nid}" class="clip note" data-start="{times[r]}" data-duration="{round(b - times[r], 3)}" data-track-index="5" style="left:{nx0 + r * (nw + 30)}px;top:{ny}px;width:{nw}px;height:{nh}px;background:{col};transform:rotate({nr}deg)"></div>'
            h_ += cs.block(f'{nid}x', times[r], b, rl, nx0 + r * (nw + 30) + 20, ny + 22, rs, p['ink'], track=6, extra=f'z-index:7;transform:rotate({nr}deg);transform-origin:0 0;')
            js += (f'tl.fromTo("#{nid}",{{scale:1.5,opacity:0}},{{scale:1,opacity:1,duration:.16,ease:"power4.in"}},{times[r]});'
                   f'tl.fromTo("#{nid}x",{{scale:1.5,opacity:0}},{{scale:1,opacity:1,duration:.16,ease:"power4.in"}},{times[r]});bye("#{nid}",{b});bye("#{nid}x",{b});')
    # the polaroid flies to its slot on the ledge
    sx, sy = 24 + slot * SLOT_W, SLOT_Y
    sc = 110 / PW
    js += f'tl.to("#{pfx}{i}",{{x:{sx - px},y:{sy - py},scale:{sc:.3f},rotation:0,duration:.36,ease:"power2.in"}},{round(b - .38, 2)});'
    thumb = (f'<div id="{pfx}{i}m" class="clip thumb" data-start="{b}" data-duration="{round(o.dur - b, 3)}" data-track-index="5" style="left:{sx}px;top:{sy}px;width:110px;height:{int(PH * sc) + 6}px;transform:rotate({(-4, 3, -2, 5)[slot % 4]}deg)">'
             + (f'<div class="ph" style="background-image:url({src})"></div>' if src else f'<div class="ty" style="left:8px;top:14px;font-size:22px;color:{ink}">{e(tl_[0][:10])}</div>')
             + '<div class="pin" style="left:36px;top:-12px;width:26px;height:26px"></div></div>')
    return h_ + thumb, js, (sx + 55, sy - 2)


def chapter(st, o, shots, k):
    p = st.pal
    h_ = '<div class="cork"></div>'
    hh, js = cs.hosts(st, o.id, o.dur, o.bstart, shots)
    h_ += hh + '<div class="ledge"></div>'
    strings = ''
    last = None
    for i, c in enumerate(o.cards):
        a, b, pin = pinned(st, c, i, f'{o.id}c', o, i)
        h_, js = h_ + a, js + b
        if last:
            sid = f'{o.id}s{i}'
            mx, my = (last[0] + pin[0]) / 2, max(last[1], pin[1]) + 26
            strings += f'<path id="{sid}" d="M{last[0]},{last[1]} Q{mx},{my} {pin[0]},{pin[1]}" stroke="{p["string"]}" stroke-width="4" fill="none" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>'
            js += f'draw("#{sid}",{round(c["b"] + .05, 2)},.3);'
        last = pin
    h_ += f'<svg class="str" viewBox="0 0 1920 1080">{strings}</svg>'
    return h_, js


def cold(st, cards, shots):
    h_, js = '', ''
    for i, c in enumerate(cards):
        class O:
            dur = st.bf.COLD
        a, b, _ = pinned(st, c, i, 'cc', O, i)
        h_, js = h_ + a, js + b
    return h_, js


def board(st, pfx, heading, rows, dur, small=None):
    """A case file pinned to the wall: the heading on an index card, the rows on notes."""
    p = st.pal
    h_ = '<div class="cork"></div><div class="ledge"></div>'
    size, ls, lh = cs.lines(heading, 1060, 130, 60, 2, FONT)
    CH = lh * len(ls) + 140
    cy = 420 - CH // 2
    h_ += f'<div id="{pfx}c" class="pol idx" style="left:380px;top:{cy}px;width:1160px;height:{CH}px;transform:rotate(-1.5deg)"><div class="pin" style="left:561px;top:-14px"></div></div>'
    js = f'tl.fromTo("#{pfx}c",{{y:-300,opacity:0}},{{y:0,opacity:1,duration:.36,ease:"back.out(1.5)"}},.05);'
    for j, ln in enumerate(ls):
        id_ = f'{pfx}l{j}'
        h_ += st.text(id_, 0, dur, ln, (1920 - kit.measure(ln, size, FONT)) / 2, cy + 70 + j * lh, size, p['ink'], track=6, extra='z-index:7;')
        js += f'wipe("#{id_} .in",{round(.35 + j * .2, 2)},.4);'
    for r, row in enumerate(rows):
        rs, rl, rlh = cs.lines(row, 760, 52, 32, 2, FONT)
        nx, ny = 580, cy + CH + 40 + r * 10
        h_ += f'<div id="{pfx}n{r}" class="note" style="left:{nx}px;top:{ny}px;width:760px;height:{rlh * len(rl) + 50}px;background:{p["note"]};transform:rotate(1.5deg)"></div>'
        h_ += cs.block(f'{pfx}n{r}x', 0, dur, rl, nx + 30, ny + 24, rs, p['ink'], track=6, extra='z-index:7;')
        js += f'tl.fromTo(["#{pfx}n{r}","#{pfx}n{r}x"],{{scale:1.4,opacity:0}},{{scale:1,opacity:1,duration:.16,ease:"power4.in"}},{round(.8 + r * .25, 2)});'
    if small:
        h_ += st.text(f'{pfx}k', 0, dur, small, 60, LEDGE + 34, 40, '#F3E3C8', track=6, extra='z-index:7;')
    return h_, js


def chapter_card(st, o, k):
    return board(st, f'{o.id}t', o.title, [], st.bf.CH_D)


def title(st):
    return board(st, 'ti', ' '.join(st.paper.get('title_lines') or [st.paper['title']]), [st.paper['sub']] if st.paper.get('sub') else [], st.bf.TITLE_D, small=st.mark)


def end(st):
    return board(st, 'en', st.paper.get('title', ''), st.paper.get('end_rows', []), st.bf.END_D, small=st.mark)


def cues(st):
    out = []
    for k, o in enumerate(st.bf.chs):
        out.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .2))
        for c in o.cards:
            out.append(('boop', o.at + c['a'] + .3, .18))
            if c['kind'] in ('stat', 'verdict'):
                out.append(('stamp', o.at + c['a'] + .32, .2))
    out.append(('whoosh_1', st.bf.END_AT, .22))
    return out


if __name__ == '__main__':
    if '--ratio' not in sys.argv:
        sys.argv += ['--ratio', '16x9']
    kit.main(sys.modules[__name__])

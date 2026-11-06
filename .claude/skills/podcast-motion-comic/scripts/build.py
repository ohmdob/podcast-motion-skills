#!/usr/bin/env python3
"""Comic: the speakers inked onto a halftone page that changes colour with every card, beside comic panels that slam in.

    python3 build.py FOLDER [--frames]

FOLDER is an episode or clip that has been through full_edit.py --render, with build/cutout.webm (the speakers alone): this look paints its own ground behind them.
Each card in cards.json is a panel: a caption box with the heading, the card's picture, and the rows in a speech bubble pointing back at the speaker.
A stat or a verdict gets a starburst and a shake. Faces are never stylised: the speakers keep their own picture and only gain an ink outline. 16:9 only.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-playbook' / 'scripts'))
import look_kit as kit
import card_stage as cs
from look_kit import e

KEY, BED, GROUND = 'comic', 'b', 'page'
PALETTE = {'page': '#FFD23F', 'pages': ['#FFD23F', '#3BCEAC', '#FF7AA8', '#5AA9E6', '#FF9F45'], 'ink': '#121212', 'paper': '#FFFFFF', 'caption': '#FFE45E', 'accent': '#E63946'}
FONTS = [('Mitr', 'Mitr-Bold.ttf', '700')]
FONT = 'Mitr-Bold.ttf'
FAM = '"Mitr", sans-serif'
BAND = (0, 820)
TITLE = {'verdict': 104, 'stat': 120, 'term': 72, 'q': 66, 'take': 70, 'rows': 64}


def css(st):
    p = st.pal
    dots = 'radial-gradient(rgba(0,0,0,.17) 21%, transparent 23%)'
    return f'''.ty {{ font-family: {FAM}; font-weight: 700; }}
    .pg {{ position: absolute; inset: 0; background-color: {p['page']}; background-image: {dots}; background-size: 22px 22px; z-index: 1; }}
    .speed {{ position: absolute; inset: 0; z-index: 2; }}
    .ink {{ filter: drop-shadow(5px 0 0 {p['ink']}) drop-shadow(-5px 0 0 {p['ink']}) drop-shadow(0 5px 0 {p['ink']}) drop-shadow(0 -5px 0 {p['ink']}) drop-shadow(16px 16px 0 rgba(0,0,0,.28)); }}
    .pn {{ position: absolute; z-index: 6; transform-origin: 50% 50%; }}
    .box {{ position: absolute; background: {p['paper']}; border: 7px solid {p['ink']}; box-shadow: 14px 14px 0 {p['ink']}; }}
    .cap {{ position: absolute; background: {p['caption']}; border: 6px solid {p['ink']}; }}
    .pic {{ position: absolute; border: 6px solid {p['ink']}; background: #fff center/cover no-repeat; }}
    .bub {{ position: absolute; background: {p['paper']}; border: 6px solid {p['ink']}; border-radius: 48px; }}
    .tail {{ position: absolute; width: 0; height: 0; }}
    svg.burst {{ position: absolute; overflow: visible; }}'''


def prepare(st):
    cs.need_cutout(st)
    cs.prepare_pictures(st, (1200, 800))


def starburst(cx, cy, r0, r1, n=16):
    import math
    pts = []
    for k in range(n * 2):
        r = r1 if k % 2 == 0 else r0
        t = math.pi * k / n
        pts.append(f'{cx + r * math.cos(t):.0f},{cy + r * math.sin(t) * .62:.0f}')
    return ' '.join(pts)


def speed_lines(cx, cy, colour):
    import math
    out = ''
    for k in range(36):
        t = 2 * math.pi * k / 36 + (k % 3) * .03
        r0, r1 = 330 + (k % 4) * 40, 1500
        w = 10 + (k * 7) % 22
        out += f'<path d="M{cx + r0 * math.cos(t):.0f},{cy + r0 * math.sin(t):.0f} L{cx + r1 * math.cos(t - .012 * w / 10):.0f},{cy + r1 * math.sin(t - .012 * w / 10):.0f} L{cx + r1 * math.cos(t + .012 * w / 10):.0f},{cy + r1 * math.sin(t + .012 * w / 10):.0f} Z" fill="{colour}"/>'
    return out


def panel(st, c, i, pfx, o=None, ground_id=None):
    """One panel on the side away from the speaker: caption box, picture, speech bubble. Sized to its content."""
    p = st.pal
    a, b, k = c['a'], c['b'], c['kind']
    x0, w = cs.away(c)
    W = w - 40
    big = k in ('stat', 'verdict')
    ts, tl_, tlh = cs.lines(c['title'], W - 80, TITLE.get(k, 66), 44, 3, FONT)
    src = cs.picture(st, c)
    rows = c['rows']
    rl = [cs.lines(r, W - 120, 44, 30, 2, FONT) for r in rows]
    cap_h = tlh * len(tl_) + 44
    bub_h = (sum(lh * len(ls) for _, ls, lh in rl) + 18 * (len(rl) - 1) + 64) if rows else 0
    pic_h = 0
    if src:
        pic_h = max(220, min(430, 930 - cap_h - bub_h - 80))
    if big and not src:
        cap_h += 120
    H = cap_h + (pic_h + 26 if src else 0) + (bub_h + 40 if rows else 0) + 40
    top = max(40, 520 - H // 2)
    rot = (-2.2, 1.8, -1.2, 2.4)[i % 4]
    d = round(b - a, 3)
    h_ = f'<div id="{pfx}{i}" class="clip pn" data-start="{a}" data-duration="{d}" data-track-index="5" style="left:{x0 + 20}px;top:{top}px;width:{W}px;height:{H}px;transform:rotate({rot}deg)">'
    h_ += f'<div class="box" style="left:0;top:0;width:{W}px;height:{H}px"></div>'
    y = 20
    js = f'tl.fromTo("#{pfx}{i}",{{scale:1.45,rotation:{rot - 9},opacity:0}},{{scale:1,rotation:{rot},opacity:1,duration:.26,ease:"back.out(2.4)"}},{a});'
    if big:
        cx, cy = W / 2, y + cap_h / 2
        h_ += f'<svg class="burst" id="{pfx}{i}s" style="left:0;top:0;width:{W}px;height:{cap_h + 40}px" viewBox="0 0 {W} {cap_h + 40}"><polygon points="{starburst(cx, cy, W * .34, W * .52)}" fill="{p["accent"]}" stroke="{p["ink"]}" stroke-width="7"/></svg>'
        ink = p['paper']
        tx = [(W - kit.measure(l, ts, FONT, 700)) / 2 for l in tl_]
        ty0 = y + (cap_h - tlh * len(tl_)) / 2
        js += f'tl.fromTo("#{pfx}{i}s",{{scale:.2,rotation:-30,transformOrigin:"50% 50%"}},{{scale:1,rotation:0,duration:.3,ease:"back.out(3)"}},{round(a + .12, 2)});'
        js += f'tl.to("#{pfx}{i}",{{keyframes:[{{x:-18,duration:.04}},{{x:14,duration:.04}},{{x:-9,duration:.04}},{{x:5,duration:.04}},{{x:0,duration:.04}}]}},{round(a + .3, 2)});'
    else:
        h_ += f'<div class="cap" style="left:18px;top:{y}px;width:{W - 36}px;height:{cap_h - 8}px"></div>'
        ink = p['ink']
        tx = [40 for _ in tl_]
        ty0 = y + 18
    for j, ln in enumerate(tl_):
        h_ += st.text(f'{pfx}{i}t{j}', a, b, ln, tx[j], ty0 + j * tlh, ts, ink, track=6)
    y += cap_h + 6
    if src:
        h_ += f'<div class="pic" id="{pfx}{i}p" style="left:18px;top:{y}px;width:{W - 48}px;height:{pic_h}px;background-image:url({src})"></div>'
        js += f'tl.fromTo("#{pfx}{i}p",{{scale:.86,opacity:0}},{{scale:1,opacity:1,duration:.22,ease:"back.out(2)"}},{round(a + .18, 2)});'
        y += pic_h + 26
    if rows:
        side = 'right' if c['who'] == 'H' else 'left'
        bx = 30
        h_ += f'<div class="bub" id="{pfx}{i}b" style="left:{bx}px;top:{y}px;width:{W - 72}px;height:{bub_h}px"></div>'
        # the tail points back at whoever is speaking
        tail_x = -34 if c['who'] == 'H' else W - 60
        h_ += (f'<svg class="burst" id="{pfx}{i}q" style="left:{tail_x}px;top:{y + bub_h - 90}px;width:80px;height:80px" viewBox="0 0 80 80">'
               f'<path d="{"M80,10 L0,60 L80,50 Z" if c["who"] == "H" else "M0,10 L80,60 L0,50 Z"}" fill="{p["paper"]}" stroke="{p["ink"]}" stroke-width="6" stroke-linejoin="round"/></svg>')
        times = st.row_times(c, o)
        ry = y + 32
        js += f'tl.fromTo(["#{pfx}{i}b","#{pfx}{i}q"],{{scale:.6,opacity:0,transformOrigin:"50% 100%"}},{{scale:1,opacity:1,duration:.22,ease:"back.out(2.6)"}},{round(times[0] - .08, 2)});'
        for r, (rs, ls, lh) in enumerate(rl):
            for j, ln in enumerate(ls):
                id_ = f'{pfx}{i}r{r}{j}'
                h_ += st.text(id_, times[r], b, ln, bx + 44, ry, rs, p['ink'], track=6)
                js += f'rise("#{id_} .in",{times[r]});'
                ry += lh
            ry += 18
    h_ += '</div>'
    if ground_id:
        js += f'tl.set("#{ground_id}",{{backgroundColor:"{p["pages"][i % len(p["pages"])]}"}},{a});'
    js += f'bye("#{pfx}{i}",{b});'
    return h_, js


def speed(st, c, i, pfx):
    """Speed lines behind the speaker while their card is up."""
    cx = 520 if c['who'] == 'H' else 1400
    a, b = c['a'], c['b']
    h_ = (f'<div id="{pfx}{i}v" class="clip speed" data-start="{a}" data-duration="{round(b - a, 3)}" data-track-index="1">'
          f'<svg viewBox="0 0 1920 1080" style="width:100%;height:100%">{speed_lines(cx, 430, "rgba(255,255,255,.55)")}</svg></div>')
    js = f'tl.fromTo("#{pfx}{i}v",{{opacity:0,scale:1.15,transformOrigin:"{cx}px 430px"}},{{opacity:1,scale:1,duration:.2,ease:"power2.out"}},{a});'
    return h_, js


def chapter(st, o, shots, k):
    gid = f'{o.id}g'
    h_ = f'<div class="pg" id="{gid}"></div>'
    hh, js = cs.hosts(st, o.id, o.dur, o.bstart, shots)
    h_ += hh.replace('class="cam"', 'class="cam ink"', 1)
    for i, c in enumerate(o.cards):
        a1, b1 = speed(st, c, i, f'{o.id}c')
        a2, b2 = panel(st, c, i, f'{o.id}c', o, gid)
        h_, js = h_ + a1 + a2, js + b1 + b2
    return h_, js


def cold(st, cards, shots):
    h_, js = '', ''
    for i, c in enumerate(cards):
        a, b = panel(st, c, i, 'cc')
        h_, js = h_ + a, js + b
    return h_, js


def cover(st, pfx, heading, rows, dur, small=None):
    """A comic cover: the heading in a starburst on a halftone page."""
    p = st.pal
    h_ = f'<div class="pg" style="background-color:{p["pages"][1]}"></div>'
    h_ += f'<div class="speed"><svg viewBox="0 0 1920 1080" style="width:100%;height:100%">{speed_lines(960, 500, "rgba(255,255,255,.5)")}</svg></div>'
    h_ += f'<svg class="burst" id="{pfx}s" style="left:0;top:0;width:1920px;height:1080px;z-index:4" viewBox="0 0 1920 1080"><polygon points="{starburst(960, 500, 520, 760, 18)}" fill="{p["caption"]}" stroke="{p["ink"]}" stroke-width="10"/></svg>'
    size, ls, lh = cs.lines(heading, 1100, 140, 70, 2, FONT)
    y = 500 - lh * len(ls) / 2 - (40 if rows else 0)
    js = f'tl.fromTo("#{pfx}s",{{scale:.1,rotation:-40,transformOrigin:"50% 46%"}},{{scale:1,rotation:0,duration:.4,ease:"back.out(2.2)"}},.05);'
    for j, ln in enumerate(ls):
        id_ = f'{pfx}l{j}'
        h_ += st.text(id_, 0, dur, ln, (1920 - kit.measure(ln, size, FONT, 700)) / 2, y + j * lh, size, p['ink'], track=6, extra='z-index:6;')
        js += f'tl.fromTo("#{id_} .in",{{scale:1.6,opacity:0}},{{scale:1,opacity:1,duration:.24,ease:"back.out(2)"}},{round(.3 + j * .12, 2)});'
    y += lh * len(ls) + 20
    for r, row in enumerate(rows):
        rs, rl, rlh = cs.lines(row, 1000, 56, 34, 1, FONT)
        id_ = f'{pfx}r{r}'
        h_ += st.text(id_, 0, dur, rl[0], (1920 - kit.measure(rl[0], rs, FONT, 700)) / 2, y, rs, p['ink'], track=6, extra='z-index:6;')
        js += f'rise("#{id_} .in",{round(.7 + r * .2, 2)});'
        y += rlh
    if small:
        h_ += st.text(f'{pfx}k', 0, dur, small, 60, 980, 40, p['ink'], track=6, extra='z-index:6;')
    return h_, js


def chapter_card(st, o, k):
    return cover(st, f'{o.id}t', o.title, [], st.bf.CH_D)


def title(st):
    return cover(st, 'ti', ' '.join(st.paper.get('title_lines') or [st.paper['title']]), [st.paper['sub']] if st.paper.get('sub') else [], st.bf.TITLE_D, small=st.mark)


def end(st):
    return cover(st, 'en', st.paper.get('title', ''), st.paper.get('end_rows', []), st.bf.END_D, small=st.mark)


def cues(st):
    out = []
    for k, o in enumerate(st.bf.chs):
        out.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .2))
        for c in o.cards:
            out.append(('pop', o.at + c['a'], .2))
            if c['kind'] in ('stat', 'verdict'):
                out.append(('stamp', o.at + c['a'] + .3, .22))
    out.append(('whoosh_1', st.bf.END_AT, .22))
    return out


if __name__ == '__main__':
    if '--ratio' not in sys.argv:
        sys.argv += ['--ratio', '16x9']
    kit.main(sys.modules[__name__])

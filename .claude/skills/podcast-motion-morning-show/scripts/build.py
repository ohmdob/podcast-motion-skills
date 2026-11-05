#!/usr/bin/env python3
"""Morning Show: the morning-TV format viewers already know, with lower thirds and a topic strip over the real conversation.

    python3 build.py FOLDER [--ratio 16x9|9x16|both] [--frames]

FOLDER is an episode or clip that has been through full_edit.py --render. Headlines are cards.json. A name plate appears only for a person whose name is set in show.json under people,
because no name goes on screen until the producer has confirmed it. There is no LIVE tag, no clock, no "breaking" and no real channel's branding: a news format can make opinion read as
reported fact, so nothing here claims to be news. The ticker is off unless looks.morning-show.ticker is true, because it competes with subtitles.
The look uses no pictures, so it costs nothing beyond the voice and transcript.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-playbook' / 'scripts'))
import look_kit as kit
from look_kit import e

KEY, BED, GROUND = 'morning-show', 'a', 'blue'
PALETTE = {'blue': '#0A4BD0', 'deep': '#06328F', 'accent': '#FFB400', 'white': '#FFFFFF', 'ink': '#0B1B3A'}
FONTS = [('Noto Sans Thai', 'NotoSansThai.ttf', '100 900')]
FONT = 'NotoSansThai.ttf'
FAM = '"Noto Sans Thai", sans-serif'
BAND = (170, 900)


def css(st):
    p = st.pal
    return f'''.ty {{ font-family: {FAM}; font-weight: 800; }}
    .bar {{ position: absolute; }} .bar .in {{ display: block; width: 100%; height: 100%; }}
    .sun {{ position: absolute; border-radius: 50%; background: {p['accent']}; }}
    .wash {{ position: absolute; inset: 0; background: {p['blue']}; }}
    .desk {{ position: absolute; left: 0; right: 0; top: 1360px; bottom: 0; background: {p['deep']}; text-align: center; font-family: {FAM}; font-weight: 900; font-size: 64px; line-height: 1.3; padding-top: 76px; color: {p['accent']}; }}
    .tick {{ position: absolute; left: 0; right: 0; overflow: hidden; background: {p['deep']}; }}
    .tick .run {{ position: absolute; left: 0; top: 0; white-space: nowrap; font-family: {FAM}; font-weight: 700; color: {p['white']}; }}'''


def bar(id_, a, b, x, y, w, h, colour, track=2):
    return f'<div id="{id_}" class="clip bar" data-start="{a}" data-duration="{round(b - a, 3)}" data-track-index="{track}" style="left:{round(x)}px;top:{round(y)}px;width:{round(w)}px;height:{round(h)}px"><span class="in" style="background:{colour}"></span></div>'


def strip(st, pfx, label, dur, entrance=True):
    """The topic strip: the show's mark and what is being talked about, for a viewer who has just landed here."""
    p = st.pal
    x, y, h = (60, 1076, 72) if st.V else (72, 944, 72)
    max_w = 960 if st.V else 1776
    m_size = 36
    m_w = int(kit.measure(st.mark, m_size, FONT)) + 48
    t_w = max_w - m_w
    size, _ = kit.fit_lines(label, t_w - 44, 40, 26, 1, FONT)
    w2 = min(t_w, int(kit.measure(label, size, FONT)) + 48)
    out = bar(f'{pfx}sa', 0, dur, x, y, m_w, h, p['accent'], track=6) + bar(f'{pfx}sb', 0, dur, x + m_w, y, w2, h, p['deep'], track=6)
    out += st.text(f'{pfx}sm', 0, dur, st.mark, x + 24, y + (h - m_size * 1.3) / 2, m_size, p['ink'], track=7)
    out += st.text(f'{pfx}st', 0, dur, label, x + m_w + 24, y + (h - size * 1.3) / 2, size, p['white'], track=7, weight=700)
    js = ''
    if entrance:
        js = f'wipe("#{pfx}sa .in",.1,.3);wipe("#{pfx}sb .in",.2,.34);wipe("#{pfx}sm .in",.14,.3);wipe("#{pfx}st .in",.28,.34);'
    return out, js


def lower_third(st, c, i, pfx, hook=False, o=None):
    """A headline above the strip. A verdict or a number gets the accent plate, so the answer is what the eye lands on."""
    p = st.pal
    k = c['kind']
    a, b = c['a'], c['b']
    x, wd = (60, 960) if st.V else (72, 1240)
    hot = k in ('verdict', 'stat')
    base = {'verdict': 100, 'stat': 96}.get(k, 62) if not st.V else {'verdict': 104, 'stat': 96}.get(k, 66)
    rows = [] if st.V and hot else list(c['rows'])[:(1 if st.V else 2)]
    # below the footage on a phone there is room for two lines of words, whatever they are, and the desk starts right after
    size, lines = kit.fit_lines(c['title'], wd - 56, base, 42, 1 if st.V and rows else 2, FONT)
    rs = 40
    # Never drop words from a claim: a row that won't fit one line takes a second.
    row_lines = [kit.fit_lines(r, wd - 56, rs, 30, 2, FONT) for r in rows]
    lh = int(size * 1.28)
    h = lh * len(lines) + 26 + sum(int(s * 1.4) * len(rl) for s, rl in row_lines)
    if st.V and h > 190:      # the desk starts just below, so the heading gives way and the words stay
        size = max(42, size - (h - 190))
        lh = int(size * 1.28)
        h = lh * len(lines) + 26 + sum(int(s * 1.4) * len(rl) for s, rl in row_lines)
        if h > 190:
            print(f"  too long for a phone: {c['title']} / {' '.join(rows)}. Shorten it, because it runs under the desk.")
    y = 1160 if st.V else 930 - h
    w_ = max(kit.measure(ln, size, FONT) for ln in lines) + 56
    if row_lines:
        w_ = max(w_, max(kit.measure(ln, s, FONT) for s, rl in row_lines for ln in rl) + 56)
    w_ = min(w_, wd)
    plate, ink = (p['accent'], p['ink']) if hot else (p['white'], p['ink'])
    h_ = bar(f'{pfx}{i}p', a, b, x, y, w_, h, plate, track=3) + (bar(f'{pfx}{i}e', a, b, x, y, 12, h, p['accent'], track=4) if not hot else '')
    js = ('' if hook else f'wipe("#{pfx}{i}p .in",{a},.3);') + f'bye("#{pfx}{i}p .in",{b});' + (f'bye("#{pfx}{i}e .in",{b});' if not hot else '')
    ty = y + 8
    for j, ln in enumerate(lines):
        id_ = f'{pfx}{i}t{j}'
        h_ += st.text(id_, a, b, ln, x + 30, ty, size, ink, track=5)
        js += ('' if hook else f'rise("#{id_} .in",{round(a + .1 + j * .06, 2)});') + f'bye("#{id_} .in",{b});'
        ty += lh
    # A phone shows only the first row, so its times are the first row's.
    times = st.row_times(dict(c, rows=rows, opts=dict(c.get('opts', {}), times=c.get('opts', {}).get('times', [None] * len(rows))[:len(rows)]) if c.get('opts', {}).get('times') else c.get('opts', {})), o)
    for r_i, (s, rl) in enumerate(row_lines):
        for j, ln in enumerate(rl):
            id_ = f'{pfx}{i}r{r_i}{j}'
            h_ += st.text(id_, times[r_i], b, ln, x + 30, ty, s, p['deep'], track=5, weight=600)
            js += f'slide("#{id_} .in",{times[r_i]},-30);bye("#{id_} .in",{b});'
            ty += int(s * 1.4)
    return h_, js


def side_panel(st, c, i, pfx, o):
    """A list needs room a lower third can't give it, so it takes the side away from the speaker. On a phone it stays below the footage."""
    if st.V:
        return lower_third(st, c, i, pfx)
    p = st.pal
    a, b = c['a'], c['b']
    x = 1160 if c['who'] == 'H' else 72
    wd = 688
    size, lines = kit.fit_lines(c['title'], wd - 64, 66, 40, 2, FONT)
    lh = int(size * 1.26)
    rows = [kit.fit_lines(r, wd - 64, 46, 30, 2, FONT) for r in c['rows']]
    head_h = lh * len(lines) + 34
    body_h = sum(int(s * 1.36) * len(l) + 18 for s, l in rows) + 22
    y0 = 96
    h_ = bar(f'{pfx}{i}p', a, b, x, y0, wd, head_h, p['deep'], track=3) + bar(f'{pfx}{i}q', a, b, x, y0 + head_h, wd, body_h, p['white'], track=3)
    js = f'wipe("#{pfx}{i}p .in",{a},.3);wipe("#{pfx}{i}q .in",{round(a + .1, 2)},.3);bye("#{pfx}{i}p .in",{b});bye("#{pfx}{i}q .in",{b});'
    ty = y0 + 14
    for j, ln in enumerate(lines):
        id_ = f'{pfx}{i}t{j}'
        h_ += st.text(id_, a, b, ln, x + 32, ty, size, p['white'], track=5)
        js += f'rise("#{id_} .in",{round(a + .12, 2)});bye("#{id_} .in",{b});'
        ty += lh
    ty = y0 + head_h + 16
    times = st.row_times(c, o)
    for r_i, (s, rl) in enumerate(rows):
        for j, ln in enumerate(rl):
            id_ = f'{pfx}{i}r{r_i}{j}'
            h_ += st.text(id_, times[r_i], b, ln, x + 32, ty, s, p['ink'], track=5, weight=600)
            js += f'slide("#{id_} .in",{times[r_i]},-30);bye("#{id_} .in",{b});'
            ty += int(s * 1.36)
        ty += 18
    return h_, js


def name_plates(st, o, shots, pfx):
    """Only for a confirmed name, and only the first time that person talks in a chapter with no card in the way."""
    p = st.pal
    people = st.show.get('people', {})
    h_, js, shown = '', '', set()
    x, y = (60, 990) if st.V else (72, 856)
    for s in shots:
        who = s['who']
        person = people.get(who, {})
        if not person.get('name') or who in shown or s.get('card') or s['end'] - s['t'] < 3:
            continue
        shown.add(who)
        a, b = s['t'], round(min(s['end'], s['t'] + 5), 2)
        label = person['name'] + (f" · {person['role']}" if person.get('role') else '')
        size, _ = kit.fit_lines(label, 900, 42, 28, 1, FONT)
        w_ = kit.measure(label, size, FONT) + 48
        id_ = f'{pfx}n{who}'
        h_ += bar(f'{id_}p', a, b, x, y, w_, 76, p['deep'], track=3) + st.text(id_, a, b, label, x + 24, y + (76 - size * 1.3) / 2, size, p['white'], track=5, weight=700)
        js += f'wipe("#{id_}p .in",{a},.28);rise("#{id_} .in",{round(a + .08, 2)});bye("#{id_}p .in",{b});bye("#{id_} .in",{b});'
    return h_, js


def ticker(st, o, pfx):
    """Off unless asked for: it competes with subtitles. It only repeats this chapter's own card headlines."""
    if not st.pal.get('ticker'):
        return '', ''
    words = ('   •   '.join(c['title'] for c in o.cards) or o.title) + '   •   '
    y, h = (1360, 56) if st.V else (1024, 56)
    run = e(words * (int((o.dur * 70 + st.W) / max(kit.measure(words, 32, FONT, 700), 1)) + 2))
    html_ = f'<div class="tick" id="{pfx}tk" style="top:{y}px;height:{h}px"><div class="run" id="{pfx}tr" style="font-size:32px;line-height:{h}px">{run}</div></div>'
    return html_, f'tl.fromTo("#{pfx}tr",{{x:0}},{{x:{-round(o.dur * 70)},duration:{o.dur},ease:"none"}},0);'


def chapter(st, o, shots, k):
    h_, js = strip(st, o.id, o.title, o.dur)
    a, b = name_plates(st, o, shots, o.id)
    h_, js = h_ + a, js + b
    for i, c in enumerate(o.cards):
        a, b = side_panel(st, c, i, f'{o.id}c', o) if c['kind'] == 'rows' and len(c['rows']) > 2 else lower_third(st, c, i, f'{o.id}c', o=o)
        h_, js = h_ + a, js + b
    if st.V:      # a set, not a void: the desk carries the show's name, and the phone's own interface can sit on it
        h_ += f'<div class="desk">{e(st.mark)}</div>'
    a, b = ticker(st, o, o.id)
    return h_ + a, js + b


def cold(st, cards, shots):
    h_, js = strip(st, 'cc', st.paper.get('title', st.mark), st.bf.COLD, entrance=False)
    for i, c in enumerate(cards):
        a, b = lower_third(st, c, i, 'cc', hook=i == 0)
        h_, js = h_ + a, js + b
    if st.V:
        h_ += f'<div class="desk">{e(st.mark)}</div>'
    return h_, js


def full_card(st, pfx, heading, rows, dur, small=None):
    p = st.pal
    X = 60 if st.V else 130
    WD = st.W - 120 if st.V else 1130     # stops short of the sun, because white on amber can't be read
    size, lines = kit.fit_lines(heading, WD, 140, 64, 3, FONT)
    lh = int(size * 1.26)
    total = lh * len(lines) + (86 if small else 0) + sum(92 for _ in rows)
    y = (((168 + 1330) // 2) if st.V else st.H // 2) - total // 2
    d = 900
    cx, cy = (780, 1740) if st.V else (1810, 1000)
    h_ = f'<div class="wash"></div><div class="sun" id="{pfx}o" style="left:{cx - d // 2}px;top:{cy - d // 2}px;width:{d}px;height:{d}px"></div>'
    js = f'tl.fromTo("#{pfx}o",{{y:{d // 2}}},{{y:0,duration:.6,ease:"power3.out"}},0);'
    if small:
        h_ += st.text(f'{pfx}k', 0, dur, small, X, y, 50, p['accent'], track=2)
        js += f'wipe("#{pfx}k .in",.1,.3);'
        y += 86
    for j, ln in enumerate(lines):
        id_ = f'{pfx}l{j}'
        h_ += st.text(id_, 0, dur, ln, X, y, size, p['white'], track=2, weight=900)
        js += f'rise("#{id_} .in",{round(.12 + j * .08, 2)});'
        y += lh
    y += 14
    for i, r in enumerate(rows):
        rs, _ = kit.fit_lines(r, WD, 56, 34, 1, FONT)
        id_ = f'{pfx}r{i}'
        t = round(.5 + i * .3, 2)
        h_ += st.text(id_, t, dur, r, X, y, rs, p['white'], track=3, weight=600)
        js += f'slide("#{id_} .in",{t},-40);'
        y += 92
    return h_, js


def chapter_card(st, o, k):
    return full_card(st, f'{o.id}t', o.title, [], st.bf.CH_D)


def title(st):
    return full_card(st, 'ti', ' '.join(st.paper.get('title_lines') or [st.paper['title']]), [st.paper['sub']] if st.paper.get('sub') else [], st.bf.TITLE_D, small=st.mark)


def end(st):
    return full_card(st, 'en', st.paper.get('title', ''), st.paper.get('end_rows', []), st.bf.END_D, small=st.mark)


def cues(st):
    out = []
    for k, o in enumerate(st.bf.chs):
        out.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .24))
        out += [('stamp', o.at + c['a'], .2) for c in o.cards if c['kind'] in ('stat', 'verdict')]
    out.append(('whoosh_1', st.bf.END_AT, .24))
    return out


if __name__ == '__main__':
    kit.main(sys.modules[__name__])

#!/usr/bin/env python3
"""Animatic: storyboard panels held and moved in stepped, hand-made motion, cut to the real voice. Between panels, the real speaker, or the chapter's name for a show with no camera.

    python3 build.py FOLDER [--ratio 16x9|9x16|both] [--frames]

FOLDER is an episode or clip that has been through full_edit.py --render. Each card in cards.json is a panel. A card with a picture (opts.panel, opts.still or opts.obj) is that picture as a
pencil sketch; a card with none is its words, lettered in the frame. Sketching is local and free, so any picture will do and mixed sources still look like one storyboard.
Panels draw ideas and objects, never the people talking: faces stay natural, so never give this a picture of a person.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageOps
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-playbook' / 'scripts'))
import look_kit as kit
from look_kit import e

KEY, BED, GROUND = 'animatic', 'a', 'paper'
PALETTE = {'paper': '#F6F7F5', 'ink': '#1C2126', 'pencil': '#59626A', 'accent': '#D3261F', 'sketch': True}
FONTS = [('Itim', 'Itim-Regular.ttf', '400')]
FONT = 'Itim-Regular.ttf'
FAM = '"Itim", sans-serif'
BAND = (170, 900)
FRAME = {False: (110, 46, 1700, 860), True: (40, 170, 1000, 900)}
CAPTION = {False: (110, 922, 1700, 130), True: (60, 1086, 960, 244)}
# Stepped moves, in turn: push in, pull out, pan each way, drift. Six steps a second is what makes it read as drawn, and not as a slideshow.
MOVES = [(1.03, 1.12, 0, 0), (1.12, 1.03, 0, 0), (1.1, 1.1, -46, 0), (1.1, 1.1, 46, 0), (1.04, 1.1, -30, -14)]


def css(st):
    p = st.pal
    return f'''.ty {{ font-family: {FAM}; font-weight: 400; }}
    .pg {{ position: absolute; inset: 0; background: {p['paper']}; }}
    .win {{ position: absolute; overflow: hidden; background: #FFFFFF; }}
    .win img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
    svg.ink {{ position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }}
    svg.ink path {{ fill: none; stroke-linecap: round; stroke-linejoin: round; }}'''


def wobble(n):
    return ((n * 37) % 11 - 5) / 5


def frame_lines(st, i):
    """Two loose pencil rectangles, not a border: the same i always gives the same lines, so a render is repeatable."""
    x, y, w, h = FRAME[st.V]
    out = ''
    for k, width in ((0, 5), (1, 2.5)):
        o = [wobble(i + k * 3 + n) * (2.4 + k * 1.6) for n in range(8)]
        out += (f'<path d="M{x + o[0]:.0f},{y + o[1]:.0f} L{x + w + o[2]:.0f},{y + o[3]:.0f} L{x + w + o[4]:.0f},{y + h + o[5]:.0f} L{x + o[6]:.0f},{y + h + o[7]:.0f} Z" '
                f'stroke="{st.pal["ink"]}" stroke-width="{width}"/>')
    return f'<svg class="ink" viewBox="0 0 {st.W} {st.H}" aria-hidden="true">{out}</svg>'


def fit_on_subject(path, size):
    """Crop to the frame's shape around where the detail is. A still is often composed off-centre to leave room for a card, and a centre crop would cut its subject off."""
    im = Image.open(path).convert('RGB')
    g = np.asarray(im.convert('L').resize((160, 90)), np.float32)
    edge = np.abs(np.diff(g, axis=1))[:-1] + np.abs(np.diff(g, axis=0))[:, :-1]
    edge = np.where(edge > np.percentile(edge, 90), edge, 0)
    total = max(float(edge.sum()), 1.0)
    cx = float((edge.sum(0) * np.arange(edge.shape[1])).sum() / total / edge.shape[1])
    cy = float((edge.sum(1) * np.arange(edge.shape[0])).sum() / total / edge.shape[0])
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(cx, cy))


def sketch(path, size):
    """A pencil sketch from any picture: a colour-dodge of the picture over its blurred negative. Free and local, so every panel looks like the same hand."""
    im = fit_on_subject(path, size)
    g = np.asarray(im.convert('L'), np.float32)
    blur = np.asarray(Image.fromarray((255 - g).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(size) / 150)), np.float32)
    dodge = np.clip(g * 255 / np.maximum(255 - blur, 1), 0, 255)
    return Image.fromarray(((dodge / 255) ** 2.6 * 255).astype(np.uint8))


def source_of(st, name):
    src = st.root / 'assets_src'
    for f in [src / 'panels' / f'{name}{x}' for x in ('.png', '.jpg', '.jpeg')] + [src / f'{pre}_{name}{x}' for pre in ('a2', 'a') for x in ('.png', '.jpg', '.jpeg')] + [src / 'pop' / f'{name}.png']:
        if f.exists():
            return f
    return None


def prepare(st):
    """Every picture the cards name becomes a panel the shape of this film's frame. A card whose picture isn't there goes on as words, and is reported."""
    out = st.p / 'assets' / 'panels'
    out.mkdir(exist_ok=True)
    _, _, w, h = FRAME[st.V]
    st.panels, missing = {}, set()
    alias = st.paper.get('aliases', {})
    for o in st.bf.chs:
        for c in o.cards:
            name = c['opts'].get('panel') or c['opts'].get('still') or c['opts'].get('obj')
            name = alias.get(name, name)
            if not name:
                continue
            f = source_of(st, name)
            if not f:
                missing.add(name)
                continue
            dest = out / f'{name}.jpg'
            if not dest.exists() or f.stat().st_mtime > dest.stat().st_mtime:
                (sketch(f, (w, h)) if st.pal.get('sketch', True) else fit_on_subject(f, (w, h))).save(dest, quality=90)
            st.panels[id(c)] = name
    print(f"panels: {len(st.panels)} cards with a picture, {sum(len(o.cards) for o in st.bf.chs) - len(st.panels)} lettered in words" + (f". Named but missing, so lettered: {', '.join(sorted(missing))}" if missing else ''))


def caption(st, c, pfx, i, o, colour=None):
    """One line at a time under the panel, each landing as it's said. opts.times puts a row on its word; a row replaces what came before, as the next board would."""
    x, y, w, h = CAPTION[st.V]
    a, b = c['a'], c['b']
    times = st.row_times(c, o) if c['rows'] else []
    lines = [(c['title'], a, times[0] if times else b)]
    for k, r in enumerate(c['rows']):
        lines.append((r, times[k], times[k + 1] if k + 1 < len(times) else b))
    out = ''
    for n, (txt, t0, t1) in enumerate(lines):
        if t1 - t0 < .05:
            continue
        hot = n == 0 and c['kind'] in ('stat', 'verdict')
        size, ls = kit.fit_lines(txt, w, (96 if hot else 66) if not st.V else (92 if hot else 66), 40, 1 if not st.V else 3, FONT)
        lh = int(size * 1.3)
        ty = y + (h - lh * len(ls)) // 2
        for j, ln in enumerate(ls):
            out += st.text(f'{pfx}{i}c{n}{j}', t0, t1, ln, x + (w - kit.measure(ln, size, FONT)) / 2, ty + j * lh, size, st.pal['accent'] if hot else (colour or st.pal['ink']), track=4)
    return out


def panel(st, c, i, pfx, o=None):
    p = st.pal
    a, b = c['a'], c['b']
    d = round(b - a, 3)
    x, y, w, h = FRAME[st.V]
    name = st.panels.get(id(c)) if hasattr(st, 'panels') else None
    body = ''
    js = ''
    if name:
        s0, s1, dx, dy = MOVES[i % len(MOVES)]
        steps = max(2, round(d * 6))
        body = f'<div class="win" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"><img id="{pfx}{i}i" src="assets/panels/{name}.jpg" alt="" /></div>'
        js = f'tl.fromTo("#{pfx}{i}i",{{scale:{s0},x:{-dx},y:{-dy}}},{{scale:{s1},x:{dx},y:{dy},duration:{d},ease:"steps({steps})"}},{a});'
    html_ = f'<div id="{pfx}{i}" class="clip pg" data-start="{a}" data-duration="{d}" data-track-index="2">{body}{frame_lines(st, i)}</div>'
    if name:
        return html_ + caption(st, c, pfx, i, o), js
    # No picture: the board itself holds the words, because an empty frame is the one thing a storyboard can't show.
    colour = p['accent'] if c['kind'] in ('stat', 'verdict') else p['ink']
    size, ls = kit.fit_lines(c['title'], w - 160, {'verdict': 190, 'stat': 170}.get(c['kind'], 124), 56, 3, FONT)
    lh = int(size * 1.3)
    rows = [kit.fit_lines(r, w - 160, 66, 40, 2, FONT) for r in c['rows']]
    total = lh * len(ls) + 24 + sum(int(s * 1.34) * len(l) + 10 for s, l in rows)
    ty = y + max(30, (h - total) // 2)
    for j, ln in enumerate(ls):
        html_ += st.text(f'{pfx}{i}t{j}', a, b, ln, x + (w - kit.measure(ln, size, FONT)) / 2, ty, size, colour, track=4)
        ty += lh
    ty += 24
    times = st.row_times(c, o) if c['rows'] else []
    for k, (s, l) in enumerate(rows):
        for j, ln in enumerate(l):
            html_ += st.text(f'{pfx}{i}r{k}{j}', times[k], b, ln, x + (w - kit.measure(ln, s, FONT)) / 2, ty, s, p['pencil'], track=4)
            ty += int(s * 1.34)
        ty += 10
    return html_, js


def gaps(o):
    """The stretches of a chapter with no panel up."""
    out, t = [], 0.0
    for c in sorted(o.cards, key=lambda c: c['a']):
        if c['a'] - t > .2:
            out.append((round(t, 3), c['a']))
        t = max(t, c['b'])
    if o.dur - t > .2:
        out.append((round(t, 3), o.dur))
    return out


def talk_title(st, o, pfx):
    """What holds the frame when no panel is up. With a camera that's the speaker, and on a phone the chapter's name sits below them. With no camera it's the chapter's name, big."""
    p = st.pal
    out = '<div class="pg"></div>' if st.paper.get('audio_only') else ''     # plain paper over the plain video, so the grade can't show on an empty frame
    for n, (a, b) in enumerate(gaps(o)):
        if st.paper.get('audio_only'):
            x, y, w, h = FRAME[st.V]
            size, ls = kit.fit_lines(o.title, w - 200, 130, 60, 3, FONT)
            lh = int(size * 1.3)
            ty = y + (h - lh * len(ls)) // 2
            out += ''.join(st.text(f'{pfx}tt{n}{j}', a, b, ln, x + (w - kit.measure(ln, size, FONT)) / 2, ty + j * lh, size, p['pencil'], track=1) for j, ln in enumerate(ls))
        elif st.V:
            out += caption_plain(st, o.title, f'{pfx}tt{n}', a, b, p['pencil'])
    return out + (frame_lines(st, 3) if st.paper.get('audio_only') else '')


def caption_plain(st, txt, id_, a, b, colour):
    x, y, w, h = CAPTION[st.V]
    size, ls = kit.fit_lines(txt, w, 66, 40, 3, FONT)
    lh = int(size * 1.3)
    ty = y + (h - lh * len(ls)) // 2
    return ''.join(st.text(f'{id_}{j}', a, b, ln, x + (w - kit.measure(ln, size, FONT)) / 2, ty + j * lh, size, colour, track=1) for j, ln in enumerate(ls))


def footer(st):
    return f'<div class="ty" style="left:60px;top:1400px;font-size:46px;color:{st.pal["pencil"]}">{e(st.mark)}</div>'


def chapter(st, o, shots, k):
    h_ = talk_title(st, o, o.id)
    js = ''
    for i, c in enumerate(o.cards):
        a, b = panel(st, c, i, f'{o.id}c', o)
        h_, js = h_ + a, js + b
    return h_ + (footer(st) if st.V else ''), js      # last, so it sits over the panels and not under them


def cold(st, cards, shots):
    """The hook is on the first frame, because that frame is the thumbnail: the words on the board, and the real speaker around them."""
    p = st.pal
    if st.paper.get('audio_only'):      # with no speaker to show, the hook is a lettered panel from the first frame
        h_, js = '', ''
        for i, c in enumerate(cards):
            a, b = panel(st, dict(c, rows=[]), i, 'cc')
            h_, js = h_ + a, js + b
        return h_ + (footer(st) if st.V else ''), js
    h_ = footer(st) if st.V else ''
    x, y, w, h = CAPTION[st.V]
    for i, c in enumerate(cards):
        hot = c['kind'] in ('stat', 'verdict')
        size, ls = kit.fit_lines(c['title'], w, 84, 44, 2 if not st.V else 3, FONT)
        lh = int(size * 1.3)
        ty = y + (h - lh * len(ls)) // 2 if st.V else st.H - 56 - lh * len(ls)
        for j, ln in enumerate(ls):
            tw = kit.measure(ln, size, FONT)
            h_ += st.text(f'cc{i}t{j}', c['a'], c['b'], ln, x + (w - tw) / 2, ty + j * lh, size, p['accent'] if hot else p['ink'], track=3, extra=f"background:{p['paper']};padding:0 22px 4px;")
    return h_, ''


def full_page(st, pfx, heading, rows, dur, small=None):
    p = st.pal
    x = 80 if st.V else 150
    wd = st.W - 160 if st.V else 1500
    size, ls = kit.fit_lines(heading, wd, 150, 64, 3, FONT)
    lh = int(size * 1.3)
    total = lh * len(ls) + (84 if small else 0) + 40 + 90 * len(rows)
    y = (((168 + 1330) // 2) if st.V else st.H // 2) - total // 2
    h_ = '<div class="pg"></div>'
    js = ''
    if small:
        h_ += st.text(f'{pfx}k', 0, dur, small, x, y, 50, p['pencil'], track=2)
        y += 84
    for j, ln in enumerate(ls):
        id_ = f'{pfx}l{j}'
        h_ += st.text(id_, 0, dur, ln, x, y, size, p['ink'], track=2)
        js += f'wipe("#{id_} .in",{round(.1 + j * .2, 2)},.3);'
        y += lh
    w_ = max(kit.measure(ln, size, FONT) for ln in ls)
    h_ += (f'<svg class="ink" viewBox="0 0 {st.W} {st.H}" aria-hidden="true"><path id="{pfx}u" d="M{x - 4},{y + 6} C{x + w_ * .3:.0f},{y - 2} {x + w_ * .62:.0f},{y + 14} {x + min(w_ + 12, wd):.0f},{y + 6}" '
           f'stroke="{p["accent"]}" stroke-width="9" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>')
    js += f'draw("#{pfx}u",{round(.25 + len(ls) * .2, 2)},.3);'
    y += 44
    for i, r in enumerate(rows):
        rs, _ = kit.fit_lines(r, wd, 60, 36, 1, FONT)
        id_ = f'{pfx}r{i}'
        t = round(.6 + i * .32, 2)
        h_ += st.text(id_, t, dur, r, x, y, rs, p['pencil'], track=3)
        js += f'wipe("#{id_} .in",{t},.3);'
        y += 90
    return h_, js


def chapter_card(st, o, k):
    return full_page(st, f'{o.id}t', o.title, [], st.bf.CH_D)


def title(st):
    return full_page(st, 'ti', ' '.join(st.paper.get('title_lines') or [st.paper['title']]), [st.paper['sub']] if st.paper.get('sub') else [], st.bf.TITLE_D, small=st.mark)


def end(st):
    return full_page(st, 'en', st.paper.get('title', ''), st.paper.get('end_rows', []), st.bf.END_D, small=st.mark)


def cues(st):
    out = []
    for k, o in enumerate(st.bf.chs):
        out.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .22))
        out += [('stamp', o.at + c['a'], .2) for c in o.cards if c['kind'] in ('stat', 'verdict')]
    out.append(('whoosh_1', st.bf.END_AT, .22))
    return out


if __name__ == '__main__':
    kit.main(sys.modules[__name__])

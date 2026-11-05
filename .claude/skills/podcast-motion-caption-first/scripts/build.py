#!/usr/bin/env python3
"""Caption-First: clean footage and large captions, and one big moment for the number.

    python3 build.py FOLDER [--ratio 16x9|9x16|both] [--captions FILE] [--frames]

FOLDER is an episode or clip that has been through full_edit.py --render. Captions come from --captions (.srt or .json), else captions.json in the folder.
Burned-in words can't be corrected after upload, so they stay a DRAFT until a speaker of the language has read them while listening; set "captions_proofed": true in paper.json then.
The look uses no pictures, so it costs nothing beyond the voice and transcript.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-playbook' / 'scripts'))
import look_kit as kit
from look_kit import e

KEY, BED, GROUND = 'caption-first', 'a', 'paper'
PALETTE = {'ink': '#111417', 'paper': '#FFFFFF', 'accent': '#FFD21F', 'accent_ink': '#111417'}
FONTS = [('Noto Sans Thai', 'NotoSansThai.ttf', '100 900')]
FONT = 'NotoSansThai.ttf'
FAM = '"Noto Sans Thai", sans-serif'
BAND = (0, 1000)
BIG = ('stat', 'verdict')


def add_args(ap):
    ap.add_argument('--captions', help='an .srt, or a .json of [{s, e, t, hi?}], on the film clock')


def css(st):
    p = st.pal
    if st.V:
        cap = f'''.cap {{ position: absolute; left: 60px; right: 60px; top: 1010px; height: 320px; display: flex; align-items: center; justify-content: center; text-align: center; text-wrap: balance; }}
    .box {{ font-family: {FAM}; font-size: 76px; font-weight: 800; line-height: 1.28; color: {p['ink']}; }}
    .desk {{ position: absolute; left: 0; right: 0; top: 1370px; bottom: 0; background: {p['accent']}; }}
    .foot {{ position: absolute; left: 60px; right: 60px; top: 1416px; font-family: {FAM}; font-size: 46px; font-weight: 800; line-height: 1.3; text-align: center; color: {p['accent_ink']}; }}'''
    else:
        cap = f'''.cap {{ position: absolute; left: 110px; right: 110px; bottom: 60px; text-align: center; text-wrap: balance; overflow: visible; }}
    .box {{ display: inline; -webkit-box-decoration-break: clone; box-decoration-break: clone; font-family: {FAM}; font-size: 72px; font-weight: 800; line-height: 1.5; color: {p['ink']}; background: {p['paper']}; padding: 6px 28px 10px; }}'''
    return cap + f'''
    .box b {{ background: {p['accent']}; color: {p['accent_ink']}; padding: 0 12px; font-weight: inherit; }}
    .flood {{ position: absolute; inset: 0; background: {p['accent']}; }}
    .ty {{ font-family: {FAM}; font-weight: 900; }}
    .full {{ position: absolute; inset: 0; background: {p['accent']}; }}'''


def caption_lines(st):
    x = st.args.captions
    path = Path(x) if x else st.root / 'captions.json'
    if not path.exists():
        sys.exit(f'FAIL: no captions. Run make_srt.py and pass --captions FILE.srt, or write {path}')
    rows = kit.parse_srt(path) if path.suffix.lower() in ('.srt', '.vtt') else json.loads(path.read_text(encoding='utf-8'))
    if not st.paper.get('captions_proofed'):
        print(f'captions: {len(rows)} lines, a DRAFT: burned-in errors cannot be fixed after upload, so have them proofread and set "captions_proofed": true in paper.json before a delivery render')
    # the cold open has its own hook words, written for it
    return [r for r in rows if r['s'] >= st.bf.COLD - .01]


def hl(text, hi):
    t = e(text)
    return t.replace(e(hi), f'<b>{e(hi)}</b>', 1) if hi else t


def root_hosts(st):
    rows = caption_lines(st)
    body, js = [], []
    for i, c in enumerate(rows):
        d = round(c['e'] - c['s'], 3)
        body.append(f'<div id="cap{i}" class="clip cap" data-start="{c["s"]}" data-duration="{d}" data-track-index="0"><span class="box" id="cap{i}b">{hl(c["t"], c.get("hi"))}</span></div>')
    st.scene('captions', '\n    '.join(body), '', overlay=True)
    return (f'<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{st.bf.TOTAL}" '
            f'data-track-index="8" data-track-kind="captions" data-width="{st.W}" data-height="{st.H}" style="position:absolute;inset:0;z-index:20"></div>')


def big_moment(st, c, i, pfx, y_mid=None):
    """The one thing a look with no cards still owes the viewer: the number, huge, while the voice carries on."""
    p = st.pal
    wd = st.W - (120 if st.V else 240)
    size, lines = kit.fit_lines(c['title'], wd, 240 if c['kind'] == 'verdict' else 200, 88, 3, FONT)
    lh = int(size * 1.24)
    top = (y_mid if y_mid is not None else st.H // 2) - lh * len(lines) // 2 - 20
    a, b = c['a'], round(min(c['b'], c['a'] + 3.0), 2)
    h_ = f'<div id="{pfx}m{i}" class="clip" data-start="{a}" data-duration="{round(b - a, 3)}" data-track-index="3" style="position:absolute;inset:0"><div class="flood" id="{pfx}m{i}f"></div></div>'
    js = f'tl.fromTo("#{pfx}m{i}f",{{clipPath:"circle(0% at 50% 50%)"}},{{clipPath:"circle(120% at 50% 50%)",duration:.38,ease:"power3.out"}},{a});'
    for j, ln in enumerate(lines):
        id_ = f'{pfx}m{i}t{j}'
        h_ += st.text(id_, a, b, ln, (st.W - kit.measure(ln, size, FONT)) / 2, top + j * lh, size, p['accent_ink'], track=4)
        js += f'rise("#{id_} .in",{round(a + .12 + j * .08, 2)});'
    return h_, js


def chapter(st, o, shots, k):
    picked = next((c for c in o.cards if c['kind'] in BIG), None)
    h_, js = '', ''
    if picked:
        a, b = big_moment(st, picked, 0, o.id, y_mid=st.band[1] // 2 if st.V else None)
        h_, js = h_ + a, js + b
    # A clip opens on its question: on screen from frame 0, because that frame is the thumbnail.
    q = next((c for c in o.cards if c['kind'] == 'q' and c['a'] < 1), None) if st.clip else None
    if q:
        a, b = hook_text(st, q, o.id)
        h_, js = h_ + a, js + b
    if st.V:
        h_ += f'<div class="desk"></div><div class="foot" id="{o.id}ft">{e(o.title)}</div>'
    return h_, js


def hook_text(st, c, pfx):
    p = st.pal
    wd = st.W - (120 if st.V else 240)
    size, lines = kit.fit_lines(c['title'], wd, 120 if not st.V else 104, 60, 2, FONT)
    y0 = 190 if st.V else 64
    h_, js = '', ''
    for j, ln in enumerate(lines):
        id_ = f'{pfx}h{j}'
        h_ += st.text(id_, c['a'], c['b'], ln, (st.W - kit.measure(ln, size, FONT)) / 2, y0 + j * int(size * 1.36), size, p['accent_ink'], track=5, extra=f"background:{p['accent']};padding:2px 24px 8px;")
        js += f'bye("#{id_} .in",{c["b"]});'
    return h_, js


def cold(st, cards, shots):
    h_, js = '', ''
    for i, c in enumerate(cards):
        wd = st.W - (120 if st.V else 240)
        p = st.pal
        size, lines = kit.fit_lines(c['title'], wd, 96 if not st.V else 92, 56, 3, FONT)
        lh = int(size * 1.34)
        y0 = 1090 if st.V else st.H - 64 - lh * len(lines)
        for j, ln in enumerate(lines):
            id_ = f'cc{i}t{j}'
            h_ += st.text(id_, c['a'], c['b'], ln, (st.W - kit.measure(ln, size, FONT)) / 2, y0 + j * lh, size, p['accent_ink'] if c['kind'] == 'verdict' else p['ink'], track=3,
                          extra=f"background:{p['accent'] if c['kind'] == 'verdict' else p['paper']};padding:2px 24px 8px;")
    if st.V:
        h_ += f'<div class="desk"></div><div class="foot">{e(st.mark)}</div>'
    return h_, js


def full_card(st, pfx, heading, rows, dur, small=None):
    p = st.pal
    x = 60 if st.V else 130
    wd = st.W - 120 if st.V else (1240 if rows else 1660)
    size, lines = kit.fit_lines(heading, wd, 150, 72, 3, FONT)
    lh = int(size * 1.26)
    total = lh * len(lines) + (72 if small else 0) + sum(96 for _ in rows)
    y = max(SAFE := 180 if st.V else 110, ((1330 + 168) // 2 if st.V else st.H // 2) - total // 2)
    h_, js = f'<div class="full"></div>', ''
    if small:
        h_ += st.text(f'{pfx}k', 0, dur, small, x, y, 48, p['accent_ink'], track=2)
        js += f'wipe("#{pfx}k .in",.1);'
        y += 72
    for j, ln in enumerate(lines):
        id_ = f'{pfx}l{j}'
        h_ += st.text(id_, 0, dur, ln, x, y, size, p['accent_ink'], track=2)
        js += f'rise("#{id_} .in",{round(.12 + j * .08, 2)});'
        y += lh
    y += 18
    for i, r in enumerate(rows):
        rs, _ = kit.fit_lines(r, wd, 58, 36, 1, FONT)
        id_ = f'{pfx}r{i}'
        t = round(.5 + i * .3, 2)
        h_ += st.text(id_, t, dur, r, x, y, rs, p['accent_ink'], track=3, weight=600)
        js += f'slide("#{id_} .in",{t},-40);'
        y += 96
    return h_, js


def chapter_card(st, o, k):
    return full_card(st, f'{o.id}t', o.title, [], st.bf.CH_D)


def title(st):
    return full_card(st, 'ti', ' '.join(st.paper.get('title_lines') or [st.paper['title']]), [st.paper.get('sub', '')] if st.paper.get('sub') else [], st.bf.TITLE_D, small=st.mark)


def end(st):
    return full_card(st, 'en', st.paper.get('title', ''), st.paper.get('end_rows', []), st.bf.END_D, small=st.mark)


def cues(st):
    out = []
    for k, o in enumerate(st.bf.chs):
        out.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .24))
        c = next((c for c in o.cards if c['kind'] in BIG), None)
        if c:
            out.append(('stamp', o.at + c['a'], .22))
    out.append(('whoosh_1', st.bf.END_AT, .24))
    return out


if __name__ == '__main__':
    kit.main(sys.modules[__name__])

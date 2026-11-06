#!/usr/bin/env python3
"""Chat Feed: the conversation as a messaging app. The speakers stand on a slowly shifting gradient, and beside them a phone fills with the talk:
"typing…", then the card's heading as a message from whoever said it, its picture as an image message, and its rows as the replies that follow.
A stat or a verdict arrives as a big sticker. The feed keeps the whole chapter, scrolling up as it grows, and the phone moves to whichever side is free.

    python3 build.py FOLDER [--frames]

FOLDER is an episode or clip that has been through full_edit.py --render, with build/cutout.webm (the speakers alone): this look paints its own ground behind them.
Names come from show.json "people". Every message is the speaker's own words from cards.json: nothing is invented to make it look like chat. 16:9 only.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'podcast-playbook' / 'scripts'))
import look_kit as kit
import card_stage as cs
from look_kit import e

KEY, BED, GROUND = 'chat', 'b', 'g1'
PALETTE = {'g1': '#FDE2E4', 'g2': '#DFE7FD', 'g3': '#E2F0E9', 'g4': '#FFF1C9', 'phone': '#FFFFFF', 'ink': '#15171C', 'muted': '#8A8F98',
           'H': '#E3EDFF', 'G': '#FFE3EC', 'Hdot': '#3D7BFF', 'Gdot': '#FF4F86', 'sticker': '#FF3D6E'}
FONTS = [('Mitr', 'Mitr-SemiBold.ttf', '600')]
FONT = 'Mitr-SemiBold.ttf'
FAM = '"Mitr", sans-serif'
BAND = (0, 820)
PW, PH, PTOP = 720, 960, 60          # the phone
FEED_TOP, FEED_H = 118, PH - 118 - 34
BW = 540                              # widest bubble
GAP = 14


def css(st):
    p = st.pal
    return f'''.ty {{ font-family: {FAM}; font-weight: 600; }}
    .grad {{ position: absolute; inset: 0; z-index: 1; background: linear-gradient(120deg, {p['g1']}, {p['g2']}, {p['g3']}, {p['g4']}, {p['g1']}); background-size: 400% 400%; }}
    .soft {{ filter: drop-shadow(0 24px 30px rgba(40,40,80,.22)); }}
    .phone {{ position: absolute; z-index: 6; width: {PW}px; height: {PH}px; border-radius: 52px; background: {p['phone']}; box-shadow: 0 30px 60px rgba(30,30,70,.25), inset 0 0 0 10px #F1F2F6; overflow: hidden; }}
    .hdr {{ position: absolute; left: 0; top: 0; width: {PW}px; height: 100px; border-bottom: 2px solid #EEF0F4; }}
    .av {{ position: absolute; top: 28px; width: 46px; height: 46px; border-radius: 50%; color: #fff; font-size: 24px; text-align: center; line-height: 46px; }}
    .feedwin {{ position: absolute; left: 0; top: {FEED_TOP}px; width: {PW}px; height: {FEED_H}px; overflow: hidden; }}
    .feed {{ position: absolute; left: 0; top: 0; width: {PW}px; }}
    .msg {{ position: absolute; }}
    .bub {{ position: absolute; border-radius: 30px; }}
    .img {{ position: absolute; border-radius: 26px; background: #fff center/cover no-repeat; box-shadow: 0 0 0 2px #EEF0F4; }}
    .dot {{ position: absolute; width: 14px; height: 14px; border-radius: 50%; background: #A6ABB5; }}'''


def prepare(st):
    cs.need_cutout(st)
    cs.prepare_pictures(st, (880, 660))


def name(st, who):
    return (st.show.get('people', {}).get(who, {}).get('name') or ('Host' if who == 'H' else 'Guest'))


def said_by(st, c, r, o):
    """Who really said row r: a row can be the other host's line (Frozen's "แน่ใจนะ?" sits on Ruby's card), and a chat must never put words in the wrong mouth."""
    src_t = (c['opts'].get('times') or [None] * len(c['rows']))[r]
    if src_t is None and o is not None:
        src_t = st.bf.local2src(o, st.row_times(c, o)[r])
    return (st.bf.speaker(src_t + .05) if src_t is not None else None) or c['who']


def messages(st, c, o):
    """A card as messages: [(kind, land time, height, payload, sender)]. Heights are measured with the real font, so the feed scrolls exactly."""
    a, b, k = c['a'], c['b'], c['kind']
    out = []
    if k in ('stat', 'verdict'):
        ts, tl_, tlh = cs.lines(c['title'], BW + 40, 110, 52, 2, FONT)
        out.append(('sticker', a + .45, tlh * len(tl_) + 30, (ts, tl_, tlh), c['who']))
    else:
        ts, tl_, tlh = cs.lines(c['title'], BW - 60, 50, 32, 3, FONT)
        out.append(('bubble', a + .45, tlh * len(tl_) + 40, (ts, tl_, tlh), c['who']))
    src = cs.picture(st, c)
    if src:
        out.append(('image', a + .75, 330, src, c['who']))
    times = st.row_times(c, o) if c['rows'] else []
    for r, row in enumerate(c['rows']):
        rs, rl, rlh = cs.lines(row, BW - 60, 44, 30, 3, FONT)
        out.append(('bubble', max(times[r], a + .9), rlh * len(rl) + 36, (rs, rl, rlh), said_by(st, c, r, o)))
    return out


def with_names(st, msgs, last):
    """A name label goes above a message whenever the sender changes, as in any chat."""
    out = []
    for m in msgs:
        if m[4] != last:
            out.append(('name', m[1], 40, name(st, m[4]), m[4]))
            last = m[4]
        out.append(m)
    return out, last


def render_msg(st, m, who, y, id_, t, b, live):
    """One message at y in the feed. live: it lands at t; otherwise it is already there (history)."""
    p = st.pal
    kind, _, h, pay, _w = m
    left = who == 'H'
    js = ''
    if kind == 'name':
        x = 34 if left else None
        style = f'left:34px' if left else f'right:34px;text-align:right'
        h_ = f'<div class="msg ty" id="{id_}" style="{style};top:{y}px;width:400px;font-size:26px;color:{p["muted"]}">{e(pay)}</div>'
    elif kind == 'image':
        w_ = 440
        x = 28 if left else PW - 28 - w_
        h_ = f'<div class="img" id="{id_}" style="left:{x}px;top:{y}px;width:{w_}px;height:{h}px;background-image:url({pay})"></div>'
    else:
        size, ls, lh = pay
        if kind == 'sticker':
            tw = max(kit.measure(l, size, FONT, 600) for l in ls)
            x = 40 if left else PW - 40 - tw
            body = '<br>'.join(e(l) for l in ls)
            h_ = (f'<div class="msg ty" id="{id_}" style="left:{x}px;top:{y}px;font-size:{size}px;line-height:1.32;color:{p["sticker"]};'
                  f'transform:rotate({-4 if left else 4}deg);text-shadow:0 4px 0 #fff, 0 -4px 0 #fff, 4px 0 0 #fff, -4px 0 0 #fff">{body}</div>')
        else:
            tw = max(kit.measure(l, size, FONT, 600) for l in ls)
            w_ = min(BW, tw + 56)
            x = 28 if left else PW - 28 - w_
            body = '<br>'.join(e(l) for l in ls)
            radius = 'border-bottom-left-radius:8px' if left else 'border-bottom-right-radius:8px'
            h_ = (f'<div class="bub" id="{id_}" style="left:{x}px;top:{y}px;width:{w_}px;height:{h}px;background:{p[who]};{radius}">'
                  f'<div class="ty" style="left:28px;top:18px;font-size:{size}px;line-height:1.32;color:{p["ink"]}">{body}</div></div>')
    if live:
        origin = '0% 100%' if left else '100% 100%'
        js += f'tl.fromTo("#{id_}",{{scale:.55,opacity:0,transformOrigin:"{origin}"}},{{scale:1,opacity:1,duration:.24,ease:"back.out(2.2)"}},{round(t, 2)});'
    return h_, js


def column(st, cards, i, pfx, o):
    """The phone for card i: every message of the chapter so far, the newest landing as they are said."""
    p = st.pal
    c = cards[i]
    a, b = c['a'], c['b']
    x = 1920 - 60 - PW if c['who'] == 'H' else 60
    feed, js, y = '', '', 16
    last = None
    for j in range(i):
        hist, last = with_names(st, messages(st, cards[j], o), last)
        for n, m in enumerate(hist):
            h_, _ = render_msg(st, m, m[4], y, f'{pfx}{i}h{j}_{n}', 0, b, False)
            feed += h_
            y += m[2] + GAP
        y += 10
    # typing…, where the first message will land
    tid = f'{pfx}{i}ty'
    left = c['who'] == 'H'
    tx = 28 if left else PW - 28 - 120
    y += 0
    feed += f'<div class="bub" id="{tid}" style="left:{tx}px;top:{y + 40}px;width:120px;height:62px;background:{p[c["who"]]}">' + ''.join(f'<div class="dot" id="{tid}{d}" style="left:{26 + d * 26}px;top:24px"></div>' for d in range(3)) + '</div>'
    js += f'tl.set("#{tid}",{{opacity:1}},{a});tl.set("#{tid}",{{opacity:0}},{round(a + .44, 2)});'
    js += ''.join(f'tl.fromTo("#{tid}{d}",{{y:0}},{{y:-10,duration:.14,yoyo:true,repeat:1,ease:"power1.inOut"}},{round(a + .04 + d * .08, 2)});' for d in range(3))
    scroll = lambda h: max(0, h - FEED_H + 20)
    js += f'tl.set("#{pfx}{i}f",{{y:{-scroll(y + 110)}}},{a});'
    live, _ = with_names(st, messages(st, c, o), last)
    for n, m in enumerate(live):
        h_, j_ = render_msg(st, m, m[4], y, f'{pfx}{i}m{n}', m[1], b, True)
        feed += h_
        js += j_
        y += m[2] + GAP
        js += f'tl.to("#{pfx}{i}f",{{y:{-scroll(y)},duration:.26,ease:"power2.out"}},{round(m[1] - .02, 2)});'
    initials = ''.join(f'<div class="av ty" style="left:{34 + k * 34}px;background:{p[w + "dot"]};z-index:{2 - k}">{e(name(st, w)[:1])}</div>' for k, w in enumerate('HG'))
    hdr = f'<div class="hdr">{initials}<div class="ty" style="left:130px;top:32px;font-size:30px;color:{p["ink"]}">{e(st.mark)}</div></div>'
    d = round(b - a, 3)
    h_ = (f'<div id="{pfx}{i}" class="clip phone" data-start="{a}" data-duration="{d}" data-track-index="5" style="left:{x}px;top:{PTOP}px">{hdr}'
          f'<div class="feedwin"><div class="feed" id="{pfx}{i}f">{feed}</div></div></div>')
    prev = cards[i - 1] if i else None
    stay_in = prev and a - prev['b'] < .5 and prev['who'] == c['who']
    nxt = cards[i + 1] if i + 1 < len(cards) else None
    stay_out = nxt and nxt['a'] - b < .5 and nxt['who'] == c['who']
    dx = 760 if c['who'] == 'H' else -760
    if not stay_in:
        js += f'tl.fromTo("#{pfx}{i}",{{x:{dx},rotation:{4 if dx > 0 else -4}}},{{x:0,rotation:0,duration:.42,ease:"power3.out"}},{a});'
    if not stay_out:
        js += f'tl.to("#{pfx}{i}",{{x:{dx},duration:.26,ease:"power2.in"}},{round(b - .27, 2)});'
    return h_, js


def chapter(st, o, shots, k):
    gid = f'{o.id}g'
    h_ = f'<div class="grad" id="{gid}"></div>'
    js = f'tl.fromTo("#{gid}",{{backgroundPosition:"0% 40%"}},{{backgroundPosition:"100% 60%",duration:{o.dur},ease:"none"}},0);'
    hh, hj = cs.hosts(st, o.id, o.dur, o.bstart, shots)
    h_ += hh.replace('class="cam"', 'class="cam soft"', 1)
    js += hj
    for i in range(len(o.cards)):
        a, b = column(st, o.cards, i, f'{o.id}c', o)
        h_, js = h_ + a, js + b
    return h_, js


def cold(st, cards, shots):
    class O:
        pass
    h_, js = '', ''
    for i in range(len(cards)):
        a, b = column(st, cards[:i + 1][-1:], 0, f'cc{i}', None)
        h_, js = h_ + a, js + b
    return h_, js


def screen(st, pfx, heading, rows, dur, small=None):
    """The phone, centred on the gradient, with the heading as a sticker and the rows as messages from each host in turn."""
    p = st.pal
    h_ = f'<div class="grad" id="{pfx}g"></div>'
    js = f'tl.fromTo("#{pfx}g",{{backgroundPosition:"0% 40%"}},{{backgroundPosition:"100% 60%",duration:{dur},ease:"none"}},0);'
    x = (1920 - PW) // 2
    feed, y = '', 40
    ts, tl_, tlh = cs.lines(heading, PW - 100, 92, 44, 3, FONT)
    m = ('sticker', .4, tlh * len(tl_) + 30, (ts, tl_, tlh), 'H')
    a, b = render_msg(st, m, 'H', y, f'{pfx}s', .4, dur, True)
    feed += a.replace('transform:rotate(-4deg)', 'transform:rotate(-3deg)')
    js += b
    y += m[2] + 30
    for r, row in enumerate(rows):
        rs, rl, rlh = cs.lines(row, BW - 60, 40, 28, 3, FONT)
        who = 'HG'[r % 2]
        m = ('bubble', .9 + r * .5, rlh * len(rl) + 36, (rs, rl, rlh), who)
        a, b = render_msg(st, m, who, y, f'{pfx}r{r}', m[1], dur, True)
        feed, js, y = feed + a, js + b, y + m[2] + GAP
    hdr = f'<div class="hdr"><div class="ty" style="left:40px;top:32px;font-size:30px;color:{p["ink"]}">{e(small or st.mark)}</div></div>'
    h_ += f'<div id="{pfx}p" class="phone" style="left:{x}px;top:{PTOP}px">{hdr}<div class="feedwin"><div class="feed">{feed}</div></div></div>'
    js += f'tl.fromTo("#{pfx}p",{{y:240,opacity:0}},{{y:0,opacity:1,duration:.45,ease:"power3.out"}},.05);'
    return h_, js


def chapter_card(st, o, k):
    return screen(st, f'{o.id}t', o.title, [], st.bf.CH_D)


def title(st):
    return screen(st, 'ti', ' '.join(st.paper.get('title_lines') or [st.paper['title']]), [st.paper['sub']] if st.paper.get('sub') else [], st.bf.TITLE_D, small=st.mark)


def end(st):
    return screen(st, 'en', st.paper.get('title', ''), st.paper.get('end_rows', []), st.bf.END_D, small=st.mark)


def cues(st):
    out = []
    for k, o in enumerate(st.bf.chs):
        out.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .2))
        for c in o.cards:
            out.append(('boop', o.at + c['a'] + .45, .16))
            if c['kind'] in ('stat', 'verdict'):
                out.append(('pop', o.at + c['a'] + .5, .2))
    out.append(('whoosh_1', st.bf.END_AT, .22))
    return out


if __name__ == '__main__':
    if '--ratio' not in sys.argv:
        sys.argv += ['--ratio', '16x9']
    kit.main(sys.modules[__name__])

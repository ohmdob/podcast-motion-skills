#!/usr/bin/env python3
"""Writes the two full-episode HyperFrames projects from the paper edit. Free; regenerable. Fix things here, not in the generated HTML.

    python3 $S/build_full.py episodes/EPxx/full a b           # projects + assets + mix
    python3 $S/build_full.py episodes/EPxx/full a b --plan    # shot and card report only
    python3 $S/build_full.py episodes/EPxx/full v             # Pop Studio at 9:16, after b
    add --frames to any of these for a contact sheet of real frames, to judge a look before a long render

A  Studio Cut   graded footage, cut as two cameras, cards in a typographic label language, bright stills
B  Pop Studio   speakers cut out on colour fields that change by chapter, an arch behind each, type behind them, real objects (pop.py)

Reads   build/edl.json, faces.jsonl, pass1.json · cards.json · paper.json · assets_src/ · show.json
The one-camera recut: every framing is a crop of the same frames, so a shot can show whoever should be on screen at that moment.
A missing picture or sound never stops a build: a card with no still simply has none, a cue with no sound is left out, and each is reported. Everything the
episode says on screen (cold-open cards, end rows, the chart's words) comes from paper.json and cards.json, so nothing here belongs to one show.
Importing this module as a library (look_kit.py does) runs the planning and builds nothing.
"""
import bisect, html, json, math, os, re, shutil, statistics as st, subprocess, sys, unicodedata
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
import studio

ROOT = Path(sys.argv[1]).resolve()
SHOW = studio.load_show(ROOT)
W, H, FPS, SR = 1920, 1080, SHOW['fps'], 48000
MARK = SHOW['mark'] or SHOW['name']
HTML_LANG = studio.words(SHOW)['html']
B_ = ROOT / 'build'


def _need(path, how):
    if not Path(path).exists():
        sys.exit(f'FAIL: no {path}. {how}')


_need(B_ / 'edl.json', 'Run full_edit.py on this folder first.')
_need(ROOT / 'cards.json', 'Write the cards first: see references/file-formats.md.')
GSAP = 'https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js'
_cut = SHOW.get('looks', {}).get('studio-cut', {})    # a show's own colours, from show.json; a new palette gets judged on real frames first
INK, LABEL, LIME, TEAL = _cut.get('ink', '#10201F'), _cut.get('label', '#F4F7F5'), _cut.get('mark', '#E6E12E'), _cut.get('accent', '#0B7A76')

edl = json.loads((B_ / 'edl.json').read_text(encoding='utf-8'))
paper = json.loads((ROOT / 'paper.json').read_text(encoding='utf-8'))
paper.setdefault('sub', '')
MARK_SUB = f"{MARK} · {paper['sub']}" if paper['sub'] else MARK
cards_raw = json.loads((ROOT / 'cards.json').read_text(encoding='utf-8'))
SHARED = (ROOT / paper.get('from', '.')).resolve() / 'build'    # a clip reuses its episode's transcript and face tracking
_need(SHARED / 'pass1.json', 'transcript.py rows writes it.')
_need(SHARED / 'faces.jsonl', 'faces.swift writes it: see references/full-episode.md.')
pass1 = json.loads((SHARED / 'pass1.json').read_text(encoding='utf-8'))
CLIP = bool(paper.get('clip'))
TITLE_D, CH_D, END_D = (0.0, 0.0, 3.0) if CLIP else (3.2, 2.0, 8.0)
if not CLIP and not edl['cold']:
    sys.exit('FAIL: paper.json has no cold open. Frame 0 has to be a hook, so an episode needs one; a clip sets "clip": true.')
COLD_CARDS = [tuple(x) for x in paper.get('cold_cards', [])]
if len(COLD_CARDS) != len(edl['cold']):
    sys.exit(f"FAIL: paper.json has {len(edl['cold'])} cold-open cuts and {len(COLD_CARDS)} cold_cards; each cut needs one [text, kind, who]")
PLAN = '--plan' in sys.argv


def tc(x):
    if isinstance(x, (int, float)):
        return float(x)
    return sum(float(v) * 60 ** i for i, v in enumerate(reversed(x.split(':'))))     # mm:ss or hh:mm:ss


# ------------------------------------------------------------------ who is where, who is talking
sam = [json.loads(l) for l in open(SHARED / 'faces.jsonl')]
SPLIT_X = SHOW['face_split_x']
ts = [r['t'] for r in sam]
mh, mg, pos_h, pos_g = [], [], [], []
for r in sam:
    h = [f for f in r['f'] if f[0] < SPLIT_X and f[2] > 70]
    g = [f for f in r['f'] if f[0] >= SPLIT_X and f[2] > 70]
    mh.append(h[0][4] if h and h[0][4] >= 0 else None)
    mg.append(g[0][4] if g and g[0][4] >= 0 else None)
    pos_h.append(h[0][:3] if h else None)
    pos_g.append(g[0][:3] if g else None)


def activity(series, a, b):
    i, j = bisect.bisect_left(ts, a), bisect.bisect_left(ts, b)
    v = [m for m in series[i:j] if m is not None]
    return st.pstdev(v) if len(v) > 2 else 0.0


relabelled = 0
for r in pass1:
    # The labels are right far more often than the mouths are readable, so they only flip on strong evidence:
    # someone whose mouth stays almost still through a whole segment is not the one talking.
    if r['b'] - r['a'] >= 2.5:
        h, g = activity(mh, r['a'], r['b']), activity(mg, r['a'], r['b'])
        if r['who'] == 'H' and h < .0135 and g > .02:
            r['who'] = 'G'; relabelled += 1
        elif r['who'] == 'G' and g < .018 and h > .018:
            r['who'] = 'H'; relabelled += 1
starts1 = [r['a'] for r in pass1]


def speaker(t):
    i = bisect.bisect_right(starts1, t) - 1
    if i >= 0 and pass1[i]['a'] <= t < pass1[i]['b']:
        return pass1[i]['who']
    return None


def face_at(series, a, b):
    i, j = bisect.bisect_left(ts, a), max(bisect.bisect_left(ts, b), bisect.bisect_left(ts, a) + 1)
    v = [p for p in series[i:j] if p]
    if not v:
        v = [p for p in series[max(0, i - 60):i + 60] if p] or [p for p in series if p]
    if not v:      # no faces anywhere: a show with no camera, so any stable framing will do
        return [450.0, 390.0, 200.0] if series is pos_h else [1500.0, 390.0, 200.0]
    return [st.median(p[k] for p in v) for k in range(3)]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def framing(kind, a, b):
    """Scale and position for a shot over source seconds a–b. The other person is always fully out of frame in a close-up."""
    hx, hy, hw = face_at(pos_h, a, b)
    gx, gy, gw = face_at(pos_g, a, b)
    if kind == 'W':
        return 1.14, -134.0, -40.0
    if kind[0] == 'H':
        s = clamp(max(1.44, W / max(gx - .78 * gw, 800)), 1.44, 1.66)
        if kind.endswith('+'):
            s = min(s + .1, 1.72)
        return round(s, 3), 0.0, round(clamp(400 - s * hy, H - H * s, 0), 1)
    s = clamp(max(1.46, 1 / max(1 - (hx + .78 * hw) / W, .3)), 1.46, 1.66)
    if kind.endswith('+'):
        s = min(s + .1, 1.72)
    return round(s, 3), round(-(s - 1) * W, 1), round(clamp(410 - s * gy, H - H * s, 0), 1)


# ------------------------------------------------------------------ the clock
class Ch:
    pass


chs = []
pos = 0.0
for c in edl['chapters']:
    o = Ch()
    o.id, o.title, o.slices = c['id'], c['title'], c['slices']
    o.bstart = pos
    o.dur = round(sum(round((q - p) * FPS) for p, q in c['slices']) / FPS, 3)
    pos = round(pos + o.dur, 3)
    chs.append(o)
BODY = pos
COLD = round(sum(round((q - p) * FPS) for p, q in edl['cold']) / FPS, 3)
t = COLD + TITLE_D
for o in chs:
    o.card_at = round(t, 3)
    o.at = round(t + CH_D, 3)
    t = round(o.at + o.dur, 3)
END_AT = t
TOTAL = round(END_AT + END_D, 3)


def src2local(o, s):
    """Chapter-local seconds of source time s; inside a removed part it lands on the next kept frame."""
    acc = 0.0
    for p, q in o.slices:
        if s < p:
            return acc
        if s <= q:
            return acc + s - p
        acc += q - p
    return acc


def local2src(o, l):
    acc = 0.0
    for p, q in o.slices:
        if l <= acc + (q - p):
            return p + l - acc
        acc += q - p
    return o.slices[-1][1]


# ------------------------------------------------------------------ cards and shots
_unknown = sorted({row[0] for row in cards_raw} - {o.id for o in chs})
if _unknown:
    sys.exit(f"FAIL: cards.json names chapters paper.json doesn't have: {', '.join(_unknown)}. Those cards would be dropped silently. The chapters are: {', '.join(o.id for o in chs)}")
for o in chs:
    o.cards = []
    for ch, a, b, kind, title, rows, opts in cards_raw:
        if ch != o.id:
            continue
        if kind == 'chart':
            sys.exit(f'FAIL: the card at {a} in {ch} is a chart, which is hand-built for its episode and is not a card kind. Make it a stat or rows card, or build it as its own sub-composition.')
        la, lb = src2local(o, tc(a)), src2local(o, tc(b))
        if kind != 'q' or True:
            o.cards.append(dict(a=round(la, 2), b=round(lb, 2), kind=kind, title=title, rows=rows, opts=opts, src=tc(a)))
    o.cards.sort(key=lambda c: c['a'])
    for x, y in zip(o.cards, o.cards[1:]):
        x['b'] = min(x['b'], round(y['a'] - .12, 2))
    for c in o.cards:
        c['who'] = c['opts'].get('who') or speaker(local2src(o, c['a'] + .3)) or 'G'
        if c['b'] - c['a'] < 1.4:
            print(f"short card {o.id} {c['title']} {c['b'] - c['a']:.2f}s")


def plan_shots(o, pop_=False):
    """Cut on speaker change and on real jumps; lock the framing while a card is up; a listening shot now and then; a wide every so often."""
    jumps, acc, last = [], 0.0, None
    for p, q in o.slices:
        if last is not None and p - last > .5:
            jumps.append(round(acc, 2))
        acc += q - p
        last = q
    shots, t, n, since_listen = [], 0.0, 0, 8.0
    while t < o.dur - .01:
        card = next((c for c in o.cards if c['a'] - .05 <= t < c['b']), None)
        src = local2src(o, min(t + .4, o.dur))
        who = (card['who'] if card else None) or speaker(src) or (shots[-1]['who'] if shots else 'G')
        if card:
            end = card['b']
            nxt = next((j for j in jumps if j > t + 1.6), None)
            if nxt and nxt < end - 1.2:
                end = nxt
            kind = 'W' if pop_ and card['kind'] == 'q' else who + ('+' if n % 2 else '')
        else:
            # how long does this person keep talking?
            run_end, x = o.dur, t + .4
            while x < o.dur:
                w = speaker(local2src(o, x))
                if w and w != who:
                    # ignore a backchannel under 1.1 s
                    y = x
                    while y < o.dur and speaker(local2src(o, y)) in (w, None):
                        y += .2
                    if y - x >= 1.1:
                        run_end = x
                        break
                    x = y
                    continue
                x += .2
            n1 = next((c['a'] for c in o.cards if c['a'] > t), o.dur)
            target = 3.4 + (n * 2.3 % 3.6)
            end = min(run_end, n1, t + target)
            nxt = next((j for j in jumps if t + 1.6 < j < end + 1.5), None)
            if nxt:
                end = min(nxt, n1)
            if since_listen > 24 and run_end - t > 9 and n1 - t > 4:
                kind, end = ('G' if who == 'H' else 'H'), t + 1.9
                since_listen = 0
            elif (n % 3 == 1 and run_end - t > 2.6 and n1 - t > 2.2) if pop_ else (n % 5 == 3 and run_end - t > 5 and n1 - t > 3):
                kind = 'W'
            else:
                kind = who + ('+' if n % 2 else '')
        end = round(min(max(end, t + 1.0), o.dur) * FPS) / FPS
        if o.dur - end < .8:
            end = o.dur
        since_listen += end - t
        a, b = local2src(o, t), local2src(o, end)
        shots.append(dict(t=round(t, 3), end=round(end, 3), kind=kind, who=who, f=framing(kind, a, b), card=bool(card)))
        t = end
        n += 1
    return shots


for o in chs:
    o.shots = plan_shots(o)
print(f"timeline: cold {COLD:.1f} s · body {BODY / 60:.2f} min · total {TOTAL / 60:.2f} min ({int(TOTAL // 60)}:{TOTAL % 60:04.1f}) · relabelled speakers {relabelled}")
print(f"shots {sum(len(o.shots) for o in chs)} (mean {BODY / sum(len(o.shots) for o in chs):.1f} s) · cards {sum(len(o.cards) for o in chs)} · stills {sum(1 for o in chs for c in o.cards if c['opts'].get('still'))}")


def write_chapters():
    (B_ / 'chapters.json').write_text(json.dumps({'total': TOTAL, 'cold': COLD, 'end': END_AT, 'chapters': [{'id': o.id, 'title': o.title, 'card': o.card_at, 'at': o.at, 'dur': o.dur, 'bstart': o.bstart, 'slices': o.slices} for o in chs]}, ensure_ascii=False))


if PLAN:
    write_chapters()      # make_srt.py and matte_qc.py need the film's clock, and can run before a build
    sys.exit(0)


# ------------------------------------------------------------------ text fitting
def units(s):
    return sum(0 if unicodedata.category(ch) == 'Mn' or ch == 'ำ' else 1 for ch in s)


def fit(text, width, base, cw, minimum=48, max_lines=2):
    text = re.sub(r'(\d) (?=\S)', '\\1\u00a0', text).replace('≠ ', '≠\u00a0')    # a number stays with its unit
    size = base
    while size >= minimum:
        lines, cur = [], ''
        for w in text.split(' '):
            t_ = (cur + ' ' + w).strip()
            if units(t_) * size * cw > width and cur:
                lines.append(cur); cur = w
            else:
                cur = t_
        lines.append(cur)
        if len(lines) <= max_lines and all(units(x) * size * cw <= width for x in lines):
            return size, lines
        size -= 4
    return size + 4, lines


def e(x):
    return html.escape(x)


# ------------------------------------------------------------------ files
def scene(p, id_, css, body, js):
    (p / 'compositions').mkdir(exist_ok=True)
    (p / 'compositions' / f'{id_}.html').write_text(f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; }}
    {css}
  </style>
  <div id="root" data-composition-id="{id_}" data-width="{W}" data-height="{H}">
    {body}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {js}
    window.__timelines["{id_}"] = tl;
  </script>
</template>
''', encoding='utf-8')


def host(id_, start, dur, track, z):
    return (f'<div id="{id_}" data-composition-id="{id_}" data-composition-src="compositions/{id_}.html" data-start="{start}" data-duration="{dur}" '
            f'data-track-index="{track}" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="position:absolute;inset:0;z-index:{z}"></div>')


def write_index(p, comp):
    hosts = [] if CLIP else [host('cold', 0, COLD, 0, 1), host('title', COLD, TITLE_D, 1, 2)]
    for o in chs:
        if not CLIP:
            hosts.append(host(f'{o.id}t', o.card_at, CH_D, 1, 3))
        hosts.append(host(o.id, o.at, o.dur, 0, 3))
    hosts.append(host('end', END_AT, END_D, 1, 3))
    (p / 'index.html').write_text(f'''<!doctype html>
<html lang="{HTML_LANG}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="{GSAP}"></script>
    <style>* {{ margin: 0; padding: 0; box-sizing: border-box; }} html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: {INK}; }} #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}</style>
  </head>
  <body>
    <div id="root" data-composition-id="{comp}" data-start="0" data-duration="{TOTAL}" data-fps="{FPS}" data-width="{W}" data-height="{H}">
      {chr(10).join(hosts)}
      <audio id="mix" class="clip" src="assets/mix.wav" data-start="0" data-duration="{TOTAL}" data-track-index="9" data-volume="1"></audio>
    </div>
    <script>window.__timelines["{comp}"] = gsap.timeline({{ paused: true }});</script>
  </body>
</html>
''', encoding='utf-8')
    if CLIP:    # a clip has no title or chapter cards, so nothing may be left behind to fail a check
        hosted = {o.id for o in chs} | {'end'}
        for f in (p / 'compositions').glob('*.html'):
            if f.stem not in hosted:
                f.unlink()


def cam_js(shots, sel, eased=False):
    out = []
    last_person = None
    for k, s in enumerate(shots):
        sc, x, y = s['f']
        d = round(s['end'] - s['t'] - .001, 3)
        person = s['kind'][0]
        # the next shot's eased move starts 0.15 s before this one ends, so this one's drift stops first and two tweens never fight
        nxt = shots[k + 1] if k + 1 < len(shots) else None
        if eased and nxt and nxt['kind'][0] != person and nxt['end'] - nxt['t'] > .5:
            d = round(d - .16, 3)
        s1, x1, y1 = sc * 1.012, (x * 1.012 if person == 'G' else x), y - (1.012 - 1) * 400
        if s['kind'] == 'W':
            x1, y1 = x - 11, y - 6
        y1 = clamp(y1, H - H * s1, 0)
        if person == 'G' and s['kind'] != 'W':
            x1 = -(s1 - 1) * W
        if eased and last_person and person != last_person and d > .5:
            out.append(f'tl.to("{sel}",{{scale:{sc},x:{x},y:{y},duration:.3,ease:"power3.inOut"}},{max(0, round(s["t"] - .15, 3))});')
            out.append(f'tl.to("{sel}",{{scale:{s1:.4f},x:{x1:.1f},y:{y1:.1f},duration:{round(d - .16, 3)},ease:"none"}},{round(s["t"] + .16, 3)});')
        else:
            out.append(f'tl.set("{sel}",{{scale:{sc},x:{x},y:{y}}},{s["t"]});tl.to("{sel}",{{scale:{s1:.4f},x:{x1:.1f},y:{y1:.1f},duration:{d},ease:"none"}},{s["t"]});')
        last_person = person
    return ''.join(out)


# ------------------------------------------------------------------ the mix
def rd(f):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(f), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


VOICE_BODY = rd(B_ / 'voice_body.wav')
VOICE_COLD = rd(B_ / 'voice_cold.wav') if (B_ / 'voice_cold.wav').exists() and edl['cold'] else np.zeros(0, np.float32)
if not len(VOICE_BODY):
    sys.exit('FAIL: no build/voice_body.wav. Run full_edit.py --render first, or the film would be silent.')
# An episode can use its own sounds, then the show's library, then the skill's.
_project = SHOW['root']
SFX_DIRS = [d for d in (ROOT / paper['sfx_dir'] if paper.get('sfx_dir') else None, ROOT / 'assets_src' / 'sfx', _project / 'assets' / 'sfx', studio.SFX_LIB) if d and Path(d).is_dir()]
PEAKS = {}
SFX = {}
NO_SFX = set()


def music_bed(which):
    """The bed for a look: the episode's, then the show's, then the skill's default, which is a stand-in until the show has its own."""
    over = paper.get('music', {}).get(which)
    for f in ([ROOT / over] if over else []) + [ROOT / f'assets_src/music/bed_{which}.mp3', _project / f'assets/music/bed_{which}.mp3', studio.MUSIC_LIB / f'bed_{which}.mp3']:
        if f.exists():
            if f.parent == studio.MUSIC_LIB:
                print(f"music: the skill's default bed_{which}.mp3; give this show its own in assets/music/")
            return f
    return None


def sfx_file(n):
    """Sound by sound, so one file in a show's library doesn't hide the rest."""
    return next((d / f'{n}.mp3' for d in SFX_DIRS if (d / f'{n}.mp3').exists()), None)


def sfx_sig(n):
    if n not in SFX:
        s = rd(sfx_file(n))
        SFX[n] = s * (.708 / max(float(np.abs(s).max()), 1e-4))
    return SFX[n]


def peak_at(n):
    if n not in PEAKS:
        f = sfx_file(n)
        table = json.loads((f.parent / 'peaks.json').read_text()) if (f.parent / 'peaks.json').exists() else {}
        if n in table:
            PEAKS[n] = table[n][0]
        else:
            s = rd(f)
            PEAKS[n] = int(np.argmax([np.sqrt(np.mean(s[i:i + 480] ** 2)) for i in range(0, max(1, len(s) - 480), 480)])) * .01
    return PEAKS[n]


def mix(p, bed_file, stingers, end_gain):
    n = int((TOTAL + .1) * SR)
    v = np.zeros(n, np.float32)
    v[:len(VOICE_COLD)] += VOICE_COLD[:n]
    for o in chs:
        a, b = int(o.bstart * SR), int((o.bstart + o.dur) * SR)
        seg = VOICE_BODY[a:b]
        i = int(o.at * SR)
        v[i:i + len(seg)] += seg
    # music: a bed under the cold open, title, chapter cards, the rapid-fire round and the end. Nothing under plain talk.
    if bed_file:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(bed_file), '-af', 'highpass=f=90,equalizer=f=2600:t=q:w=1.4:g=-4,loudnorm=I=-16:TP=-2:LRA=9', '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
        bed = np.frombuffer(raw, np.float32)
        bed = np.tile(bed, n // len(bed) + 2)[:n]
        if CLIP:    # a short film keeps a low bed under the talk and comes up on the end card
            env_t, env_v = [0, .3, END_AT - .2, END_AT + .3, TOTAL - .7, TOTAL], [.0, .17, .17, end_gain, end_gain, .0]
        else:
            pts = [(0, .0), (.3, .17), (COLD - .2, .17), (COLD + .2, .5), (COLD + TITLE_D - .1, .5)]
            env_t, env_v = [p_[0] for p_ in pts], [p_[1] for p_ in pts]
            for o in chs:
                floor = .10 if o.id in paper.get('music_under', []) else 0.0
                for tt, vv in [(o.card_at - .1, .34 if o is not chs[0] else .5), (o.card_at + .1, .42), (o.at - .1, .42), (o.at + .5, floor), (o.at + o.dur - .2, floor)]:
                    env_t.append(tt); env_v.append(vv)
            env_t += [END_AT - 1.0, END_AT + .3, TOTAL - 1.0, TOTAL]; env_v += [0.0, end_gain, end_gain, 0.0]
        env = np.interp(np.arange(n) / SR, env_t, env_v).astype(np.float32)
        v += bed * env
    else:
        print('no music bed: voice and effects only')
    for name, t_, vol in stingers:
        if CLIP and t_ < .5:     # the chapter-card sounds have no card to belong to in a clip
            continue
        if not sfx_file(name):
            NO_SFX.add(name)
            continue
        s = sfx_sig(name)
        i = max(0, int((t_ + .04 - peak_at(name)) * SR))
        v[i:i + len(s)] += (s * vol)[:max(0, n - i)]
    if NO_SFX:
        print(f"no sound for these cues, left out: {', '.join(sorted(NO_SFX))}")
    a = p / 'assets'
    a.mkdir(parents=True, exist_ok=True)
    tmp = a / '_m.raw'
    np.clip(v, -1, 1).astype(np.float32).tofile(tmp)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(tmp), '-ac', '2', '-c:a', 'pcm_s16le', str(a / 'mix.wav')], check=True)
    tmp.unlink()


def relink(src, dst):
    dst.unlink(missing_ok=True)
    os.link(src, dst)


def clean_project(p):
    shutil.rmtree(p / 'compositions', ignore_errors=True)


# ------------------------------------------------------------------ A · Studio Cut
def build_a():
    p = ROOT / 'variant_a'
    if not (p / 'hyperframes.json').exists():
        subprocess.run(['npx', 'hyperframes', 'init', str(p), '--skip-skills'], capture_output=True, check=True)
    clean_project(p)
    a = p / 'assets'
    (a / 'fonts').mkdir(parents=True, exist_ok=True)
    src = ROOT / 'assets_src'
    for f in [f for pat in ('a2_*', 'a_*') for f in src.glob(pat) if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]:
        out = a / (f.stem.split('_', 1)[1] + '.jpg')
        if not out.exists() or f.stat().st_mtime > out.stat().st_mtime:     # a replaced picture has to reach the film
            ImageOps.fit(Image.open(f).convert('RGB'), (2240, 1260), Image.LANCZOS).save(out, quality=92, subsampling=0)      # cropped, never stretched
    shutil.copy(studio.FONTS / 'NotoSansThai.ttf', a / 'fonts')
    relink(B_ / 'body.mp4', a / 'body.mp4')
    if edl['cold']:
        relink(B_ / 'cold.mp4', a / 'cold.mp4')
    grade = html.escape(json.dumps({'preset': None, 'intensity': 1, 'adjust': {'exposure': 0, 'contrast': .07, 'highlights': 0, 'shadows': 0, 'whites': 0, 'blacks': 0, 'temperature': .03, 'tint': 0, 'vibrance': 0, 'saturation': .08},
                                    'details': {'vignette': .1, 'vignetteMidpoint': .5, 'vignetteRoundness': 0, 'vignetteFeather': .65, 'grain': 0, 'grainSize': .25}}), quote=True)
    fam = '"Inter", "Noto Sans Thai", sans-serif'
    css = f'''@font-face {{ font-family: "Noto Sans Thai"; src: url("assets/fonts/NotoSansThai.ttf") format("truetype"); font-weight: 100 900; }}
    #root {{ background: {INK}; }}
    .cam {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; transform-origin: 0 0; }}
    .cam video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
    .br {{ position: absolute; inset: 0; overflow: hidden; z-index: 3; }} .br img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
    .label {{ position: absolute; background: {LABEL}; color: {INK}; font-family: {fam}; padding: 26px 34px 30px; overflow: visible; z-index: 5; }}
    .rule {{ background: {INK}; width: 100%; transform-origin: 0 50%; }}
    .r14 {{ height: 14px; margin: 12px 0 14px; }} .r6 {{ height: 6px; margin: 10px 0; }} .r2 {{ height: 3px; margin: 8px 0; }}
    .tt {{ font-weight: 900; line-height: 1.2; letter-spacing: -.01em; }}
    .row {{ font-size: 46px; font-weight: 600; line-height: 1.34; }}
    .mark {{ background: {LIME}; padding: 0 14px; font-weight: 900; display: inline-block; }}
    .full {{ left: 0; top: 0; width: 100%; height: 100%; padding: 0 130px; display: flex; flex-direction: column; justify-content: center; }}'''
    JS_HELP = '''
    const inL = (s, t) => tl.fromTo(s, { clipPath: "inset(0% 0% 100% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: .4, ease: "expo.out" }, t);
    const outL = (s, t) => tl.to(s, { clipPath: "inset(0% 0% 0% 100%)", duration: .22, ease: "power3.in" }, t - .22);
    const inked = (s, t) => tl.fromTo(s, { opacity: 0, filter: "blur(6px)" }, { opacity: 1, filter: "blur(0px)", duration: .16, ease: "power2.out" }, t);
    const ruled = (s, t) => tl.fromTo(s, { scaleX: 0 }, { scaleX: 1, duration: .3, ease: "power3.out" }, t);
    '''

    def card_html(c, i, prefix):
        side = 1014 if c['who'] == 'H' else 96
        base = {'q': 96, 'term': 104, 'stat': 104, 'verdict': 128, 'take': 88, 'rows': 84}.get(c['kind'], 88)
        size, lines = fit(c['title'], 728, base, .6)
        tt = ''.join(f'<div class="tt" style="font-size:{size}px">' + (f'<span class="mark">{e(x)}</span>' if c['kind'] == 'verdict' else e(x)) + '</div>' for x in lines)
        rows = ''
        js = [f'inL("#{prefix}{i}",{c["a"]});', f'outL("#{prefix}{i}",{c["b"]});']
        if c['rows']:
            rows += f'<div class="rule r14" id="{prefix}{i}r"></div>'
            gap = (c['b'] - c['a'] - 1.6) / max(len(c['rows']), 1)
            for k, r in enumerate(c['rows']):
                rs, rl = fit(r, 728, 46, .56, 34, 2)
                rows += ''.join(f'<div class="row" id="{prefix}{i}x{k}{j}" style="font-size:{rs}px">{e(x)}</div>' for j, x in enumerate(rl))
                if k < len(c['rows']) - 1:
                    rows += '<div class="rule r2"></div>'
                t_ = round(c['a'] + .35 + min(gap, 2.6) * k, 2)
                js += [f'inked("#{prefix}{i}x{k}{j}",{t_});' for j in range(len(rl))]
        return (f'<div id="{prefix}{i}" class="clip label" data-start="{c["a"]}" data-duration="{round(c["b"] - c["a"], 3)}" data-track-index="{2 + i % 3}" style="left:{side}px;top:96px;width:800px">{tt}{rows}</div>', ''.join(js))

    for o in chs:
        body, js = [f'<div class="cam" id="cam-{o.id}"><video id="v-{o.id}" class="clip" src="assets/body.mp4" data-start="0" data-duration="{o.dur}" data-media-start="{o.bstart}" data-track-index="0" muted playsinline data-color-grading="{grade}"></video></div>'], [JS_HELP, cam_js(o.shots, f'#cam-{o.id}')]
        for i, c in enumerate(o.cards):
            h_, j_ = card_html(c, i, o.id + 'c')
            body.append(h_); js.append(j_)
            st_ = c['opts'].get('still')
            if st_ and not (a / f'{st_}.jpg').exists():
                print(f'no still {st_}: card {c["title"]} goes without')
                st_ = None
            if st_:
                d = round(min(3.8, c['b'] - c['a']), 2)
                flip = c['who'] == 'H'
                body.append(f'<div id="{o.id}s{i}" class="clip br" data-start="{c["a"]}" data-duration="{d}" data-track-index="1"><img id="{o.id}s{i}i" src="assets/{st_}.jpg" alt="" /></div>')
                sx0, sx1 = (-1.03, -1.1) if flip else (1.03, 1.1)
                js.append(f'tl.fromTo("#{o.id}s{i}i",{{scaleX:{sx0},scaleY:1.03}},{{scaleX:{sx1},scaleY:1.1,duration:{d},ease:"none"}},{c["a"]});')
        scene(p, o.id, css, '\n    '.join(body), ''.join(js))

    # chapter cards are the label itself
    for k, o in enumerate(chs):
        size, lines = fit(o.title, 1640, 150, .6)
        tt = ''.join(f'<div class="tt" id="{o.id}tl{j}" style="font-size:{size}px">{e(x)}</div>' for j, x in enumerate(lines))
        scene(p, f'{o.id}t', css, f'''<div id="{o.id}tb" class="label full"><div class="rule r14" id="{o.id}tr"></div>{tt}<div class="rule r6" id="{o.id}tr2"></div></div>''',
              JS_HELP + f'tl.fromTo("#{o.id}tb",{{clipPath:"inset(0% 100% 0% 0%)"}},{{clipPath:"inset(0% 0% 0% 0%)",duration:.3,ease:"power3.inOut"}},0);ruled("#{o.id}tr",.14);ruled("#{o.id}tr2",.3);tl.to("#{o.id}tb",{{clipPath:"inset(0% 0% 0% 100%)",duration:.2,ease:"power3.in"}},{CH_D - .22});')
    # title
    scene(p, 'title', css, f'''<div id="tb" class="label full"><div style="font-size:52px;font-weight:800">{e(MARK)}</div><div class="rule r14" id="tr"></div><div class="tt" style="font-size:150px">{e(paper["title"])}</div><div class="rule r6" id="tr2"></div><div class="row" id="ts" style="font-size:56px;font-weight:700">{e(paper["sub"])}</div></div>''',
          JS_HELP + 'tl.fromTo("#tb",{clipPath:"inset(0% 100% 0% 0%)"},{clipPath:"inset(0% 0% 0% 0%)",duration:.4,ease:"power3.inOut"},0);ruled("#tr",.25);ruled("#tr2",.5);inked("#ts",.7);')
    # end: left side carries the summary, the right side stays free for YouTube's end-screen elements
    rows = paper.get('end_rows', [])
    scene(p, 'end', css, f'''<div id="eb" class="label full" style="padding-right:600px"><div class="tt" style="font-size:104px">{e(paper["title"])}</div><div class="rule r14" id="er"></div>''' +
          '<div class="rule r2"></div>'.join(f'<div class="row" id="er{i}" style="font-size:54px;padding:6px 0">{e(r)}</div>' for i, r in enumerate(rows)) +
          f'''<div class="rule r6" id="er9" style="margin-top:22px"></div><div class="row" id="ef" style="font-size:44px;font-weight:800">{e(MARK_SUB)}</div></div>''',
          JS_HELP + 'tl.fromTo("#eb",{clipPath:"inset(0% 100% 0% 0%)"},{clipPath:"inset(0% 0% 0% 0%)",duration:.42,ease:"power3.inOut"},0);ruled("#er",.3);' + ''.join(f'inked("#er{i}",{[".5", ".75", "1.0"][i] if i < 3 else round(.5 + i * .25, 2)});' for i in range(len(rows))) + 'ruled("#er9",1.2);inked("#ef",1.35);')
    # cold open: three questions, three answers
    cuts = []
    acc = 0.0
    for q_, r_ in edl['cold']:
        cuts.append((round(acc, 3), round(acc + q_ - r_ * 0 - r_ if False else acc + (r_ - q_), 3), q_, r_))
        acc += r_ - q_
    texts = COLD_CARDS
    shots = [dict(t=a_, end=b_, kind=wh, who=wh, f=framing(wh, q_, r_)) for (a_, b_, q_, r_), (_, _, wh) in zip(cuts, texts)]
    body, js = [f'<div class="cam" id="cam-cold"><video id="v-cold" class="clip" src="assets/cold.mp4" data-start="0" data-duration="{COLD}" data-track-index="0" muted playsinline data-color-grading="{grade}"></video></div>'], [JS_HELP, cam_js(shots, '#cam-cold')]
    for i, ((a_, b_, _, _), (tx, kd, wh)) in enumerate(zip(cuts, texts)):
        c = dict(a=a_, b=round(b_, 2), kind=kd, title=tx, rows=[], who=wh, opts={})
        h_, j_ = card_html(c, i, 'cc')
        if i == 0:   # the hook is on screen from frame 0
            j_ = j_.replace(f'inL("#cc0",{a_});', '')
        body.append(h_); js.append(j_)
    scene(p, 'cold', css, '\n    '.join(body), ''.join(js))
    write_index(p, 'studio-cut-full')
    cues = [('whoosh_1', COLD, .3)]
    for k, o in enumerate(chs):
        cues.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at, .24))
        for c in o.cards:
            if c['kind'] in ('stat', 'verdict'):
                cues.append(('stamp', o.at + c['a'], .22))
    cues.append(('whoosh_1', END_AT, .26))
    mix(p, music_bed('a'), cues, .46)
    print('OK: variant_a')


# ------------------------------------------------------------------ B · Pop Studio
def build_b():
    """The look lives in pop.py. Speakers are cut out of the frame (make_cutout.py), so a shot can place them anywhere."""
    import pop
    pop.apply_show(SHOW)
    _need(B_ / 'cutout.webm', 'Run rvm_matte.py, then make_cutout.py: see the podcast-motion-pop-studio skill.')
    p = ROOT / 'variant_b'
    if not (p / 'hyperframes.json').exists():
        subprocess.run(['npx', 'hyperframes', 'init', str(p), '--skip-skills'], capture_output=True, check=True)
    clean_project(p)
    a = p / 'assets'
    shutil.rmtree(a, ignore_errors=True)
    (a / 'fonts').mkdir(parents=True, exist_ok=True)
    (a / 'obj').mkdir()
    fonts = studio.FONTS
    for f in pop.FONT_FILES.values():
        shutil.copy(fonts / f, a / 'fonts')
    size_of = {}
    for f in (ROOT / 'assets_src/pop').glob('*.png'):
        if f.stem.startswith('src_'):
            continue
        im = Image.open(f).convert('RGBA')
        im.thumbnail((1000, 1000), Image.LANCZOS)
        im.save(a / 'obj' / f.name, optimize=True)
        size_of[f.stem] = im.size
    # a picture with no single subject can't be cut out, so it stands in an arch-shaped window (paper.json "windows": names of src_<name>.png)
    for win in paper.get('windows', []):
        cls = Image.open(ROOT / f'assets_src/pop/src_{win}.png').convert('RGB')
        cw, ch = cls.size
        cls = cls.crop((int(cw / 2 - ch * .4), 0, int(cw / 2 + ch * .4), ch)).resize((800, 1000), Image.LANCZOS)
        mask = Image.new('L', (800, 1000), 0)
        from PIL import ImageDraw
        d = ImageDraw.Draw(mask)
        d.ellipse((0, 0, 800, 800), fill=255)
        d.rectangle((0, 400, 800, 1000), fill=255)
        cls.putalpha(mask)
        cls.save(a / f'obj/{win}.png', optimize=True)
        size_of[win] = (800, 1000)
    ALIAS = paper.get('aliases', {})
    relink(B_ / 'cutout.webm', a / 'cutout.webm')
    if edl['cold']:
        relink(B_ / 'cutout_cold.webm', a / 'cutout_cold.webm')
    occ_b = np.load(B_ / 'cutout.occ.npy') if (B_ / 'cutout.occ.npy').exists() else None
    occ_c = np.load(B_ / 'cutout_cold.occ.npy') if (B_ / 'cutout_cold.occ.npy').exists() else None

    def ty(id_, a_, b_, txt, x, y, size, ink, wt=700, cls_='', inner='', extra=''):
        return (f'<div id="{id_}" class="clip ty {cls_}" data-start="{a_}" data-duration="{round(b_ - a_, 3)}" data-track-index="2" style="left:{round(x)}px;top:{round(y)}px;font-size:{size}px;font-weight:{wt};color:{ink};{extra}"><span class="in" style="{inner}">{pop.e(txt)}</span></div>')

    def obj_tag(id_, name, a_, b_, x, y, h_, w_):
        return f'<div id="{id_}" class="clip ob" data-start="{a_}" data-duration="{round(b_ - a_, 3)}" data-track-index="3" style="left:{round(x)}px;top:{round(y)}px;width:{w_}px;height:{h_}px"><span class="in"><img src="assets/obj/{name}.png" alt="" style="width:{w_}px;height:{h_}px" /></span></div>'

    def fit_obj(name, max_w, max_h):
        ow, oh = size_of[name]
        k = min(max_w / ow, max_h / oh)
        return int(ow * k), int(oh * k)

    def card(c, i, pfx, pal, hook=False):
        """Text on the side the speaker faces. The heading goes behind the person, so a gesture passes in front of it; the rows stay on top."""
        back, front, js = [], [], []
        k = c['kind']
        ob = c['opts'].get('still') or c['opts'].get('obj')
        ob = ALIAS.get(ob, ob)
        if k == 'q':
            size, lines = pop.fit(c['title'], 1800, 176, 112, 1) if pop.measure(c['title'], 112) <= 1800 else pop.fit(c['title'], 1800, 104, 72, 2)
            y = 6 if len(lines) == 1 else 2
            for j, ln in enumerate(lines):
                id_ = f'{pfx}{i}t{j}'
                back.append(ty(id_, c['a'], c['b'], ln, 960 - pop.measure(ln, size) / 2, y, size, pal['ink']))
                if not hook:
                    js.append(f'rise("#{id_} .in",{round(c["a"] + j * .08, 2)});')
                js.append(f'bye("#{id_} .in",{c["b"]});')
                y += int(size * 1.26)
            if ob and ob in size_of:
                w_, h_ = fit_obj(ob, 420, 420)
                id_ = f'{pfx}{i}o'
                back.append(obj_tag(id_, ob, c['a'], c['b'], 960 - w_ / 2, 1040 - h_, h_, w_))
                js.append(f'popIn("#{id_} .in",{round(c["a"] + .15, 2)},{-6 if i % 2 else 6});popOut("#{id_} .in",{c["b"]});')
            return back, front, ''.join(js), bool(ob)
        X, WD = (930, 920) if c['who'] == 'H' else (80, 880)
        base = {'verdict': 190, 'stat': 150, 'term': 136, 'take': 116, 'rows': 110}.get(k, 116)
        size, lines = pop.fit(c['title'], WD - (70 if k == 'term' else 0), base, 72, 3)
        ink = {'verdict': pal['fink'], 'stat': pal['hero']}.get(k, pal['ink'])
        lh = int(size * 1.48) if k == 'term' else int(size * 1.28)
        y = 84
        row_h = sum(int(pop.fit(r, WD - 44, 64, 40, 2, wt=600)[0] * 1.34) * len(pop.fit(r, WD - 44, 64, 40, 2, wt=600)[1]) for r in c['rows'])
        body_h = lh * len(lines) + 14 + row_h
        has_obj = bool(ob and ob in size_of and 1050 - (84 + body_h) >= 190)
        if not has_obj:
            y = max(70, (940 - body_h) // 2)
        for j, ln in enumerate(lines):
            id_ = f'{pfx}{i}t{j}'
            if k == 'term':
                back.append(ty(id_, c['a'], c['b'], ln, X, y, size, pal['mink'], cls_='block', inner=f'background:{pal["mark"]}'))
                y += int(size * 1.48)
                if not hook:
                    js.append(f'wipe("#{id_} .in",{round(c["a"] + j * .1, 2)});')
            else:
                back.append(ty(id_, c['a'], c['b'], ln, X, y, size, ink))
                y += lh
                if not hook:
                    js.append(f'rise("#{id_} .in",{round(c["a"] + j * .1, 2)});')
            js.append(f'bye("#{id_} .in",{c["b"]});')
        y += 14
        gap = (c['b'] - c['a'] - 1.6) / max(len(c['rows']), 1)
        row_ink = pal['fink'] if k == 'verdict' else pal['ink']
        dot = pal['fink'] if k == 'verdict' else pal['a']
        for r_i, r in enumerate(c['rows']):
            rs, rl = pop.fit(r, WD - 44, 64, 40, 2, wt=600)
            t_ = round(c['a'] + .35 + min(gap, 2.6) * r_i, 2)
            for j, ln in enumerate(rl):
                id_ = f'{pfx}{i}r{r_i}{j}'
                mark = f'<i class="dot" style="background:{dot}"></i>' if j == 0 else ''
                pad = 0 if j == 0 else int(rs * .78)
                front.append(ty(id_, t_, c['b'], ln, X + pad, y, rs, row_ink, 600).replace('<span class="in" style="">', f'<span class="in" style="">{mark}'))
                js.append(f'slide("#{id_} .in",{t_},{-50 if c["who"] == "G" else 50});bye("#{id_} .in",{c["b"]});')
                y += int(rs * 1.34)
        placed = False
        if ob and ob in size_of:
            room = 1050 - y
            if room >= 190:
                w_, h_ = fit_obj(ob, WD * .72, min(room, 480))
                ox = X + WD - w_ - 20 - (i * 37 % 90) if c['who'] == 'H' else X + 10 + (i * 67 % 120)
                id_ = f'{pfx}{i}o'
                back.append(obj_tag(id_, ob, c['a'], c['b'], ox, y + (room - h_) * .5, h_, w_))
                js.append(f'popIn("#{id_} .in",{round(c["a"] + .18, 2)},{-5 if i % 2 else 5});popOut("#{id_} .in",{c["b"]});')
                placed = True
        return back, front, ''.join(js), placed

    def stage(id_, video, media_start, dur, shots, cards, pfx, pal, next_g, hook=False):
        ms = f' data-media-start="{media_start}"' if media_start is not None else ''
        o_ = next((z for z in chs if z.id == id_), None)
        back, front, extra, js = [], [], [], [pop.JS, pop.shots_js(shots, pfx, ghost=o_ is not None)]
        gh_html = ''
        if o_ is not None:
            gh_html, gh_js = pop.ghost(pfx, o_.title, dur, pal)
            js.append(gh_js)
        for i, c in enumerate(cards):
            sh = next((z for z in shots if z['t'] - .05 <= c['a'] < z['end']), shots[0])
            b1, f1, j1, _ = card(c, i, pfx, pal, hook and i == 0)
            back += b1; front += f1; js.append(j1)
            if c['kind'] == 'verdict':
                js.append(f'flood("#{pfx}fl",{max(0, round(c["a"] - .1, 2))},{c["b"]},{sh["focus"][0]},{sh["focus"][1]});')
        js.append(f'tl.to("#{pfx}cur",{{y:-1430,duration:.34,ease:"power3.in"}},{round(dur - .34, 3)});')
        body = f"""<div class="ground" style="background:{pal['g']}"></div>{gh_html}
    <div class="arch" id="{pfx}A"></div><div class="arch" id="{pfx}Ai"></div><div class="arch" id="{pfx}B"></div>
    <div class="flood" id="{pfx}fl" style="background:{pal['flood']}"></div>
    <div class="back">{"".join(back)}</div>
    <div class="cam" id="{pfx}c"><video id="{pfx}v" class="clip" src="assets/{video}" data-start="0" data-duration="{dur}"{ms} data-track-index="0" muted playsinline data-layout-allow-occlusion></video></div>
    {"".join(extra)}
    <div class="front">{"".join(front)}</div>
    <div class="cur" id="{pfx}cur" style="background:{next_g}"></div>"""
        scene(p, id_, pop.CSS, body, ''.join(js))

    def stage_shots(shots, to_src, frame_of, occ, pal):
        tight = 0
        for i, s in enumerate(shots):
            sa, sb = to_src(s['t']), to_src(s['end'])
            hf = face_at(pos_h, sa, sb)[:2]
            gf = face_at(pos_g, sa, sb)[:2]
            split, clean = pop.free_split(occ, frame_of(s['t']), frame_of(s['end'])) if s['kind'] != 'W' else (0, True)
            if not clean:
                if s.get('card'):
                    tight += 1
                else:
                    s['kind'] = 'W'
            s.update(pop.layout(s['kind'], s['who'], bool(s.get('card')), hf, gf, i, pal, split))
        return tight

    sequence = [pop.CYCLE[k % len(pop.CYCLE)] for k in range(len(chs))]
    TITLE_P, COLD_P, END_P = pop.MANGO_P, pop.MINT_P, pop.MINT_P
    tight = 0
    for k, o in enumerate(chs):
        o.pal = sequence[k]
        o.shots_b = plan_shots(o, pop_=True)
        tight += stage_shots(o.shots_b, lambda l, o=o: local2src(o, l), lambda l, o=o: round((o.bstart + l) * FPS), occ_b, o.pal)
    print(f'solo shots with no clean split: {tight}; shots {sum(len(o.shots_b) for o in chs)}, two-shots {sum(1 for o in chs for s in o.shots_b if s["kind"] == "W")}')
    for k, o in enumerate(chs):
        next_g = sequence[k + 1]['g'] if k + 1 < len(chs) else END_P['g']
        stage(o.id, 'cutout.webm', o.bstart, o.dur, o.shots_b, o.cards, o.id, o.pal, next_g)

    def rainbow(pfx, cx, sizes, colours, t0, y0=300):
        html_, js_ = [], []
        for j, (w_, col) in enumerate(zip(sizes, colours)):
            top_ = y0 + (sizes[0] - w_) // 2
            html_.append(f'<div id="{pfx}{j}" style="position:absolute;left:{cx - w_ // 2}px;top:{top_}px;width:{w_}px;height:{1200 - top_}px;border-radius:{w_ // 2}px {w_ // 2}px 0 0;background:{col};z-index:{1 + j}"></div>')
            js_.append(f'tl.fromTo("#{pfx}{j}",{{y:{1200 - top_}}},{{y:0,duration:.62,ease:"back.out(1.25)"}},{round(t0 + j * .07, 2)});')
        return ''.join(html_), js_

    for k, o in enumerate(chs):
        pal = o.pal
        size, lines = pop.fit(o.title, 950, 176, 84, 3)
        lh = int(size * 1.28)
        y0 = 540 - lh * len(lines) // 2 - 10
        arches, a_js = rainbow(f'{o.id}a', 1540, [900, 620, 340], [pal['a'], pal['b'], pal['g']], .03, 250)
        tt = ''.join(ty(f'{o.id}t{j}', 0, CH_D, ln, 110, y0 + j * lh, size, pal['ink'] if pal['name'] != 'tomato' else pal['hero']) for j, ln in enumerate(lines))
        js_ = pop.JS + ''.join(a_js) + ''.join(f'rise("#{o.id}t{j} .in",{round(.1 + j * .08, 2)});bye("#{o.id}t{j} .in",{CH_D});' for j in range(len(lines)))
        js_ += ''.join(f'tl.to("#{o.id}a{j}",{{y:1000,duration:.22,ease:"power3.in"}},{round(CH_D - .24, 2)});' for j in range(3))
        scene(p, f'{o.id}t', pop.CSS, f'<div class="ground" style="background:{pal["g"]}"></div>{arches}<div class="front">{tt}</div>', js_)
    # title
    tp = TITLE_P
    lines = paper.get('title_lines') or [paper['title']]
    size = min(pop.fit(ln, 1010, 200, 90, 1)[0] for ln in lines)
    arches, a_js = rainbow('ta', 1590, [860, 600], [tp['a'], tp['b']], .05, 150)
    els = ty('tb', .15, TITLE_D, MARK, 110, 130, 66, tp['ink'])
    js_ = pop.JS + ''.join(a_js) + 'wipe("#tb .in",.15);'
    y = 226
    for j, ln in enumerate(lines):
        els += ty(f'tm{j}', .28, TITLE_D, ln, 104, y, size, tp['ink'])
        js_ += f'rise("#tm{j} .in",{round(.28 + j * .1, 2)});'
        y += int(size * 1.24)
    els += ty('ts', .75, TITLE_D, paper['sub'], 110, y + 14, 76, tp['ink'], 600)
    js_ += 'wipe("#ts .in",.75);'
    objs = ''
    title_objs = [n for n in paper.get('title_objects', []) if n in size_of][:3]
    for j, (n, (x_, y_, h_, r_)) in enumerate(zip(title_objs, [(1370, 280, 640, -9), (1570, 470, 500, 8), (1210, 750, 300, -5)])):
        w_, h1 = fit_obj(n, 760, h_)
        objs += f'<div id="to{j}" class="ob" style="left:{x_}px;top:{y_}px;width:{w_}px;height:{h1}px;z-index:6"><span class="in"><img src="assets/obj/{n}.png" alt="" style="width:{w_}px;height:{h1}px" /></span></div>'
        js_ += f'popIn("#to{j} .in",{round(.5 + j * .14, 2)},{r_});'
    first_g = sequence[0]['g']
    js_ += f'tl.to("#tcur",{{y:-1430,duration:.34,ease:"power3.in"}},{round(TITLE_D - .34, 3)});'
    scene(p, 'title', pop.CSS, f'<div class="ground" style="background:{tp["g"]}"></div>{arches}{objs}<div class="front">{els}</div><div class="cur" id="tcur" style="background:{first_g}"></div>', js_)
    # end: left carries the summary, the right stays free for YouTube's end-screen elements
    ep = END_P
    rows = paper.get('end_rows', [])
    size, lines = pop.fit(paper['title'], 1140, 110, 72, 2)
    els, js_, y = '', pop.JS, 96
    for j, ln in enumerate(lines):
        els += ty(f'e0{j}', .1, END_D, ln, 100, y, size, ep['ink'])
        js_ += f'rise("#e0{j} .in",{round(.1 + j * .08, 2)});'
        y += int(size * 1.28)
    y += 26
    for i, r in enumerate(rows):
        rs, _ = pop.fit(r, 1090, 70, 40, 1, wt=600)
        t_ = round(.5 + i * .3, 2)
        els += ty(f'e{i + 1}', t_, END_D, r, 100, y, rs, ep['ink'], 600).replace('<span class="in" style="">', f'<span class="in" style=""><i class="dot" style="background:{ep["a"]}"></i>')
        js_ += f'slide("#e{i + 1} .in",{t_},-50);'
        y += 112
    els += ty('e9', 1.5, END_D, MARK_SUB, 100, 880, 52, ep['ink'])
    js_ += 'wipe("#e9 .in",1.5);'
    arches, a_js = rainbow('ea', 1620, [860, 560], [ep['a'], ep['b']], .05, 340)
    scene(p, 'end', pop.CSS, f'<div class="ground" style="background:{ep["g"]}"></div>{arches}<div class="front">{els}</div>', js_ + ''.join(a_js))
    # cold open
    cuts, acc = [], 0.0
    for q_, r_ in edl['cold']:
        cuts.append((round(acc, 3), round(acc + r_ - q_, 3), q_, r_))
        acc += r_ - q_
    texts = COLD_CARDS
    cc = [dict(a=a_, b=round(b_ - .02, 2), kind=kd, title=tx, rows=[], who=wh, opts={}) for (a_, b_, _, _), (tx, kd, wh) in zip(cuts, texts)]
    shots = [dict(t=a_, end=b_, kind=('W' if kd == 'q' else wh), who=wh, card=True, sa=q_, sb=r_) for (a_, b_, q_, r_), (_, kd, wh) in zip(cuts, texts)]
    for i, s in enumerate(shots):
        hf, gf = face_at(pos_h, s['sa'], s['sb'])[:2], face_at(pos_g, s['sa'], s['sb'])[:2]
        split, _ = pop.free_split(occ_c, round(s['t'] * FPS), round(s['end'] * FPS)) if s['kind'] != 'W' else (0, True)
        s.update(pop.layout(s['kind'], s['who'], True, hf, gf, i, COLD_P, split))
    if not CLIP:
        stage('cold', 'cutout_cold.webm', None, COLD, shots, cc, 'cc', COLD_P, TITLE_P['g'], hook=True)
    write_index(p, 'pop-studio-full')
    cues = [('whoosh_1', COLD - .3, .28)]
    for k, o in enumerate(chs):
        cues.append(('whoosh_2' if k % 2 else 'whoosh_1', o.card_at - .3, .24))
        cues.append(('pop', o.card_at + .16, .16))
        for c in o.cards:
            if c['kind'] in ('stat', 'verdict'):
                cues.append(('boop', o.at + c['a'] + .04, .26))
            elif c['opts'].get('obj') or c['opts'].get('still'):
                cues.append(('pop', o.at + c['a'] + .22, .2))
    for t_ in (.5, .64, .78)[:0 if CLIP else len(title_objs)]:
        cues.append(('pop', COLD + t_, .2))
    cues.append(('whoosh_1', END_AT - .3, .24))
    mix(p, music_bed('b'), cues, .46)
    print('OK: variant_b')


# ------------------------------------------------------------------ B at 9:16
def build_v():
    """Pop Studio recomposed for 9:16: same cut, same mix, same cards. Words take the band above the head; a desk across the bottom carries the chapter's name.
    Subtitles stay in the .srt, as in 16:9, because machine-made subtitles can't be corrected once burned in."""
    global W, H
    import pop
    pop.apply_show(SHOW)
    _need(ROOT / 'variant_b/assets', 'Build b first: 9:16 reuses its assets.')
    p = ROOT / 'variant_b_9x16'
    if not (p / 'hyperframes.json').exists():
        subprocess.run(['npx', 'hyperframes', 'init', str(p), '--skip-skills'], capture_output=True, check=True)
    clean_project(p)
    a = p / 'assets'
    shutil.rmtree(a, ignore_errors=True)
    shutil.copytree(ROOT / 'variant_b/assets', a, copy_function=os.link)
    W, H = 1080, 1920
    size_of = {f.stem: Image.open(f).size for f in (a / 'obj').glob('*.png')}
    ALIAS = paper.get('aliases', {})
    occ_b = np.load(B_ / 'cutout.occ.npy')
    occ_c = np.load(B_ / 'cutout_cold.occ.npy') if edl['cold'] else None
    DESK = {'mint': pop.INK_G, 'tomato': pop.INK_T, 'sky': '#0B2A66', 'mango': pop.INK_M, 'pink': pop.INK_P}
    DESK_DOWN = 280
    css = pop.CSS + f"""
    .cur {{ left: -760px; top: 1930px; width: 2600px; height: 3000px; border-radius: 1300px 1300px 0 0; }}
    .desk {{ position: absolute; left: -30px; right: -30px; top: 1420px; height: 900px; border-radius: 44px 44px 0 0; z-index: 7; font-family: "Mitr", sans-serif; font-weight: 700; color: {pop.MANGO}; text-align: center; padding-top: 44px; line-height: 1.3; white-space: nowrap; }}"""
    X, WD = 60, 960

    def ty(id_, a_, b_, txt, x, y, size, ink, wt=700, cls_='', inner=''):
        return (f'<div id="{id_}" class="clip ty {cls_}" data-start="{a_}" data-duration="{round(b_ - a_, 3)}" data-track-index="2" style="left:{round(x)}px;top:{round(y)}px;font-size:{size}px;font-weight:{wt};color:{ink}"><span class="in" style="{inner}">{pop.e(txt)}</span></div>')

    def obj_tag(id_, name, a_, b_, x, y, h_, w_):
        return f'<div id="{id_}" class="clip ob" data-start="{a_}" data-duration="{round(b_ - a_, 3)}" data-track-index="3" style="left:{round(x)}px;top:{round(y)}px;width:{w_}px;height:{h_}px"><span class="in"><img src="assets/obj/{name}.png" alt="" style="width:{w_}px;height:{h_}px" /></span></div>'

    def fit_obj(name, max_w, max_h):
        ow, oh = size_of[name]
        k = min(max_w / ow, max_h / oh)
        return int(ow * k), int(oh * k)

    def obj_of(c):
        ob = c['opts'].get('still') or c['opts'].get('obj')
        return ALIAS.get(ob, ob) if ob else None

    def block(c):
        """The largest type at which heading and rows fit above the head."""
        base = {'verdict': 170, 'stat': 140, 'term': 124, 'take': 108, 'rows': 104}.get(c['kind'], 108)
        for k in (1, .92, .84, .76, .68, .6):
            size, lines = pop.fit(c['title'], WD - (70 if c['kind'] == 'term' else 0), int(base * k), 52, 3)
            lh = int(size * 1.48) if c['kind'] == 'term' else int(size * 1.28)
            rows = [pop.fit(r, WD - 44, max(44, int(62 * k)), 36, 2, wt=600) for r in c['rows']]
            h_ = lh * len(lines) + 14 + sum(int(rs * 1.34) * len(rl) for rs, rl in rows)
            if h_ <= 450:
                break
        return size, lines, lh, rows, h_

    def card(c, i, pfx, pal, hook=False):
        back, front, js = [], [], []
        k = c['kind']
        ob = obj_of(c)
        if k == 'q':
            size, lines = pop.fit(c['title'], WD, 118, 64, 3)
            y = 186
            for j, ln in enumerate(lines):
                id_ = f'{pfx}{i}t{j}'
                back.append(ty(id_, c['a'], c['b'], ln, X, y, size, pal['ink']))
                if not hook:
                    js.append(f'rise("#{id_} .in",{round(c["a"] + j * .08, 2)});')
                js.append(f'bye("#{id_} .in",{c["b"]});')
                y += int(size * 1.26)
            room = 720 - y
            if ob and ob in size_of and room >= 190:
                w_, h_ = fit_obj(ob, 400, min(room, 340))
                id_ = f'{pfx}{i}o'
                back.append(obj_tag(id_, ob, c['a'], c['b'], 1040 - w_, y + (room - h_) * .4, h_, w_))
                js.append(f'popIn("#{id_} .in",{round(c["a"] + .15, 2)},{-6 if i % 2 else 6});popOut("#{id_} .in",{c["b"]});')
            return back, front, ''.join(js)
        size, lines, lh, rows, h_ = block(c)
        ink = {'verdict': pal['fink'], 'stat': pal['hero']}.get(k, pal['ink'])
        y = 176 + int((450 - h_) * .4)
        for j, ln in enumerate(lines):
            id_ = f'{pfx}{i}t{j}'
            if k == 'term':
                back.append(ty(id_, c['a'], c['b'], ln, X, y, size, pal['mink'], cls_='block', inner=f'background:{pal["mark"]}'))
                if not hook:
                    js.append(f'wipe("#{id_} .in",{round(c["a"] + j * .1, 2)});')
            else:
                back.append(ty(id_, c['a'], c['b'], ln, X, y, size, ink))
                if not hook:
                    js.append(f'rise("#{id_} .in",{round(c["a"] + j * .1, 2)});')
            y += lh
            js.append(f'bye("#{id_} .in",{c["b"]});')
        y += 14
        gap = (c['b'] - c['a'] - 1.6) / max(len(rows), 1)
        row_ink = pal['fink'] if k == 'verdict' else pal['ink']
        dot = pal['fink'] if k == 'verdict' else pal['a']
        for r_i, (rs, rl) in enumerate(rows):
            t_ = round(c['a'] + .35 + min(gap, 2.6) * r_i, 2)
            for j, ln in enumerate(rl):
                id_ = f'{pfx}{i}r{r_i}{j}'
                mark = f'<i class="dot" style="background:{dot}"></i>' if j == 0 else ''
                pad = 0 if j == 0 else int(rs * .78)
                front.append(ty(id_, t_, c['b'], ln, X + pad, y, rs, row_ink, 600).replace('<span class="in" style="">', f'<span class="in" style="">{mark}'))
                js.append(f'slide("#{id_} .in",{t_},-50);bye("#{id_} .in",{c["b"]});')
                y += int(rs * 1.34)
        if ob and ob in size_of:
            w_, h_ = fit_obj(ob, 430, 420)
            ox = 1050 - w_ if c['who'] == 'H' else 20
            id_ = f'{pfx}{i}o'
            back.append(obj_tag(id_, ob, c['a'], c['b'], ox, 700 + (420 - h_) * .5, h_, w_))
            js.append(f'popIn("#{id_} .in",{round(c["a"] + .18, 2)},{-5 if i % 2 else 5});popOut("#{id_} .in",{c["b"]});')
        return back, front, ''.join(js)

    def stage(id_, video, media_start, dur, shots, cards, pfx, pal, next_g, label, hook=False):
        ms = f' data-media-start="{media_start}"' if media_start is not None else ''
        o_ = next((z for z in chs if z.id == id_), None)
        back, front, extra, js = [], [], [], [pop.JS, pop.shots_js(shots, pfx, ghost=o_ is not None)]
        gh_html = ''
        if o_ is not None:
            gh_html, gh_js = pop.ghost(pfx, o_.title, dur, pal)
            js.append(gh_js)
        for i, c in enumerate(cards):
            sh = next((z for z in shots if z['t'] - .05 <= c['a'] < z['end']), shots[0])
            b1, f1, j1 = card(c, i, pfx, pal, hook and i == 0)
            back += b1; front += f1; js.append(j1)
            if c['kind'] == 'verdict':
                js.append(f'flood("#{pfx}fl",{max(0, round(c["a"] - .1, 2))},{c["b"]},{sh["focus"][0]},{sh["focus"][1]});')
        # two-shots: one camera for each person, so they stand closer than they sat
        two = []
        js.append(f'tl.set("#{pfx}dk",{{y:{DESK_DOWN}}},0);')
        for n, s in enumerate(shots):
            if s['kind'] != 'W':
                continue
            prev_w = n > 0 and shots[n - 1]['kind'] == 'W'
            next_w = n + 1 < len(shots) and shots[n + 1]['kind'] == 'W'
            if not prev_w:
                js.append(f'tl.fromTo("#{pfx}dk",{{y:{DESK_DOWN}}},{{y:0,duration:.42,ease:"back.out(1.3)",immediateRender:false}},{s["t"]});')
            if not next_w:
                js.append(f'tl.set("#{pfx}dk",{{y:{DESK_DOWN}}},{s["end"]});')
            for who_, (fx_, fy_), (tx, ty_), clip in (('h', s['hf'], (290, 880), f'inset(-200px {round(1920 - s["split"])}px -200px -200px)'), ('g', s['gf'], (790, 1000), f'inset(-200px -200px -200px {round(s["split"])}px)')):
                vid = f'{pfx}w{n}{who_}'
                two.append(f'<div class="cam" id="{vid}" style="clip-path:{clip};transform:translate({round(tx - .96 * fx_)}px,{round(ty_ - .96 * fy_)}px) scale(.96)"><video id="{vid}v" class="clip" src="assets/{video}" data-start="{s["t"]}" data-duration="{round(s["end"] - s["t"], 3)}" data-media-start="{round((media_start or 0) + s["t"], 3)}" data-track-index="5" muted playsinline data-layout-allow-occlusion></video></div>')
        js.append(f'tl.to("#{pfx}cur",{{y:-2060,duration:.34,ease:"power3.in"}},{round(dur - .34, 3)});')
        dsize = pop.fit(label, 980, 62, 34, 1)[0]
        body = f"""<div class="ground" style="background:{pal['g']}"></div>{gh_html}
    <div class="arch" id="{pfx}A"></div><div class="arch" id="{pfx}Ai"></div><div class="arch" id="{pfx}B"></div>
    <div class="flood" id="{pfx}fl" style="background:{pal['flood']}"></div>
    <div class="back">{"".join(back)}</div>
    <div class="cam" id="{pfx}c"><video id="{pfx}v" class="clip" src="assets/{video}" data-start="0" data-duration="{dur}"{ms} data-track-index="0" muted playsinline data-layout-allow-occlusion></video></div>
    {"".join(two)}
    <div class="desk" id="{pfx}dk" style="background:{DESK[pal['name']]};font-size:{dsize}px">{pop.e(label)}</div>
    {"".join(extra)}
    <div class="front">{"".join(front)}</div>
    <div class="cur" id="{pfx}cur" style="background:{next_g}"></div>"""
        scene(p, id_, css, body, ''.join(js))

    def dress(s, i, sa, sb, f0, f1, occ, c, pal):
        hf, gf = face_at(pos_h, sa, sb)[:2], face_at(pos_g, sa, sb)[:2]
        k = s['kind']
        split, clean = pop.free_split(occ, f0, f1, hug=None if k == 'W' else k[0])
        if not clean and not c and k != 'W':
            k = 'W'
            split, clean = pop.free_split(occ, f0, f1)
        s['kind'] = k
        s.update(split=split, hf=hf, gf=gf)
        carded = bool(c)
        has_obj = bool(c and obj_of(c) and c['kind'] != 'q')
        tx = {('H', True, True): 360, ('H', True, False): 470, ('H', False, False): 520, ('G', True, True): 700, ('G', True, False): 640, ('G', False, False): 620}.get((k[0], carded, has_obj))
        s.update(pop.layout_v(k, i, pal, split, hf, gf, tx_=tx, ty_=960 if carded else 930, top=300))
        if k == 'W':    # the left speaker stands lower here, so the desk hides the lap and what the matte leaves around it
            s['shapes']['A'].update(top=610, height=1450)
        return not clean

    sequence = [pop.CYCLE[k % len(pop.CYCLE)] for k in range(len(chs))]
    TITLE_P, COLD_P, END_P = pop.MANGO_P, pop.MINT_P, pop.MINT_P
    tight = total = two_n = 0
    for k, o in enumerate(chs):
        shots = plan_shots(o, pop_=True)
        for i, s in enumerate(shots):
            c = next((c for c in o.cards if c['a'] - .05 <= s['t'] < c['b']), None)
            tight += dress(s, i, local2src(o, s['t']), local2src(o, s['end']), round((o.bstart + s['t']) * FPS), round((o.bstart + s['end']) * FPS), occ_b, c, sequence[k])
        total += len(shots); two_n += sum(1 for s in shots if s['kind'] == 'W')
        next_g = sequence[k + 1]['g'] if k + 1 < len(chs) else END_P['g']
        stage(o.id, 'cutout.webm', o.bstart, o.dur, shots, o.cards, o.id, sequence[k], next_g, o.title)
    print(f'9:16 shots {total}, two-shots {two_n}, no clean split {tight}')

    def rainbow(pfx, cx, sizes, colours, t0, y0):
        html_, js_ = [], []
        for j, (w_, col) in enumerate(zip(sizes, colours)):
            top_ = y0 + (sizes[0] - w_) // 2
            h_ = H + 220 - top_
            html_.append(f'<div id="{pfx}{j}" style="position:absolute;left:{cx - w_ // 2}px;top:{top_}px;width:{w_}px;height:{h_}px;border-radius:{w_ // 2}px {w_ // 2}px 0 0;background:{col};z-index:{1 + j}"></div>')
            js_.append(f'tl.fromTo("#{pfx}{j}",{{y:{h_}}},{{y:0,duration:.62,ease:"back.out(1.25)"}},{round(t0 + j * .07, 2)});')
        return ''.join(html_), js_

    for k, o in enumerate(chs):
        pal = sequence[k]
        size, lines = pop.fit(o.title, WD, 150, 76, 3)
        lh = int(size * 1.28)
        y0 = 270
        arches, a_js = rainbow(f'{o.id}a', 540, [1000, 700, 400], [pal['a'], pal['b'], pal['g']], .03, 880)
        tt = ''.join(ty(f'{o.id}t{j}', 0, CH_D, ln, X, y0 + j * lh, size, pal['ink'] if pal['name'] != 'tomato' else pal['hero']) for j, ln in enumerate(lines))
        js_ = pop.JS + ''.join(a_js) + ''.join(f'rise("#{o.id}t{j} .in",{round(.1 + j * .08, 2)});bye("#{o.id}t{j} .in",{CH_D});' for j in range(len(lines)))
        js_ += ''.join(f'tl.to("#{o.id}a{j}",{{y:1100,duration:.22,ease:"power3.in"}},{round(CH_D - .24, 2)});' for j in range(3))
        scene(p, f'{o.id}t', css, f'<div class="ground" style="background:{pal["g"]}"></div>{arches}<div class="front">{tt}</div>', js_)
    # title
    tp = TITLE_P
    lines = paper.get('title_lines') or [paper['title']]
    size = min(pop.fit(ln, WD, 170, 80, 1)[0] for ln in lines)
    arches, a_js = rainbow('ta', 540, [1040, 720], [tp['a'], tp['b']], .05, 860)
    els = ty('tb', .15, TITLE_D, MARK, X, 180, 66, tp['ink'])
    js_ = pop.JS + ''.join(a_js) + 'wipe("#tb .in",.15);'
    y = 276
    for j, ln in enumerate(lines):
        els += ty(f'tm{j}', .28, TITLE_D, ln, X - 4, y, size, tp['ink'])
        js_ += f'rise("#tm{j} .in",{round(.28 + j * .1, 2)});'
        y += int(size * 1.24)
    els += ty('ts', .75, TITLE_D, paper['sub'], X, y + 14, 76, tp['ink'], 600)
    js_ += 'wipe("#ts .in",.75);'
    objs = ''
    title_objs = [n for n in paper.get('title_objects', []) if n in size_of][:3]
    for j, (n, (x_, y_, h_, r_)) in enumerate(zip(title_objs, [(280, 930, 640, -9), (560, 1040, 520, 8), (140, 1320, 300, -5)])):
        w_, h1 = fit_obj(n, 760, h_)
        objs += f'<div id="to{j}" class="ob" style="left:{x_}px;top:{y_}px;width:{w_}px;height:{h1}px;z-index:6"><span class="in"><img src="assets/obj/{n}.png" alt="" style="width:{w_}px;height:{h1}px" /></span></div>'
        js_ += f'popIn("#to{j} .in",{round(.5 + j * .14, 2)},{r_});'
    js_ += f'tl.to("#tcur",{{y:-2060,duration:.34,ease:"power3.in"}},{round(TITLE_D - .34, 3)});'
    scene(p, 'title', css, f'<div class="ground" style="background:{tp["g"]}"></div>{arches}{objs}<div class="front">{els}</div><div class="cur" id="tcur" style="background:{sequence[0]["g"]}"></div>', js_)
    # end
    ep = END_P
    rows = paper.get('end_rows', [])
    size, lines = pop.fit(paper['title'], WD, 116, 72, 2)
    els, js_, y = '', pop.JS, 190
    for j, ln in enumerate(lines):
        els += ty(f'e0{j}', .1, END_D, ln, X, y, size, ep['ink'])
        js_ += f'rise("#e0{j} .in",{round(.1 + j * .08, 2)});'
        y += int(size * 1.28)
    y += 26
    for i, r in enumerate(rows):
        rs, _ = pop.fit(r, WD - 44, 66, 40, 1, wt=600)
        t_ = round(.5 + i * .3, 2)
        els += ty(f'e{i + 1}', t_, END_D, r, X, y, rs, ep['ink'], 600).replace('<span class="in" style="">', f'<span class="in" style=""><i class="dot" style="background:{ep["a"]}"></i>')
        js_ += f'slide("#e{i + 1} .in",{t_},-50);'
        y += 104
    els += ty('e9', 1.5, END_D, MARK_SUB, X, y + 40, pop.fit(MARK_SUB, WD, 54, 36, 1)[0], ep['ink'])
    js_ += 'wipe("#e9 .in",1.5);'
    arches, a_js = rainbow('ea', 540, [1000, 680], [ep['a'], ep['b']], .05, 1120)
    scene(p, 'end', css, f'<div class="ground" style="background:{ep["g"]}"></div>{arches}<div class="front">{els}</div>', js_ + ''.join(a_js))
    # cold open
    cuts, acc = [], 0.0
    for q_, r_ in edl['cold']:
        cuts.append((round(acc, 3), round(acc + r_ - q_, 3), q_, r_))
        acc += r_ - q_
    texts = COLD_CARDS
    cc = [dict(a=a_, b=round(b_ - .02, 2), kind=kd, title=tx, rows=[], who=wh, opts={}) for (a_, b_, _, _), (tx, kd, wh) in zip(cuts, texts)]
    shots = [dict(t=a_, end=b_, kind=('W' if kd == 'q' else wh), who=wh, card=True) for (a_, b_, _, _), (_, kd, wh) in zip(cuts, texts)]
    for i, (s, (_, _, q_, r_), c) in enumerate(zip(shots, cuts, cc)):
        dress(s, i, q_, r_, round(s['t'] * FPS), round(s['end'] * FPS), occ_c, c, COLD_P)
    if not CLIP:
        stage('cold', 'cutout_cold.webm', None, COLD, shots, cc, 'cc', COLD_P, TITLE_P['g'], MARK, hook=True)
    write_index(p, 'pop-studio-full-9x16')
    W, H = 1920, 1080
    print('OK: variant_b_9x16')


for v in sys.argv[2:]:
    if v == 'a':
        build_a()
    elif v == 'b':
        build_b()
    elif v == 'v':
        build_v()
print(json.dumps({'total': TOTAL, 'chapters': [{'title': o.title, 'at': o.card_at} for o in chs]}, ensure_ascii=False)[:120])
write_chapters()
if '--frames' in sys.argv:
    import look_kit
    for v in sys.argv[2:]:
        if v in ('a', 'b', 'v'):
            look_kit.contact_sheet(sys.modules[__name__], ROOT / {'a': 'variant_a', 'b': 'variant_b', 'v': 'variant_b_9x16'}[v], v == 'v')

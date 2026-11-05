#!/usr/bin/env python3
"""A subtitle file and YouTube chapters for the full episode, on its final clock. Free.

    python3 $S/make_srt.py episodes/EPxx/full outputs/EPxx_full

Writes  <prefix>.<lang>.srt      subtitles, DRAFT until a speaker of the language has read them while listening
        <prefix>_chapters.txt   chapter list for the YouTube description

Text comes from the first transcript, which reads better; timing comes from aligning it to the second, which has a time for every character.
Fillers are removed. srt_fixes.json beside paper.json holds mishearings found by reading the transcript in context, as [wrong, right, from second, to second];
each is a judgement, not a fact: proof them. Thai is what this has been run on; other languages take their filler lists from show.json.
"""
import difflib, json, re, subprocess, sys, tempfile, unicodedata
from pathlib import Path
import studio

ROOT = Path(sys.argv[1]).resolve()
PREFIX = Path(sys.argv[2])
B_ = ROOT / 'build'
SHOW = studio.load_show(ROOT)
WORDS = studio.words(SHOW)
PAPER = json.loads((ROOT / 'paper.json').read_text(encoding='utf-8'))
SHARED = (ROOT / PAPER.get('from', '.')).resolve()
if not (B_ / 'chapters.json').exists():
    sys.exit(f'FAIL: no {B_}/chapters.json. Run build_full.py {ROOT} --plan first: it works out the film\'s clock and builds nothing.')
chap = json.loads((B_ / 'chapters.json').read_text(encoding='utf-8'))
edl = json.loads((B_ / 'edl.json').read_text(encoding='utf-8'))
pass1 = json.loads((SHARED / 'build' / 'pass1.json').read_text(encoding='utf-8'))
sc = [c for c in json.loads((SHARED / 'audio' / 'scribe.json').read_text(encoding='utf-8'))['words'] if c['type'] == 'word']
text2, t2 = [], []
for c in sc:
    for ch in c['text']:
        text2.append(ch); t2.append(c['start'])

# (source start, source end, final start) for everything kept
spans, acc = [], 0.0
for p, q in edl['cold']:
    spans.append((p, q, acc)); acc += q - p
for c in chap['chapters']:
    l = 0.0
    for p, q in c['slices']:
        spans.append((p, q, c['at'] + l)); l += q - p


def final_times(s):
    return [f + s - p for p, q, f in spans if p <= s < q]


FIXES = json.loads((ROOT / 'srt_fixes.json').read_text(encoding='utf-8')) if (ROOT / 'srt_fixes.json').exists() else []
BACK = set(WORDS['srt_back'])
TAIL = re.compile(WORDS['srt_tail']) if WORDS.get('srt_tail') else None


def char_times(r):
    """A time for every character of a first-pass row, by matching it to the second pass around that moment."""
    txt = r['t']
    i0 = next((i for i, t in enumerate(t2) if t >= r['a'] - 1.5), len(t2))
    i1 = next((i for i, t in enumerate(t2) if t > r['b'] + 1.5), len(t2))
    other = ''.join(text2[i0:i1])
    known = {}
    for a, b, n in difflib.SequenceMatcher(None, txt, other, autojunk=False).get_matching_blocks():
        if n >= 2:
            for k in range(n):
                known[a + k] = t2[i0 + b + k]
    pts = sorted(known.items())
    if not pts:
        return [r['a'] + (r['b'] - r['a']) * k / max(len(txt), 1) for k in range(len(txt))]
    out, j = [], 0
    for k in range(len(txt)):
        while j + 1 < len(pts) and pts[j + 1][0] <= k:
            j += 1
        (x0, y0) = pts[j]
        (x1, y1) = pts[j + 1] if j + 1 < len(pts) else (len(txt), r['b'])
        if k < x0:
            out.append(max(r['a'], y0 - (x0 - k) * .08))
        else:
            out.append(y0 + (y1 - y0) * (k - x0) / max(x1 - x0, 1))
    return out


rows = []
for r in pass1:
    if not r['t'] or r['t'] in BACK:
        continue
    txt = r['t']
    for bad, good, a, b in FIXES:
        if a <= r['a'] <= b:
            txt = txt.replace(bad, good)
    rows.append(dict(r, t=txt))

# Thai word boundaries, so a cut point can never split a word
exe = tempfile.mktemp()
subprocess.run(['swiftc', '-O', str(Path(__file__).parent / 'thai_words.swift'), '-o', exe], check=True, capture_output=True)
all_words = json.loads(subprocess.run([exe], input=json.dumps([r['t'] for r in rows], ensure_ascii=False).encode(), capture_output=True).stdout)
DROP = set(WORDS['srt_drop'])


def units(s):
    return sum(0 if unicodedata.category(ch) == 'Mn' or ch == 'ำ' else 1 for ch in s)


runs = []
for r, ws in zip(rows, all_words):
    times = char_times(r)
    # where each word sits in time
    pos, spots = 0, []
    for w in ws:
        k = r['t'].find(w, pos)
        if k < 0:
            continue
        pos = k + len(w)
        spots.append((w, times[k], times[min(pos - 1, len(times) - 1)]))
    # a word is kept if its middle falls inside a kept span; one run per place it lands (the cold open repeats some of it)
    for sp in spans:
        kept = [(w, a, b) for w, a, b in spots if sp[0] <= (a + b) / 2 < sp[1]]
        if kept:
            runs.append(dict(words=kept, off=sp[2] - sp[0], lo=sp[0], hi=sp[1]))
runs.sort(key=lambda x: x['words'][0][1] + x['off'])

MAXU = 42
cues = []
LEADW = set(WORDS['srt_lead'])
for r in runs:
    cur, cs, ce = [], None, None
    while len(r['words']) > 1 and r['words'][0][0] in LEADW:     # only at the start of a spoken line
        r['words'] = r['words'][1:]
    for w, a, b in r['words']:
        if w in DROP:
            continue
        t0, t1 = max(a, r['lo']) + r['off'], min(b + .1, r['hi']) + r['off']
        if cur and units(''.join(cur) + w) > MAXU:
            cues.append([cs, ce, cur]); cur, cs = [], None
        cs = t0 if cs is None else cs
        cur.append(w); ce = t1
    if cur:
        cues.append([cs, ce, cur])


def tidy(ws):
    x = ''
    for w in ws:
        # a space around Latin words reads better than running them into Thai
        if x and (re.match(r'[A-Za-z0-9]', w) or re.match(r'[A-Za-z0-9]', x[-1])):
            x += ' '
        x += w
    x = (TAIL.sub('', x) if TAIL else x).strip()
    return x


clean = [[a, b, tidy(ws)] for a, b, ws in cues]
clean = [c for c in clean if c[2] and c[2] not in BACK and units(c[2]) >= 2]
clean.sort(key=lambda c: c[0])
# fold fragments into a neighbour so nothing flashes by
merged = []
for c in clean:
    if merged and c[0] - merged[-1][1] < .5 and (units(c[2]) < 10 or units(merged[-1][2]) < 10) and units(merged[-1][2] + c[2]) <= MAXU + 6:
        merged[-1][1] = c[1]; merged[-1][2] += c[2]
    else:
        merged.append(c)
clean = merged
for u, v in zip(clean, clean[1:]):
    u[1] = min(max(u[1], u[0] + .9), v[0] - .02)
clean = [c for c in clean if c[1] - c[0] > .3]


def stamp(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')


PREFIX.parent.mkdir(parents=True, exist_ok=True)
Path(f"{PREFIX}.{WORDS['html']}.srt").write_text(''.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{x}\n\n' for i, (a, b, x) in enumerate(clean, 1)), encoding='utf-8')


def clock(t):
    t = int(t)
    return f'{t // 60:02d}:{t % 60:02d}'


lines = ([f"00:00 {WORDS['cold_label']}"] if edl['cold'] else []) + [f"{clock(c['card'])} {c['title']}" for c in chap['chapters']]
Path(str(PREFIX) + '_chapters.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'OK: {len(clean)} subtitles · {len(lines)} chapters · film {clock(chap["total"])}')

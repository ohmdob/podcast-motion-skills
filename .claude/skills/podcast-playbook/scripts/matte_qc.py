#!/usr/bin/env python3
"""Find see-through people without watching the film. Free and local.

    python3 $S/matte_qc.py episodes/EPxx/matte episodes/EPxx/full    # the matte, through the edit
    python3 $S/matte_qc.py --alpha build/cutout_cold.webm [start_s]               # any finished cutout

A person on a sofa holds still, so what was solid a second ago should be solid now. For every frame this compares each speaker's alpha with
the median of the 4 seconds around it: `gone` is the share of that speaker's solid body now below half opacity, `thin` below 86%. A moving arm
scores a little and a torso dropping out scores a lot. It reports runs of frames over the limit, and FAIL if there are any.
Delivery QC measures picture size and sound; it cannot see this. Read frames too: this finds dropouts, it does not judge hair edges.
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
import studio

_show = studio.load_show(sys.argv[2] if sys.argv[1] != '--alpha' else None, required=False)
W, H, FPS, SPLIT = 240, 135, _show['fps'], round(_show['body_split_x'] * 240 / 1920)    # analysis size; where the speakers divide, scaled from 1920
GONE, THIN, MIN_RUN = .06, .12, 3


def small(cmd):
    raw = subprocess.run(cmd + ['-vf', f'{sys.modules[__name__].PRE}scale={W}:{H}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W)


def erode(m, r=2):
    o = m.copy()
    for k in range(1, r + 1):
        o[k:] &= m[:-k]; o[:-k] &= m[k:]; o[:, k:] &= m[:, :-k]; o[:, :-k] &= m[:, k:]
    return o


def score(a):
    """Per frame and per speaker: (gone, thin)."""
    n, out, ref = len(a), np.zeros((len(a), 2, 2), np.float32), None
    for i in range(n):
        if i % 5 == 0:
            idx = [min(n - 1, max(0, i + d)) for d in range(-50, 51, 10)]
            ref = erode(np.median(a[idx], axis=0) > 200)
        f = a[i]
        for s, (x0, x1) in enumerate(((0, SPLIT), (SPLIT, W))):
            r, g = ref[:, x0:x1], f[:, x0:x1]
            t = r.sum()
            if t >= 150:
                out[i, s] = ((r & (g < 128)).sum() / t, (r & (g < 220)).sum() / t)
    return out


def runs(sc, used=None):
    bad = (sc[:, :, 0] > GONE) | (sc[:, :, 1] > THIN)
    res = []
    for s in (0, 1):
        i = 0
        while i < len(bad):
            if bad[i, s]:
                j = i
                while j + 1 < len(bad) and bad[j + 1, s]:
                    j += 1
                if j - i + 1 >= MIN_RUN:
                    w = i + int(np.argmax(sc[i:j + 1, s, 0]))
                    res.append(dict(speaker='LR'[s], frame=i, frames=j - i + 1, worst=w, gone=round(float(sc[w, s, 0]), 3), thin=round(float(sc[w, s, 1]), 3)))
                i = j + 1
            else:
                i += 1
    return sorted(res, key=lambda r: -r['gone'])


if sys.argv[1] == '--alpha':
    PRE = 'alphaextract,'
    a = small(['ffmpeg', '-v', 'error', '-c:v', 'libvpx-vp9', '-i', sys.argv[2]])
    start = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    r = runs(score(a))
    print(f'{len(a)} frames · {len(r)} runs over the limit')
    for x in r[:14]:
        print(f"  {x['speaker']} at {start + x['frame'] / FPS:7.2f} s · {x['frames'] / FPS:.2f} s long · worst {start + x['worst'] / FPS:.2f} s · gone {x['gone']:.0%} thin {x['thin']:.0%}")
    sys.exit(1 if r else 0)

MATTE, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
PRE = ''
edges = [int(x) for x in (MATTE / 'parts.txt').read_text().split()]
a = np.concatenate([small(['ffmpeg', '-v', 'error', '-i', str(MATTE / f'p{i}.mkv')]) for i in range(len(edges) - 1)])
print(f'matte {len(a)} frames, recording {edges[-1]}', flush=True)
if len(a) != edges[-1]:
    sys.exit('FAIL: the matte parts do not add up to the recording')
sc = score(a)
e = json.loads((ROOT / 'build/edl.json').read_text(encoding='utf-8'))
# build_full.py writes chapters.json, and with no build yet the times below are simply on the edit's own clock.
_chap = ROOT / 'build/chapters.json'
if _chap.exists():
    ch = json.loads(_chap.read_text(encoding='utf-8'))['chapters']
else:
    _b, ch = 0.0, []
    for c in e['chapters']:
        ch.append({'at': _b, 'bstart': _b})
        _b += sum(q - p for p, q in c['slices'])
    print('no build yet: times are on the edit clock, not the film clock', flush=True)
film = {}                                                 # recording frame → film time, for the frames the edit actually uses
t = 0
for p, q in e['cold']:
    for f in range(round(p * FPS), round(q * FPS)):
        film[f] = t / FPS; t += 1
b = 0
for c, cc in zip(e['chapters'], ch):
    for p, q in c['slices']:
        for f in range(round(p * FPS), round(q * FPS)):
            film[f] = cc['at'] + (b / FPS - cc['bstart']); b += 1
use = np.array(sorted(film))
r = runs(sc[use])
for x in r:
    x['film'] = round(film[int(use[x['worst']])], 2); x['src'] = int(use[x['worst']])
print(f'{len(use)} frames in the edit · {len(r)} runs over the limit')
for x in r[:20]:
    print(f"  {x['speaker']} film {int(x['film'] // 60):02d}:{x['film'] % 60:05.2f} · {x['frames'] / FPS:.2f} s long · gone {x['gone']:.0%} thin {x['thin']:.0%}")
(ROOT / 'build/matte_qc.json').write_text(json.dumps(r))
print('worst across the edit: gone %.1f%%, thin %.1f%%' % (sc[use][:, :, 0].max() * 100, sc[use][:, :, 1].max() * 100))
print('OK: no see-through runs' if not r else f'FAIL: {len(r)} runs to look at')
sys.exit(1 if r else 0)

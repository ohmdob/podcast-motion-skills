#!/usr/bin/env python3
"""Subtitles straight from a script, for a show that was written rather than recorded. Free.

    python3 script_srt.py CLIP_FOLDER OUT.srt

make_srt.py rebuilds its lines from a transcript. A script-made transcript has no word boundaries in Thai, so it ran words together and broke them in the middle.
The script already holds what was said, so cues here break only at its own spaces. Reads script timing from build/lines.json and the cut from build/edl.json.
"""
import json, sys
from pathlib import Path

C, OUT = Path(sys.argv[1]), Path(sys.argv[2])
MAX = 34
lines = json.loads((C / 'build/lines.json').read_text(encoding='utf-8'))
slices = [s for ch in json.loads((C / 'build/edl.json').read_text(encoding='utf-8'))['chapters'] for s in ch['slices']]


def film(s):
    acc = 0.0
    for p, q in slices:
        if s < p:
            return acc
        if s <= q:
            return acc + s - p
        acc += q - p
    return acc


def tc(t):
    ms = round(t * 1000)
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


cues = []
for l in lines:
    parts, cur = [], ''
    for w in l['t'].split(' '):
        if cur and len(cur) + 1 + len(w) > MAX:
            parts.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    parts.append(cur)
    total, used = len(l['t']), 0
    for p in parts:
        a = l['a'] + (l['b'] - l['a']) * used / total
        used += len(p) + 1
        cues.append((film(a), film(l['a'] + (l['b'] - l['a']) * min(used - 1, total) / total), p))
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(''.join(f'{i + 1}\n{tc(a)} --> {tc(b)}\n{t}\n\n' for i, (a, b, t) in enumerate(cues)), encoding='utf-8')
print(f'OK: {len(cues)} cues · ends {cues[-1][1]:.2f} s · {OUT}')

#!/usr/bin/env python3
"""Transcripts into the two shapes the pipeline reads. Free and local.

    python3 transcript.py rows audio/scribe.json --md transcripts/EP02.md --rows build/pass1.json [--take 0:speaker_0=H,speaker_1=G] [--take 600:speaker_0=G,speaker_1=H]
    python3 transcript.py import captions.srt audio/scribe.json [--who G]

rows    turns timed words into readable rows: a table to read and pick moments from, and pass1.json, [{a, b, who, t}], which the shot planner and subtitles use.
        Speaker labels can swap between camera takes, so --take says which label is which person from a given second onward. H is the person on the left of frame, G the right.
        Check these against the footage: diarization on one mixed mono track is often wrong, and no tool here can settle it.
import  makes a scribe-shaped file from any .srt, .vtt or [{text, start, end}] JSON, such as `npx hyperframes transcribe` output, so the pipeline runs with no ElevenLabs key.
        An .srt has no word times, so those are spread evenly through each cue. That is good enough to find anchors; real cuts still come from silence detection.
"""
import argparse, json, re, sys
from pathlib import Path


def stamp(t):
    return f'{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d}'


def speaker_map(takes):
    """[(from second, {label: person})], latest first."""
    out = []
    for raw in takes or ['0:speaker_0=H,speaker_1=G']:
        at, pairs = raw.split(':', 1)
        out.append((float(at), dict(p.split('=') for p in pairs.split(','))))
    return sorted(out, key=lambda x: -x[0])


def who_at(maps, t, label):
    for at, m in maps:
        if t >= at:
            return m.get(label, label or '?')
    return label or '?'


def rows(x):
    words = json.loads(Path(x.src).read_text(encoding='utf-8')).get('words', [])
    maps = speaker_map(x.take)
    out, cur = [], None
    for w in words:
        if w.get('type') == 'spacing':
            if cur:
                cur['t'] += ' '
            continue
        if w.get('type') not in (None, 'word'):
            continue
        who = who_at(maps, w['start'], w.get('speaker_id'))
        if cur and (who != cur['who'] or w['start'] - cur['b'] > x.gap or w['start'] - cur['a'] > x.longest):
            out.append(cur)
            cur = None
        if not cur:
            cur = {'a': round(w['start'], 2), 'b': round(w['end'], 2), 'who': who, 't': w['text']}
        else:
            cur['t'] += w['text']
            cur['b'] = round(w['end'], 2)
    if cur:
        out.append(cur)
    for r in out:
        r['t'] = r['t'].strip()
    if not out:
        sys.exit(f'FAIL: no timed words in {x.src}')
    if x.rows:
        Path(x.rows).parent.mkdir(parents=True, exist_ok=True)
        Path(x.rows).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    if x.md:
        Path(x.md).parent.mkdir(parents=True, exist_ok=True)
        body = ''.join(f"| {stamp(r['a'])} – {stamp(r['b'])} | {r['who']} | {r['t']} |\n" for r in out)
        Path(x.md).write_text(f'# Transcript: {Path(x.src).name}\n\nA machine transcript: read it against the sound before trusting a word or a name.\n\n| Timecode | Speaker | Script |\n|---|---|---|\n{body}', encoding='utf-8')
    print(f'OK: {len(out)} rows, {stamp(out[-1]["b"])} long')


def cues_from_srt(text):
    out = []
    for m in re.finditer(r'(\d+):(\d\d):(\d\d)[,.](\d{1,3})\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d{1,3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)', text.replace('\r', ''), re.S):
        g = m.groups()
        sec = lambda h, mi, s, ms: int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, '0')) / 1000
        line = re.sub(r'<[^>]+>', '', ' '.join(g[8].split('\n'))).strip()
        if line:
            out.append((sec(*g[:4]), sec(*g[4:8]), line))
    return out


def import_(x):
    p = Path(x.src)
    raw = p.read_text(encoding='utf-8-sig')
    words = []
    if p.suffix.lower() == '.json':
        d = json.loads(raw)
        thai = lambda t: bool(re.search(r'[\u0E00-\u0E7F]', t))
        for w in (d.get('words', []) if isinstance(d, dict) else d):
            if w.get('type') == 'spacing':
                continue
            text = w.get('text') or w.get('word', '')
            # Thai runs on with no spaces; any other word needs one, or rows and subtitles run the words together.
            if words and not (thai(text) and thai(words[-1]['text'])):
                words.append({'text': ' ', 'start': float(w['start']), 'end': float(w['start']), 'type': 'spacing', 'speaker_id': x.who})
            words.append({'text': text, 'start': float(w['start']), 'end': float(w['end']), 'type': 'word', 'speaker_id': w.get('speaker_id', x.who)})
    else:
        for a, b, line in cues_from_srt(raw):
            chars = sum(len(t) for t in line.split()) or 1
            t, step = a, (b - a) / chars
            for tok in line.split():
                if words:
                    words.append({'text': ' ', 'start': round(t, 3), 'end': round(t, 3), 'type': 'spacing', 'speaker_id': x.who})
                # Thai runs have no spaces and the anchors work per character, so give each character its own slice of the cue.
                parts = list(tok) if re.search(r'[฀-๿]', tok) else [tok]
                for part in parts:
                    d_ = step * len(part)
                    words.append({'text': part, 'start': round(t, 3), 'end': round(t + d_, 3), 'type': 'word', 'speaker_id': x.who})
                    t += d_
    if not words:
        sys.exit(f'FAIL: found no cues or words in {p}')
    Path(x.out).parent.mkdir(parents=True, exist_ok=True)
    Path(x.out).write_text(json.dumps({'language_code': '', 'text': '', 'words': words}, ensure_ascii=False), encoding='utf-8')
    print(f'OK: {sum(w["type"] == "word" for w in words)} timed pieces, {words[-1]["end"]:.0f} s → {x.out}')


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest='cmd', required=True)
r = sub.add_parser('rows')
r.add_argument('src')
r.add_argument('--md')
r.add_argument('--rows')
r.add_argument('--take', action='append')
r.add_argument('--gap', type=float, default=1.2, help='a new row after a pause this long')
r.add_argument('--longest', type=float, default=14.0, help='a new row after this many seconds')
i = sub.add_parser('import')
i.add_argument('src')
i.add_argument('out')
i.add_argument('--who', default='speaker_0')
args = ap.parse_args()
(rows if args.cmd == 'rows' else import_)(args)

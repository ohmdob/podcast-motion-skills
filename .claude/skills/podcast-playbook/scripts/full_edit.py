#!/usr/bin/env python3
"""The paper edit → a real cut of a full episode. Free; re-run it as often as you like while tuning the length.

    python3 $S/full_edit.py episodes/EPxx/full               # plan only: anchors, durations, what was removed
    python3 $S/full_edit.py episodes/EPxx/full --render      # also writes build/body.mp4, cold.mp4, voice_body.wav, voice_cold.wav
    python3 $S/full_edit.py episodes/EPxx/full --render --voice-only   # voice only, after changing "voice" in paper.json

Reads   paper.json        chapters of [start tc, first words, end tc, last words] taken from the first transcript, and "source"
        audio/scribe.json character timings on the isolated voice (the text differs a little, so anchors match fuzzily near their timecode)
        audio/isolated.mp3 and audio/boost.wav; with no isolated voice (no ElevenLabs), the denoised real voice alone
        A clip is a one-chapter paper.json with "clip": true and "from": "../../full", which reuses that folder's audio/ and transcript, so it costs nothing new.
Writes  build/edl.json    every kept slice in source seconds, frame-accurate, by chapter

Inside a kept range:
 · a pause over 0.24 s is shortened to 0.16 s (speech is never touched)
 · a lone backchannel (อืม, อ่า, ใช่ …) with quiet on both sides is removed, so the guest's thought runs on
Cut points are always on a frame, so picture and sound cut together. stdout ends with OK:/FAIL:.
"""
import difflib, json, re, subprocess, sys
from pathlib import Path
import numpy as np
from voice_lib import DENOISE, GENTLE, filt, read, steady, voice_mix
import studio

SR = 48000
ROOT = Path(sys.argv[1]).resolve()
BUILD = ROOT / 'build'
SHOW = studio.load_show(ROOT)
FPS = SHOW['fps']
paper = json.loads((ROOT / 'paper.json').read_text(encoding='utf-8'))
if not paper.get('source'):
    sys.exit('FAIL: paper.json needs "source": the recording, relative to the project')
SOURCE = SHOW['root'] / paper['source']
if not SOURCE.exists():
    sys.exit(f'FAIL: no such recording: {SOURCE}')
AUDIO = (ROOT / paper.get('from', '.')).resolve() / 'audio'
ISO, BOOST = AUDIO / 'isolated.mp3', AUDIO / 'boost.wav'
if not ISO.exists() and not BOOST.exists():
    sys.exit(f'FAIL: no {BOOST}. It is the first step of the sound stage: see references/sound-and-script.md.')
if not (AUDIO / 'scribe.json').exists():
    sys.exit(f'FAIL: no {AUDIO}/scribe.json. el.py scribe writes it; with no ElevenLabs key, transcript.py import makes one from an .srt')
BACK = set(studio.words(SHOW)['back'])
MIN_SIL, KEEP_SIL = 0.24, 0.16
# The end of the last frame in the source: a slice past it asks for a frame that does not exist.
LAST = int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', str(SOURCE)], capture_output=True, text=True).stdout.strip().rstrip(',')) / FPS


def tc(s):
    """mm:ss or hh:mm:ss, the form the transcript prints."""
    return sum(float(v) * 60 ** i for i, v in enumerate(reversed(s.split(':'))))


def frame(t):
    return round(t * FPS) / FPS


chars = [c for c in json.loads((AUDIO / 'scribe.json').read_text(encoding='utf-8'))['words'] if c['type'] == 'word']
# per-character arrays: Scribe's "words" here are characters or Latin words
text, starts, ends = [], [], []
for c in chars:
    for ch in c['text']:
        text.append(ch); starts.append(c['start']); ends.append(c['end'])
text_s = ''.join(text)
starts, ends = np.array(starts), np.array(ends)


def locate(t, phrase, want_end, reach=14.0):
    """Best fuzzy match of phrase near t; returns (seconds, similarity)."""
    lo, hi = np.searchsorted(starts, t - reach), np.searchsorted(starts, t + reach)
    n = len(phrase)
    best, where = 0.0, None
    for i in range(int(lo), max(int(lo) + 1, int(hi) - n + 1), 2):
        r = difflib.SequenceMatcher(None, phrase, text_s[i:i + n], autojunk=False).ratio()
        r -= abs(starts[i] - t) * 0.002     # prefer the nearer of two repeats
        if r > best:
            best, where = r, i
    if where is None:
        return t, 0.0
    return (float(ends[min(where + n - 1, len(ends) - 1)]) if want_end else float(starts[where])), best


# silences on the isolated voice
sil = []
def quiet_level():
    """An isolated voice is close to silent between words, so a fixed -38 dB finds every pause. A real voice keeps its room tone, boosted along with the speech, and may never go that low:
    take the line from this recording's own quiet parts. Measured against an isolated voice over 8 minutes of talk, this finds about 43% of the long pauses, and about 76% of the
    time it trims is truly silent. A higher line finds more and cuts into quiet speech, and leaving a pause in does less harm than clipping a word."""
    if ISO.exists():
        return -38.0
    x = read(BOOST, DENOISE, 16000)
    hop = 320
    rms = np.sqrt(np.array([np.mean(x[i:i + hop] ** 2) for i in range(0, len(x) - hop, hop)])) + 1e-7
    db = 20 * np.log10(rms)
    floor = np.percentile(db, 10)
    level = floor + 8
    print(f'no isolated voice: silence line {level:.0f} dB, from quiet parts at {floor:.0f} dB. Fewer pauses will be found: listen to the cut.')
    return float(level)


out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(ISO if ISO.exists() else BOOST), '-af', ('' if ISO.exists() else f'{DENOISE},') + f'silencedetect=noise={quiet_level():.1f}dB:d=0.1', '-f', 'null', '-'], capture_output=True, text=True).stderr
for m in re.finditer(r'silence_end: ([\d.]+) \| silence_duration: ([\d.]+)', out):
    e, d = float(m.group(1)), float(m.group(2))
    sil.append((e - d, e))
if not sil:
    sys.exit('FAIL: found no silences in this voice, so there is nowhere safe to cut. Listen to audio/boost.wav: is it all noise, or very short?')


def chars_between(a, b):
    i, j = np.searchsorted(starts, a), np.searchsorted(starts, b)
    return text_s[int(i):int(j)]


def slices(a, b, stats):
    """Kept slices of [a, b]: long pauses shortened, lone backchannels dropped."""
    inner = [(max(s, a), min(e, b)) for s, e in sil if e > a and s < b]
    # sound islands between silences
    islands, cur = [], a
    for s, e in inner:
        if s > cur:
            islands.append([cur, s])
        cur = e
    if cur < b:
        islands.append([cur, b])
    kept = []
    for k, (p, q) in enumerate(islands):
        word = re.sub(r'\s', '', chars_between(p - .02, q + .02))
        if 0 < k < len(islands) - 1 and q - p < 1.0 and word in BACK:
            stats['back'] += q - p
            continue
        kept.append([p, q])
    res = []
    for p, q in kept:
        if res and p - res[-1][1] <= MIN_SIL:
            res[-1][1] = q
        elif res:
            gap = p - res[-1][1]
            stats['pause'] += gap - KEEP_SIL
            res[-1][1] += KEEP_SIL / 2
            res.append([p - KEEP_SIL / 2, q])
        else:
            res.append([p, q])
    # breathing room at the edges, then snap to frames
    res[0][0] -= .06; res[-1][1] += .08
    res = [[frame(p), min(frame(q), LAST)] for p, q in res]
    return [r for r in res if r[1] - r[0] >= .12]


stats = {'pause': 0.0, 'back': 0.0}
weak, edl = [], {'cold': [], 'chapters': []}
# The cold open is short and jumps around the source, so its cuts are written in exact seconds, chosen from silences and character timings.
edl['cold'] = [[frame(a), frame(b)] for a, b in paper.get('cold', [])]
prog = 0.0
for ch in paper['chapters']:
    sl, raw = [], 0.0
    for t1, w1, t2, w2 in ch['keep']:
        a, r1 = locate(tc(t1), w1, False)
        # An empty end anchor means the transcript is unusable there: cut at the start of the silence nearest that timecode.
        b, r2 = (min((x for x, _ in sil), key=lambda x: abs(x - tc(t2))), 1.0) if not w2 else locate(tc(t2), w2, True)
        for w, r, t in ((w1, r1, t1), (w2, r2, t2)):
            if r < .62:
                weak.append((t, w, round(r, 2)))
        if b <= a:
            weak.append((t1, f'range ends before it starts: {w1} → {w2}', 0))
            continue
        raw += b - a
        if abs((b - a) - (tc(t2) - tc(t1))) > 4:     # an anchor that matched a repeated phrase shows up as a range of the wrong length
            weak.append((t1, f'range is {b - a:.1f}s, expected about {tc(t2) - tc(t1):.0f}s: {w1[:18]} → {w2[:18]}', 0))
        sl += slices(a, b, stats)
    # Neighbouring ranges can overlap by a few frames after padding. Left alone, select() drops the repeat from the picture while the
    # voice plays it twice, and sync slips by the end of the episode.
    merged = []
    for p, q in sorted(sl):
        if merged and p <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], q)
        else:
            merged.append([p, q])
    if edl['chapters'] and merged and merged[0][0] < edl['chapters'][-1]['slices'][-1][1]:
        merged[0][0] = edl['chapters'][-1]['slices'][-1][1]
    sl = merged
    d = sum(q - p for p, q in sl)
    edl['chapters'].append({'id': ch['id'], 'title': ch['title'], 'slices': sl, 'dur': round(d, 2), 'raw': round(raw, 2)})
    prog += d
BUILD.mkdir(exist_ok=True)
if '--voice-only' in sys.argv:
    # The picture is already cut from the stored edit. If paper.json has moved on, a fresh one would cut the voice differently from it.
    edl = json.loads((BUILD / 'edl.json').read_text(encoding='utf-8'))
else:
    (BUILD / 'edl.json').write_text(json.dumps(edl, ensure_ascii=False))

cold = sum(q - p for p, q in edl['cold'])
n = sum(len(c['slices']) for c in edl['chapters'])
print(f"{'chapter':<34}{'raw':>7}{'cut':>7}")
for c in edl['chapters']:
    print(f"{c['title'][:30]:<34}{c['raw']:>7.1f}{c['dur']:>7.1f}")
print(f"body {prog/60:.2f} min in {n} slices · cold open {cold:.1f} s · pauses saved {stats['pause']:.0f} s · backchannels saved {stats['back']:.0f} s")
for w in weak:
    print('WEAK anchor', w)
if weak and '--render' in sys.argv and '--voice-only' not in sys.argv and '--force' not in sys.argv:
    sys.exit('FAIL: weak anchors above, so nothing was rendered. A bad anchor can silently delete part of an answer. Fix them, or add --force if you have checked them.')

if '--render' in sys.argv:
    # A clip sounds like its episode unless it says otherwise.
    _from = (ROOT / paper['from'] / 'paper.json') if paper.get('from') else None
    vcfg = paper.get('voice') or (json.loads(_from.read_text(encoding='utf-8')).get('voice') if _from and _from.exists() else None) or {'mix': 1.0, 'chain': 'gentle'}
    sig = voice_mix(ISO, BOOST, vcfg['mix'])

    def voice(ranges, out):
        fade = int(.008 * SR)
        parts = []
        for p, q in ranges:
            x = sig[int(p * SR):int(q * SR)].copy()
            x[:fade] *= np.linspace(0, 1, fade); x[-fade:] *= np.linspace(1, 0, fade)
            parts.append(x)
        # Light on purpose. The first chain (de-esser, 2.4:1 compressor, dynaudnorm) measured fine and sounded warped: it pushed up the residue in the gaps.
        chain = {'gentle': GENTLE, 'none': 'anull'}[vcfg['chain']]
        y, gain, lufs, tp = steady(filt(np.concatenate(parts), chain))
        tmp = BUILD / '_v.raw'
        y.astype(np.float32).tofile(tmp)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(tmp), '-c:a', 'pcm_s24le', str(BUILD / f'_{out.name}')], check=True)
        (BUILD / f'_{out.name}').replace(out)    # all at once, so nothing ever reads a half-written voice
        tmp.unlink()
        print(f'{out.name}: fixed gain {gain:+.1f} dB → {lufs:.1f} LUFS, {tp:.1f} dBTP')

    def picture(ranges, out):
        """ffmpeg's select expression tops out at about 100 functions, so cut in groups, in parallel, and join. Frame counts are checked."""
        from concurrent.futures import ThreadPoolExecutor
        count = lambda f: int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', str(f)], capture_output=True, text=True).stdout.strip().rstrip(','))
        want = sum(round(q * FPS) - round(p * FPS) for p, q in ranges)
        if out.exists() and out.stem != 'cold' and count(out) == want and len(ranges) > 1:
            print(f'{out.name}: {want} frames already, reused')
            return
        groups = [ranges[i:i + 60] for i in range(0, len(ranges), 60)]

        def one(k):
            g = groups[k]
            base = round(g[0][0] * FPS)
            expr = '+'.join(f'between(n,{round(p * FPS) - base},{round(q * FPS) - 1 - base})' for p, q in g)
            sel = BUILD / f'_sel{k}.txt'
            part = BUILD / f'_g{out.stem}{k}.mp4'
            sel.write_text(f"select='{expr}',setpts=N/{FPS}/TB,hqdn3d=1.2:1.2:3:3,unsharp=5:5:0.45:5:5:0,format=yuv420p")
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{base / FPS - .001:.3f}', '-i', str(SOURCE), '-/filter:v', str(sel), '-an', '-r', str(FPS), '-fps_mode', 'cfr',
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-g', str(FPS), '-bf', '0', '-frames:v', str(sum(round(q * FPS) - round(p * FPS) for p, q in g)), str(part)], check=True)
            sel.unlink()
            return part

        with ThreadPoolExecutor(5) as ex:
            parts = list(ex.map(one, range(len(groups))))
        lst = BUILD / f'_l{out.stem}.txt'
        lst.write_text(''.join(f"file '{p}'\n" for p in parts))
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(out)], check=True)
        lst.unlink()
        for p in parts:
            p.unlink()
        got = count(out)
        if want != got:
            sys.exit(f'FAIL: {out.name} has {got} frames, wanted {want}')

    body = [r for c in edl['chapters'] for r in c['slices']]
    voice(body, BUILD / 'voice_body.wav')
    if edl['cold']:
        voice(edl['cold'], BUILD / 'voice_cold.wav')
    if '--voice-only' in sys.argv:      # change the voice treatment without touching the picture
        print('OK: voice only')
        sys.exit(0)
    picture(body, BUILD / 'body.mp4')
    # the cold open jumps backwards in the source, so each part is cut alone and joined
    dur = lambda f: float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)], capture_output=True, text=True).stdout)
    print(f"rendered: body picture {dur(BUILD/'body.mp4'):.2f}s voice {dur(BUILD/'voice_body.wav'):.2f}s")
    if edl['cold']:
        parts = []
        for i, r in enumerate(edl['cold']):
            p = BUILD / f'_c{i}.mp4'
            picture([r], p)
            parts.append(p)
        lst = BUILD / '_c.txt'
        lst.write_text(''.join(f"file '{p}'\n" for p in parts))
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(BUILD / 'cold.mp4')], check=True)
        for p in parts + [lst]:
            p.unlink()
        print(f"rendered: cold picture {dur(BUILD/'cold.mp4'):.2f}s voice {dur(BUILD/'voice_cold.wav'):.2f}s")
print('FAIL: weak anchors above' if weak else 'OK')
sys.exit(1 if weak else 0)

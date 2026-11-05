#!/usr/bin/env python3
"""A clip's cut list → a synced picture and voice, plus word timings on the clip's own clock. Free; everything regenerable.

    python3 edl.py episodes/EPxx/clips/Cnn_name [--voice-only]

Reads   edl.json          {"source", "fps"?, "work_offset", "cuts": [[in, out], …], "tail"?, "voice"?} (times on audio/work.wav)
        audio/work.wav    this range's voice, used to find quiet places to cut
        audio/align.json  Forced Alignment over audio/tokens.txt; or audio/words.json, a [{text, start, end}] from any other transcriber
        "voice"           optional {"mix": .4, "iso": "audio/isolated.mp3", "boost": "audio/boost.wav", "start": 450, "chain": "gentle"}: the same blend as the full episode.
                          `start` is the recording time where those two files begin. With no block, the voice is work.wav as it stands.
Writes  build/edit.mp4    silent mezzanine: light denoise + sharpen, last frame held for `tail` s under the end card, keyframe every second (HyperFrames seeks cleanly)
        build/voice.wav   cut with short fades, one fixed gain and a limiter (voice_lib.steady), so it matches the episode. Music and effects bring the mix up; the master sets -14 LUFS
        build/tokens.json [{text, start, end}] per token, on the clip's clock
        build/energy.json voice energy per frame (0-1), for anything that reacts to who is talking
Cut points snap to the quietest 20 ms within ±90 ms, then to a frame, so picture and sound always cut together. stdout ends with OK:/FAIL:.
"""
import json, re, subprocess, sys
from pathlib import Path
import numpy as np
import studio
from voice_lib import GENTLE, SR, filt, read, steady, voice_mix


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'FAIL: {cmd[0]} {r.stderr[-800:]}')
    return r


def snap(sig, t, fps, sr=SR):
    """Quietest 20 ms window within ±90 ms of t, then rounded to the nearest frame."""
    win, reach = int(0.02 * sr), int(0.09 * sr)
    c = int(t * sr)
    lo, hi = max(0, c - reach), min(len(sig) - win, c + reach)
    energies = [(float(np.mean(sig[i:i + win] ** 2)), i) for i in range(lo, hi, int(0.005 * sr))]
    best = min(energies)[1] + win // 2
    return round(best / sr * fps) / fps


def load_tokens(root):
    align, words = root / 'audio' / 'align.json', root / 'audio' / 'words.json'
    if align.exists():
        out, cur = [], None
        for c in json.loads(align.read_text(encoding='utf-8'))['characters']:
            if c['text'].strip() == '':
                if cur:
                    out.append(cur)
                cur = None
            elif cur is None:
                cur = {'text': c['text'], 'start': c['start'], 'end': c['end']}
            else:
                cur['text'] += c['text']
                cur['end'] = c['end']
        return out + ([cur] if cur else [])
    if words.exists():
        return json.loads(words.read_text(encoding='utf-8'))
    print('no audio/align.json or audio/words.json: tokens.json is empty, so time the words on screen by hand')
    return []


def main():
    root = Path(sys.argv[1]).resolve()
    show = studio.load_show(root)
    for f, how in ((root / 'edl.json', 'Write it by hand: see references/file-formats.md.'), (root / 'audio' / 'work.wav', 'See "A clip with no episode behind it" in references/sound-and-script.md.')):
        if not f.exists():
            sys.exit(f'FAIL: no {f}. {how}')
    edl = json.loads((root / 'edl.json').read_text(encoding='utf-8'))
    fps, off = edl.get('fps', show['fps']), edl['work_offset']
    source = show['root'] / edl['source']
    if '--voice-only' not in sys.argv and not source.exists():
        sys.exit(f'FAIL: no such recording: {source}')
    sig = read(root / 'audio' / 'work.wav')
    cuts = [(snap(sig, a, fps), snap(sig, b, fps)) for a, b in edl['cuts']]
    build = root / 'build'
    build.mkdir(exist_ok=True)

    def to_clip(t):
        """Clip-clock time of source time t; a time inside a removed part lands on the next kept frame."""
        acc = 0.0
        for a, b in cuts:
            if t < a:
                return acc
            if t <= b:
                return acc + (t - a)
            acc += b - a
        return acc

    out = [{'text': k['text'], 'start': round(to_clip(k['start']), 3), 'end': round(to_clip(k['end']), 3)} for k in load_tokens(root)]
    out = [k for k in out if k['end'] > k['start']]
    (build / 'tokens.json').write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')

    # picture
    if '--voice-only' not in sys.argv:
        n = len(cuts)
        base = max(0, off - 2)    # -ss before -i moves the input clock, so trim times are relative to it
        v = ';'.join(f"[0:v]trim=start={off + a - base:.3f}:end={off + b - base:.3f},setpts=PTS-STARTPTS[v{i}]" for i, (a, b) in enumerate(cuts))
        fc = f"{v};{''.join(f'[v{i}]' for i in range(n))}concat=n={n}:v=1:a=0,hqdn3d=1.2:1.2:3:3,unsharp=5:5:0.45:5:5:0,tpad=stop_mode=clone:stop_duration={edl.get('tail', 3)},format=yuv420p[v]"
        run(['ffmpeg', '-y', '-v', 'error', '-ss', str(base), '-i', str(source), '-filter_complex', fc, '-map', '[v]', '-an', '-r', str(fps),
             '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-g', str(round(fps)), '-bf', '0', str(build / 'edit.mp4')])

    # voice: the same blend, chain and level as the full episode, so a clip and its episode sound like one recording
    vcfg = edl.get('voice')
    if vcfg:
        full = voice_mix(root / vcfg.get('iso', 'audio/isolated.mp3'), root / vcfg.get('boost', 'audio/boost.wav'), vcfg.get('mix', 1.0))
        work = full[int(round((off - vcfg.get('start', off)) * SR)):]
    else:
        work = sig
    fade = int(.008 * SR)
    parts = []
    for p, q in cuts:
        x = work[int(p * SR):int(q * SR)].copy()
        x[:fade] *= np.linspace(0, 1, fade)
        x[-fade:] *= np.linspace(1, 0, fade)
        parts.append(x)
    # Light on purpose. A heavy chain (de-esser, 2.4:1 compressor, dynaudnorm) measured fine and sounded warped: it pushed up the residue in the gaps.
    chain = {'gentle': GENTLE, 'none': 'anull'}[(vcfg or {}).get('chain', 'gentle')]
    y, gain, lufs, tp = steady(filt(np.concatenate(parts), chain))
    tmp = build / '_v.raw'
    y.astype(np.float32).tofile(tmp)
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(tmp), '-c:a', 'pcm_s24le', str(build / '_voice.wav')])
    (build / '_voice.wav').replace(build / 'voice.wav')    # all at once, so nothing ever reads a half-written voice
    tmp.unlink()
    print(f'voice.wav: fixed gain {gain:+.1f} dB → {lufs:.1f} LUFS, {tp:.1f} dBTP')

    # energy per frame
    hop = int(SR / fps)
    e = np.array([np.sqrt(np.mean(y[i:i + hop] ** 2)) for i in range(0, len(y), hop)])
    e = np.clip(e / max(np.percentile(e, 98), 1e-6), 0, 1)
    (build / 'energy.json').write_text(json.dumps({'fps': fps, 'energy': [round(float(x), 3) for x in e]}))

    dur = float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(build / 'edit.mp4')]).stdout)
    adur = len(y) / SR
    print('cuts', [(round(a, 2), round(b, 2)) for a, b in cuts])
    print(f'OK: picture {dur:.3f}s · voice {adur:.3f}s · {len(out)} tokens')


if __name__ == '__main__':
    main()

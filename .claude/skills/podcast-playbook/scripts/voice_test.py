#!/usr/bin/env python3
"""Voice treatments side by side, on the same words, for a person to judge by ear. Free and local; no new API calls.

    python3 voice_test.py episodes/EPxx/full outputs/audio_test 10,18 40,50 [--blends .8,.6,.4]

The ranges are recording times: take them from the film's own words, including the cold open, using build/edl.json.
Every file holds the same ranges at the same loudness (-16 LUFS), so the only difference is the treatment. Numbers can show that a noise floor
dropped; only a listener can tell whether a voice still sounds like the person. With no isolated voice, this compares the source and denoise only.
"""
import subprocess, sys
from pathlib import Path
import numpy as np
from voice_lib import DENOISE, GENTLE, SR, blend_shift, filt, read as rd, steady

args = sys.argv[1:]
blends = [.8, .6, .4]
if '--blends' in args:
    i = args.index('--blends')
    blends = [float(v) for v in args[i + 1].split(',')]
    del args[i:i + 2]
ROOT, OUT = Path(args[0]).resolve(), Path(args[1])
RANGES = [tuple(float(x) for x in a.split(',')) for a in args[2:]]
if not RANGES:
    sys.exit('FAIL: give at least one range, as start,end in recording seconds')
OUT.mkdir(parents=True, exist_ok=True)
ISO, BOOST = ROOT / 'audio' / 'isolated.mp3', ROOT / 'audio' / 'boost.wav'
if not BOOST.exists():
    sys.exit(f'FAIL: no {BOOST}. It is the first step of the sound stage: see references/sound-and-script.md.')

raw, clean = rd(BOOST), rd(BOOST, DENOISE)
if ISO.exists():
    iso = rd(ISO)
    k = blend_shift(ISO, BOOST)
    print(f'denoised voice is {k / SR * 1000:.2f} ms behind the isolated one; aligned for blends')
    raw_a, clean_a = np.roll(raw, -k), np.roll(clean, -k)
    n = min(len(iso), len(raw_a))
    lo, hi = (SR * 60, SR * 360) if n > SR * 90 else (0, n)

    def blend(w):
        # matched levels first, or the mix ratio means nothing
        g = np.sqrt(np.mean(iso[lo:hi] ** 2) / np.mean(clean_a[lo:hi] ** 2))
        return iso[:n] * w + clean_a[:n] * g * (1 - w)

    VERS = [('0_source_no_cleanup', raw_a[:n], ''), ('1_isolation_only', iso[:n], ''), ('2_isolation_gentle', iso[:n], GENTLE)]
    VERS += [(f'{3 + i}_blend_{round(w * 100)}_{round((1 - w) * 100)}', blend(w), GENTLE) for i, w in enumerate(blends)]
    VERS.append((f'{3 + len(blends)}_no_ai_denoise_only', clean_a[:n], GENTLE))
else:
    print('no isolated voice: comparing the source and denoise only')
    VERS = [('0_source_no_cleanup', raw, ''), ('1_no_ai_denoise_only', clean, GENTLE)]


def stats(x):
    w = np.hanning(1024)
    fr = np.array([np.abs(np.fft.rfft(x[i:i + 1024] * w)) for i in range(0, len(x) - 1024, 512)]) + 1e-9
    f = np.fft.rfftfreq(1024, 1 / SR)
    band = lambda a, b: 20 * np.log10(np.mean(fr[:, (f >= a) & (f < b)]))
    h = SR // 20
    e = np.array([np.sqrt(np.mean(x[i:i + h] ** 2)) for i in range(0, len(x) - h, h)]) + 1e-7
    floor = 20 * np.log10(np.percentile(e, 8))
    return f'quietest parts {floor:6.1f} dB · 4-8 kHz {band(4000, 8000):5.0f} · 8-12 kHz {band(8000, 12000):5.0f} · crest {20 * np.log10(np.abs(x).max() / np.sqrt(np.mean(x ** 2))):4.1f} dB'


for name, sig, chain in VERS:
    parts = []
    for a, b in RANGES:
        x = sig[int(a * SR):int(b * SR)].copy()
        parts += [x, np.zeros(int(.5 * SR), np.float32)]
    x = np.concatenate(parts)
    y = steady(filt(x, chain) if chain else x)[0]    # the same fixed gain and limiter as the film, so the test is what ships
    tmp = OUT / '_t.raw'
    y.astype(np.float32).tofile(tmp)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(tmp), '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(OUT / f'{name}.wav')], check=True)
    tmp.unlink()
    print(f'{name:<24}', stats(rd(OUT / f'{name}.wav')))
print('OK:', OUT)

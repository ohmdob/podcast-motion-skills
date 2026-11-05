#!/usr/bin/env python3
"""How the show's voice is blended and levelled. Shared by full_edit.py, edl.py and voice_test.py, so a test sounds like the film.

Two faults that delivery QC cannot see, both measured on a real episode and both built into what the producer first heard:
- Alignment. afftdn delays its output by exactly 25.00 ms, and the isolated voice ran ahead of the raw one by about 19 ms more. Waveform
  correlation can't measure this, because the isolated voice is rebuilt and barely correlates with the real one (about 0.1): it returned
  7 ms and 32 ms depending on the input. Speech envelopes agree across the whole recording (corr about 0.73, 44 ms).
- Level. `loudnorm ... linear=true` silently runs dynamic when the gain would break its true-peak target, which a quiet recording always
  does. The voice then rode up and down by as much as 10 dB over the film. steady() uses one fixed gain and a limiter on the peaks.

With no isolated voice (no ElevenLabs key), voice_mix() returns the denoised real voice alone.
"""
import re, subprocess, sys, tempfile
from pathlib import Path
import numpy as np

SR = 48000
DENOISE = 'afftdn=nr=16:nf=-30:tn=1'
GENTLE = 'highpass=f=70,acompressor=threshold=-20dB:ratio=1.5:attack=25:release=300:makeup=1'
# Voice at -16 LUFS with peaks held here: the setting of the file the producer picked. It limits about 5% of speech by over 1 dB.
# The mix's mono-to-stereo step lowers peaks by about 2.3 dB and leaves loudness alone, so the master's gain to -14 LUFS still fits under -1.2 dBTP.
VOICE_LIMIT = -1.5


def read(path, af=None, sr=SR):
    cmd = ['ffmpeg', '-v', 'error', '-i', str(path)] + (['-af', af] if af else []) + ['-f', 'f32le', '-ac', '1', '-ar', str(sr), '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()


def filt(x, af):
    """Run a mono signal through an ffmpeg filter chain."""
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / 'x.raw'
        x.astype(np.float32).tofile(t)
        out = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(t), '-af', af, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).copy()


def loudness(x):
    """Integrated LUFS and true peak of a mono signal."""
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / 'x.raw'
        x.astype(np.float32).tofile(t)
        s = subprocess.run(['ffmpeg', '-nostats', '-hide_banner', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(t), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    s = s[s.rfind('Summary:'):]
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', s)[1]), float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s)[1])


def blend_shift(iso_path, boost_path):
    """How many samples the denoised real voice sits behind the isolated one, from speech envelopes at 1 ms across the recording."""
    band = 'highpass=f=300,highpass=f=300,lowpass=f=3400,lowpass=f=3400'
    env = lambda x: np.convolve(np.abs(x), np.ones(48) / 48, 'same')[::16]
    a, b = env(read(boost_path, f'{DENOISE},{band}', 16000)), env(read(iso_path, band, 16000))
    secs = min(len(a), len(b)) // 1000
    # A whole recording gets separate windows through its length. A short clip can't, so its windows overlap and fewer have to agree.
    win, starts, need = (12, range(20, secs - 30, 35), 5) if secs >= 300 else (min(12, max(4, secs // 4)), range(0, max(1, secs - min(12, max(4, secs // 4))), 3), 2)
    lags = []
    for t in starts:
        u, v = a[t * 1000:(t + win) * 1000], b[t * 1000:(t + win) * 1000]
        u, v = u - u.mean(), v - v.mean()
        x = np.fft.irfft(np.fft.rfft(u, 2 * len(u)) * np.conj(np.fft.rfft(v, 2 * len(u))))
        w = np.concatenate([x[-120:], x[:121]])
        if w.max() / np.sqrt((u ** 2).sum() * (v ** 2).sum()) > .6:
            lags.append(int(np.argmax(w)) - 120)
    if len(lags) < need:
        sys.exit(f'FAIL: only {len(lags)} windows agree on the voice alignment; check the isolated track')
    return round(float(np.median(lags)) / 1000 * SR)


def voice_mix(iso_path, boost_path, mix=1.0):
    """The voice before its chain: `mix` of the isolated voice plus the rest of the aligned, denoised real voice, levels matched first or the ratio means nothing.
    Blending real voice back restores natural consonants and hides the warble of a voice rebuilt from a noisy source."""
    iso_path, boost_path = Path(iso_path), Path(boost_path)
    if not iso_path.exists():
        if not boost_path.exists():
            sys.exit(f'FAIL: neither {iso_path} nor {boost_path} exists')
        print(f'no {iso_path.name}: using the denoised real voice alone', flush=True)
        return read(boost_path, DENOISE)
    sig = read(iso_path)
    if mix >= 1:
        return sig
    if not boost_path.exists():
        sys.exit(f'FAIL: a {mix:.0%} blend needs {boost_path}')
    cln = np.roll(read(boost_path, DENOISE), -blend_shift(iso_path, boost_path))
    n = min(len(sig), len(cln))
    lo, hi = (SR * 60, SR * 360) if n > SR * 90 else (0, n)
    g = np.sqrt(np.mean(sig[lo:hi] ** 2) / np.mean(cln[lo:hi] ** 2))
    return sig[:n] * mix + cln[:n] * g * (1 - mix)


def steady(x, target=-16.0, limit_db=VOICE_LIMIT):
    """One fixed gain to the target loudness, and a limiter that only touches peaks. Returns the signal, the gain, LUFS and true peak."""
    limit = 10 ** (limit_db / 20)
    gain = target - loudness(x)[0]
    for _ in range(5):      # the limiter lowers loudness a little, so step the gain until it lands
        y = filt(x * 10 ** (gain / 20), f'alimiter=limit={limit:.4f}:attack=5:release=50:level=disabled:latency=1')
        i, tp = loudness(y)
        if abs(i - target) < .05:
            break
        gain += target - i
    return y, gain, i, tp

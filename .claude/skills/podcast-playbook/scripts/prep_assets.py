#!/usr/bin/env python3
"""Turns a clip's raw assets (assets_src/) into what its Studio Cut and Pop Studio projects use. Free; safe to re-run.

    python3 prep_assets.py episodes/EPxx/clips/Cnn_name

Stills  a_*.png → variant_a/assets/*.jpg
Music   music/bed_a|b.mp3 → variant_*/assets/bed.wav: room carved for speech (high-pass 90 Hz, -4 dB at 2.6 kHz), -16 LUFS
SFX     sfx/*.mp3 → variant_*/assets/sfx/*.wav at -3 dBFS peak, and sfx/peaks.json, so a cue's peak can land one frame after its picture
Links   build/ picture and voice into each project, fonts copied
With no music or effects of its own, a clip takes the show's library (assets/music, assets/sfx) and then the skill's. A clip with no stills simply has none.
A take with a peak under 0.02 is near-silent: it is reported as FAIL so it can't reach a film unnoticed.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
import studio

D = Path(sys.argv[1]).resolve()
show = studio.load_show(D)
A, Va, Vb = D / 'assets_src', D / 'variant_a' / 'assets', D / 'variant_b' / 'assets'
for p in (Va / 'fonts', Va / 'sfx', Vb / 'fonts', Vb / 'sfx', A):
    p.mkdir(parents=True, exist_ok=True)

for f in sorted(f for f in A.glob('a_*') if f.suffix.lower() in ('.png', '.jpg', '.jpeg')):
    ImageOps.fit(Image.open(f).convert('RGB'), (2240, 1260), Image.LANCZOS).save(Va / f"{f.stem.split('_', 1)[1]}.jpg", quality=93, subsampling=0)     # cropped, never stretched

for name, out in (('bed_a', Va), ('bed_b', Vb)):
    src = next((f for f in (A / 'music' / f'{name}.mp3', show['root'] / 'assets' / 'music' / f'{name}.mp3', studio.MUSIC_LIB / f'{name}.mp3') if f.exists()), None)
    if not src:
        print(f'no {name}.mp3: that variant has no music')
        continue
    if src.parent == studio.MUSIC_LIB:
        print(f"music: the skill's default {name}.mp3; give this show its own in assets/music/")
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-af', 'highpass=f=90,equalizer=f=2600:t=q:w=1.4:g=-4,loudnorm=I=-16:TP=-2:LRA=9',
                    '-ar', '48000', '-c:a', 'pcm_s16le', str(out / 'bed.wav')], check=True)

# A clip keeps its own copy of the library's sounds, because peaks.json is written beside them and the skill's folder stays read-only.
sfx_dir = A / 'sfx'
if not list(sfx_dir.glob('*.mp3')):
    sfx_dir.mkdir(exist_ok=True)
    for lib in (studio.SFX_LIB, show['root'] / 'assets' / 'sfx'):     # the skill's first, so the show's replace them sound by sound
        for f in lib.glob('*.mp3'):
            shutil.copy(f, sfx_dir)

peaks, bad = {}, []
for f in sorted(sfx_dir.glob('*.mp3')) if sfx_dir.is_dir() else []:
    n = f.stem
    s = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', str(f), '-f', 'f32le', '-ac', '1', '-ar', '48000', '-'], capture_output=True).stdout, np.float32)
    pk = float(np.abs(s).max())
    if pk < 0.02:
        bad.append(n)
    e = [np.sqrt(np.mean(s[i:i + 480] ** 2)) for i in range(0, len(s) - 480, 480)]
    d = len(s) / 48000
    peaks[n] = (round(int(np.argmax(e)) * .01, 2), round(d, 2), round(pk, 3))
    for out in (Va, Vb):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(f), '-af', f'volume={0.708 / max(pk, 1e-4):.3f},afade=t=out:st={max(0, d - .03):.3f}:d=0.03', '-ar', '48000', '-ac', '2',
                        '-c:a', 'pcm_s16le', str(out / 'sfx' / f'{n}.wav')], check=True)
if sfx_dir.is_dir():
    (sfx_dir / 'peaks.json').write_text(json.dumps(peaks))

for src, dst in ((D / 'build/edit.mp4', Va / 'edit.mp4'), (D / 'build/voice.wav', Va / 'voice.wav'), (D / 'build/voice.wav', Vb / 'voice.wav')):
    if src.exists():
        dst.unlink(missing_ok=True)
        os.link(src, dst)
shutil.copy(studio.FONTS / 'NotoSansThai.ttf', Va / 'fonts')
print(f"FAIL: near-silent takes: {', '.join(bad)}" if bad else f'OK: {len(peaks)} sfx, stills, beds')

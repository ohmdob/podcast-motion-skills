#!/usr/bin/env python3
"""Final sound pass and delivery QC for a rendered clip or episode. Free; the picture is copied untouched.

    python3 $S/master_clip.py IN.mp4 OUT.mp4 [--target SECONDS] [--lufs -14.8] [--audio mix.wav]    # one fixed gain, 320k AAC, then QC
    python3 $S/master_clip.py --qc FILE.mp4 [--target SECONDS]     # QC only
    Add --size 1080x1920 for a vertical cut. --audio takes the sound from the mix itself rather than the render's compressed copy.
    --fps N sets the frame rate to check; otherwise show.json's, otherwise 25.

Spec: 1920×1080, the camera's frame rate, −14 LUFS ±1, true peak ≤ −1 dBTP, runtime within 0.5 s of target, no black ≥ 2 s, no frozen picture ≥ 12 s.
A fixed gain and nothing else: loudnorm says `linear=true` and silently turns dynamic when the peaks don't allow it, which QC can't see. If the peaks
don't fit here, this stops and says so.
stdout: one PASS/FAIL line per check, then OK:/FAIL:. This measures sound; it cannot hear it. A person still listens once.
"""
import json, re, subprocess, sys
import studio

SIZE = tuple(int(x) for x in sys.argv[sys.argv.index('--size') + 1].split('x')) if '--size' in sys.argv else (1920, 1080)
FPS = float(sys.argv[sys.argv.index('--fps') + 1]) if '--fps' in sys.argv else studio.load_show(required=False)['fps']


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def measure(f):
    er = run(['ffmpeg', '-nostats', '-i', f, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
    s = er[er.rfind('Summary:'):]
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', s).group(1)), float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s).group(1))


def master(src, out, lufs=-14.0, audio=None):
    i, tp = measure(audio or src)
    gain = lufs - i
    if tp + gain > -1.2:
        sys.exit(f'FAIL: {gain:+.2f} dB to reach {lufs} LUFS puts the peaks at {tp + gain:.2f} dBTP, over -1.2. Hold the peaks lower in the mix or aim quieter.')
    streams = ['-i', src, '-i', audio, '-map', '0:v', '-map', '1:a', '-shortest'] if audio else ['-i', src]
    r = run(['ffmpeg', '-y', '-v', 'error', *streams, '-c:v', 'copy', '-af', f'volume={gain:.3f}dB', '-ar', '48000', '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', out])
    if r.returncode:
        sys.exit('FAIL: ' + r.stderr[-400:])
    print(f'mix before master: {i} LUFS, {tp} dBTP · fixed gain {gain:+.2f} dB')


def qc(f, target=None):
    p = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', f]).stdout)
    v = next(s for s in p['streams'] if s['codec_type'] == 'video')
    a = [s for s in p['streams'] if s['codec_type'] == 'audio']
    dur = float(p['format']['duration'])
    num, den = map(int, v['r_frame_rate'].split('/'))
    checks = [(f'picture {SIZE[0]}×{SIZE[1]}', (v['width'], v['height']) == SIZE, f"{v['width']}×{v['height']}"),
              (f'{FPS:g} fps', abs(num / den - FPS) < 0.01, f'{num / den:.3f}'),
              ('audio present', bool(a), a[0]['codec_name'] if a else 'none')]
    er = run(['ffmpeg', '-nostats', '-i', f, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
    s = er[er.rfind('Summary:'):]
    lufs = float(re.search(r'I:\s+(-?[\d.]+) LUFS', s).group(1))
    tp = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s).group(1))
    checks += [('loudness −14 LUFS ±1', abs(lufs + 14) <= 1, f'{lufs:.1f} LUFS'), ('true peak ≤ −1 dBTP', tp <= -1.0, f'{tp:.1f} dBTP')]
    if target:
        checks.append((f'runtime {target}s ±0.5', abs(dur - target) <= .5, f'{dur:.2f}s'))
    bl = run(['ffmpeg', '-nostats', '-i', f, '-vf', 'blackdetect=d=2:pix_th=0.05', '-an', '-f', 'null', '-']).stderr
    blacks = re.findall(r'black_start:([\d.]+)', bl)
    checks.append(('no black ≥ 2 s', not blacks, ', '.join(blacks) or 'none'))
    fr = run(['ffmpeg', '-nostats', '-i', f, '-vf', 'freezedetect=n=0.0005:d=12', '-an', '-f', 'null', '-']).stderr
    frozen = re.findall(r'freeze_start: ([\d.]+)', fr)
    checks.append(('no frozen picture ≥ 12 s', not frozen, ', '.join(frozen) or 'none'))
    ok = True
    for name, good, val in checks:
        print(f"{'PASS' if good else 'FAIL'}  {name}: {val}")
        ok &= good
    print(f"{'OK' if ok else 'FAIL'}: {sum(g for _, g, _ in checks)}/{len(checks)} checks · {f}")
    return ok


def main():
    a = sys.argv[1:]
    target = float(a[a.index('--target') + 1]) if '--target' in a else None
    if a[0] == '--qc':
        return 0 if qc(a[1], target) else 1
    master(a[0], a[1], float(a[a.index('--lufs') + 1]) if '--lufs' in a else -14.0, a[a.index('--audio') + 1] if '--audio' in a else None)
    return 0 if qc(a[1], target) else 1


if __name__ == '__main__':
    sys.exit(main())

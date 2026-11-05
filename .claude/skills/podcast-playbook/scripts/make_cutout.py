#!/usr/bin/env python3
"""Edit + matte → transparent VP9 with only the people in it. Free and local; needs rvm_matte.py to have run on the uncut recording.

    python3 $S/make_cutout.py episodes/EPxx/matte episodes/EPxx/full                  # build/cutout.webm and build/cutout_cold.webm
    python3 $S/make_cutout.py episodes/EPxx/matte episodes/EPxx/clips/Cnn_name        # build/cutout.webm

The matte is cut with exactly the frames of the edit. A clip's edit is matched to the recording picture by picture.
Beside each cutout: .occ.npy, how much person is in each 8 px column (so a shot can clear the other speaker with a line that really is
empty), and .area.npy, how much of each speaker there is in every frame (so a dropout can be found without watching the whole film).
"""
import json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import studio

MATTE, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
SHOW = studio.load_show(ROOT)
W, H, FPS = 1920, 1080, SHOW['fps']
WORKERS, THREADS = 5, 3
FILTER = ("[1:v]format=gray,lut=y='clip((val-14)*255/226\\,0\\,255)'[m];"
          "[0:v]unsharp=5:5:0.7:5:5:0,eq=contrast=1.08:saturation=1.12,format=yuv420p[v];[v][m]alphamerge,format=yuva420p")
edges = [int(x) for x in (MATTE / 'parts.txt').read_text().split()]


def read_range(a, b):
    """Source frames a … b−1 of the matte, across parts if need be."""
    for i in range(len(edges) - 1):
        lo, hi = max(a, edges[i]), min(b, edges[i + 1])
        if lo >= hi:
            continue
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{(lo - edges[i]) / FPS:.3f}', '-i', str(MATTE / f'p{i}.mkv'), '-frames:v', str(hi - lo), '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
        for k in range(hi - lo):
            buf = p.stdout.read(W * H)
            if len(buf) < W * H:
                sys.exit(f'FAIL: matte part {i}: wanted {hi - lo} frames from {lo}, got {k}')
            yield buf
        p.stdout.close()
        p.wait()


def frames(ranges):
    for a, b in ranges:
        yield from read_range(a, b)


def small(path, ss=None, n=None):
    cmd = ['ffmpeg', '-v', 'error'] + (['-ss', f'{ss:.3f}'] if ss is not None else []) + ['-i', str(path)] + (['-frames:v', str(n)] if n else []) + ['-vf', 'scale=160:90:flags=area', '-f', 'rawvideo', '-pix_fmt', 'gray', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.uint8).reshape(-1, 90, 160).astype(np.float32)


def match_clip(edit, first_guess, source):
    """Which recording frame each edit frame came from, by comparing pictures."""
    e = small(edit)
    base = max(0, first_guess - 75)
    s = small(source, base / FPS, len(e) + 500)
    out, cur = [], None
    for f in e:
        if cur is not None and cur + 1 < len(s) and np.abs(f - s[cur + 1]).mean() < 1.0:
            cur += 1
        else:
            lo = 0 if cur is None else cur
            errs = np.abs(s[lo:] - f).mean((1, 2))
            cur = lo + int(np.argmin(errs))
        out.append(base + cur)
    return out


def split(ranges, k):
    """The ranges in k groups of nearly equal frames, cutting a range in two where need be."""
    size = -(-sum(b - a for a, b in ranges) // k)
    parts, cur, room = [], [], size
    for a, b in ranges:
        while a < b:
            take = min(b - a, room)
            cur.append((a, a + take))
            a += take
            room -= take
            if not room:
                parts.append(cur)
                cur, room = [], size
    return parts + ([cur] if cur else [])


def encode_part(cut, ranges, first, tmp):
    """Edit frames from `first`, for as many as the ranges hold, as one VP9 file. Returns the two per-frame tables."""
    want = sum(b - a for a, b in ranges)
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-ss', f'{first / FPS:.3f}', '-i', str(cut), '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-filter_complex', FILTER, '-frames:v', str(want), '-c:v', 'libvpx-vp9', '-crf', '24', '-b:v', '0', '-row-mt', '1', '-tile-columns', '2', '-threads', str(THREADS),
                            '-deadline', 'good', '-cpu-used', '5', '-auto-alt-ref', '0', '-g', '50', '-an', str(tmp)], stdin=subprocess.PIPE)
    occ, area, n = [], [], 0
    split_x = SHOW['body_split_x']
    for buf in frames(ranges):
        enc.stdin.write(buf)
        m = np.frombuffer(buf, np.uint8).reshape(H, W) > 128
        occ.append(np.add.reduceat(m[:900].sum(0), np.arange(0, W, 8)).clip(0, 65535).astype(np.uint16))
        area.append((int(m[:, :split_x].sum()), int(m[:, split_x:].sum())))
        n += 1
    enc.stdin.close()
    if enc.wait():
        sys.exit(f'FAIL {tmp}: the encoder stopped')
    if n != want:
        sys.exit(f'FAIL {tmp}: {n} frames, expected {want}')
    print(f'  {tmp.name}: {n} frames · {time.strftime("%H:%M")}', flush=True)
    return occ, area


def packets(f):
    return int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', str(f)], capture_output=True, text=True).stdout.strip().rstrip(','))


def encode(cut, ranges, out):
    """Five encoders side by side, joined at keyframes: about 29 fps here against 16 for one given all 12 threads. More encoders gained nothing.
    The joins were checked frame by frame: picture and alpha line up at offset 0 and alpha keeps its error across them."""
    n_expected = sum(b - a for a, b in ranges)
    t0 = time.time()
    groups = split(ranges, WORKERS if n_expected >= 300 else 1)
    firsts = [sum(b - a for g in groups[:i] for a, b in g) for i in range(len(groups))]
    tmps = [out.with_name(f'_{out.stem}.{i}.webm') for i in range(len(groups))]    # projects hard-link the cutout: writing in place would break them all if this stopped
    with ThreadPoolExecutor(len(groups)) as ex:
        res = list(ex.map(encode_part, [cut] * len(groups), groups, firsts, tmps))
    lst, joined = out.with_name(f'_{out.stem}.txt'), out.with_name(f'_{out.name}')
    lst.write_text(''.join(f"file '{t.resolve()}'\n" for t in tmps))
    r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(joined)], capture_output=True, text=True)
    got = packets(joined) if not r.returncode else -1
    if got != n_expected:
        sys.exit(f'FAIL {out}: joined {got} frames, expected {n_expected}. {r.stderr[-300:]}')
    joined.replace(out)
    lst.unlink()
    for t in tmps:
        t.unlink()
    np.save(out.with_suffix('.occ.npy'), np.array([x for o, _ in res for x in o]))
    np.save(out.with_suffix('.area.npy'), np.array([x for _, a in res for x in a], np.int32))
    print(f'OK {out}: {got} frames in {(time.time() - t0) / 60:.1f} min, {len(groups)} encoders', flush=True)


B = ROOT / 'build'
if (B / 'edl.json').exists():
    d = json.loads((B / 'edl.json').read_text(encoding='utf-8'))
    if d['cold']:
        encode(B / 'cold.mp4', [(round(p * FPS), round(q * FPS)) for p, q in d['cold']], B / 'cutout_cold.webm')
    encode(B / 'body.mp4', [(round(p * FPS), round(q * FPS)) for c in d['chapters'] for p, q in c['slices']], B / 'cutout.webm')
else:
    d = json.loads((ROOT / 'edl.json').read_text(encoding='utf-8'))
    src = match_clip(B / 'edit.mp4', round(d['work_offset'] * FPS), SHOW['root'] / d['source'])
    (B / 'frames.json').write_text(json.dumps(src))
    jumps = sum(1 for x, y in zip(src, src[1:]) if y != x + 1)
    print(f'clip matched: {len(src)} frames, {jumps} jumps', flush=True)
    ranges, a = [], src[0]
    for x, y in zip(src, src[1:] + [None]):
        if y != x + 1:
            ranges.append((a, x + 1))
            a = y
    encode(B / 'edit.mp4', ranges, B / 'cutout.webm')

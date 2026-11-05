#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["onnxruntime==1.22.1", "numpy<2"]
# ///
"""Person matte for a whole recording, with Robust Video Matting on this Mac. Free. About 50 min for 30 min of footage.

    uv run $S/rvm_matte.py 1080p/recording.mp4 episodes/EPxx/matte

Always run it on the ORIGINAL, uncut recording. The network remembers previous frames, which is what holds a torso solid when a
hand crosses it, but straight after a jump cut it has the wrong memory and the body goes see-through for a second. make_cutout.py
then cuts the matte with the same frames as the edit.

Run it through uv, as above: onnxruntime is pinned on purpose. 1.24.3 leaks 41 MB a frame on this Mac (measured, whatever the session
options), which filled the RAM and about 80 GB of swap and took the machine down. 1.22.1 holds 340 MB and its alpha matches to 1/255.
Writes lossless two-minute parts (p0.mkv …), so a crash costs minutes. A finished part is not redone: re-run the same command to resume.

The model (models/rvm_mobilenetv3_fp32.onnx) is Peter Lin's RobustVideoMatting, GPL-3.0.
"""
import resource, subprocess, sys, time
from pathlib import Path
import numpy as np

def _probe(src):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=width,height,r_frame_rate', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip().split(',')
    num, den = out[2].split('/')
    return int(out[0]), int(out[1]), int(num) / int(den)


W, H, FPS = _probe(sys.argv[2] if sys.argv[1] == '--part' else sys.argv[1])
if (W, H) != (1920, 1080):
    sys.exit(f'FAIL: {W}x{H}: this is tuned for 1920x1080. Scale the recording at ingest first.')
DS, WORKERS, WARM, CHUNK = .375, 3, 125, 3000
MAX_RSS = 4 * 1024 ** 3    # a worker that grows past this stops itself, rather than take the machine down
MODEL = Path(__file__).resolve().parent / 'models/rvm_mobilenetv3_fp32.onnx'
MODEL_URL = 'https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx'
MODEL_SHA256 = '88d4531297118f595bf2fd60f6f566aec2e559393802d1f436c380f0cbbd2828'


def fetch_model():
    """The weights are GPL-3.0 and 15 MB, so they stay out of the repo and arrive on first use, checked against a pinned hash: a download can also be an error page."""
    if MODEL.exists():
        return
    import hashlib, urllib.request
    MODEL.parent.mkdir(exist_ok=True)
    tmp = MODEL.with_suffix('.part')
    print(f'fetching the matting model (15 MB) from {MODEL_URL}', flush=True)
    urllib.request.urlretrieve(MODEL_URL, tmp)
    got = hashlib.sha256(tmp.read_bytes()).hexdigest()
    if got != MODEL_SHA256:
        tmp.unlink()
        sys.exit(f'FAIL: the downloaded model is not the expected file ({got[:12]}…); try again, or put it at {MODEL}')
    tmp.rename(MODEL)


def worker(src, out, a, b):
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    sess = ort.InferenceSession(str(MODEL), so, providers=['CPUExecutionProvider'])
    start = max(0, a - WARM)
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{start / FPS:.3f}', '-i', src, '-frames:v', str(b - start), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    tmp = out.with_suffix('.part.mkv')
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', '4', str(tmp)], stdin=subprocess.PIPE)
    rec = [np.zeros((1, 1, 1, 1), np.float32) for _ in range(4)]
    ds = np.array([DS], np.float32)
    n, t0 = start, time.time()
    while n < b:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        src_ = np.frombuffer(buf, np.uint8).reshape(H, W, 3).transpose(2, 0, 1)[None].astype(np.float32) / 255
        pha, *rec = sess.run(['pha', 'r1o', 'r2o', 'r3o', 'r4o'], {'src': src_, 'r1i': rec[0], 'r2i': rec[1], 'r3i': rec[2], 'r4i': rec[3], 'downsample_ratio': ds})
        if n >= a:
            enc.stdin.write((np.clip(pha[0, 0], 0, 1) * 255).astype(np.uint8).tobytes())
        n += 1
        if (n - start) % 500 == 0:
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > MAX_RSS:
                sys.exit(f'FAIL {out.stem}: memory past {MAX_RSS // 1024 ** 3} GB at frame {n}: is onnxruntime pinned? Run through uv.')
    enc.stdin.close()
    if enc.wait():
        sys.exit(f'FAIL {out.stem}: the encoder stopped (disk full?)')
    if n != b:
        sys.exit(f'FAIL {out.stem}: stopped at {n}, expected {b}')
    tmp.rename(out)
    print(f'OK {out.stem}: {b - a} frames · {(n - start) / (time.time() - t0):.1f} fps · {time.strftime("%H:%M")}', flush=True)


if sys.argv[1] == '--part':
    worker(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
    sys.exit(0)
src, out = sys.argv[1], Path(sys.argv[2])
fetch_model()
out.mkdir(parents=True, exist_ok=True)
total = int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.split(',')[0])
edges = list(range(0, total, CHUNK)) + [total]
layout = ' '.join(map(str, edges))
stored = out / 'parts.txt'
if stored.exists() and stored.read_text() != layout and any('.part' not in p.name for p in out.glob('p*.mkv')):
    sys.exit(f'FAIL: finished parts in {out} were cut to another layout; move them away first')
stored.write_text(layout)
for p in out.glob('*.part.mkv'):    # a stopped run's unfinished part can't be continued
    p.unlink()
todo = [i for i in range(len(edges) - 1) if not (out / f'p{i}.mkv').exists()]
print(f'{total} frames · {len(todo)} of {len(edges) - 1} parts to do · {time.strftime("%H:%M")}', flush=True)
running, failed = [], 0
while todo or running:
    while todo and len(running) < WORKERS:
        i = todo.pop(0)
        running.append(subprocess.Popen([sys.executable, __file__, '--part', src, str(out / f'p{i}.mkv'), str(edges[i]), str(edges[i + 1])]))
    time.sleep(1)
    failed += sum(1 for p in running if p.poll())
    running = [p for p in running if p.poll() is None]
print('OK: matte done' if not failed else f'FAIL: {failed} part(s) stopped; re-run to do just those', flush=True)
sys.exit(1 if failed else 0)

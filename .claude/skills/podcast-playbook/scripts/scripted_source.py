#!/usr/bin/env python3
"""A show with no recording: turn a script and its voice takes into the "recording" the rest of the pipeline cuts. Free and local.

    python3 scripted_source.py CLIP_FOLDER [--tempo 1.0]

Reads   script.json          [{n, who, t}], who is H (left of frame) or G (right)
        audio/takes/NN.mp3   one take a line, from el.py tts or your own microphone (.wav works too)
        paper.json           "source": where the video goes
        hosts.json           optional: drawn hosts. Without it the video is plain paper, for the audio-only route
Writes  audio/lines/*.wav · audio/boost.wav · audio/isolated.mp3 · audio/scribe.json · build/pass1.json · build/faces.jsonl · build/lines.json · the source video

hosts.json, paths relative to the show:
    {"background": "assets/set.png", "front": "assets/set_front.png", "ground": "#0A1A33", "live": "tools/deck.py",
     "H": {"base": "assets/cast/a.png", "mouth": "assets/cast/a_mouth.png", "blink": "assets/cast/a_blink.png", "scale": 0.527, "at": [-110, 100],
           "face": [506, 395, 450, 500], "holes": [[703, 181]], "erase": [[1472, 1300, 1700, 1600]], "hair": [1210, 860, 1400]},
     "G": {...}}

- base, mouth, blink are the same drawing, pixel-aligned, on a plain ground. Only what differs from base is used.
- at is where the top-left of the scaled drawing sits. face is [x, y, width, height] for the shot planner, in frame pixels: H must stay left of 763 and G right of 1157, or a close-up catches a sliver of the other host.
- holes: the middles of ground showing through the hair, in the drawing's own pixels. A flood from the edges can't reach them, and against a dark set they show as white patches.
- hair: [above y, left of x, right of x]: every enclosed pale patch there counts as a hole. Keep the face out of it: a rule that was too wide once cut the white out of an eye.
- erase: rectangles of the drawing to remove.
- live: a Python file with optional behind(frame, step) and front(frame, step), each painting on a PIL image, for anything on the set that moves.

The ground is never flooded from the bottom edge, because a white shirt touching it would go too. The video gets a new drawing about six times a second, the Animatic's own rate.
stdout ends with OK: or FAIL:. Mouths flap on loudness: this is not lip sync.
"""
import argparse, importlib.util, json, re, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ni
import studio

SR, W, H = 48000, 1920, 1080
LEAD, GAP, TAIL = .2, .22, 1.0     # a gap of .22 s stays as it is: full_edit.py only shortens pauses over .24 s
TRIM = 'silenceremove=start_periods=1:start_threshold=-48dB:detection=peak,areverse,silenceremove=start_periods=1:start_threshold=-48dB:detection=peak,areverse'
BOB = [0, -2, -4, -2]


def read(f):
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', str(f), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout, np.float32)


def lufs(files):
    args = sum((['-i', str(f)] for f in files), [])
    er = subprocess.run(['ffmpeg', '-nostats', *args, '-filter_complex', ''.join(f'[{i}:a]' for i in range(len(files))) + f'concat=n={len(files)}:v=0:a=1,ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', er)[-1])


def take(C, n):
    return next((f for f in (C / f'audio/takes/{n:02d}{x}' for x in ('.mp3', '.wav', '.m4a')) if f.exists()), None)


def make_lines(C, script, tempo):
    """One fixed gain per host, so each voice keeps its own dynamics and the two sit level with each other."""
    gone = [l['n'] for l in script if not take(C, l['n'])]
    if gone:
        sys.exit(f'FAIL: no take for lines {gone} in {C}/audio/takes')
    out = C / 'audio/lines'
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob('*.wav'):
        f.unlink()
    gain = {who: -18 - lufs([take(C, l['n']) for l in script if l['who'] == who]) for who in {l['who'] for l in script}}
    for l in script:
        af = f"{TRIM},atempo={tempo:.4f},volume={gain[l['who']]:.2f}dB"
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(take(C, l['n'])), '-af', af, '-ac', '1', '-ar', str(SR), '-c:a', 'pcm_s16le', str(out / f"{l['n']:02d}.wav")], check=True)


def make_voice(C, script):
    sig, t, lines = [np.zeros(int(LEAD * SR), np.float32)], LEAD, []
    for l in script:
        x = read(C / f"audio/lines/{l['n']:02d}.wav")
        lines.append({**l, 'a': round(t, 3), 'b': round(t + len(x) / SR, 3)})
        sig += [x, np.zeros(int(GAP * SR), np.float32)]
        t = lines[-1]['b'] + GAP
    sig.append(np.zeros(int(TAIL * SR), np.float32))
    voice = np.concatenate(sig)
    (C / 'build').mkdir(exist_ok=True)
    (C / 'build/lines.json').write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding='utf-8')
    raw = C / 'audio/_v.raw'
    voice.tofile(raw)
    for out, codec in ((C / 'audio/boost.wav', ['-c:a', 'pcm_s16le']), (C / 'audio/isolated.mp3', ['-c:a', 'libmp3lame', '-q:a', '0'])):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(raw), *codec, str(out)], check=True)
    raw.unlink()
    # the shape the cut reads. Thai runs have no spaces, so each character gets its own slice of the line. An anchor in paper.json must leave out spaces, because the cut's text has none.
    words = []
    for l in lines:
        sp = 'speaker_0' if l['who'] == 'H' else 'speaker_1'
        st = (l['b'] - l['a']) / max(len(l['t']), 1)
        for k, ch in enumerate(l['t']):
            words.append({'text': ch, 'start': round(l['a'] + k * st, 3), 'end': round(l['a'] + (k + 1) * st, 3), 'type': 'spacing' if ch.isspace() else 'word', 'speaker_id': sp})
    (C / 'audio/scribe.json').write_text(json.dumps({'text': ' '.join(l['t'] for l in lines), 'words': words}, ensure_ascii=False), encoding='utf-8')
    (C / 'build/pass1.json').write_text(json.dumps([{'a': l['a'], 'b': l['b'], 'who': l['who'], 't': l['t']} for l in lines], ensure_ascii=False, indent=1), encoding='utf-8')
    return voice, lines


def matte(path, spec):
    im = np.asarray(Image.open(path).convert('RGB'), np.int32)
    bg = np.median(np.concatenate([im[:40, :40].reshape(-1, 3), im[:40, -40:].reshape(-1, 3)]), axis=0)
    d = np.sqrt(((im - bg) ** 2).sum(2))
    lab, n = ni.label(d < 24)
    edge = set(np.unique(lab[0])) | set(np.unique(lab[:, 0])) | set(np.unique(lab[:, -1]))
    holes, hair = spec.get('holes', []), spec.get('hair')
    if holes or hair:
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            if len(xs) > 30 and (any(abs(xs.mean() - hx) < 14 and abs(ys.mean() - hy) < 14 for hx, hy in holes) or (hair and ys.mean() < hair[0] and (xs.mean() < hair[1] or xs.mean() > hair[2]))):
                edge.add(i)
    edge.discard(0)
    m = ni.binary_dilation(np.isin(lab, list(edge)), iterations=3)      # past the pale fringe, which would show against a dark set
    for x0, y0, x1, y1 in spec.get('erase', []):
        m[y0:y1, x0:x1] = True
    return Image.fromarray((ni.gaussian_filter((~m).astype(np.float32), 1.0) * 255).astype(np.uint8))


def delta(base, other):
    d = np.abs(np.asarray(base.convert('RGB'), np.int32) - np.asarray(other.convert('RGB'), np.int32)).sum(2) > 24
    d = ni.binary_dilation(ni.binary_opening(d, iterations=1), iterations=8)
    return Image.fromarray((d * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))


def host_states(root, spec):
    src = Image.open(root / spec['base']).convert('RGB')
    al = matte(root / spec['base'], spec)
    op = Image.open(root / spec['mouth']).convert('RGB') if spec.get('mouth') else None
    bl = Image.open(root / spec['blink']).convert('RGB') if spec.get('blink') else None
    o = src.copy()
    if op:
        o.paste(op, (0, 0), delta(src, op))
    b, ob = src.copy(), o.copy()
    if bl:
        bm = delta(src, bl)
        b.paste(bl, (0, 0), bm)
        ob.paste(bl, (0, 0), bm)
    size = (round(src.width * spec['scale']), round(src.height * spec['scale']))
    a = al.resize(size, Image.LANCZOS)
    return {k: (v.resize(size, Image.LANCZOS), a) for k, v in {(0, 0): src, (1, 0): o, (0, 1): b, (1, 1): ob}.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clip')
    ap.add_argument('--tempo', type=float, default=1.0, help='keep it near 1: measure with full_edit.py first, because it already shortens the long pauses')
    x = ap.parse_args()
    C = Path(x.clip).resolve()
    show = studio.load_show(C)
    root, fps = show['root'], show['fps']
    step = max(1, round(fps / 6))
    paper = json.loads((C / 'paper.json').read_text(encoding='utf-8'))
    if not paper.get('source'):
        sys.exit('FAIL: paper.json needs "source": where the video goes')
    script = json.loads((C / 'script.json').read_text(encoding='utf-8'))
    make_lines(C, script, x.tempo)
    voice, lines = make_voice(C, script)
    total = len(voice) / SR
    nframes = int(total * fps)
    source = root / paper['source']
    source.parent.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((C / 'hosts.json').read_text(encoding='utf-8')) if (C / 'hosts.json').exists() else None

    ground = Image.new('RGB', (W, H), (cfg or {}).get('ground', show.get('looks', {}).get('animatic', {}).get('paper', '#F6F7F5')))
    if cfg and cfg.get('background'):
        ground = Image.open(root / cfg['background']).convert('RGB').resize((W, H))
    front = Image.open(root / cfg['front']).convert('RGBA') if cfg and cfg.get('front') else None
    live = None
    if cfg and cfg.get('live'):
        spec = importlib.util.spec_from_file_location('set_live', root / cfg['live'])
        live = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(live)
    who_list = [w for w in 'HG' if cfg and w in cfg]
    sprites = {w: host_states(root, cfg[w]) for w in who_list}

    env = np.array([np.sqrt(np.mean(voice[int(i * SR / fps):int((i + step) * SR / fps)] ** 2) + 1e-12) for i in range(0, nframes, step)])
    thr = max(float(np.percentile(env[env > 1e-4], 25)) * .55, 1e-3)
    rng = np.random.default_rng(11)

    def blinks(n):
        out, s = set(), int(rng.integers(6, 18))
        while s < n:
            out.add(s)
            s += int(rng.integers(14, 32))
        return out
    blink = {w: blinks(len(env)) for w in who_list}
    who_at = lambda sec: next((l['who'] for l in lines if l['a'] - .03 <= sec < l['b'] + .03), None)

    ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-i', str(C / 'audio/boost.wav'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', '-g', str(fps), '-bf', '0', '-c:a', 'aac', '-b:a', '256k', '-shortest', str(source)], stdin=subprocess.PIPE)
    with (C / 'build/faces.jsonl').open('w') as faces:
        for s in range(len(env)):
            sec = s * step / fps
            who = who_at(sec + .08)
            talking = who is not None and env[s] > thr
            frame = ground.copy()
            if live and hasattr(live, 'behind'):
                live.behind(frame, s)
            mouth = {}
            for w in who_list:
                m = 1 if (talking and who == w and s % 2 == 0) else 0
                dy = BOB[(s // 2) % 4] if (who == w and talking) else 0
                rgb, al = sprites[w][(m, 1 if s in blink[w] else 0)]
                frame.paste(rgb, (cfg[w]['at'][0], cfg[w]['at'][1] + dy), al)
                mouth[w] = .12 * m
            if front:
                frame.paste(front, (0, 0), front)
            if live and hasattr(live, 'front'):
                live.front(frame, s)
            raw = frame.tobytes()
            faces.write(json.dumps({'t': round(sec, 3), 'f': [cfg[w]['face'] + [mouth[w]] for w in who_list]}) + '\n')
            for k in range(step):
                if s * step + k < nframes:
                    ff.stdin.write(raw)
    ff.stdin.close()
    ff.wait()
    speech = sum(l['b'] - l['a'] for l in lines)
    print(f'OK: {len(lines)} lines · speech {speech:.1f} s · source {total:.1f} s, {nframes} frames. Run full_edit.py for the real length: it shortens the long pauses.')


if __name__ == '__main__':
    main()

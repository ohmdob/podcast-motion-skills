#!/usr/bin/env python3
"""Pictures through the Codex CLI's built-in image tool, for when Ideogram isn't available. It takes the same shots.json as ideogram.py.

    python3 codex_image.py --batch shots.json          # quotes, spends nothing
    python3 codex_image.py --batch shots.json --yes    # one Codex run per missing image, one at a time

Use it only after asking the producer: no Ideogram means asking which alternative they want, not choosing one. It uses whatever account Codex is signed in with, and that
usage counts against that plan, so its ledger rows carry no credit figure. Check the first picture by eye before running a long batch.

Codex's image tool has no size control and saves to its own folder, so this tells Codex where to copy the result, then crops the picture to the shot's shape. Left uncropped,
a 3:2 picture would be stretched by the build, which resizes every still to 16:9. A file that already exists is skipped. A failed run is reported and never retried, since it may have
used quota. stdout ends with OK: · FAIL: · QUOTE:
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path
from PIL import Image
import studio

SERVICE = 'Codex imagegen'
TIMEOUT = 600
SHAPES = {'16:9': 'wide landscape, 16:9', '9:16': 'tall portrait, 9:16', '1:1': 'square'}


def shape_of(item):
    """(w, h) of the shot's shape, from an Ideogram-style size such as '(2K) 2560x1440 (16:9)', or from aspect. Defaults to 16:9, as ideogram.py does."""
    m = re.search(r'(\d+):(\d+)', str(item.get('aspect') or item.get('size') or '16:9'))
    return (int(m[1]), int(m[2])) if m else (16, 9)


def crop_to(path, w, h):
    im = Image.open(path)
    im.load()
    iw, ih = im.size
    if abs(iw / ih - w / h) < .01:
        return iw, ih
    if iw / ih > w / h:
        nw = round(ih * w / h)
        box = ((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih)
    else:
        nh = round(iw * h / w)
        box = (0, (ih - nh) // 2, iw, (ih - nh) // 2 + nh)
    im.crop(box).save(path)
    return box[2] - box[0], box[3] - box[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--batch', required=True)
    ap.add_argument('--yes', action='store_true', help='run Codex; without it this only quotes')
    ap.add_argument('--force', action='store_true', help='replace outputs that already exist (the old ones go to old/)')
    x = ap.parse_args()
    root = studio.load_show()['root']     # no show.json, no ledger, no spending
    codex = shutil.which('codex')
    items = json.loads(Path(x.batch).read_text(encoding='utf-8'))
    for it in items:
        if not it.get('out') or not it.get('prompt'):
            sys.exit(f'FAIL: every item needs out and prompt: {str(it)[:120]}')
    todo = [i for i in items if x.force or not (root / i['out']).exists()]
    if not todo:
        print(f'OK: all {len(items)} already exist, nothing spent')
        return 0
    if not x.yes:
        print(f"QUOTE: {len(todo)} of {len(items)} images through Codex, one run each, counted against the plan Codex is signed in with; it reports no cost. {'' if codex else 'The codex command was not found. '}Nothing spent; add --yes once the producer has approved.")
        return studio.EXIT_QUOTE
    if not codex:
        sys.exit('FAIL: the codex command was not found. Ask the producer for another way to get these pictures.')
    good = 0
    for it in todo:
        out = root / it['out']
        w, h = shape_of(it)
        label = f"{Path(it['out']).name} · \"{it['prompt'][:60]}\""
        tmp = out.with_name(f'_{out.stem}.codex.png')
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.unlink(missing_ok=True)
        shape = SHAPES.get(f'{w}:{h}', f'{w}:{h}')
        ask = (f'Use the imagegen skill with the built-in image_gen tool, not the CLI fallback, to generate exactly one image. Shape: {shape}.\n'
               f'Image prompt:\n{it["prompt"]}\n\nThen copy the generated image to this exact path: {tmp}\n'
               'Do nothing else: change no other file and run no other command.')
        try:
            r = subprocess.run([codex, 'exec', '--skip-git-repo-check', '-s', 'workspace-write', '-C', str(root), ask], capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            studio.ledger(root, SERVICE, label, 'plan', 'unknown: timed out')
            print(f'FAIL: {out.name}: Codex ran past {TIMEOUT // 60} minutes. It may have used quota. Not retried.')
            continue
        if r.returncode or not tmp.exists():
            studio.ledger(root, SERVICE, label, 'plan', f'failed: exit {r.returncode}')
            tail = studio.redact((r.stderr or r.stdout)[-300:])
            tmp.unlink(missing_ok=True)
            print(f'FAIL: {out.name}: Codex gave no picture (exit {r.returncode}). It may have used quota. Not retried. {tail}')
            continue
        try:
            got = crop_to(tmp, w, h)
        except OSError as e:
            studio.ledger(root, SERVICE, label, 'plan', 'failed: not an image')
            tmp.unlink(missing_ok=True)
            print(f'FAIL: {out.name}: what came back is not a picture ({e}).')
            continue
        studio.keep_old(out)
        tmp.replace(out)
        studio.ledger(root, SERVICE, label, 'plan', 'ok')
        print(f'{out.name}: {got[0]}×{got[1]}', file=sys.stderr, flush=True)
        good += 1
    print(f"{'OK' if good == len(todo) else 'FAIL'}: {good}/{len(todo)} images through Codex. Look at them: a picture with any words in it goes back, because type stays live.")
    return 0 if good == len(todo) else 1


if __name__ == '__main__':
    sys.exit(main())

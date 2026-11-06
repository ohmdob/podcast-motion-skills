#!/usr/bin/env python3
"""Shared pieces for looks that change what is behind the speaker (Comic, Evidence Board, Chat Feed) or show the card's picture in colour (Bento Grid too).

    import card_stage as cs
    cs.need_cutout(st)                        # in prepare(): the speakers, cut out, for a look that paints its own ground
    h, js = cs.hosts(st, pfx, dur, start, shots)  # in chapter(): the cutout on the same camera moves as the footage, so the shot plan holds
    src = cs.picture(st, c)                   # the card's picture as assets/pics/<name>.jpg, in colour on white, or None

Not a look on its own. A look keeps its own palette, type and moves, and calls these.
"""
import importlib.util, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
import look_kit as kit

ANIMATIC = Path(__file__).resolve().parents[2] / 'podcast-motion-animatic' / 'scripts' / 'build.py'
_anim = None
PIC = {}


def _animatic():
    """The Animatic's picture finder and subject-centred crop, loaded under its own name so it never shadows the calling look's build.py."""
    global _anim
    if _anim is None:
        spec = importlib.util.spec_from_file_location('animatic_build', ANIMATIC)
        _anim = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_anim)
    return _anim


def need_cutout(st):
    src = st.bf.B_ / 'cutout.webm'
    if not src.exists():
        sys.exit('FAIL: no build/cutout.webm. This look puts the speakers on its own ground, so it needs the cutout: rvm_matte.py then make_cutout.py '
                 '(podcast-motion-pop-studio). For drawn hosts, make the matte from their own alpha instead: the person matte can lose a drawn head.')
    st.bf.relink(src, st.p / 'assets' / 'cutout.webm')


def hosts(st, pfx, dur, media_start, shots, style=''):
    """The speakers alone, on the footage's own camera, above the look's ground."""
    ms = f' data-media-start="{media_start}"' if media_start is not None else ''
    h_ = (f'<div class="cam" id="{pfx}k" style="z-index:3;{style}"><video id="{pfx}kv" class="clip" src="assets/cutout.webm" data-start="0" data-duration="{dur}"{ms} '
          f'data-track-index="1" muted playsinline data-layout-allow-occlusion></video></div>')
    return h_, st.camera(shots, f'#{pfx}k')


def prepare_pictures(st, size=(1200, 900)):
    """Every picture a card names, fitted on its subject and balanced to a white ground, so it sits on any card with no grey box. Free and local."""
    a = _animatic()
    out = st.p / 'assets' / 'pics'
    out.mkdir(parents=True, exist_ok=True)
    PIC.clear()
    missing = set()
    alias = st.paper.get('aliases', {})
    for o in st.bf.chs:
        for c in o.cards:
            name = c['opts'].get('panel') or c['opts'].get('still') or c['opts'].get('obj')
            name = alias.get(name, name)
            if not name or name in PIC:
                continue
            f = a.source_of(st, name)
            if not f:
                missing.add(name)
                continue
            im = np.asarray(Image.open(f).convert('RGB'), np.float32)
            edge = np.concatenate([im[:12].reshape(-1, 3), im[-12:].reshape(-1, 3), im[:, :12].reshape(-1, 3), im[:, -12:].reshape(-1, 3)])
            ground = np.maximum(np.median(edge, axis=0), 1)
            if ground.min() > 150:
                im = np.clip(im * 255 / ground, 0, 255)
            im = np.where((im > 226).all(2, keepdims=True), 255, im).astype(np.uint8)
            im = Image.fromarray(tight(im, size))
            im.save(out / f'{name}.jpg', quality=90)
            PIC[name] = f'assets/pics/{name}.jpg'
    n = sum(1 for o in st.bf.chs for c in o.cards if picture(st, c))
    print(f'pictures: {n} cards with a picture' + (f'. Named but missing: {", ".join(sorted(missing))}' if missing else ''))


def tight(im, size, margin=.28):
    """Crop a picture on a white ground to its subject, with room around it, at the panel's shape: a small object in a big studio reads as an empty panel."""
    ink = (im < 232).any(2)
    ys, xs = np.nonzero(ink)
    if len(xs) < 200:
        return np.asarray(ImageOps.fit(Image.fromarray(im), size, Image.LANCZOS))
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    w, h = (x1 - x0) * (1 + 2 * margin), (y1 - y0) * (1 + 2 * margin)
    ar = size[0] / size[1]
    w, h = max(w, h * ar), max(h, w / ar)
    H_, W_ = im.shape[:2]
    if w >= W_ or h >= H_:
        return np.asarray(ImageOps.fit(Image.fromarray(im), size, Image.LANCZOS, centering=((x0 + x1) / 2 / W_, (y0 + y1) / 2 / H_)))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    l = int(min(max(cx - w / 2, 0), W_ - w))
    t = int(min(max(cy - h / 2, 0), H_ - h))
    return np.asarray(Image.fromarray(im).crop((l, t, l + int(w), t + int(h))).resize(size, Image.LANCZOS))


def picture(st, c):
    name = c['opts'].get('panel') or c['opts'].get('still') or c['opts'].get('obj')
    return PIC.get(st.paper.get('aliases', {}).get(name, name))


def away(c):
    """The card takes the side away from whoever is talking: (left x, width) of that half, with a margin."""
    return (1000, 880) if c['who'] == 'H' else (40, 880)


def lines(text, width, base, minimum, max_lines, font):
    size, ls = kit.fit_lines(text, width, base, minimum, max_lines, font)
    return size, ls, int(size * 1.32)


def block(id_, a, b, ls, x, y, size, ink, track=4, extra='', cls='ty'):
    """Several pre-broken lines as one element, so they move together."""
    body = '<br>'.join(kit.e(l) for l in ls)
    return (f'<div id="{id_}" class="clip {cls}" data-start="{a}" data-duration="{round(b - a, 3)}" data-track-index="{track}" '
            f'style="left:{round(x)}px;top:{round(y)}px;font-size:{size}px;color:{ink};line-height:1.32;{extra}"><span class="in">{body}</span></div>')

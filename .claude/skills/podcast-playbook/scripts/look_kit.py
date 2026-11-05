#!/usr/bin/env python3
"""The shared stage for looks built on real footage. A look only says what goes on top; this holds the cut, the camera, the clock, the mix and the test frames.

It runs build_full.py's planning (who is on screen, how each shot is framed, where the cards land) and builds nothing with it, so every look cuts the same way.
A look lives in its own skill as a small build.py with a palette and a few functions, and calls main() here. Works on an episode folder or a clip folder alike.

    16:9  the camera moves over the full frame.
    9:16  a footage band, recomposed rather than cropped to the full height, which would need a punch-in past what soft source footage can hold. The band keeps the other
          person out of shot, and the words get the space below it, inside the part of a phone screen the app leaves clear (y 168 to 1330).
"""
import argparse, html, json, math, os, re, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import studio

GRADE = html.escape(json.dumps({'preset': None, 'intensity': 1, 'adjust': {'exposure': 0, 'contrast': .07, 'highlights': 0, 'shadows': 0, 'whites': 0, 'blacks': 0, 'temperature': .03, 'tint': 0, 'vibrance': 0, 'saturation': .08},
                                'details': {'vignette': .1, 'vignetteMidpoint': .5, 'vignetteRoundness': 0, 'vignetteFeather': .65, 'grain': 0, 'grainSize': .25}}), quote=True)
SAFE_TOP, SAFE_BOTTOM = 168, 1330     # 9:16: words and faces stay in this band, because the app's own interface covers the rest

JS = '''
    const wipe = (s, t, d = .4) => tl.fromTo(s, { clipPath: "inset(-12% 100% -12% -2%)" }, { clipPath: "inset(-12% -2% -12% -2%)", duration: d, ease: "power2.out" }, t);
    const rise = (s, t) => tl.fromTo(s, { yPercent: 40, opacity: 0 }, { yPercent: 0, opacity: 1, duration: .34, ease: "power3.out" }, t);
    const slide = (s, t, dx) => tl.fromTo(s, { x: dx, opacity: 0 }, { x: 0, opacity: 1, duration: .34, ease: "power3.out" }, t);
    const bye = (s, t) => tl.to(s, { opacity: 0, duration: .15, ease: "power2.in" }, t - .16);
    const draw = (s, t, d = .4) => tl.fromTo(s, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: d, ease: "power1.inOut" }, t);
    '''
_fonts = {}


def e(x):
    return html.escape(str(x))


def measure(text, size, font, weight=800):
    """The real width at the real weight. A variable font measured at its default is about 8% narrower than the same words at 800, and that is a line running off its plate."""
    key = (font, weight)
    if key not in _fonts:
        f = ImageFont.truetype(str(studio.FONTS / font), 200)
        try:
            f.set_variation_by_axes([weight if a['name'] in (b'Weight', 'Weight') else a['default'] for a in f.get_variation_axes()])
        except OSError:      # not a variable font
            pass
        _fonts[key] = f
    return _fonts[key].getlength(text) * size / 200 * 1.02


def fit_lines(text, width, base, minimum, max_lines, font):
    """The largest size at which the text fits, measured with the real font, and its lines. A number stays with its unit, and lines break only at spaces, so write card text with spaces where a break can go."""
    text = re.sub(r'(\d) (?=\S)', '\\1\u00a0', str(text))
    size = base
    while True:
        lines, cur = [], ''
        for w in text.split(' '):
            t = (cur + ' ' + w).strip()
            if measure(t, size, font) > width and cur:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
        if len(lines) <= max_lines and all(measure(x, size, font) <= width for x in lines):
            return size, lines
        if size <= minimum:
            print(f'  does not fit at {minimum}px: {text}')
            return minimum, lines
        size = max(minimum, size - 4)


def parse_srt(path):
    out = []
    for m in re.finditer(r'(\d+):(\d\d):(\d\d)[,.](\d+)\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d+)[^\n]*\n(.*?)(?=\n\s*\n|\Z)', Path(path).read_text(encoding='utf-8-sig').replace('\r', ''), re.S):
        g = m.groups()
        sec = lambda h, mi, s, ms: int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, '0')[:3]) / 1000
        out.append({'s': round(sec(*g[:4]), 3), 'e': round(sec(*g[4:8]), 3), 't': ' '.join(g[8].split('\n')).strip()})
    return out


def engine(root):
    argv, sys.argv = sys.argv, ['build_full', str(root)]
    try:
        import build_full
    finally:
        sys.argv = argv
    return build_full


class Stage:
    def __init__(self, look, root, ratio, args):
        self.look, self.root, self.args = look, Path(root), args
        self.V = ratio == '9x16'
        self.bf = engine(root)
        self.W, self.H = (1080, 1920) if self.V else (1920, 1080)
        self.bf.W, self.bf.H = self.W, self.H
        self.show, self.paper, self.clip, self.mark = self.bf.SHOW, self.bf.paper, self.bf.CLIP, self.bf.MARK
        self.pal = {**look.PALETTE, **self.show.get('looks', {}).get(look.KEY, {})}
        self.p = self.root / (f"variant_{look.KEY.replace('-', '_')}" + ('_9x16' if self.V else ''))
        self.band = look.BAND if self.V else None
        fonts = ''.join(f'@font-face {{ font-family: "{fam}"; src: url("assets/fonts/{file}") format("truetype"); font-weight: {w}; }}\n    ' for fam, file, w in look.FONTS)
        self.css = fonts + f'''#root {{ background: {self.pal[look.GROUND]}; }}
    .cam {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: 0 0; }}
    .cam video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
    .band {{ position: absolute; left: 0; width: 1080px; overflow: hidden; }}
    .ty {{ position: absolute; white-space: nowrap; line-height: 1.3; overflow: visible; }} .ty .in {{ display: inline-block; }}
    ''' + look.css(self)

    def prepare(self):
        bf, p = self.bf, self.p
        for f in ('body.mp4',) + (('cold.mp4',) if bf.edl['cold'] else ()):
            if not (bf.B_ / f).exists():
                sys.exit(f'FAIL: no build/{f}. Run full_edit.py --render first.')
        if not (p / 'hyperframes.json').exists():
            subprocess.run(['npx', 'hyperframes', 'init', str(p), '--skip-skills'], capture_output=True, check=True)
        bf.clean_project(p)
        a = p / 'assets'
        (a / 'fonts').mkdir(parents=True, exist_ok=True)
        for _, file, _ in self.look.FONTS:
            shutil.copy(studio.FONTS / file, a / 'fonts')
        bf.relink(bf.B_ / 'body.mp4', a / 'body.mp4')
        if bf.edl['cold']:
            bf.relink(bf.B_ / 'cold.mp4', a / 'cold.mp4')

    # ------------------------------------------------------------ the camera
    def v_frame(self, kind, who, a, b):
        bf = self.bf
        _, bh = self.band
        hx, hy, hw = bf.face_at(bf.pos_h, a, b)
        gx, gy, gw = bf.face_at(bf.pos_g, a, b)
        p = kind[0] if kind[0] in 'HG' else who
        fill = bh / 1080 * 1.14     # a little in from the full frame: the edges of a set hold stands, cables and picture frames
        # just enough scale to fill the band and keep the other person fully out of shot
        s = max(fill, 1080 / max(gx - .78 * gw, 700)) if p == 'H' else max(fill, 1080 / max(1920 - (hx + .78 * hw), 700))
        if kind.endswith('+'):
            s *= 1.06
        s = min(s, 1.6)
        fx, fy = (hx, hy) if p == 'H' else (gx, gy)
        x = max(1080 - 1920 * s, min(0.0, 540 - s * fx))
        y = max(bh - 1080 * s, min(0.0, .42 * bh - s * fy))
        return round(s, 3), round(x, 1), round(y, 1)

    def shots(self, o):
        bf = self.bf
        out = bf.plan_shots(o)
        if self.V:
            for s in out:
                s['f'] = self.v_frame(s['kind'], s['who'], bf.local2src(o, s['t']), bf.local2src(o, s['end']))
        return out

    def camera(self, shots, sel):
        if not self.V:
            return self.bf.cam_js(shots, sel)
        js = []
        _, bh = self.band
        for s in shots:
            sc, x, y = s['f']
            s1 = sc * 1.012
            x1 = max(1080 - 1920 * s1, min(0.0, x - (s1 - sc) * 900))
            y1 = max(bh - 1080 * s1, min(0.0, y - (s1 - sc) * 400))
            d = round(s['end'] - s['t'] - .001, 3)
            js.append(f'tl.set("{sel}",{{scale:{sc},x:{x},y:{y}}},{s["t"]});tl.to("{sel}",{{scale:{s1:.4f},x:{x1:.1f},y:{y1:.1f},duration:{d},ease:"none"}},{s["t"]});')
        return ''.join(js)

    def footage(self, pfx, video, media_start, dur):
        ms = f' data-media-start="{media_start}"' if media_start is not None else ''
        v = f'<div class="cam" id="{pfx}c"><video id="{pfx}v" class="clip" src="assets/{video}" data-start="0" data-duration="{dur}"{ms} data-track-index="0" muted playsinline data-color-grading="{GRADE}"></video></div>'
        if not self.V:
            return v
        return f'<div class="band" style="top:{self.band[0]}px;height:{self.band[1]}px">{v}</div>'

    def cold_parts(self):
        """The cold open as (cards, shots): one card per cut, each on the film's own clock."""
        bf = self.bf
        cuts, acc = [], 0.0
        for q, r in bf.edl['cold']:
            cuts.append((round(acc, 3), round(acc + r - q, 3), q, r))
            acc += r - q
        cards = [dict(a=a, b=round(b - .02, 2), kind=kd, title=tx, rows=[], who=wh, opts={}) for (a, b, _, _), (tx, kd, wh) in zip(cuts, bf.COLD_CARDS)]
        shots = []
        for (a, b, q, r), (_, _, wh) in zip(cuts, bf.COLD_CARDS):
            f = self.v_frame(wh, wh, q, r) if self.V else bf.framing(wh, q, r)
            shots.append(dict(t=a, end=b, kind=wh, who=wh, f=f, card=True))
        return cards, shots

    def row_times(self, c, o=None):
        """When each row lands. opts.times, recording seconds from the transcript, puts a note on the word that says it; otherwise rows are spaced through the card."""
        times = c.get('opts', {}).get('times')
        if times and len(times) != len(c['rows']):
            sys.exit(f"FAIL: the card \"{c['title']}\" has {len(c['rows'])} rows and {len(times)} opts.times. Give one time per row.")
        if times and o is not None:
            return [round(self.bf.src2local(o, t), 2) for t in times]
        gap = (c['b'] - c['a'] - 1.6) / max(len(c['rows']), 1)
        return [round(c['a'] + .35 + min(gap, 2.6) * k, 2) for k in range(len(c['rows']))]

    def scene(self, id_, body, js, overlay=False):
        """overlay: a layer over other scenes, such as captions, so its ground must let them show through."""
        self.bf.scene(self.p, id_, self.css + ('\n    #root { background: transparent; }' if overlay else ''), body, JS + js)

    def text(self, id_, a, b, txt, x, y, size, ink, track=2, weight=None, family=None, extra=''):
        fam = f'font-family:{family};' if family else ''
        wt = f'font-weight:{weight};' if weight else ''
        return (f'<div id="{id_}" class="clip ty" data-start="{a}" data-duration="{round(b - a, 3)}" data-track-index="{track}" '
                f'style="left:{round(x)}px;top:{round(y)}px;font-size:{size}px;color:{ink};{fam}{wt}{extra}"><span class="in">{e(txt)}</span></div>')

    # ------------------------------------------------------------ the film
    def build(self, reuse_mix=False):
        bf, look = self.bf, self.look
        self.prepare()
        if hasattr(look, 'prepare'):
            look.prepare(self)
        for k, o in enumerate(bf.chs):
            shots = self.shots(o)
            h_, j_ = look.chapter(self, o, shots, k)
            self.scene(o.id, self.footage(o.id, 'body.mp4', o.bstart, o.dur) + h_, self.camera(shots, f'#{o.id}c') + j_)
            if not self.clip:
                h_, j_ = look.chapter_card(self, o, k)
                self.scene(f'{o.id}t', h_, j_)
        if not self.clip:
            cards, shots = self.cold_parts()
            h_, j_ = look.cold(self, cards, shots)
            self.scene('cold', self.footage('cold', 'cold.mp4', None, bf.COLD) + h_, self.camera(shots, '#coldc') + j_)
            h_, j_ = look.title(self)
            self.scene('title', h_, j_)
        h_, j_ = look.end(self)
        self.scene('end', h_, j_)

        bf.write_index(self.p, look.KEY + ('-9x16' if self.V else ''))
        extra = look.root_hosts(self) if hasattr(look, 'root_hosts') else ''
        if extra:
            idx = self.p / 'index.html'
            idx.write_text(idx.read_text(encoding='utf-8').replace('<audio id="mix"', extra + '\n      <audio id="mix"'), encoding='utf-8')

        other = self.root / self.p.name.replace('_9x16', '')
        a = self.p / 'assets' / 'mix.wav'
        if reuse_mix:
            bf.relink(other / 'assets' / 'mix.wav', a)      # built a moment ago from the same cut and the same words
        else:
            bf.mix(self.p, bf.music_bed(look.BED), look.cues(self), .46)
        print(f'OK: {self.p.name} · {bf.TOTAL:.1f} s · {self.W}×{self.H}')

    def frames(self):
        return contact_sheet(self.bf, self.p, self.V)


def contact_sheet(bf, project, vertical):
    """A contact sheet of real frames from a built project: the cheap way to judge a look before any long render. Nothing here renders the film."""
    W, H = (1080, 1920) if vertical else (1920, 1080)
    times, seen = [], set()
    add = lambda t, label: times.append((round(t, 2), label))
    if not bf.CLIP:
        add(.4, 'hook, frame 0')
        add(bf.COLD + bf.TITLE_D * .7, 'title')
        add(bf.chs[0].card_at + bf.CH_D * .6, 'chapter card')
    for o in bf.chs:
        for c in o.cards:
            if c['kind'] not in seen:
                seen.add(c['kind'])
                # a number or a verdict is a moment, so catch it early; a list needs time for its rows to land
                add(o.at + (c['a'] + 1.5 if c['kind'] in ('stat', 'verdict') else min(c['b'] - .3, c['a'] + max(2.2, (c['b'] - c['a']) * .75))), c['kind'])
        free = next(((a['b'], b['a']) for a, b in zip(o.cards, o.cards[1:]) if b['a'] - a['b'] > 3), None)
        if free and 'talk' not in seen:
            seen.add('talk')
            add(o.at + free[0] + 1.5, 'talk, no card')
    add(bf.END_AT + bf.END_D * .7, 'end card')
    times = sorted(times)
    out = project / 'test_frames'
    shutil.rmtree(out, ignore_errors=True)
    r = subprocess.run(['npx', 'hyperframes', 'snapshot', str(project), '--at', ','.join(str(t) for t, _ in times), '--no-end', '-o', str(out), '--timeout', '120000'], capture_output=True, text=True)
    stamp = lambda f: float(m[1]) if (m := re.search(r'([\d.]+)s?\.png$', f.name.replace('s.png', '.png'))) else 0
    pngs = sorted(out.glob('*.png'), key=stamp)
    if not pngs:
        sys.exit(f'FAIL: no frames came back: {r.stderr[-400:]}')
    cols = 5 if vertical else 4
    tw = 324 if vertical else 640
    th = round(tw * H / W)
    sheet = Image.new('RGB', (cols * (tw + 12) + 12, math.ceil(len(pngs) / cols) * (th + 46) + 12), '#FFFFFF')
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(studio.FONTS / 'NotoSansThai.ttf'), 22)
    for i, (f, (t, label)) in enumerate(zip(pngs, times)):
        x, y = 12 + (i % cols) * (tw + 12), 12 + (i // cols) * (th + 46)
        sheet.paste(Image.open(f).convert('RGB').resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x, y + th + 6), f'{label} · {t:.1f} s', fill='#111111', font=font)
    dest = project / f'test_frames_{project.name}.jpg'
    sheet.save(dest, quality=88)
    print(f'OK: {len(pngs)} frames · {dest}')
    return dest


def main(look):
    ap = argparse.ArgumentParser(description=look.__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('folder', help='an episode folder (episodes/EPxx/full) or a clip folder')
    ap.add_argument('--ratio', default='16x9', choices=['16x9', '9x16', 'both'])
    ap.add_argument('--frames', action='store_true', help='also write a contact sheet of real frames, to judge the look before any long render')
    if hasattr(look, 'add_args'):
        look.add_args(ap)
    x = ap.parse_args()
    root = Path(x.folder).resolve()
    for ratio in (['16x9', '9x16'] if x.ratio == 'both' else [x.ratio]):
        st = Stage(look, root, ratio, x)
        st.build(reuse_mix=x.ratio == 'both' and ratio == '9x16')
        if x.frames:
            st.frames()

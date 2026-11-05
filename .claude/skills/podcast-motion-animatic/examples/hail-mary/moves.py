"""This film's own moves, for tools/animatic_moves.py or a moves.py beside paper.json. register(h) gets animatic_cards, for its helpers. Each move works in a 1700×860 space and returns (html, js)."""
import math, random

FLAME = '#FFB547'
WALK = [f'rocky_frames_w{n}' for n in range(8)]
HAPPY = [f'rocky_frames_h{n}' for n in range(6)]
SUN = [f'sun_frames_f{n:02d}' for n in range(18)]


def register(h):
    lerp, poses, show, flip, stack = h.lerp, h.poses, h.show, h.flip, h.stack

    def space(id_):
        """The nebula and stars, panned at different speeds behind whatever flies through."""
        return (f'<img id="{id_}n" src="{h.raw("nebula")}" alt="" style="width:2500px;height:{h.FH}px;right:auto;object-fit:fill" />'
                f'<img id="{id_}s" src="{h.raw("stars")}" alt="" style="width:2500px;height:{h.FH}px;right:auto;object-fit:fill" />')

    def pan(id_, a, d, near, far):
        return poses(f'#{id_}n', a, d, lambda t, u: dict(x=lerp(0, -far, u))) + poses(f'#{id_}s', a, d, lambda t, u: dict(x=lerp(0, -near, u)))

    def ship(id_, fire=True):
        ox, oy, tail = 850, 430, 345
        fl = ''
        if fire:
            for g in range(2):
                ln = ''.join(f'<path d="M{tail - 6},{oy + dy} L{tail - L_},{oy + dy + wb}" stroke="{FLAME}" stroke-width="{sw}" fill="none" stroke-linecap="round"/>' for dy, L_, wb, sw in ((-46, 170 + g * 70, 6, 8), (0, 290 - g * 60, -5, 12), (46, 160 + g * 80, 4, 8)))
                fl += f'<g id="{id_}e{g}" opacity="{1 - g}">{ln}</g>'
        return f'<div class="lay" id="{id_}" style="mix-blend-mode:normal;transform-origin:{ox}px {oy}px"><img src="{h.raw("ship_art")}" alt="" style="mix-blend-mode:normal" />{h.svg(fl, True)}</div>'

    def fire(id_, a, d):
        return ''.join(show(f'#{id_}e0', k % 2 == 0, a + k / h.RATE) + show(f'#{id_}e1', k % 2 == 1, a + k / h.RATE) for k in range(int(d * h.RATE)))

    def throw(st, c, id_, a, d, rows):
        f = lambda t, u: dict(x=lerp(-1000, 560, u ** 1.5), y=lerp(90, -120, u) + 7 * math.sin(t * 9), scale=lerp(.55, .85, u), rotation=lerp(2, -7, u))
        return space(id_) + ship(f'{id_}m'), pan(id_, a, d, 700, 260) + poses(f'#{id_}m', a, d, f) + fire(f'{id_}m', a, d)

    def adrift(st, c, id_, a, d, rows):
        f = lambda t, u: dict(x=lerp(-170, 170, u), y=18 * math.sin(t * .9), scale=.72, rotation=lerp(-11, 11, u))
        return space(id_) + ship(f'{id_}m', False), pan(id_, a, d, 130, 60) + poses(f'#{id_}m', a, d, f)

    def astro(st, c, id_, a, d, rows):
        """One line in three drawings: they multiply in the dish, swarm the sun as it dims, and the ship sets off."""
        r0, r1 = rows[0], rows[1]
        ox, oy, w, hh = h.center('dish')
        A = f'<div class="lay" id="{id_}A" style="transform-origin:{ox:.0f}px {oy:.0f}px"><img src="{h.src("dish")}" alt="" />{h.svg(h.cells(id_ + "a", ox, oy, .42 * w, .34 * hh))}</div>'
        js = poses(f'#{id_}A', a, r0 - a, lambda t, u: dict(scale=lerp(1.0, 1.3, u)))
        for g in range(14):
            js += show(f'#{id_}ag{g}', True, a + round((g + 1) / 15 * (r0 - a) * .9 * h.RATE) / h.RATE)
        for k in range(int((r0 - a) * h.RATE)):
            for g in range(0, 14, 2):
                random.seed(g * 97 + k)
                js += f'tl.set("#{id_}ag{g}",{{x:{random.uniform(-5, 5):.1f},y:{random.uniform(-5, 5):.1f}}},{a + k / h.RATE:.3f});'
        sun, ids = stack(f'{id_}f', SUN)
        db = r1 - r0
        total = max(1, int(db * 3))
        B = f'<div class="lay" id="{id_}B" style="opacity:0">{sun}{h.svg(h.cells(id_ + "b", 300, 430, 280, 330, groups=8, per=12, r0=5, r1=10, seed=31), True)}</div>'
        js += show(f'#{id_}A', False, r0) + show(f'#{id_}B', True, r0) + flip(ids, r0, db, lambda k: SUN[min(17, 5 + int(k / total * 13))], 3)
        for g in range(8):
            js += show(f'#{id_}bg{g}', True, r0 + g * .12)
            js += poses(f'#{id_}bg{g}', r0, db, lambda t, u, g=g: dict(x=((t * 330 + g * 95) % 640), y=30 * math.sin(t * 5 + g)))
        dc = a + d - r1
        star = h.svg(f'<path d="M1420,190 L1436,262 L1508,278 L1436,294 L1420,366 L1404,294 L1332,278 L1404,262 Z" fill="{FLAME}"/>')
        C = f'<div class="lay" id="{id_}C" style="opacity:0">{space(id_ + "c")}{star}{ship(id_ + "m")}</div>'
        js += show(f'#{id_}B', False, r1) + show(f'#{id_}C', True, r1) + pan(f'{id_}c', r1, dc, 300, 120)
        js += poses(f'#{id_}m', r1, dc, lambda t, u: dict(x=lerp(-900, 430, u), y=lerp(170, -170, u), scale=lerp(.55, .28, u), rotation=lerp(-4, -14, u))) + fire(f'{id_}m', r1, dc)
        return A + B + C, js

    def rocky(st, c, id_, a, d, rows):
        tr = rows[-1] - a
        html_, ids = stack(f'{id_}r', WALK + HAPPY)
        js = flip(ids, a, tr, lambda k: WALK[k % 8]) + show(f'#{ids[WALK[int(tr * h.RATE - 1) % 8]]}', False, a + tr) + flip(ids, a + tr, d - tr, lambda k: HAPPY[k % 6])
        f = lambda t, u: dict(x=lerp(-760, 0, min(1, t / tr)), y=6 * math.sin(t * 12)) if t < tr else dict(x=0, y=-70 * abs(math.sin((t - tr) * 2 * math.pi / .84)))
        return f'<div class="lay" id="{id_}m" style="transform-origin:850px 500px">{html_}</div>', poses(f'#{id_}m', a, d, f) + js

    def hung(period):
        def move(st, c, id_, a, d, rows):
            x0, y0, x1, y1 = h.BOX['puppet']
            cx = (x0 + x1) / 2
            html_, ids = stack(f'{id_}r', WALK)
            inner = f'<div style="position:absolute;inset:0;transform-origin:850px 282px;transform:translate(-90px,{y1 - 62 - 282:.0f}px) scale(.62)">{html_}</div>'
            f = lambda t, u: dict(x=22 * math.sin(t * math.pi / period), y=-250 + 14 * math.sin(t * 4 * math.pi / period), rotation=8 * math.sin(t * 2 * math.pi / period))
            return f'<div class="lay" id="{id_}m" style="transform-origin:{cx:.0f}px {y0:.0f}px"><img src="{h.src("puppet")}" alt="" />{inner}</div>', poses(f'#{id_}m', a, d, f) + flip(ids, a, d, lambda k: WALK[(k // 2) % 8])
        return move

    def catch(st, c, id_, a, d, rows):
        """The ball thrown at the start comes down, and this time someone is there."""
        tr = max(.5, round((rows[0] - a) * h.RATE) / h.RATE)
        fx, fy, fw, _ = h.center('football')
        bs = 300 / fw
        html_, ids = stack(f'{id_}r', WALK + HAPPY)
        body = f'<div class="lay" id="{id_}m" style="transform:translate(170px,20px)">{html_}</div>' + h.img(f'{id_}b', 'football', fx, fy)
        rest = (500 - fx, 590 - fy)

        def f(t, u):
            if t < tr:
                v = t / tr
                return dict(x=lerp(-1000, rest[0], v), y=lerp(-200, rest[1], v) - 300 * math.sin(math.pi * v), scale=lerp(.32, bs, v), rotation=lerp(-560, -18, v))
            return dict(x=rest[0], y=rest[1] - 70 * abs(math.sin((t - tr) * math.pi / .5)) * math.exp(-(t - tr) * 2.2), scale=bs, rotation=-18)
        return body, poses(f'#{id_}b', a, d, f) + show(f'#{ids[WALK[0]]}', True, a) + show(f'#{ids[WALK[0]]}', False, a + tr) + flip(ids, a + tr, d - tr, lambda k: HAPPY[k % 6])

    def friends(st, c, id_, a, d, rows):
        html_, ids = stack(f'{id_}r', HAPPY)
        return f'<div class="lay" id="{id_}m">{html_}</div>', flip(ids, a, d, lambda k: HAPPY[k % 6]) + poses(f'#{id_}m', a, d, lambda t, u: dict(y=-60 * abs(math.sin(t * 2 * math.pi / .84))))

    return dict(throw=throw, adrift=adrift, astro=astro, rocky=rocky, puppet=hung(1.7), puppet_half=hung(1.1), catch=catch, friends=friends)

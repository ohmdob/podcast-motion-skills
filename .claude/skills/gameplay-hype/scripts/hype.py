#!/usr/bin/env python3
"""Gameplay Hype: a beat-cut 9:16 short from gameplay recordings, built as a HyperFrames composition.

  hype.py scout  REC.mov [--every 0.5] [--out sheet.jpg]   contact sheet to pick shots from (prints index -> time)
  hype.py beat   MUSIC.mp3 [--want 30]                     tempo, first beat, and the loudest stretch to start from
  hype.py cut    CLIP_DIR [ids...]                         cut every shot in plan.json to 1080x1920 (all, or the ids given)
  hype.py frames CLIP_DIR                                  contact sheet of every shot's middle frame (check the crops)
  hype.py compose CLIP_DIR                                 write CLIP_DIR/hf/index.html from plan.json + build/timeline.json
  hype.py master CLIP_DIR [--out film.mp4]                 render, loudness -14 LUFS, trim, black-frame QC

CLIP_DIR holds plan.json (see references/plan.md). Shots go to CLIP_DIR/hf/assets/shots, logs and renders to CLIP_DIR/build.
"""
import argparse, json, math, os, shutil, subprocess, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W9, H9 = 1080, 1920
COL = (40, 160)          # left / right inset of the text column: clear of TikTok's right rail


def sh(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"failed: {' '.join(cmd[:6])} ...\n{r.stderr[-2500:]}")
    return r.stdout + r.stderr


def probe(path, entries="stream=width,height:format=duration"):
    out = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries, "-of", "json", path])
    return json.loads(out)


def load(clip):
    clip = os.path.abspath(clip)
    plan = json.load(open(os.path.join(clip, "plan.json")))
    rel = lambda p: p if os.path.isabs(p) else os.path.normpath(os.path.join(clip, p))
    plan["sources"] = {k: rel(v) for k, v in plan["sources"].items()}
    if plan.get("logo"): plan["logo"] = rel(plan["logo"])
    plan["music"]["src"] = rel(plan["music"]["src"])
    # defaults: the font and effects bundled with podcast-playbook, which sits beside this skill
    shared = os.path.join(os.path.dirname(SKILL), "podcast-playbook", "assets")
    plan.setdefault("font", os.path.join(shared, "fonts", "Mitr-SemiBold.ttf"))
    plan.setdefault("sfx_dir", os.path.join(shared, "sfx"))
    plan["font"] = rel(plan["font"]); plan["sfx_dir"] = rel(plan["sfx_dir"])
    plan.setdefault("fps", 30); plan.setdefault("game_volume", 2.2)
    return clip, plan


def frame_t(plan, beat):
    fps = plan["fps"]
    return round(beat * 60 / plan["bpm"] * fps) / fps


def timeline(plan):
    out = []
    for s in plan["shots"]:
        t0 = frame_t(plan, s["beats"][0]); t1 = min(plan["duration"], frame_t(plan, s["beats"][1]))
        out.append(dict(id=s["id"], start=t0, dur=round(t1 - t0, 6)))
    return out


# ---------------------------------------------------------------- scout / beat
def cmd_scout(a):
    d = float(probe(a.rec)["format"]["duration"])
    n = int(d / a.every) + 1; cols = 6; rows = math.ceil(n / cols)
    out = a.out or os.path.splitext(os.path.basename(a.rec))[0] + "_scout.jpg"
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.rec, "-vf",
        f"fps={1/a.every},scale=312:-2,tile={cols}x{rows}", "-frames:v", "1", out])
    print(f"{out}: {n} frames, {cols} a row, row-major. frame i is at about i*{a.every} s ({d:.1f} s long)")


def cmd_beat(a):
    import numpy as np
    sr = 11025
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.music, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32); hop, win = 256, 1024
    spec = np.log1p(np.array([np.abs(np.fft.rfft(x[i:i + win] * np.hanning(win))) for i in range(0, len(x) - win, hop)]))
    flux = np.maximum(0, np.diff(spec, axis=0)).sum(1); flux -= flux.mean(); fr = sr / hop
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]; idx = np.arange(len(ac))
    bpm = max(np.arange(70, 181, 0.5), key=lambda b: np.interp(fr * 60 / b, idx, ac) + 0.5 * np.interp(fr * 120 / b, idx, ac))
    per = fr * 60 / bpm
    ph = max(range(int(per)), key=lambda p: flux[np.round(np.arange(p, len(flux), per)).astype(int)].sum())
    first = ph / fr; beat = 60 / bpm
    # loudest window of `want` s that starts on a beat (half-second RMS, the last 5 s may be quieter: end card)
    hs = sr // 2; rms = np.array([np.sqrt((x[i:i + hs] ** 2).mean()) for i in range(0, len(x) - hs, hs)])
    db = 20 * np.log10(rms + 1e-9); body = int((a.want - 5) * 2)
    best = None
    k = 0
    while first + k * beat + a.want < len(x) / sr:
        t = first + k * beat; i = int(t * 2)
        if i + body <= len(db):
            score = db[i:i + body].mean()
            if best is None or score > best[1]: best = (t, score)
        k += 1
    print(f"bpm {bpm}  beat {beat:.4f} s  first beat {first:.3f} s")
    print(f"loudest {a.want:.0f} s on the beat grid starts at {best[0]:.2f} s (mean {best[1]:.1f} dB): music.start")
    print("listen to it: the tempo is measured, not heard; a half or double tempo reading is common")


# ---------------------------------------------------------------- cut
def cmd_cut(a):
    clip, plan = load(a.clip)
    shots_dir = os.path.join(clip, "hf", "assets", "shots"); os.makedirs(shots_dir, exist_ok=True)
    os.makedirs(os.path.join(clip, "build"), exist_ok=True)
    tl = {t["id"]: t for t in timeline(plan)}; fps = plan["fps"]
    for s in plan["shots"]:
        if a.ids and s["id"] not in a.ids: continue
        src = plan["sources"][s["src"]]; p = probe(src)["streams"][0]; W, H = p["width"], p["height"]
        dur = tl[s["id"]]["dur"]; speed = s.get("speed", 1.0)
        cx0, cx1 = (s.get("cx") or [0.5, 0.5]) if isinstance(s.get("cx"), list) else (s.get("cx", 0.5),) * 2
        slow = f"setpts={1/speed:.4f}*PTS," if speed != 1 else ""
        if s["mode"] == "tall":                       # 9:16 crop that follows the action
            ch = int(H / s.get("zoom", 1.0)) // 2 * 2; cw = int(ch * 9 / 16) // 2 * 2; y = (H - ch) // 2
            x = f"max(0,min({W - cw},({cx0}+({cx1}-{cx0})*t/{dur})*{W}-{cw // 2}))"
            fc = f"[0:v]{slow}fps={fps},crop={cw}:{ch}:'{x}':{y},scale={W9}:{H9}:flags=lanczos,setsar=1[v]"
        else:                                          # the frame across the width, over a blurred copy of itself
            fh = 860; fw = int(W * fh / H) // 2 * 2; fx = f"max(0,min({fw - W9},{cx0}*{fw}-{W9 // 2}))"
            cw = int(H * 9 / 16) // 2 * 2
            fc = (f"[0:v]{slow}fps={fps},split[a][b];"
                  f"[a]crop={cw}:{H}:{(W - cw) // 2}:0,scale=270:480,boxblur=10:2,scale={W9}:{H9},eq=brightness=-0.06:saturation=1.15[bg];"
                  f"[b]scale={fw}:{fh}:flags=lanczos,crop={W9}:{fh}:'{fx}':0[fg];[bg][fg]overlay=0:450,setsar=1[v]")
        has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                    "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip() != ""
        amap = []
        if has_audio:
            fc += f";[0:a]atempo={speed}[a2]" if speed != 1 else ";[0:a]anull[a2]"
            amap = ["-map", "[a2]", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]
        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(s["in"]), "-t", f"{(dur + 0.2) * speed:.3f}",
            "-i", src, "-filter_complex", fc, "-map", "[v]", *amap, "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-g", "15", "-movflags", "+faststart", os.path.join(shots_dir, s["id"] + ".mp4")])
        print(f'{s["id"]} {s["mode"]:4} {s["src"]}@{s["in"]:<6} -> {tl[s["id"]]["start"]:.3f} s, {dur:.3f} s', flush=True)
    json.dump(timeline(plan), open(os.path.join(clip, "build", "timeline.json"), "w"), indent=1)


def cmd_frames(a):
    clip, plan = load(a.clip); tmp = os.path.join(clip, "build", "frames"); os.makedirs(tmp, exist_ok=True)
    for t in timeline(plan):
        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t['dur'] / 2:.3f}", "-i",
            os.path.join(clip, "hf", "assets", "shots", t["id"] + ".mp4"), "-frames:v", "1", "-vf", "scale=216:384",
            os.path.join(tmp, t["id"] + ".png")])
    out = os.path.join(clip, "build", "shots_sheet.jpg")
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", os.path.join(tmp, "*.png"),
        "-vf", "tile=10x2", out])
    print(out)


# ---------------------------------------------------------------- compose
def f6(x): return f"{x:.6f}".rstrip("0").rstrip(".")


def word_html(w, th):
    k = w["kind"]; g = " gold" if w.get("gold") else ""
    if k == "chip": return f'<span class="chip">{w["text"]}</span>'
    if k == "title":
        return "".join(f'<div class="{l.get("size", "big")} w{" gold" if l.get("gold") else ""}">{l["t"]}</div>' for l in w["lines"])
    if k == "stamp": return f'<div class="stamp tilt-{w.get("tilt", "l")}{g}">{w["text"]}</div>'
    if k == "num": return f'<div class="num{g or " w"}">{w["text"]}</div>' + (f'<div class="sub">{w["sub"]}</div>' if w.get("sub") else "")
    if k == "rank": return f'<div class="rank{" sm" if w.get("small") else ""}">{w["text"]}</div>' + (f'<div class="sub">{w["sub"]}</div>' if w.get("sub") else "")
    if k == "boss": return f'<div class="boss">{w["text"]}</div>'
    sys.exit(f"unknown word kind {k}")


def cmd_compose(a):
    clip, plan = load(a.clip); hf = os.path.join(clip, "hf"); A = os.path.join(hf, "assets")
    tl_path = os.path.join(clip, "build", "timeline.json")
    TL = json.load(open(tl_path)) if os.path.exists(tl_path) else timeline(plan)
    S = {t["id"]: t["start"] for t in TL}; DUR = plan["duration"]; BEAT = 60 / plan["bpm"]
    th = {"ink": "#1A1210", "gold": "#F6C54B", "red": "#E0322B", "bg": "#140E0C", **plan.get("theme", {})}
    # assets the page needs
    for sub in ("fonts", "sfx", "stills"): os.makedirs(os.path.join(A, sub), exist_ok=True)
    font = plan.get("font")
    if not os.path.exists(font): sys.exit(f"plan.font not found: {font}")
    shutil.copy(font, os.path.join(A, "fonts", "thai.ttf"))
    shutil.copy(plan["music"]["src"], os.path.join(A, "music" + os.path.splitext(plan["music"]["src"])[1]))
    music_rel = "assets/music" + os.path.splitext(plan["music"]["src"])[1]
    for x in plan.get("sfx", []):
        shutil.copy(os.path.join(plan["sfx_dir"], x["file"] + ".mp3"), os.path.join(A, "sfx", x["file"] + ".mp3"))
    end = plan.get("end")
    if end and plan.get("logo"): shutil.copy(plan["logo"], os.path.join(A, "stills", "logo" + os.path.splitext(plan["logo"])[1]))

    def at(x):  # {"shot": id, "at": s} or {"shot": id, "atb": beats}
        return S[x["shot"]] + (x["atb"] * BEAT if "atb" in x else x.get("at", 0.0))

    vids = "\n".join(
        f'        <video id="{t["id"]}" class="clip" src="assets/shots/{t["id"]}.mp4" data-start="{f6(t["start"])}" '
        # +0.02 s overlap: a clip that ends a hair before the next starts renders one black frame
        f'data-duration="{f6(min(DUR - t["start"], t["dur"] + 0.02))}" data-track-index="1" data-has-audio="true" '
        f'data-volume="{plan["game_volume"]}" playsinline></video>' for t in TL)

    words, js = [], []
    for w in plan.get("words", []):
        st = at(w); du = w["dur"]; i = w["id"]
        pos = f"top:{w['top']}px;" + (f"right:{w['right']}px;" if "right" in w else f"left:{w['left']}px;" if "left" in w
                                      else f"left:{COL[0]}px;right:{COL[1]}px;")
        words.append(f'      <div id="{i}" class="clip txt" data-start="{f6(st)}" data-duration="{f6(du)}" data-track-index="3" '
                     f'data-layout-allow-overlap style="{pos}"><div class="in" id="{i}-in">{word_html(w, th)}</div></div>')
        enter = w.get("enter", "slam")
        if enter == "none": pass
        elif enter == "on": js.append(f'tl.fromTo("#{i}-in", {{ scale: 1.06 }}, {{ scale: 1, duration: 0.25, ease: E }}, {f6(st)});')
        elif enter == "blur": js.append(f'blurIn("#{i}-in > div, #{i}-in > span", {f6(st)}, 0.12);')
        elif enter == "blur-slam": js.append(f'blurIn("#{i}-in > .small", {f6(st)}); slam("#{i}-in > .big", {f6(st + 0.2)}, {w.get("from", 2.6)});')
        else: js.append(f'slam("#{i}-in", {f6(st)}, {w.get("from", 2.4)});')
        if w.get("exit", True): js.append(f'out("#{i}-in", {f6(st + du - 0.16)});')

    if end:
        st = S[end["shot"]]; rest = DUR - st
        lg = "assets/stills/logo" + os.path.splitext(plan["logo"])[1] if plan.get("logo") else None
        if lg: words.append(f'      <div id="t-logo" class="clip txt" data-start="{f6(st + 0.15)}" data-duration="{f6(rest - 0.15)}" data-track-index="3" '
                            f'style="left:0;right:{COL[1] - COL[0]}px;top:{end.get("logo_top", 380)}px;mix-blend-mode:screen"><div class="in" id="t-logo-in"><img id="logo" src="{lg}" alt="logo"></div></div>')
        if end.get("cta"): words.append(f'      <div id="t-cta" class="clip txt" data-start="{f6(st + 0.55)}" data-duration="{f6(rest - 0.55)}" data-track-index="3" '
                                        f'style="left:{COL[0]}px;right:{COL[1]}px;top:{end.get("cta_top", 930)}px"><div class="in" id="t-cta-in"><div class="cta w">{end["cta"]}</div></div></div>')
        if end.get("url"): words.append(f'      <div id="t-url" class="clip txt" data-start="{f6(st + 0.85)}" data-duration="{f6(rest - 0.85)}" data-track-index="3" '
                                        f'style="left:{COL[0]}px;right:{COL[1]}px;top:{end.get("url_top", 1150)}px"><div class="in" id="t-url-in"><span class="url">{end["url"]}</span></div></div>')
        js += [f'tl.fromTo("#endveil", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4, ease: "power2.inOut", immediateRender: false }}, {f6(st)});',
               f'tl.fromTo("#t-logo-in", {{ scale: 0.82, opacity: 0, filter: "blur(10px)" }}, {{ scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.5, ease: E, immediateRender: false }}, {f6(st + 0.15)});',
               f'blurIn("#t-cta-in", {f6(st + 0.55)});',
               f'tl.fromTo("#t-url-in", {{ y: 40, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.4, ease: E, immediateRender: false }}, {f6(st + 0.85)});']

    for x in plan.get("fx", []):
        t = at(x)
        if "punch" in x: js.append(f"punch({f6(t)}, {x['punch']});")
        if "shake" in x: js.append(f"shake({f6(t)}, {x['shake']});")
        if "flash" in x: js.append(f"flash('#flash', {f6(t)}, {x['flash'][0]}, {x['flash'][1]});")
        if "red" in x: js.append(f"flash('#redflash', {f6(t)}, {x['red'][0]}, {x['red'][1]});")

    sfx = "\n".join(
        f'      <audio id="x{n:02d}-{x["file"]}" class="clip" src="assets/sfx/{x["file"]}.mp3" data-start="{f6(at(x))}" '
        f'data-duration="{x.get("dur", 0.6)}" data-track-index="5" data-volume="{x.get("vol", 0.6)}"></audio>'
        for n, x in enumerate(plan.get("sfx", [])))
    m = plan["music"]
    css = open(os.path.join(SKILL, "assets", "hype.css")).read()
    for k, v in th.items(): css = css.replace("{" + k + "}", v)
    html = f'''<!doctype html>
<html lang="{plan.get("lang", "th")}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W9}, height={H9}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
{css}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{f6(DUR)}" data-width="{W9}" data-height="{H9}">
      <div id="cam">
{vids}
      </div>
      <div id="shade"></div>
      <div id="endveil"></div>
{chr(10).join(words)}
      <div id="flash"></div>
      <div id="redflash"></div>
      <audio id="bgm" class="clip" src="{music_rel}" data-start="0" data-duration="{f6(DUR)}" data-media-start="{m["start"]}" data-track-index="4" data-volume="{m.get("volume", 0.8)}" data-fade-out="{m.get("fade_out", 1.6)}"></audio>
{sfx}
    </div>
    <script>
const S = {json.dumps({k: round(v, 6) for k, v in S.items()})};
const tl = gsap.timeline({{ paused: true }});
const E = "expo.out";
// camera: reset on every cut, then punch-ins and shakes from plan.fx
Object.values(S).forEach(t => tl.set("#cam", {{ scale: 1, x: 0, y: 0 }}, t));
function punch(t, s) {{ tl.fromTo("#cam", {{ scale: 1 }}, {{ scale: s, duration: 0.12, ease: E, immediateRender: false }}, t); }}
const J = [[-22,10],[18,-14],[-14,-8],[12,12],[-8,6],[5,-4],[0,0]];
function shake(t, k) {{ J.forEach((p, i) => tl.to("#cam", {{ x: p[0]*k, y: p[1]*k, duration: 0.035, ease: "none" }}, t + i*0.035)); }}
function flash(sel, t, a, d) {{ tl.fromTo(sel, {{ opacity: a }}, {{ opacity: 0, duration: d, ease: "power2.out", immediateRender: false }}, t); }}
function slam(sel, t, from) {{ tl.fromTo(sel, {{ scale: from || 2.4, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.28, ease: E, immediateRender: false }}, t); }}
function blurIn(sel, t, gap) {{ document.querySelectorAll(sel).forEach((el, i) =>
  tl.fromTo(el, {{ opacity: 0, filter: "blur(10px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.16, ease: "power2.out", immediateRender: false }}, t + i*(gap||0.09))); }}
function out(sel, t) {{ tl.to(sel, {{ opacity: 0, filter: "blur(8px)", duration: 0.14, ease: "power2.in" }}, t); }}
{chr(10).join(js)}
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''
    os.makedirs(hf, exist_ok=True)
    open(os.path.join(hf, "index.html"), "w").write(html)
    if not os.path.exists(os.path.join(hf, "hyperframes.json")):
        json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                   "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
                   "media": {"autoProxy": True}}, open(os.path.join(hf, "hyperframes.json"), "w"), indent=2)
    print(f"{hf}/index.html: {len(TL)} shots, {len(plan.get('words', []))} words, {len(plan.get('sfx', []))} sfx, {DUR} s")


# ---------------------------------------------------------------- master
def cmd_master(a):
    clip, plan = load(a.clip); hf = os.path.join(clip, "hf"); rd = os.path.join(clip, "build", "renders")
    os.makedirs(rd, exist_ok=True); raw = os.path.join(rd, "raw.mp4")
    r = subprocess.run(["npx", "hyperframes", "render", "-o", raw], cwd=hf, capture_output=True, text=True)
    open(os.path.join(clip, "build", "render.log"), "w").write(r.stdout + r.stderr)
    if r.returncode: sys.exit("render failed: see build/render.log")
    out = os.path.abspath(a.out or os.path.join(rd, "final.mp4")); tmp = out + ".tmp.mp4"
    meas = sh(["ffmpeg", "-hide_banner", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-vn", "-f", "null", "-"])
    j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']},aresample=48000")
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", raw, "-t", str(plan["duration"]), "-c:v", "copy",
        "-af", ln, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp])
    os.replace(tmp, out)
    qc = sh(["ffmpeg", "-hide_banner", "-i", out, "-vf", "blackdetect=d=0.01:pix_th=0.08", "-af", "ebur128=peak=true", "-f", "null", "-"])
    blacks = qc.count("black_start")
    summ = qc[qc.rfind("Summary:"):]
    I = next((l.split()[1] for l in summ.splitlines() if l.strip().startswith("I:")), "?")
    P = next((l.split()[1] for l in summ.splitlines() if l.strip().startswith("Peak:")), "?")
    print(f"{out}\n  {probe(out)['format']['duration']} s · {I} LUFS · peak {P} dBFS · black frames: {blacks}")
    if blacks: print("  a black frame is a gap between two shots or a shot that ran out: check the cut times")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scout"); s.add_argument("rec"); s.add_argument("--every", type=float, default=0.5); s.add_argument("--out")
    s = sp.add_parser("beat"); s.add_argument("music"); s.add_argument("--want", type=float, default=30)
    s = sp.add_parser("cut"); s.add_argument("clip"); s.add_argument("ids", nargs="*")
    s = sp.add_parser("frames"); s.add_argument("clip")
    s = sp.add_parser("compose"); s.add_argument("clip")
    s = sp.add_parser("master"); s.add_argument("clip"); s.add_argument("--out")
    a = p.parse_args()
    {"scout": cmd_scout, "beat": cmd_beat, "cut": cmd_cut, "frames": cmd_frames, "compose": cmd_compose, "master": cmd_master}[a.cmd](a)


if __name__ == "__main__":
    main()

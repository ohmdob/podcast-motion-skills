#!/usr/bin/env python3
"""What this machine and this project can do right now. Free: it never prints a key and never spends a credit.

    python3 doctor.py [folder]

Run it first. Either key is optional, and so is having both: the last section says what each step will use with the keys that are set.
"""
import json, shutil, subprocess, sys, urllib.error, urllib.request
from pathlib import Path
import studio
import el
import ideogram

start = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
problems = 0


def row(label, value):
    print(f'  {label:<16}{value}')


print('Keys')
found = studio.env_files(start)
for name in studio.KEYS:
    src = studio.secret_source(name, start)
    row(name, f'set, in {src}' if src else 'empty')
if not found:
    print(f'  no .env found. Make one with the two lines from {studio.TEMPLATES / "env.example"}')
for f in found:
    if studio.loose_permissions(f):
        print(f'  WARN {f} is readable by other users: chmod 600 it')
    if studio.SKILL in f.resolve().parents:
        problems += 1
        print(f'  WARN {f} sits inside the skill folder, and packaging a skill includes it. Move it up to the repo root.')

print('Services (free checks)')
has_el, has_comfy = bool(studio.secret('ELEVENLABS-API', start)), False
if has_el:
    b = el.balance(start)
    row('ElevenLabs', f'{b[0]:,} of {b[1]:,} credits left ({b[2]})' if b else el.PROBLEM)
    has_el = bool(b)
else:
    row('ElevenLabs', 'skipped, no key')
host = studio.secret('COMFY-HOST', start) or studio.DEFAULT_COMFY
problem = studio.comfy_host_problem(host)
if studio.secret('COMFY-API', start) and problem:
    row('Comfy', problem)
elif studio.secret('COMFY-API', start):
    comfy = ideogram.Comfy(host)
    try:
        q = json.loads(comfy.get('/api/queue', timeout=20))
        has_comfy = comfy.has_ideogram()
        row(comfy.label, f"{host}: {len(q.get('queue_running', []))} running, {len(q.get('queue_pending', []))} waiting; Ideogram nodes {'present' if has_comfy else 'MISSING'}")
    except urllib.error.HTTPError as e:
        row(comfy.label, f'{host}: the key was refused' if e.code in (401, 403) else f'{host}: HTTP {e.code}')
    except (urllib.error.URLError, OSError, ValueError) as e:
        row(comfy.label, f'{host}: not reachable ({type(e).__name__})')
else:
    row('Comfy', 'skipped, no key')

print('Tools')
for tool, why, core in (('ffmpeg', 'everything', True), ('ffprobe', 'everything', True), ('python3', 'everything', True), ('node', 'HyperFrames', True), ('npx', 'HyperFrames', True),
                        ('swiftc', 'face tracking, which every look uses, and word breaks in subtitles: macOS with the Xcode command line tools', True), ('uv', 'the person matte for Pop Studio', False), ('rclone', 'publishing to a CDN', False)):
    p = shutil.which(tool)
    row(tool, p or f'MISSING, needed for {why}')
    problems += bool(core and not p)
for mod, why in (('numpy', 'voice and cuts'), ('PIL', 'stills and type')):
    try:
        __import__(mod)
        row(mod, 'ok')
    except ImportError:
        problems += 1
        row(mod, f'MISSING, needed for {why}: python3 -m pip install numpy pillow')

print('Project')
show = studio.load_show(start, required=False)
if show['root']:
    row('show', f"{show['name'] or '(no name)'} · {show['root']} · {show['lang']}, {show['fps']} fps")
    row('mark on screen', show['mark'] or show['name'] or '(none set)')
    row('STYLES.md', 'present' if (show['root'] / 'STYLES.md').exists() else 'missing: it records which looks this show has approved')
    row('ledger', show['root'] / 'data' / 'ledger.md')
else:
    row('show', f'none here. Make one: python3 {Path(__file__).parent}/init_show.py <folder> --name "Show name"')

print('What each step will use')
row('voice', 'ElevenLabs Audio Isolation, blended with the real voice' if has_el else 'ordinary denoise only (free); blends need ELEVENLABS-API')
row('transcript', 'ElevenLabs Scribe' if has_el else 'bring one: npx hyperframes transcribe, or any .srt, then transcript.py import')
row('word timing', 'ElevenLabs Forced Alignment' if has_el else 'from that transcript, coarser; check it by ear')
row('music, effects', 'ElevenLabs Music and SFX, your own files, or the bundled set' if has_el else 'your own files in assets/music and assets/sfx, or the bundled set')
codex = shutil.which('codex')
row('pictures', 'Ideogram 4.5 through Comfy' if has_comfy else f"no Ideogram. If this film needs pictures, ASK the producer which alternative: {'Codex imagegen (codex is installed), ' if codex else ''}their own photographs, another service, or none")
print('FAIL: fix the items above' if problems else 'OK')
sys.exit(1 if problems else 0)

#!/usr/bin/env python3
"""ElevenLabs for the podcast pipeline. Reads ELEVENLABS_API from .env and never prints it.

    python3 el.py quota                                                free: credits used and left
    python3 el.py isolate IN.wav OUT.mp3 [--note "EP02"]               Audio Isolation, 660 credits a minute (measured)
    python3 el.py scribe  IN.wav OUT.json [--lang tha] [--speakers 2] [--model scribe_v1]    20 a minute: word timing + diarization
    python3 el.py align   IN.wav TEXT.txt OUT.json                     Forced Alignment, about 21 a minute: a space-separated token gets its own timing
    python3 el.py sfx     "prompt" OUT.mp3 [--dur 1.5] [--influence 0.5]    6-24 with a set duration, 55 without
    python3 el.py music   "prompt" OUT.mp3 --dur 46                    instrumental bed, about 14 a second
    python3 el.py voices  [--lang th] [--previews DIR --names A,B]     free: models that speak the language, voices in your library, their preview clips
    python3 el.py tts     SCRIPT.json OUTDIR --voices H=ID,G=ID [--model eleven_v4] [--only 3,5]    one take a line. Thai on eleven_v4 measured about 0.44 a character

A paid command only quotes unless given --yes, and exits 3 having spent nothing. An output that already exists is skipped; --force replaces
it and keeps the old one in old/. Nothing is ever retried: a duplicate call pays twice, so a lost connection ends in UNKNOWN and a ledger row.
stdout ends with OK: · FAIL: · QUOTE: · UNKNOWN:
"""
import argparse, http.client, json, subprocess, sys, urllib.error, urllib.request, uuid
from pathlib import Path
import studio

BASE = 'https://api.elevenlabs.io'
TTS_RATE = {'eleven_v4': 1.0, 'eleven_v3': 1.0, 'eleven_v4_turbo': .5, 'eleven_v3_conversational': .5}    # the most a character can cost; the header on each reply says what it did
LANG_NAME = {'th': 'Thai', 'en': 'English', 'ja': 'Japanese'}
PROBLEM = ''     # why balance() came back empty
PER_SECOND = {'isolate': 660 / 60, 'scribe': 20 / 60, 'align': 15 / 43, 'music': 630 / 46}
NAMES = {'isolate': 'Audio Isolation', 'scribe': 'Scribe', 'align': 'Forced Alignment', 'sfx': 'SFX', 'music': 'Music'}


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout)
    except ValueError:
        sys.exit(f'FAIL: cannot read the length of {path}')


def balance(start=None):
    """(credits left, limit, plan), or None. Free."""
    global PROBLEM
    key = studio.secret('ELEVENLABS_API', start)
    if not key:
        return None
    PROBLEM = ''
    try:
        req = urllib.request.Request(BASE + '/v1/user/subscription', headers={'xi-api-key': key})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        return d['character_limit'] - d['character_count'], d['character_limit'], d.get('tier', '?')
    except urllib.error.HTTPError as e:
        PROBLEM = 'the key was refused (HTTP 401): it is wrong or revoked, so make a new one' if e.code == 401 else f'ElevenLabs answered HTTP {e.code}'
        return None
    except (urllib.error.URLError, OSError, ValueError, KeyError, http.client.HTTPException) as e:
        PROBLEM = f'could not reach ElevenLabs ({type(e).__name__})'
        return None


def multipart(fields, file_field=None, file_path=None):
    b = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    if file_path:
        p = Path(file_path)
        out += (f'--{b}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{p.name}"\r\n'
                f'Content-Type: application/octet-stream\r\n\r\n').encode()
        out += p.read_bytes() + b'\r\n'
    out += f'--{b}--\r\n'.encode()
    return bytes(out), f'multipart/form-data; boundary={b}'


def call(root, service, job, path, body, ctype, out, timeout=600):
    """One request, one ledger row, no retry."""
    req = urllib.request.Request(BASE + path, data=body, method='POST', headers={'xi-api-key': studio.need('ELEVENLABS_API'), 'Content-Type': ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data, headers = r.read(), r.headers
    except urllib.error.HTTPError as e:
        msg = studio.redact(e.read()[:400].decode('utf-8', 'replace'))
        studio.ledger(root, service, job, '?', f'failed: HTTP {e.code}')
        sys.exit(f'FAIL: HTTP {e.code} {msg}')
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        studio.ledger(root, service, job, '?', f'unknown: {type(e).__name__}')
        print(f'UNKNOWN: the connection ended before a reply ({type(e).__name__}). The call may have been charged. Not retried: check "el.py quota" before running it again.')
        sys.exit(studio.EXIT_UNKNOWN)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    studio.keep_old(out)
    out.write_bytes(data)
    cost = headers.get('character-cost') or headers.get('x-character-count') or '?'
    studio.ledger(root, service, job, cost, 'ok')
    return cost


def peak(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', '48000', '-'], capture_output=True).stdout
    import array
    a = array.array('f')
    a.frombytes(raw[:len(raw) - len(raw) % 4])
    return max((abs(x) for x in a), default=0.0)


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={'xi-api-key': studio.need('ELEVENLABS_API')})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'FAIL: HTTP {e.code} on {path}: {studio.redact(e.read()[:200].decode("utf-8", "replace"))}')


def voices(x):
    """Free. Casting starts here: preview clips cost nothing, and a producer can often choose from them with no audition at all."""
    lang = (x.lang or 'th')[:2]
    for m in fetch('/v1/models'):
        if m.get('can_do_text_to_speech') and any(l.get('language_id', '')[:2] == lang for l in m.get('languages', [])):
            print(f"model  {m['model_id']}  rate {m.get('model_rates', {}).get('character_cost_multiplier', '?')}")
    name = LANG_NAME.get(lang, lang)
    found = []
    for v in fetch('/v1/voices').get('voices', []):
        known = {str(l.get('language', ''))[:2] for l in v.get('verified_languages') or []}
        desc = (v.get('description') or '').replace('\n', ' ')
        if lang in known or name in desc or lang == (v.get('labels') or {}).get('language'):
            found.append(v)
            print(f"voice  {v['voice_id']}  {v['name'][:30]:<30}  {desc[:90]}")
    print(f"{len(found)} voices in your library speak {name}. More are in the shared library, but using one takes a voice slot on the account.")
    if x.previews:
        want = {n.strip() for n in (x.names or '').split(',') if n.strip()}
        out = Path(x.previews)
        out.mkdir(parents=True, exist_ok=True)
        for v in found:
            short = v['name'].split(' - ')[0].split()[-1]
            if v.get('preview_url') and (not want or short in want or v['name'] in want):
                with urllib.request.urlopen(v['preview_url'], timeout=60) as r:
                    (out / f'{short}.mp3').write_bytes(r.read())
                print(f"preview  {out / (short + '.mp3')}")
    print('OK')
    return 0


def tts(x):
    """[{n, who, t}] into one take a line, OUTDIR/NN.mp3. A line that changes costs only itself, and a line dropped from the script costs nothing, so tune length after hearing the real voices."""
    if not (x.a and x.b and x.voices):
        sys.exit('FAIL: tts needs SCRIPT.json OUTDIR --voices H=ID,G=ID')
    show = studio.load_show()
    ids = dict(p.split('=', 1) for p in x.voices.split(','))
    only = {int(n) for n in x.only.split(',')} if x.only else None
    model = x.model if x.model != 'scribe_v1' else 'eleven_v4'
    lines = [l for l in json.loads(Path(x.a).read_text(encoding='utf-8')) if not only or l['n'] in only]
    gone = sorted({l['who'] for l in lines} - set(ids))
    if gone:
        sys.exit(f"FAIL: no voice for {', '.join(gone)}. Give --voices {','.join(w + '=ID' for w in gone)}")
    out = Path(x.b)
    todo = [l for l in lines if x.force or not (out / f"{l['n']:02d}.mp3").exists()]
    if not todo:
        print(f'OK: all {len(lines)} takes exist, nothing spent')
        return 0
    chars = sum(len(l['t']) for l in todo)
    if not x.yes:
        b = balance()
        tail = f' · {b[0]:,} left' if b else ''
        print(f'QUOTE: {len(todo)} takes, {chars} characters, at most {chars * TTS_RATE.get(model, 1.0):,.0f} credits on {model}{tail}. Nothing spent; add --yes once the producer has approved.')
        return studio.EXIT_QUOTE
    code = (x.lang or show['lang'])[:2]
    for l in todo:
        body = json.dumps({'text': l['t'], 'model_id': model, 'language_code': code}).encode()
        call(show['root'], f'ElevenLabs TTS {model}', f"line {l['n']} {l['who']} · \"{l['t'][:40]}\"", f"/v1/text-to-speech/{ids[l['who']]}?output_format=mp3_44100_192", body, 'application/json', out / f"{l['n']:02d}.mp3", timeout=180)
    print(f'OK: {len(todo)} takes in {out}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['quota', 'isolate', 'scribe', 'align', 'sfx', 'music', 'voices', 'tts'])
    ap.add_argument('a', nargs='?')
    ap.add_argument('b', nargs='?')
    ap.add_argument('c', nargs='?')
    ap.add_argument('--note', default='')
    ap.add_argument('--lang')
    ap.add_argument('--speakers', type=int)
    ap.add_argument('--model', default='scribe_v1')
    ap.add_argument('--dur', type=float)
    ap.add_argument('--influence', type=float, default=0.5)
    ap.add_argument('--previews')
    ap.add_argument('--names')
    ap.add_argument('--voices')
    ap.add_argument('--only')
    ap.add_argument('--yes', action='store_true', help='spend the credits; without it a paid command only quotes')
    ap.add_argument('--force', action='store_true', help='replace an existing output (the old one goes to old/)')
    x = ap.parse_args(argv)

    if x.cmd == 'quota':
        studio.need('ELEVENLABS_API')
        b = balance()
        if not b:
            sys.exit(f'FAIL: {PROBLEM}')
        print(f'OK: {b[0]:,} of {b[1]:,} credits left ({b[2]})')
        return 0

    if x.cmd == 'voices':
        return voices(x)
    if x.cmd == 'tts':
        return tts(x)

    missing = {'isolate': not (x.a and x.b), 'scribe': not (x.a and x.b), 'align': not (x.a and x.b and x.c), 'sfx': not (x.a and x.b), 'music': not (x.a and x.b)}[x.cmd]
    if missing:
        ap.error(f'{x.cmd}: missing arguments, see --help')
    show = studio.load_show()     # no show.json, no ledger, no spending
    root = show['root']
    out = x.c if x.cmd == 'align' else x.b

    if Path(out).exists() and not x.force:
        print(f'OK: {out} already exists, nothing spent (--force to replace it)')
        return 0

    if x.cmd in ('isolate', 'scribe', 'align'):
        secs = duration(x.a)
        estimate = f'≈ {secs * PER_SECOND[x.cmd]:,.0f} credits for {secs / 60:.1f} min'
    elif x.cmd == 'music':
        estimate = f'≈ {(x.dur or 60) * PER_SECOND["music"]:,.0f} credits for {x.dur or 60:.0f} s'
    else:
        estimate = '6-24 credits with a set duration' if x.dur else 'about 55 credits with no set duration'
    if not x.yes:
        b = balance()
        tail = f' · {b[0]:,} left' if b else ('' if studio.secret('ELEVENLABS_API') else ' · ELEVENLABS_API is empty')
        print(f'QUOTE: {NAMES[x.cmd]} {estimate}{tail}. Nothing spent; add --yes once the producer has approved.')
        return studio.EXIT_QUOTE

    if x.cmd == 'isolate':
        body, ct = multipart({}, 'audio', x.a)
        # An hour of speech takes a while to process, and a timeout here would be charged anyway.
        cost = call(root, 'ElevenLabs Audio Isolation', f'{x.note} {Path(x.a).name}', '/v1/audio-isolation', body, ct, out, timeout=max(600, int(duration(x.a))))
    elif x.cmd == 'scribe':
        fields = {'model_id': x.model, 'diarize': 'true', 'num_speakers': x.speakers or show['speakers'], 'timestamps_granularity': 'word', 'tag_audio_events': 'false'}
        lang = x.lang or show['lang']
        if lang:
            fields['language_code'] = lang
        body, ct = multipart(fields, 'file', x.a)
        cost = call(root, f'ElevenLabs Scribe {x.model}', f'{x.note} {Path(x.a).name}', '/v1/speech-to-text', body, ct, out, timeout=max(600, int(duration(x.a))))
    elif x.cmd == 'align':
        body, ct = multipart({'text': Path(x.b).read_text(encoding='utf-8').strip()}, 'file', x.a)
        cost = call(root, 'ElevenLabs Forced Alignment', f'{x.note} {Path(x.a).name}', '/v1/forced-alignment', body, ct, out)
    elif x.cmd == 'sfx':
        payload = {'text': x.a, 'prompt_influence': x.influence, 'model_id': 'eleven_text_to_sound_v2'}
        if x.dur:
            payload['duration_seconds'] = x.dur
        cost = call(root, 'ElevenLabs SFX', f'{x.note} {Path(out).name} · "{x.a[:60]}"', '/v1/sound-generation', json.dumps(payload).encode(), 'application/json', out)
        pk = peak(out)
        if pk < 0.02:      # a real take came back near-silent twice with no error from the API
            aside = Path(out).with_name(f'{Path(out).stem}.near_silent{Path(out).suffix}')
            Path(out).replace(aside)    # moved, or a re-run would call it "already exists" and never try again
            print(f'FAIL: near-silent (peak {pk:.3f}). It was paid for and is not usable, so it is now {aside}. Reword the prompt and run again.')
            return 1
    elif x.cmd == 'music':
        payload = {'prompt': x.a, 'music_length_ms': int((x.dur or 60) * 1000), 'model_id': 'music_v1', 'force_instrumental': True}
        cost = call(root, 'ElevenLabs Music', f'{x.note} {Path(out).name} · {x.dur}s · "{x.a[:60]}"', '/v1/music', json.dumps(payload).encode(), 'application/json', out)
    print(f'OK: {out} (cost {cost})')
    return 0


if __name__ == '__main__':
    sys.exit(main())

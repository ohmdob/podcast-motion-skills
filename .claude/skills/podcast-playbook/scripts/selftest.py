#!/usr/bin/env python3
"""Checks the promises around money and keys, offline, against a fake ElevenLabs and a fake ComfyUI. No real call, no credit.

    python3 selftest.py

Run it after changing el.py, ideogram.py or studio.py. Each check names a promise: a paid call only runs with --yes, nothing retries, a re-run never pays twice,
a key is never printed, never reaches a storage host, and every paid call gets a ledger row.
"""
import contextlib, http.server, io, json, os, shutil, subprocess, sys, tempfile, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import el, ideogram, studio

KEY_E, KEY_C = 'sk_fake_elevenlabs_0123456789', 'comfy_fake_key_9876543210'
log, passed, failed = [], 0, 0
PNG = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082')


class Fake(http.server.BaseHTTPRequestHandler):
    mode = {}
    history = {}

    def log_message(self, *a):
        pass

    def send(self, code, body, ctype='application/json', headers=None):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        log.append(('GET', self.path, dict(self.headers), b''))
        if self.path.startswith('/v1/user/subscription'):
            return self.send(200, json.dumps({'character_count': 1000, 'character_limit': 131000, 'tier': 'creator'}).encode())
        if self.path.startswith('/v1/models'):
            return self.send(200, json.dumps([{'model_id': 'eleven_v4', 'can_do_text_to_speech': True, 'languages': [{'language_id': 'th'}], 'model_rates': {'character_cost_multiplier': 1.0}}]).encode())
        if self.path.startswith('/v1/voices'):
            return self.send(200, json.dumps({'voices': [{'voice_id': 'v1', 'name': 'Mali', 'description': 'A Thai voice'}]}).encode())
        outs = {'0_2': {'images': [{'filename': 'x.png', 'subfolder': '', 'type': 'output'}]}}
        if self.path.startswith('/api/history/'):
            pid = self.path.split('/')[-1]
            done = {'status': {'completed': True, 'status_str': 'success', 'messages': []}, 'outputs': outs}
            return self.send(200, json.dumps({pid: done} if Fake.mode.get('job_done', True) else {}).encode())
        if self.path.startswith('/api/queue'):
            return self.send(200, json.dumps({'queue_running': [[0, Fake.mode.get('alive', 'p1')]], 'queue_pending': []}).encode())
        if self.path.startswith('/api/job/'):       # Comfy Cloud's way of reporting
            return self.send(200, json.dumps({'status': Fake.mode.get('cloud_status', 'success')}).encode())
        if self.path.startswith('/api/jobs/'):
            lost = Fake.mode.get('cloud_status', 'success') != 'success'
            return self.send(200, json.dumps({'status': 'failed', 'outputs': {}} if lost else {'status': 'completed', 'outputs': outs}).encode())
        if self.path.startswith('/api/view'):
            if Fake.mode.get('redirect_to'):      # Comfy Cloud sends a picture from signed storage on another host
                self.send_response(302)
                self.send_header('Location', Fake.mode['redirect_to'])
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            return self.send(200, PNG, 'image/png')
        if self.path.startswith('/signed/'):
            return self.send(200, PNG, 'image/png')
        self.send(404, b'{}')

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        log.append(('POST', self.path, dict(self.headers), body))
        if Fake.mode.get('hangup'):
            self.close_connection = True
            self.connection.close()
            return
        if Fake.mode.get('refuse'):
            return self.send(401, json.dumps({'detail': f'bad key {KEY_E} {KEY_C}'}).encode())
        if self.path == '/api/prompt':
            return self.send(200, json.dumps({'prompt_id': 'p1'}).encode())
        self.send(200, b'ID3fake-audio-bytes', 'audio/mpeg', {'character-cost': '660'})


def check(name, ok, detail=''):
    global passed, failed
    print(('PASS  ' if ok else 'FAIL  ') + name + (f'  [{detail}]' if detail and not ok else ''))
    passed, failed = passed + bool(ok), failed + (not ok)


def call(fn, *args):
    """Run a tool's main() here, and hand back (exit code, everything it printed)."""
    buf = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = fn(list(args)) or 0
        except SystemExit as e:
            if isinstance(e.code, str):
                print(e.code)
                code = 1
            else:
                code = e.code or 0
    return code, buf.getvalue()


def posts(path=None):
    return [r for r in log if r[0] == 'POST' and (path is None or r[1] == path)]


def main():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_address[1]}'
    el.BASE = url
    tmp = Path(tempfile.mkdtemp())
    os.environ['PODCAST_ENV'] = str(tmp / '.env')
    studio.SKILL = tmp / 'not' / 'the' / 'skill'      # a real .env above the repo must not count here: it would pass as a key the test thinks is empty, and go to the fake server
    (tmp / '.env').write_text(f'# a comment\nexport ELEVENLABS_API="{KEY_E}"\nCOMFY_API={KEY_C}\nEMPTY=\n', encoding='utf-8')
    (tmp / 'show.json').write_text(json.dumps({'name': 't', 'lang': 'tha'}))
    os.chdir(tmp)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=60', str(tmp / 'in.wav')], check=True)
    ledger = tmp / 'data' / 'ledger.md'

    # .env
    check('.env: reads names, export and quotes', studio.secret('ELEVENLABS_API') == KEY_E and studio.secret('COMFY_API') == KEY_C)
    check('.env: a blank value counts as not set', studio.secret('EMPTY') is None)
    (tmp / 'sub').mkdir()
    (tmp / 'sub' / '.env').write_text('COMFY_API=\n')
    check('.env: blank in the nearer file falls through to the next', studio.secret('COMFY_API', tmp / 'sub') == KEY_C)
    (tmp / 'legacy').mkdir()
    (tmp / 'legacy' / '.env').write_text('OLD-STYLE=legacy\n')
    check('.env: the old hyphenated name still works', studio.secret('OLD_STYLE', tmp / 'legacy') == 'legacy')

    # money gate
    log.clear()
    code, out = call(el.main, 'isolate', 'in.wav', 'out.mp3')
    check('el: without --yes it quotes and exits 3', code == studio.EXIT_QUOTE and out.startswith('QUOTE:'), out)
    check('el: the quote is the measured rate (660 for a minute)', '≈ 660 credits' in out, out)
    check('el: a quote sends nothing paid', not posts() and not (tmp / 'out.mp3').exists())
    code, out = call(ideogram.main, 'gen', '--batch', str(_shots(tmp)), '--host', url)
    check('ideogram: without --yes it quotes and exits 3', code == studio.EXIT_QUOTE and out.startswith('QUOTE:') and not posts(), out)

    # a paid call, once
    log.clear()
    code, out = call(el.main, 'isolate', 'in.wav', 'out.mp3', '--yes', '--note', 'test')
    check('el: --yes spends once and writes the file', code == 0 and len(posts('/v1/audio-isolation')) == 1 and (tmp / 'out.mp3').exists(), out)
    check('el: the key goes in the header', posts()[0][2].get('Xi-Api-Key') == KEY_E)
    check('el: a ledger row with the cost', '| ElevenLabs Audio Isolation | test in.wav | 660 | ok |' in ledger.read_text(encoding='utf-8'))
    log.clear()
    code, out = call(el.main, 'isolate', 'in.wav', 'out.mp3', '--yes')
    check('el: an existing output pays nothing', code == 0 and not posts() and 'nothing spent' in out, out)
    code, out = call(el.main, 'isolate', 'in.wav', 'out.mp3', '--yes', '--force')
    check('el: --force keeps the old file in old/', list((tmp / 'old').glob('out-*.mp3')) != [], out)

    # a script into voices
    log.clear()
    (tmp / 'script.json').write_text(json.dumps([{'n': 1, 'who': 'H', 't': 'สวัสดี'}, {'n': 2, 'who': 'G', 't': 'ครับ'}], ensure_ascii=False), encoding='utf-8')
    code, out = call(el.main, 'tts', 'script.json', 'takes', '--voices', 'H=v1,G=v2')
    check('tts: without --yes it quotes and exits 3', code == studio.EXIT_QUOTE and out.startswith('QUOTE:') and not posts(), out)
    code, out = call(el.main, 'tts', 'script.json', 'takes', '--voices', 'H=v1')
    check('tts: a line with no voice stops before spending', code != 0 and not posts(), out)
    code, out = call(el.main, 'tts', 'script.json', 'takes', '--voices', 'H=v1,G=v2', '--yes')
    check('tts: one call a line, each with the key in the header', code == 0 and len(posts()) == 2 and posts()[0][2].get('Xi-Api-Key') == KEY_E, out)
    check('tts: each line gets a ledger row', ledger.read_text(encoding='utf-8').count('ElevenLabs TTS') == 2)
    log.clear()
    code, out = call(el.main, 'tts', 'script.json', 'takes', '--voices', 'H=v1,G=v2', '--yes')
    check('tts: takes that exist pay nothing', code == 0 and not posts() and 'nothing spent' in out, out)
    code, out = call(el.main, 'voices', '--lang', 'th')
    check('voices: casting sends nothing paid', code == 0 and not posts() and 'Mali' in out and 'eleven_v4' in out, out)

    # failures
    log.clear()
    Fake.mode = {'refuse': True}
    code, out = call(el.main, 'scribe', 'in.wav', 'bad.json', '--yes')
    check('el: an error from the service stops, with no retry', code != 0 and len(posts()) == 1, out)
    check('el: a key echoed back by a service is scrubbed', KEY_E not in out and KEY_C not in out and '***' in out, out)
    check('el: a failed call still gets a ledger row', 'failed: HTTP 401' in ledger.read_text(encoding='utf-8'))
    log.clear()
    Fake.mode = {'hangup': True}
    code, out = call(el.main, 'scribe', 'in.wav', 'lost.json', '--yes')
    check('el: a lost connection is UNKNOWN, not retried', code == studio.EXIT_UNKNOWN and out.startswith('UNKNOWN:') and len(posts()) == 1, out)
    check('el: a lost call gets a ledger row', 'unknown:' in ledger.read_text(encoding='utf-8'))
    Fake.mode = {}

    # ideogram: submit once, collect, and survive being stopped
    shots = _shots(tmp)
    log.clear()
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', url, '--yes')
    check('ideogram: --yes submits one job and saves the image', code == 0 and len(posts('/api/prompt')) == 1 and (tmp / 'pic.png').exists(), out)
    sent = json.loads(posts('/api/prompt')[0][3])
    check('ideogram: the key goes only in extra_data', sent['extra_data']['api_key_comfy_org'] == KEY_C and KEY_C not in json.dumps(sent['prompt']))
    check('ideogram: a ledger row with the price', '18.1 | ok |' in ledger.read_text(encoding='utf-8'))
    log.clear()
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', url, '--yes')
    check('ideogram: a re-run with the file there pays nothing', code == 0 and not posts('/api/prompt'), out)

    (tmp / 'pic.png').unlink()
    (tmp / 'data/comfy_pending').mkdir(exist_ok=True)
    (tmp / 'data/comfy_pending/p1.json').write_text(json.dumps({'prompt_id': 'p1', 'items': [{'node': '0_2', 'out': str(tmp / 'pic.png'), 'credits': 18.1, 'label': 'stopped run'}]}))
    log.clear()
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', url, '--yes')
    check('ideogram: a stopped run is collected, not paid for again', code == 0 and not posts('/api/prompt') and (tmp / 'pic.png').exists() and not list((tmp / 'data/comfy_pending').glob('*.json')), out)

    # the same promise for edit, and for gen --force, which a first version broke
    (tmp / 'src.png').write_bytes(PNG)
    (tmp / 'data/comfy_pending/p1.json').write_text(json.dumps({'prompt_id': 'p1', 'items': [{'node': '0_2', 'out': str(tmp / 'edited.png'), 'credits': 18.1, 'label': 'stopped edit'}]}))
    log.clear()
    code, out = call(ideogram.main, 'edit', 'src.png', 'edited.png', 'change one thing', '--host', url, '--yes')
    check('ideogram edit: a stopped run is collected, not paid for again', code == 0 and not posts('/api/prompt') and (tmp / 'edited.png').exists(), out)
    (tmp / 'data/comfy_pending/p1.json').write_text(json.dumps({'prompt_id': 'p1', 'items': [{'node': '0_2', 'out': str(tmp / 'pic.png'), 'credits': 18.1, 'label': 'stopped run'}]}))
    log.clear()
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', url, '--yes', '--force')
    check('ideogram gen --force: a stopped run is collected, not paid for again', code == 0 and not posts('/api/prompt'), out)

    # no Ideogram means asking, so nothing may quote it as if it could run
    saved = studio.secret('COMFY_API')
    (tmp / '.env').write_text(f'ELEVENLABS_API="{KEY_E}"\nCOMFY_API=\n', encoding='utf-8')
    log.clear()
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', url, '--force')
    check('ideogram: an empty key says ask the producer, with no quote', code != 0 and 'Ask the producer' in out and 'QUOTE' not in out, out)
    code, out = call(ideogram.main, 'edit', 'src.png', 'x.png', 'y', '--host', url)
    check('ideogram edit: an empty key says ask the producer, with no quote', code != 0 and 'Ask the producer' in out and 'QUOTE' not in out, out)
    (tmp / '.env').write_text(f'ELEVENLABS_API="{KEY_E}"\nCOMFY_API={saved}\n', encoding='utf-8')
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', 'http://127.0.0.1:9', '--force')
    check('ideogram: ComfyUI down says ask the producer, with no quote', code != 0 and 'Ask the producer' in out and 'QUOTE' not in out, out)

    (tmp / 'pic.png').unlink()
    Fake.mode = {'hangup': True}
    log.clear()
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', url, '--yes')
    check('ideogram: a lost connection while submitting is UNKNOWN', code == studio.EXIT_UNKNOWN and out.startswith('UNKNOWN:') and len(posts('/api/prompt')) == 1, out)
    Fake.mode = {}
    (tmp / 'data/comfy_pending/p1.json').unlink(missing_ok=True)

    # Comfy Cloud: signs in by header, reports its own way, and sends the picture from another host, which must never see the key
    storage = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
    threading.Thread(target=storage.serve_forever, daemon=True).start()
    ideogram.CLOUD_HOSTS = {'127.0.0.1'}
    Fake.mode = {'redirect_to': f'http://127.0.0.1:{storage.server_address[1]}/signed/x.png'}
    (tmp / 'pic.png').unlink(missing_ok=True)
    log.clear()
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', url, '--yes')
    check('cloud: submits one job and saves the picture', code == 0 and len(posts('/api/prompt')) == 1 and (tmp / 'pic.png').exists(), out)
    check('cloud: signs in with X-API-Key on its own routes', posts('/api/prompt')[0][2].get('X-Api-Key') == KEY_C)
    check('cloud: job status and result use its own routes', any(r[1].startswith('/api/job/') for r in log) and any(r[1].startswith('/api/jobs/') for r in log))
    signed = [r for r in log if r[1].startswith('/signed/')]
    check('cloud: the signed storage address is fetched', len(signed) == 1)
    check('cloud: the storage host never sees the key', signed and 'X-Api-Key' not in signed[0][2] and 'x-api-key' not in {k.lower() for k in signed[0][2]})
    (tmp / 'pic.png').unlink()
    Fake.mode = {'cloud_status': 'lost'}
    log.clear()
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', url, '--yes')
    check('cloud: a job that ends lost is reported, and not submitted again', code != 0 and len(posts('/api/prompt')) == 1 and not (tmp / 'pic.png').exists(), out)
    Fake.mode = {}
    storage.shutdown()
    ideogram.CLOUD_HOSTS = {'cloud.comfy.org'}
    check('host: Comfy Cloud is the default', studio.DEFAULT_COMFY == 'https://cloud.comfy.org' and ideogram.Comfy(studio.DEFAULT_COMFY).cloud and studio.comfy_host_problem(studio.DEFAULT_COMFY) is None)
    (tmp / 'pic.png').unlink(missing_ok=True)
    code, out = call(ideogram.main, 'gen', '--batch', str(shots), '--host', 'http://8.8.8.8:8188', '--yes')
    check('ideogram: the key is refused for plain http to a public address', code != 0 and 'refusing' in out, out)

    # nothing anywhere printed a key, including the ledger
    check('the ledger holds no key', KEY_E not in ledger.read_text(encoding='utf-8') and KEY_C not in ledger.read_text(encoding='utf-8'))

    # no show.json, no spending, because there would be nowhere to record it
    bare = Path(tempfile.mkdtemp())
    os.chdir(bare)
    shutil.copy(tmp / 'in.wav', bare / 'in.wav')
    log.clear()
    code, out = call(el.main, 'isolate', 'in.wav', 'o.mp3', '--yes')
    check('el: no show.json means no spending', code != 0 and not posts() and 'show.json' in out, out)
    os.chdir('/')
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(bare, ignore_errors=True)
    srv.shutdown()
    print(f"{'OK' if not failed else 'FAIL'}: {passed} passed, {failed} failed")
    return 1 if failed else 0


def _shots(tmp):
    p = tmp / 'shots.json'
    p.write_text(json.dumps([{'out': 'pic.png', 'prompt': 'a plain white cup on a table. No text, no people.'}]))
    return p


if __name__ == '__main__':
    sys.exit(main())

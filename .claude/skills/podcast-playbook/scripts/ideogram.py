#!/usr/bin/env python3
"""Ideogram 4.5 through Comfy Cloud's Partner Nodes (https://cloud.comfy.org), billed to the Comfy account behind COMFY-API, the key from platform.comfy.org.
The key goes only to Comfy, as X-API-Key and as api_key_comfy_org, and is never printed. It never goes to the storage host that a finished picture is fetched from.

    python3 ideogram.py gen --batch shots.json                   # [{out, prompt, size?, quality?, seed?, magic?}] as ONE queued job
    python3 ideogram.py edit IN.png OUT.png "change this detail" [--ref R.png] [--mode precise|edit] [--box x,y,w,h] [--pad .5] [--long 1024]
    python3 ideogram.py edit --batch fixes.json                  # [{in, out, prompt, box?, refs?, mode?, quality?, seed?}]
    common: [--quality medium] [--seed 42] [--host URL] [--yes] [--force]

Without --yes this only quotes, and exits 3 having spent nothing. `gen` skips an output that already exists, so a re-run pays only for what is missing;
--force replaces it and keeps the old one in old/. Batch paths are relative to the project; single-edit paths to the current folder.

Text-to-image is for new pictures. To change one detail in a picture you like, use `edit`: Precise Edit keeps every untouched pixel, costs the same and
cannot lose what you liked. --box crops a small detail, enlarges it, edits only that and pastes it back with a feathered edge.

A job can wait behind another for a long time, and it is billed whether or not anyone is still watching. So the job is written to data/comfy_pending/
before waiting. If this stops for any reason, run the same command again: it collects the job already paid for instead of submitting a new one.

Comfy Cloud by default. For a ComfyUI you run yourself: --host, or COMFY-HOST in .env. stdout ends with OK: · FAIL: · QUOTE: · UNKNOWN:
"""
import argparse, http.client, json, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path
import studio

GEN_CREDITS = {'low': 9.05, 'medium': 18.1, 'high': 60.35}    # measured on Edit; text-to-image is assumed to match until an invoice says otherwise
EDIT_CREDITS = {'very_low': 2.41, **GEN_CREDITS}
SERVICE = 'Ideogram 4.5 (Comfy)'
WAIT_LIMIT = 3 * 3600
CLOUD_HOSTS = {'cloud.comfy.org'}
JOB_FINISHED = {'success', 'completed'}
JOB_FAILED = {'error', 'non_retryable_error', 'lost', 'cancelled', 'failed'}     # any other status means it is still in flight


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class Comfy:
    """Comfy Cloud and a self-run ComfyUI take the same graph and the same /api paths. They differ in how you sign in, how a job reports back, and where a picture comes from."""

    def __init__(self, host):
        self.host = host.rstrip('/')
        self.cloud = urllib.parse.urlparse(self.host).hostname in CLOUD_HOSTS
        self.label = 'Comfy Cloud' if self.cloud else 'ComfyUI'

    def headers(self, extra=None):
        h = {'User-Agent': 'podcast-playbook', **(extra or {})}
        key = studio.secret('COMFY-API') if self.cloud else None
        if key:
            h['X-API-Key'] = key
        return h

    def get(self, path, timeout=120):
        with urllib.request.urlopen(urllib.request.Request(self.host + path, headers=self.headers()), timeout=timeout) as r:
            return r.read()

    def post(self, path, data, ctype, timeout=120):
        req = urllib.request.Request(self.host + path, data=data, headers=self.headers({'Content-Type': ctype}), method='POST')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()

    def fetch_picture(self, query):
        """Comfy Cloud answers with a redirect to a signed storage address. It is followed by hand, with no key: urllib would otherwise carry X-API-Key to the storage host."""
        req = urllib.request.Request(f'{self.host}/api/view?{query}', headers=self.headers())
        try:
            with urllib.request.build_opener(NoRedirect).open(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (301, 302, 303, 307, 308) or not e.headers.get('Location'):
                raise
            signed = e.headers['Location']
        with urllib.request.urlopen(urllib.request.Request(signed, headers={'User-Agent': 'podcast-playbook'}), timeout=300) as r:
            return r.read()

    def job_state(self, pid):
        """('waiting' | 'gone' | 'done', outputs, error text)."""
        if self.cloud:
            try:
                status = json.loads(self.get(f'/api/job/{pid}/status')).get('status', '')
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return 'gone', {}, ''
                raise
            if status not in JOB_FINISHED | JOB_FAILED:
                return 'waiting', {}, ''
            d = json.loads(self.get(f'/api/jobs/{pid}'))
            err = (d.get('execution_error') or {}).get('exception_message', '') or ('' if status in JOB_FINISHED else status)
            return 'done', d.get('outputs') or {}, err
        h = json.loads(self.get(f'/api/history/{pid}')).get(pid)
        if h and (h['status'].get('completed') or h['status'].get('status_str') == 'error'):
            err = next((m[1].get('exception_message', '') for m in h['status'].get('messages', []) if m[0] == 'execution_error'), '')
            return 'done', h.get('outputs', {}), err
        if not h:
            q = json.loads(self.get('/api/queue'))
            if not any(item[1] == pid for key in ('queue_running', 'queue_pending') for item in q.get(key, [])):
                return 'gone', {}, ''
        return 'waiting', {}, ''

    def has_ideogram(self):
        """Comfy Cloud has no per-node route, so it has to read the whole list."""
        return 'IdeogramTextToImageApi' in json.loads(self.get('/api/object_info' if self.cloud else '/api/object_info/IdeogramTextToImageApi', timeout=60))

    def upload(self, img):
        img = Path(img)
        b, name = uuid.uuid4().hex, f'pp_{uuid.uuid4().hex[:8]}_{img.name}'
        body = (f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: image/png\r\n\r\n'.encode()
                + img.read_bytes() + f'\r\n--{b}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{b}--\r\n'.encode())
        return json.loads(self.post('/api/upload/image', body, f'multipart/form-data; boundary={b}'))['name']


def host_of(x):
    host = x.host or studio.secret('COMFY-HOST') or studio.DEFAULT_COMFY
    problem = studio.comfy_host_problem(host)
    if problem:
        sys.exit(f'FAIL: {problem}')
    return host


ASK = 'Ask the producer which alternative to use: codex_image.py takes this same batch file, or their own photographs, or another service, or none.'


def ensure_available(comfy):
    """No Ideogram means asking the producer, so don't quote a service that can't run. Free."""
    if not studio.secret('COMFY-API'):
        sys.exit(f'FAIL: COMFY-API is empty, so there is no Ideogram. {ASK}')
    try:
        comfy.get('/api/queue', timeout=20)
    except urllib.error.HTTPError as e:
        why = 'COMFY-API was refused' if e.code in (401, 403) else f'it answered HTTP {e.code}'
        sys.exit(f'FAIL: {comfy.label} at {comfy.host}: {why}. Nothing was submitted. Check the key at platform.comfy.org. If it stays this way: {ASK}')
    except NET_ERRORS as e:
        sys.exit(f'FAIL: cannot reach {comfy.label} at {comfy.host} ({type(e).__name__}). Nothing was submitted. If it stays down: {ASK}')


NET_ERRORS = (urllib.error.URLError, OSError, http.client.HTTPException)


def graph_edit(names, prompt, mode, quality, seed, prefix):
    g = {str(i + 1): {'class_type': 'LoadImage', 'inputs': {'image': n}} for i, n in enumerate(names)}
    node = {'model': 'ideogram-4.5', 'model.prompt': prompt, 'model.quality': quality, 'model.seed': seed}
    for i in range(len(names)):
        node[f'model.images.image_{i + 1}'] = [str(i + 1), 0]
    if mode == 'edit':
        node['model.size'] = 'source'
        node['model.width'], node['model.height'] = 2048, 2048    # required by the node even when size is not 'custom'
    g['10'] = {'class_type': 'IdeogramEditApi' if mode == 'edit' else 'IdeogramPreciseEditApi', 'inputs': node}
    g['11'] = {'class_type': 'SaveImage', 'inputs': {'images': ['10', 0], 'filename_prefix': prefix}}
    return g


def prep_box(it):
    """Crop for --box. Returns the file to upload and the crop rectangle, or None when the whole picture goes."""
    if not it.get('box'):
        return it['src'], None
    from PIL import Image
    im = Image.open(it['src']).convert('RGB')
    pad, longest = it.get('pad', 0.5), it.get('long', 1024)
    x, y, w, h = it['box']
    x0, y0 = max(0, int(x - w * pad)), max(0, int(y - h * pad))
    x1, y1 = min(im.width, int(x + w * (1 + pad))), min(im.height, int(y + h * (1 + pad)))
    k = longest / max(x1 - x0, y1 - y0)
    tmp = Path(tempfile.mkdtemp()) / f"{Path(it['src']).stem}_box.png"
    im.crop((x0, y0, x1, y1)).resize((round((x1 - x0) * k), round((y1 - y0) * k)), Image.LANCZOS).save(tmp)
    return tmp, (x0, y0, x1, y1)


def write_result(item, data):
    out = Path(item['out'])
    out.parent.mkdir(parents=True, exist_ok=True)
    studio.keep_old(out)
    if not item.get('crop'):
        out.write_bytes(data)
        return
    from PIL import Image, ImageDraw, ImageFilter
    base = Image.open(item['src']).convert('RGB')
    x0, y0, x1, y1 = item['crop']
    tmp = Path(tempfile.mkdtemp()) / 'edited.png'
    tmp.write_bytes(data)
    patch = Image.open(tmp).convert('RGB').resize((x1 - x0, y1 - y0), Image.LANCZOS)
    f = max(4, min(x1 - x0, y1 - y0) // 12)
    mask = Image.new('L', patch.size, 0)
    ImageDraw.Draw(mask).rectangle([f, f, patch.width - f, patch.height - f], fill=255)
    base.paste(patch, (x0, y0), mask.filter(ImageFilter.GaussianBlur(f / 2)))
    base.save(out)


def collect(comfy, root, pending_file):
    """Wait for a submitted job and save what it made. Returns (saved outputs, bad, error text)."""
    job = json.loads(pending_file.read_text(encoding='utf-8'))
    pid = job['prompt_id']
    start = time.time()
    while True:
        try:
            state, outputs, err = comfy.job_state(pid)
        except NET_ERRORS as e:
            print(f'UNKNOWN: lost contact with {comfy.label} while waiting ({type(e).__name__}). Job {pid[:8]} is safe: run the same command again to collect it.')
            sys.exit(studio.EXIT_UNKNOWN)
        if state == 'gone':
            # The server no longer knows this job, for instance after a restart: it may have been charged, and there is nothing left to collect.
            for it in job['items']:
                studio.ledger(root, SERVICE, f"{it['label']} (job {pid[:8]} lost)", '?', 'unknown: job gone from the server')
            pending_file.unlink()
            return [], len(job['items']), f'job {pid[:8]} is gone from the server; it may have been charged'
        if state == 'done':
            break
        if time.time() - start > WAIT_LIMIT:
            print(f'UNKNOWN: job {pid[:8]} is still waiting after {WAIT_LIMIT // 3600} hours. Run the same command again to keep waiting; it will not pay twice.')
            sys.exit(studio.EXIT_UNKNOWN)
        time.sleep(job.get('poll', 4))
    err = studio.redact(err)
    saved, bad = [], 0
    for it in list(job['items']):
        imgs = outputs.get(it['node'], {}).get('images', [])
        if not imgs:
            bad += 1
            studio.ledger(root, SERVICE, it['label'], '?', f'not run: {err[:60]}')
        else:
            q = urllib.parse.urlencode({'filename': imgs[0]['filename'], 'subfolder': imgs[0].get('subfolder', ''), 'type': 'output'})
            try:
                data = comfy.fetch_picture(q)
            except NET_ERRORS as e:
                print(f'UNKNOWN: job {pid[:8]} finished and is paid for, but its picture could not be fetched ({type(e).__name__}). It is safe: run the same command again to collect it.')
                sys.exit(studio.EXIT_UNKNOWN)
            write_result(it, data)
            studio.ledger(root, SERVICE, it['label'], it['credits'], 'ok')
            print(it['out'], file=sys.stderr, flush=True)
            saved.append(str(Path(it['out']).resolve()))
        # What is done leaves the file, so a stop halfway collects only the rest.
        job['items'].remove(it)
        pending_file.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding='utf-8')
    pending_file.unlink()
    return saved, bad, err


def settle_pending(comfy, root):
    """Anything a stopped run left behind is collected before anything new is quoted, so a re-run can't pay twice."""
    d = root / 'data' / 'comfy_pending'
    done = set()
    for f in sorted(d.glob('*.json')) if d.is_dir() else []:
        saved, bad, err = collect(comfy, root, f)
        print(f'collected an earlier job: {len(saved)} saved, {bad} not {err[:120]}', file=sys.stderr)
        done.update(saved)
    return done


def submit(comfy, root, graph, items):
    key = studio.need('COMFY-API')
    body = json.dumps({'prompt': graph, 'client_id': 'podcast-playbook', 'front': True, 'extra_data': {'api_key_comfy_org': key}}).encode()
    try:
        pid = json.loads(comfy.post('/api/prompt', body, 'application/json'))['prompt_id']
    except urllib.error.HTTPError as e:
        # A job is checked before anything runs, so a refusal here has cost nothing. On Comfy Cloud, 402 means out of credits and 429 an inactive subscription.
        sys.exit(f'FAIL: {comfy.label} refused the job, nothing spent: HTTP {e.code} {studio.redact(e.read()[:600].decode("utf-8", "replace"))}')
    except NET_ERRORS as e:
        for it in items:
            studio.ledger(root, SERVICE, it['label'], '?', f'unknown: {type(e).__name__} while submitting')
        print(f'UNKNOWN: the connection ended while submitting ({type(e).__name__}). The job may be running and billed. Check your jobs on {comfy.host} before submitting again.')
        sys.exit(studio.EXIT_UNKNOWN)
    d = root / 'data' / 'comfy_pending'
    d.mkdir(parents=True, exist_ok=True)
    f = d / f'{pid}.json'
    f.write_text(json.dumps({'prompt_id': pid, 'items': items}, ensure_ascii=False, indent=1), encoding='utf-8')
    return f


def finish(good, total, credits, err):
    print(f"{'OK' if good == total else 'FAIL'}: {good}/{total} images, ≈ {credits:.1f} credits {err[:200] if good != total else ''}".rstrip())
    return 0 if good == total else 1


def gen(x, comfy, root):
    items = json.loads(Path(x.batch).read_text(encoding='utf-8'))
    for it in items:
        if not it.get('out') or not it.get('prompt'):
            sys.exit(f'FAIL: every item needs out and prompt: {str(it)[:120]}')
        q = it.get('quality', x.quality)
        if q not in GEN_CREDITS:
            sys.exit(f'FAIL: quality {q!r}; text-to-image takes {", ".join(GEN_CREDITS)}')
    ensure_available(comfy)
    done = settle_pending(comfy, root)
    # Something a stopped run just collected is what this run came for, even with --force.
    todo = [i for i in items if str((root / i['out']).resolve()) not in done and (x.force or not (root / i['out']).exists())]
    total = sum(GEN_CREDITS[i.get('quality', x.quality)] for i in todo)
    if not todo:
        print(f'OK: all {len(items)} already exist, nothing spent')
        return 0
    if not x.yes:
        print(f'QUOTE: {len(todo)} of {len(items)} images to generate, ≈ {total:.1f} Comfy credits. Nothing spent; add --yes once the producer has approved.')
        return studio.EXIT_QUOTE
    g, rows = {}, []
    for n, it in enumerate(todo):
        q = it.get('quality', x.quality)
        g[f'{n}_1'] = {'class_type': 'IdeogramTextToImageApi', 'inputs': {
            'model': 'ideogram-4.5', 'model.prompt': it['prompt'], 'model.size': it.get('size', '(2K) 2560x1440 (16:9)'),
            'model.quality': q, 'model.magic_prompt': it.get('magic', 'auto'), 'model.seed': it.get('seed', x.seed)}}
        g[f'{n}_2'] = {'class_type': 'SaveImage', 'inputs': {'images': [f'{n}_1', 0], 'filename_prefix': f"ideogram/{Path(it['out']).stem}"}}
        rows.append({'node': f'{n}_2', 'out': str(root / it['out']), 'credits': GEN_CREDITS[q],
                     'label': f"t2i {q} · {Path(it['out']).name} · \"{it['prompt'][:60]}\""})
    saved, bad, err = collect(comfy, root, submit(comfy, root, g, rows))
    return finish(len(saved), len(saved) + bad, total, err)


def edit(x, comfy, root):
    if x.batch:
        raw = json.loads(Path(x.batch).read_text(encoding='utf-8'))
        items = [{**r, 'src': root / r['in'], 'out': root / r['out'], 'refs': [root / p for p in r.get('refs', [])]} for r in raw]
    else:
        if not (x.a and x.b and x.c):
            sys.exit('FAIL: edit needs IN.png OUT.png "what to change", or --batch')
        it = {'src': Path(x.a).resolve(), 'out': Path(x.b).resolve(), 'prompt': x.c, 'refs': [Path(r).resolve() for r in x.ref], 'mode': x.mode, 'quality': x.quality, 'seed': x.seed}
        if x.box:
            it['box'] = [int(v) for v in x.box.split(',')]
            it['pad'], it['long'] = x.pad, x.long
        items = [it]
    for it in items:
        if not Path(it['src']).exists():
            sys.exit(f"FAIL: no such picture: {it['src']}")
        if it.get('quality', x.quality) not in EDIT_CREDITS:
            sys.exit(f"FAIL: quality {it.get('quality')!r}; edits take {', '.join(EDIT_CREDITS)}")
    ensure_available(comfy)
    done = settle_pending(comfy, root)
    items = [i for i in items if str(Path(i['out']).resolve()) not in done]
    if not items:
        print('OK: a stopped run had already paid for these, and they are collected. Nothing new spent.')
        return 0
    total = sum(EDIT_CREDITS[i.get('quality', x.quality)] for i in items)
    if not x.yes:
        print(f'QUOTE: {len(items)} edits, ≈ {total:.1f} Comfy credits. Nothing spent; add --yes once the producer has approved.')
        return studio.EXIT_QUOTE
    g, rows = {}, []
    for n, it in enumerate(items):
        up, crop = prep_box(it)
        names = [comfy.upload(p) for p in [up, *it.get('refs', [])]]
        mode, q = it.get('mode', 'precise'), it.get('quality', x.quality)
        sub = graph_edit(names, it['prompt'], mode, q, it.get('seed', x.seed), f"ideogram/{Path(it['out']).stem}")
        for k, node in sub.items():
            for v in node['inputs'].values():
                if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                    v[0] = f'{n}_{v[0]}'
            g[f'{n}_{k}'] = node
        rows.append({'node': f'{n}_11', 'out': str(it['out']), 'src': str(it['src']), 'crop': crop, 'credits': EDIT_CREDITS[q],
                     'label': f"{mode} {q} · {Path(it['src']).name}{' box ' + ','.join(map(str, it['box'])) if it.get('box') else ''} → {Path(it['out']).name} · \"{it['prompt'][:60]}\""})
    saved, bad, err = collect(comfy, root, submit(comfy, root, g, rows))
    return finish(len(saved), len(saved) + bad, total, err)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['gen', 'edit'])
    ap.add_argument('a', nargs='?')
    ap.add_argument('b', nargs='?')
    ap.add_argument('c', nargs='?')
    ap.add_argument('--batch')
    ap.add_argument('--ref', action='append', default=[])
    ap.add_argument('--mode', default='precise', choices=['precise', 'edit'])
    ap.add_argument('--box')
    ap.add_argument('--pad', type=float, default=0.5)
    ap.add_argument('--long', type=int, default=1024)
    ap.add_argument('--quality', default='medium')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--host')
    ap.add_argument('--yes', action='store_true', help='spend the credits; without it this only quotes')
    ap.add_argument('--force', action='store_true', help='gen: replace outputs that already exist (the old ones go to old/)')
    x = ap.parse_args(argv)
    if x.cmd == 'gen' and not x.batch:
        ap.error('gen needs --batch shots.json')
    root = studio.load_show()['root']     # no show.json, no ledger, no spending
    comfy = Comfy(host_of(x))
    try:
        return gen(x, comfy, root) if x.cmd == 'gen' else edit(x, comfy, root)
    except NET_ERRORS as e:
        sys.exit(f'FAIL: lost contact with {comfy.label} at {comfy.host} before anything was submitted ({type(e).__name__}). If it stays down: {ASK}')


if __name__ == '__main__':
    sys.exit(main())

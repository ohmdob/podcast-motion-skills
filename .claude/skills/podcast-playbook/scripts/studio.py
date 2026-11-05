#!/usr/bin/env python3
"""What every tool shares: where the project is, where the keys are, what the show is, and the paid-call ledger.

A project is a folder with a show.json (init_show.py makes one). Keys are never printed by anything here, and redact() scrubs them from
anything a service sends back. Paid tools end with one of: OK: · FAIL: · QUOTE: (nothing spent) · UNKNOWN: (may have been charged).
"""
import datetime, ipaddress, json, os, re, socket, stat, sys, urllib.parse
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
FONTS = SKILL / 'assets' / 'fonts'
SFX_LIB = SKILL / 'assets' / 'sfx'
MUSIC_LIB = SKILL / 'assets' / 'music'
TEMPLATES = SKILL / 'assets' / 'templates'
KEYS = ('ELEVENLABS-API', 'COMFY-API')
DEFAULT_COMFY = 'https://cloud.comfy.org'    # COMFY-HOST in .env to use a ComfyUI you run yourself
EXIT_QUOTE, EXIT_UNKNOWN = 3, 4

SHOW_DEFAULTS = {'name': '', 'mark': '', 'lang': 'tha', 'speakers': 2, 'fps': 25, 'face_split_x': 1000, 'body_split_x': 800, 'people': {}, 'looks': {}}

# Words the cut and the subtitles treat as filler. Thai is what has been run on a real episode; a show can add or replace any of these under "words" in show.json.
WORDS = {
    'tha': {'html': 'th', 'cold_label': 'ตัวอย่างในตอนนี้',
            'back': ['อืม', 'อือ', 'อ่า', 'อา', 'อ่ะ', 'อะ', 'เออ', 'เอ่อ', 'โอเค', 'ใช่', 'ใช่ๆ', 'ใช่ๆๆ', 'ค่ะ', 'คะ', 'อ๋อ', 'ครับ'],
            'srt_back': ['อืม', 'อ่า', 'โอเค', 'ใช่', 'ใช่ๆ', 'ใช่ๆๆ', 'ค่ะ', 'อ๋อ', 'เออ', 'อ่ะ', 'อื้อ'],
            'srt_drop': ['อ่ะ', 'เออ', 'เอ่อ', 'เอ้อ', 'อ่า', 'อะ', 'เอ้ย'],
            'srt_lead': ['อ่า', 'ใช่', 'ใช่ๆ', 'ใช่ๆๆ', 'โอเค', 'ค่ะ'],
            'srt_tail': r'(?:อะไรอย่างนี้|อะไรอย่างเงี้ย|อย่างเงี้ย)(?:ค่ะ|นะคะ)?$'},
    'eng': {'html': 'en', 'cold_label': 'In this episode',
            'back': ['mm', 'mhm', 'hmm', 'uh-huh', 'yeah', 'yep', 'right', 'okay', 'ok', 'uh', 'um'],
            'srt_back': ['mm', 'mhm', 'hmm', 'uh-huh', 'yeah', 'yep', 'right', 'okay', 'ok'],
            'srt_drop': ['um', 'uh', 'erm'],
            'srt_lead': ['yeah', 'right', 'okay', 'ok'],
            'srt_tail': None},
}


# ---------------------------------------------------------------- the project
def find_root(start=None):
    p = Path(start or Path.cwd()).resolve()
    if p.is_file():
        p = p.parent
    for d in [p, *p.parents]:
        if (d / 'show.json').exists():
            return d
    return None


def root_or_fail(start=None):
    r = find_root(start)
    if not r:
        sys.exit(f'FAIL: no show.json at or above {start or Path.cwd()}. Make one: python3 {Path(__file__).parent}/init_show.py <folder> --name "Show name"')
    return r


def load_show(start=None, required=True):
    r = root_or_fail(start) if required else find_root(start)
    if not r:
        return {**SHOW_DEFAULTS, 'root': None}
    return {**SHOW_DEFAULTS, **json.loads((r / 'show.json').read_text(encoding='utf-8')), 'root': r}


def words(show):
    base = WORDS.get(show['lang'], WORDS['eng'])
    return {**base, **show.get('words', {})}


def first_dir_with(glob, *dirs):
    """The first folder that holds a file matching glob, so an episode can override the show's library, and the show the skill's."""
    for d in dirs:
        if d and Path(d).is_dir() and any(Path(d).glob(glob)):
            return Path(d)
    return None


# ---------------------------------------------------------------- the keys
def env_files(start=None):
    """Where keys may live, nearest first: $PODCAST_ENV, then .env from here upward, then .env above the skill.
    That last one is what lets one shared file serve every show. It sits outside the skill folder on purpose: packaging a skill does not exclude .env."""
    seen, out = set(), []
    base = Path(start or Path.cwd()).resolve()
    cands = [Path(os.environ['PODCAST_ENV'])] if os.environ.get('PODCAST_ENV') else []
    cands += [d / '.env' for d in [base, *base.parents]] + [d / '.env' for d in SKILL.parents]
    for c in cands:
        if c not in seen and c.is_file():
            seen.add(c)
            out.append(c)
    return out


def parse_env(path):
    """NAME=value lines. The names hold a hyphen, so a shell cannot export or source them; that is why tools read the file themselves."""
    out = {}
    try:
        text = Path(path).read_text(encoding='utf-8-sig')
    except (OSError, UnicodeDecodeError):
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
            v = v[1:-1]
        out[k.strip()] = v
    return out


def secret(name, start=None):
    """The value, or None. A blank line counts as not set, so a show's own .env can leave a key to the shared file."""
    for f in env_files(start):
        v = parse_env(f).get(name)
        if v:
            return v
    return None


def secret_source(name, start=None):
    for f in env_files(start):
        if parse_env(f).get(name):
            return f
    return None


def need(name, start=None):
    v = secret(name, start)
    if not v:
        where = env_files(start)
        sys.exit(f'FAIL: {name} is empty. Set {name}= in {where[0] if where else SKILL.parents[2] / ".env"}')
    return v


def comfy_host_problem(url):
    """Why COMFY-API must not be sent to this address, or None. The key goes in the request body, so plain http is only acceptable on a network that stays private."""
    u = urllib.parse.urlparse(url)
    if u.scheme == 'https':
        return None
    host = u.hostname or ''
    if host == 'localhost' or host.endswith('.local'):
        return None
    try:
        addresses = {ipaddress.ip_address(a[4][0].split('%')[0]) for a in socket.getaddrinfo(host, None)}
    except (OSError, ValueError):
        return f'cannot resolve {host}, so cannot tell whether it is private'
    public = sorted(str(a) for a in addresses if a.is_global)
    return f'refusing to send COMFY-API over plain http to {host} ({public[0]}). Use https, or a private address.' if public else None


def loose_permissions(path):
    return bool(os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO))


def redact(text, start=None):
    text = str(text)
    for name in KEYS:
        v = secret(name, start)
        if v:
            text = text.replace(v, '***')
    return text


# ---------------------------------------------------------------- the ledger
def ledger(root, service, job, credits, result):
    """Every paid call gets a row, including the ones that failed or whose result we never saw."""
    path = Path(root) / 'data' / 'ledger.md'
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# Paid-call ledger\n\n| when | service | job | credits | result |\n|---|---|---|---|---|\n', encoding='utf-8')
    clean = lambda x: re.sub(r'[|\r\n]+', ' ', str(x)).strip()
    when = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    with path.open('a', encoding='utf-8') as f:
        f.write(f'| {when} | {clean(service)} | {clean(job)} | {clean(credits)} | {clean(result)} |\n')


def keep_old(out):
    """Move an existing output into old/ before replacing it, so a paid file is never lost to a re-run."""
    out = Path(out)
    if out.exists():
        old = out.parent / 'old'
        old.mkdir(exist_ok=True)
        n = len(list(old.glob(out.stem + '-*'))) + 1
        out.replace(old / f'{out.stem}-{n}{out.suffix}')

#!/usr/bin/env python3
"""Make a show's folder, an episode or a clip. Free. Never overwrites anything.

    python3 init_show.py FOLDER --name "Show name" [--mark "SHOW NAME"] [--lang tha] [--env]
    python3 init_show.py FOLDER --episode EP02
    python3 init_show.py FOLDER --clip EP02/C01_short_name

--mark is the show's name as set in type on screen. There is no logo step on purpose: never invent one.
--env makes a blank .env here. Without it, the show uses the shared .env at the root of the skills repo.
"""
import argparse, json, os, shutil, sys
from pathlib import Path
import studio


def put(path, text=None, template=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    if template:
        shutil.copy(studio.TEMPLATES / template, path)
    else:
        path.write_text(text, encoding='utf-8')
    print('  made', path)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('folder')
    ap.add_argument('--name')
    ap.add_argument('--mark')
    ap.add_argument('--lang', default='tha')
    ap.add_argument('--env', action='store_true')
    ap.add_argument('--episode')
    ap.add_argument('--clip')
    x = ap.parse_args()
    root = Path(x.folder).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    if not (root / 'show.json').exists():
        if not x.name:
            sys.exit(f'FAIL: no show.json in {root} yet, so give --name "Show name"')
        put(root / 'show.json', json.dumps({'name': x.name, 'mark': x.mark or x.name.upper(), 'lang': x.lang, 'speakers': 2, 'fps': 25, 'people': {'H': {'name': '', 'role': ''}, 'G': {'name': '', 'role': ''}}, 'looks': {}}, ensure_ascii=False, indent=2) + '\n')
        put(root / '.gitignore', '.env\nnode_modules/\n.DS_Store\n*.log\n.thumbnails/\n')
        put(root / 'data' / 'ledger.md', '# Paid-call ledger\n\n| when | service | job | credits | result |\n|---|---|---|---|---|\n')
        put(root / 'STYLES.md', template='STYLES.md')
        for d in ('1080p', 'transcripts', 'outputs', 'episodes', 'assets/music', 'assets/sfx'):
            (root / d).mkdir(parents=True, exist_ok=True)
    if x.env and put(root / '.env', template='env.example'):
        os.chmod(root / '.env', 0o600)

    if x.episode:
        f = root / 'episodes' / x.episode / 'full'
        for d in ('audio', 'build', 'assets_src'):
            (f / d).mkdir(parents=True, exist_ok=True)
        put(f / 'paper.json', template='paper.json')
        put(f / 'cards.json', template='cards.json')
        put(f / 'STORYBOARD.md', template='STORYBOARD.md')
        put(f / 'REVIEW.md', template='REVIEW.md')
    if x.clip:
        if '/' not in x.clip:
            sys.exit('FAIL: --clip takes EPxx/Cnn_short_name')
        ep, name = x.clip.split('/', 1)
        c = root / 'episodes' / ep / 'clips' / name
        (c / 'build').mkdir(parents=True, exist_ok=True)
        put(c / 'paper.json', template='paper_clip.json')
        put(c / 'cards.json', template='cards.json')
        put(c / 'STORYBOARD.md', template='STORYBOARD.md')
        put(c / 'REVIEW.md', template='REVIEW.md')
    print(f'OK: {root}')


if __name__ == '__main__':
    main()

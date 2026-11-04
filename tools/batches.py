"""batches.py: translator batches (references/translation.md). The English lands in script/ only through `merge`, which refuses a bad batch.
usage: batches.py split              writes work/tl/b001.tsv.. and terms_b001.txt for strings with no English; refuses to overwrite a batch
       batches.py check BATCH [..]   validates work/tl/BATCH.out.tsv, prints OK or the bad ids (the translator's check)
       batches.py merge BATCH [..]   check, then write the English (and to every identical table/code string) into script/
       batches.py story OUT          whole script as text, per chunk of ~30k characters, for synopsis readers
       batches.py fit TEXT [--box 17x3]  how a text wraps in a box
Input columns: id, speaker, form, limit, jp. Lines that are only ・！？ fill in by themselves at split."""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import extract
import fit

ROOT = Path(__file__).resolve().parents[1]
TL = ROOT / 'work/tl'
GLOSSARY = ROOT / 'glossary.md'
MAX_CHARS, MAX_LINES = 3500, 150
PUNCT = re.compile(r'^[・！？\s]+$')
# Portrait number (0a/11) -> name. From the unit tables' face byte (SYSTEM/10, offset 2) for playable units, by reading for the rest (docs/synopsis.md).
FACES = json.loads((ROOT / 'tools/faces.json').read_text(encoding='utf-8'))
MACRO = re.compile(r'\{[0-9A-F]{4}\}')


def speaker(s):
    f = s.get('face')
    if f is None or f == 104:  # 104 is the empty frame: a line with no portrait
        return ''
    return FACES.get(str(f), f'face{f}')


def form_limit(rel, s):
    """(form, the limit the checker holds it to, as text). Limits are docs/re/windows.md, measured in game."""
    if s.get('box'):
        return ('dlg' if s.get('face') not in (None, 104) else 'narration'), s['box']
    if s.get('cell'):
        return 'menu', f'{s["cell"] * 2}r{s["max"] // s["cell"]}'
    if rel == 'table/magic.json' and s['id'].endswith('.name'):
        return 'name', '14ch'  # the magic list window is 7 cells wide, narrower than the field's 8 words
    if s.get('max'):
        # code strings that outgrow their place go to the long table (engine.Long), so the limit is a window row, not the field
        room = -(-s['max'] * 2 // 38) * 38 if rel.startswith('code/') else s['max'] * 2
        return ('choice' if s.get('op') == '1d' else 'name' if s['max'] <= 8 else 'menu'), f'{room}ch'
    return 'menu', '38ch' if s.get('op') == '20' else '16ch'


def auto_english(jp):
    if PUNCT.match(jp):
        return re.sub('・+', '...', jp.replace('！', '!').replace('？', '?').replace('\n', ' ')).replace('　', ' ')
    return None


def shared_key(rel, s):
    """Identical table and code strings take one translation. Script lines stay separate: a speaker changes how they read."""
    return None if rel.startswith('scn/') else (s['jp'], s.get('max'), s.get('cell'))


def queue(docs):
    """Strings still needing a translator, tables before scripts (names and items first), in script order."""
    seen, out = set(), []
    for rel in sorted(docs, key=lambda r: (r.startswith('scn/'), r)):
        for s in docs[rel]['strings']:
            if s['en'] or not s['jp'].strip() or s.get('kind') or auto_english(s['jp']) is not None:
                continue
            k = shared_key(rel, s)
            if k is not None:
                if k in seen:
                    continue
                seen.add(k)
            out.append((rel, s))
    return out


def glossary_rows():
    """(jp terms, row) of the glossary's tables."""
    rows = []
    for line in GLOSSARY.read_text(encoding='utf-8').splitlines():
        cells = [c.strip() for c in line.strip('|').split('|')]
        if line.startswith('|') and len(cells) >= 2 and cells[0] not in ('JP', 'Japanese') and not set(cells[0]) <= set('-'):
            rows.append((re.split(r'\s*/\s*', cells[0]), cells, line))
    return rows


def split():
    docs = extract.load()
    TL.mkdir(parents=True, exist_ok=True)
    if list(TL.glob('b[0-9][0-9][0-9].tsv')):
        sys.exit('work/tl already has batches; move them away first')
    # the lines that fill in by themselves
    n = 0
    for rel, doc in docs.items():
        dirty = False
        for s in doc['strings']:
            a = auto_english(s['jp'])
            if a is not None and not s['en']:
                s['en'], dirty, n = a, True, n + 1
        if dirty:
            save(rel, doc)
    print(n, 'punctuation lines filled')
    rows = glossary_rows()
    q, batches, cur, chars = queue(docs), [], [], 0
    for rel, s in q:
        if cur and (chars + len(s['jp']) > MAX_CHARS or len(cur) >= MAX_LINES or rel.split('/')[0] != cur[-1][0].split('/')[0]):
            batches.append(cur)
            cur, chars = [], 0
        cur.append((rel, s))
        chars += len(s['jp'])
    if cur:
        batches.append(cur)
    for i, b in enumerate(batches, 1):
        name = f'b{i:03}'
        with open(TL / f'{name}.tsv', 'w', encoding='utf-8', newline='\n') as f:
            for rel, s in b:
                form, limit = form_limit(rel, s)
                f.write('\t'.join((s['id'], speaker(s), form, limit, s['jp'].replace('\n', ' / '))) + '\n')
        text = '\n'.join(s['jp'] for _, s in b)
        terms = [line for jps, _, line in rows if any(j and j in text for j in jps)]
        (TL / f'terms_{name}.txt').write_text('\n'.join(terms) + '\n', encoding='utf-8', newline='\n')
    print(len(batches), 'batches,', len(q), 'strings')


def save(rel, doc):
    (extract.OUT / rel).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')


def read_out(name):
    """{id: English} of a batch's output, with \\n as a break. Duplicate ids raise."""
    out = {}
    for line in (TL / f'{name}.out.tsv').read_text(encoding='utf-8-sig').splitlines():
        if not line.strip():
            continue
        if '\t' not in line:
            raise ValueError(f'no tab: {line[:40]}')
        k, v = line.split('\t', 1)
        if k in out:
            raise ValueError(f'{k}: twice')
        out[k] = v.replace('\\n', '\n').rstrip()
    return out


def problems(entry, en, avoid):
    """Why an English line can't go in. entry: the input row."""
    sid, _, form, limit, jp = entry
    bad = []
    if '\t' in en or '\\u' in en:
        bad.append('tab or \\u escape')
    if not all(0x20 <= ord(c) <= 0x7E or c == '\n' for c in en):
        bad.append('not plain ASCII: ' + ''.join(c for c in en if ord(c) > 0x7E)[:8])
    if sorted(MACRO.findall(jp.replace(' / ', ''))) != sorted(MACRO.findall(en)):
        bad.append('control words differ from the Japanese')
    if '{' in MACRO.sub('', en) or '}' in MACRO.sub('', en):
        bad.append('stray brace')
    if not en.strip():
        bad.append('empty')
    bad += fit.check(en, limit)
    for jps, wrong in avoid:
        if any(j and j in jp for j in jps) and wrong.lower() in en.lower():
            bad.append(f'glossary says avoid "{wrong}"')
    return bad


def avoid_terms():
    out = []
    for jps, cells, _ in glossary_rows():
        if len(cells) >= 5 and cells[4]:
            out += [(jps, w.strip()) for w in cells[4].split(',') if w.strip()]
    return out


def check(names):
    avoid, ok = avoid_terms(), True
    for name in names:
        rows = list(csv.reader(open(TL / f'{name}.tsv', encoding='utf-8', newline=''), delimiter='\t', quoting=csv.QUOTE_NONE))
        try:
            out = read_out(name)
        except (OSError, ValueError) as e:
            print(name, e)
            ok = False
            continue
        want = [r[0] for r in rows]
        for sid in sorted(set(want) - set(out)):
            print(f'{sid}: missing')
            ok = False
        for sid in sorted(set(out) - set(want)):
            print(f'{sid}: not in this batch')
            ok = False
        for r in rows:
            if r[0] in out:
                for b in problems(r, out[r[0]], avoid):
                    print(f'{r[0]}: {b}')
                    ok = False
        if ok:
            print(name, 'OK')
    return ok


def merge(names):
    if not check(names):
        sys.exit('not merged')
    docs = extract.load()
    new = {}
    for name in names:
        new.update(read_out(name))
    keys, dirty = {}, set()
    for rel, doc in docs.items():
        for s in doc['strings']:
            if s['id'] in new:
                s['en'] = new[s['id']]
                dirty.add(rel)
                k = shared_key(rel, s)
                if k is not None:
                    keys[k] = s['en']
    for rel, doc in docs.items():
        for s in doc['strings']:
            k = shared_key(rel, s)
            if k in keys and not s['en']:
                s['en'] = keys[k]
                dirty.add(rel)
    for rel in dirty:
        save(rel, docs[rel])
    print(len(new), 'lines merged into', len(dirty), 'files')


def story(out):
    docs = extract.load()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    chunks, cur, chars = [], [], 0
    for rel in sorted(r for r in docs if r.startswith('scn/')):
        strings = docs[rel]['strings']
        if not strings:
            continue
        if chars > 30000:
            chunks.append(cur)
            cur, chars = [], 0
        cur.append(f'\n# script {int(rel[4:8])}')
        for s in strings:
            if PUNCT.match(s['jp']):
                continue
            who = speaker(s) or ('-' if 'face' not in s else '-')
            cur.append(f'{who}: ' + s['jp'].replace('\n', ' '))
            chars += len(s['jp'])
    chunks.append(cur)
    for i, c in enumerate(chunks, 1):
        (out / f'story{i:02}.txt').write_text('\n'.join(c) + '\n', encoding='utf-8', newline='\n')
    print(len(chunks), 'chunks')


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'split':
        split()
    elif cmd == 'check':
        sys.exit(0 if check(args) else 1)
    elif cmd == 'merge':
        merge(args)
    elif cmd == 'story':
        story(args[0])
    elif cmd == 'fit':
        box = args[args.index('--box') + 1] if '--box' in args else '17x3'
        cols, page = map(int, box.split('x'))
        for row in fit.wrap(args[0], cols, page):
            print(f'{fit.width(row):3} {row}')
        print(fit.check(args[0], box) or 'fits')


if __name__ == '__main__':
    main()

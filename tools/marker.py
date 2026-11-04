"""marker.py: the marker text (pipeline phase 5). Each string becomes `[TAG] The quick brown fox..`, as long as its field or box
allows, so every box on screen shows which string it is and how far it reaches. TAG is a base-36 index over all strings.
usage: marker.py TAG [TAG..]   prints id and Japanese of each tag. build.py --marker uses text()."""
import json
import sys
from pathlib import Path

import engine
import extract

ROOT = Path(__file__).resolve().parents[1]
FILL = 'The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs. '
BOX, RCOL = 114, 38  # dialogue: 3 rows of 38 letters (19 cells), docs/re/font.md
DIGITS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
# The name-entry data isn't text to mark: its real English goes in as it is (docs/re/font.md).
SKIP_KINDS = ('grid', 'menu', 'name')
NAMES = ('Zen', 'Prah', 'MichetteXyz1', 'Cla', 'Prica', 'Dom', 'Abel')


def tag(i):
    return DIGITS[i // 1296 % 36] + DIGITS[i // 36 % 36] + DIGITS[i % 36]


def tags(docs):
    """{string id: tag}, stable over the sorted documents."""
    ids = [s['id'] for rel in sorted(docs) for s in docs[rel]['strings']]
    return {sid: tag(i) for i, sid in enumerate(ids)}


def _macros(jp):
    return ''.join(jp[i:i + 6] for i in range(len(jp)) if jp[i] == '{')


def _fit(head, letters, cap):
    """head + filler to `letters` letters, cut until it encodes in `cap` words (when given)."""
    mac = _macros(head)
    plain = head[:head.find('{')] if mac else head
    n = max(letters - len(plain), 0)
    t = plain + mac + (FILL * 3)[:n]
    while cap is not None and len(engine.encode(t)) > cap and n > 0:
        n -= 1
        t = plain + mac + (FILL * 3)[:n]
    while cap is not None and len(engine.encode(t)) > cap and len(plain) > 1:
        plain = plain[:-1]
        t = plain + mac
    return t


def text(s, t, scale=1.0):
    """The marker for string s with tag t. scale < 1 shortens script lines to fit the script buffer."""
    head = f'[{t}]' + _macros(s['jp'])
    if s.get('cell'):
        rows = s['max'] // s['cell']
        return '\n'.join(_fit(head if r == 0 else f'r{r}', s['cell'] * 2, s['cell']) for r in range(rows))
    if s.get('max'):
        jprows = s['jp'].split('\n')
        if len(jprows) > 1:  # explicit rows stay rows: same count of breaks, even share of the words
            each = (s['max'] - len(jprows) + 1) // len(jprows)
            return '\n'.join(_fit(head if r == 0 else f'r{r}', each * 2, each) for r in range(len(jprows)))
        return _fit(head, s['max'] * 2, s['max'])
    if s['op'] == '20':
        return _fit(head, RCOL, 19)
    if s['op'] == '08/15':
        return _fit(head, 16, 8)
    # Dialogue: as long as the Japanese would come out in English, fills whole rows, no \n (a row that fills exactly wraps by itself).
    n = min(BOX, max(len(head), int(len(s['jp']) * 2.6 * scale)))
    return _fit(head, n, BOX // 2)


def build_docs(docs):
    """A copy of docs with each string's `out` set to its marker; scripts shrink their lines to fit the buffer."""
    tg = tags(docs)
    leaves = None
    for rel, doc in docs.items():
        group = rel.split('/')[0]
        keep = [s for s in doc['strings'] if s.get('kind') in SKIP_KINDS]
        for s in keep:
            s['out'] = s['en'] or s['jp']
        for s, name in zip([s for s in keep if s['kind'] == 'name'], NAMES):  # odd and even lengths, to see the half cell an odd one leaves
            s['out'] = name + '＿' * (6 - len(engine.encode(name)))
        for scale in (1.0, 0.8, 0.6, 0.45, 0.3, 0.2, 0.1, 0):
            for s in doc['strings']:
                if s not in keep:
                    s['out'] = text(s, tg[s['id']], scale)
            if group != 'scn':
                break
            if leaves is None:
                leaves = extract.dat_leaves(1)['SCENARIO']
            x = leaves[doc['source'].split(':')[1]]
            try:
                extract.script_apply(x, doc['strings'], 'out', engine.encode)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f'{rel}: markers do not fit the script buffer')
    return docs


def main():
    docs = extract.load()
    tg = tags(docs)
    rev = {v: k for k, v in tg.items()}
    byid = {s['id']: s for d in docs.values() for s in d['strings']}
    for t in sys.argv[1:]:
        sid = rev.get(t.upper())
        print(t, sid, json.dumps(byid[sid]['jp'], ensure_ascii=False) if sid else '?')


if __name__ == '__main__':
    main()

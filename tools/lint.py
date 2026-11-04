"""lint.py: every string in script/ against the English rules (references/pipeline.md, Checks). Prints errors and a count, exit 1 on any.
The batch check's rules (batches.problems: fit, control words, ASCII, glossary Avoid) run here over the whole script, plus what only a whole
script can show. usage: lint.py"""
import json
import re
import sys
from pathlib import Path

import batches
import engine
import extract
import fit

ROOT = Path(__file__).resolve().parents[1]
KEEP = ROOT / 'script/keep_jp.txt'  # one id and reason per line: Japanese that stays on purpose
JP = re.compile('[぀-ヿ一-鿿]')
ORDINAL = re.compile(r'\{[0-9A-F]{4}\}(st|nd|rd|th)\b')
STUB = 6  # a dialogue text's last row under this many letters is one orphaned word


def keep_list():
    if not KEEP.exists():
        return set()
    return {l.split(None, 1)[0] for l in KEEP.read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')}


def errors(docs=None):
    docs = docs or extract.load()
    keep, avoid, out = keep_list(), batches.avoid_terms(), []
    for rel, doc in docs.items():
        for s in doc['strings']:
            sid, jp, en = s['id'], s['jp'], s['en']
            if not jp.strip():
                continue
            if not en:
                if sid not in keep:
                    out.append(f'{sid}: no English')
                continue
            if s.get('kind'):  # name-entry data: hand-placed, full-width on purpose. It only has to fill its field exactly.
                if len(engine.encode(en)) != s['max']:
                    out.append(f'{sid}: {len(engine.encode(en))} words, the field is {s["max"]}')
                continue
            form, limit = batches.form_limit(rel, s)
            out += [f'{sid}: {b}' for b in batches.problems((sid, '', form, limit, jp.replace('\n', ' / ')), en, avoid)]
            if JP.search(en):
                out.append(f'{sid}: Japanese in the English')
            if ORDINAL.search(en):
                out.append(f'{sid}: ordinal glued to a variable')
            # A stray blank. Japanese padding needs no copy (names, indents); code strings place theirs by hand to centre a row.
            if not rel.startswith('code/') and ((en[0] == ' ' and jp[0] not in ' 　') or (en[-1] == ' ' and jp[-1] not in ' 　')):
                out.append(f'{sid}: leading or trailing blank the Japanese lacks')
            if s.get('box'):
                cols, page = map(int, s['box'].split('x'))
                last = en.split('\n')[-1]  # a short row after a forced break is the writer's choice
                rows = fit.wrap(last, cols, page)
                if len(rows) > 1 and fit.width(rows[-1]) < STUB:
                    out.append(f'{sid}: last row is only "{rows[-1]}"')
    return out


def main():
    bad = errors()
    for line in bad:
        print(line)
    print(len(bad), 'lint errors')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

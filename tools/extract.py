"""extract.py: every string of both discs -> script/, and back. Layouts and evidence: docs/re/text.md.

script/scn/NNNN.json   a scenario script (SCENARIO/NNNN)
script/table/*.json    data tables (TABLES)
script/code/*.json     EXE and overlays (CODE)
Each file: {source, copies, strings: [{id, jp, en, ...}]}; copies lists every disc location holding the same bytes.
Strings: `\\n` = word 0x0010, {XXXX} = a control word. `max` = words the field holds; `cell` = words per row of a
fixed-layout field, whose rows are split by `\\n` here and padded with `　` on the way back.

usage: extract.py [--force]. Never overwrites script/ without --force, since that would lose the English."""
import hashlib
import json
import struct
import sys
from pathlib import Path

import dat
import psi

ROOT = Path(__file__).resolve().parents[1]
ORIG = ROOT / 'work/orig'
OUT = ROOT / 'script'
BLANK = 0x8140
DATS = 'SYSTEM SCENARIO BATTLE EVENT'.split()  # SOUND holds no text
EXE = {1: 'SLPS_029.62', 2: 'SLPS_029.63'}

# name: (leaf, head size, row size, {field: (offset in row, words, cell)}). A counted field: u16 count, then its words.
# With a cell, count is always the capacity; without, count is the length and the rest stays padded.
_HELP = {'text': (0, 57, 19)}
_UNIT = {'name': (0xE, 6, None)}
TABLES = {
    'weapon': ('SYSTEM/5.0', 0x10, 0x8E, {'name': (0, 8, None), 'desc': (0x12, 38, 19)}),
    'sweapon': ('SYSTEM/5.1', 0x10, 0x88, {'name': (0, 7, None), 'desc': (0x12, 19, 19), 'effect': (0x3A, 38, 19)}),
    'armor': ('SYSTEM/5.2', 0x10, 0x6E, {'name': (0, 8, None), 'desc': (0x12, 38, 19)}),
    'magic': ('SYSTEM/5.3', 0x10, 0x4E, {'name': (2, 8, None), 'desc': (0x14, 28, 28)}),
    'unit10': ('SYSTEM/10', 0x10, 0x50, _UNIT),
    'unit11': ('SYSTEM/11', 0x10, 0x50, _UNIT),
    'unit12': ('SYSTEM/12', 0x10, 0x50, _UNIT),
    'enemy5': ('BATTLE/5.0', 0x40, 0x50, _UNIT),
    'enemy6': ('BATTLE/6.0', 0x40, 0x50, _UNIT),
    'enemy7': ('BATTLE/7.0', 0x40, 0x50, _UNIT),
    'help_shop': ('SYSTEM/6', 0x10, 0x74, _HELP),
    'help_stage': ('SYSTEM/13.3', 0x10, 0x74, _HELP),
    'help_levelup': ('SYSTEM/15.4', 0x10, 0x74, _HELP),
    'help_battle': ('BATTLE/0.9', 0x10, 0x74, _HELP),
    'help_free': ('EVENT/80.3', 0x10, 0x74, _HELP),
}
# name: (file, load address, header skipped, areas of counted strings by RAM address, big-endian uncounted fields).
# An area bounds where psi.walk is trusted: outside them its hits are code (tools/recon_counted.py).
CODE = {
    'slps': (EXE[1], 0x80010000, 0x800, [(0x80011484, 0x800114B0), (0x80072D7C, 0x80073640), (0x80075EF0, 0x800763D0),
                                         (0x80076DE8, 0x80076FA0)],
             [(0x800111DC, 142, 'grid'), (0x800113FC, 10, 'menu')] + [(0x80011414 + 16 * i, 6, 'name') for i in range(7)]),
    '2nd': ('2ND.BIN', 0x800EB000, 0, [(0x8012E768, 0x8012E7C0), (0x8012ED48, 0x8012F090)], []),
    '3rd': ('3RD.BIN', 0x80110800, 0, [(0x80111420, 0x80111440), (0x8011B250, 0x8011B870)], []),
    '4th': ('4TH.BIN', 0x800EB000, 0, [(0x800FD564, 0x800FD5C0)], []),
    '5th': ('5TH.BIN', 0x800EB000, 0, [(0x800F16DC, 0x800F17C0)], []),
}


def _cells(words, cell):
    """Fixed-layout words -> rows split by \\n, each without its trailing blanks."""
    rows = [list(words[i:i + cell]) for i in range(0, len(words), cell)]
    for r in rows:
        while r and r[-1] == BLANK:
            r.pop()
    while rows and not rows[-1]:
        rows.pop()
    return '\n'.join(psi.decode(r) for r in rows)


def _uncells(text, cell, cap, enc):
    words = []
    for row in text.split('\n'):
        r = enc(row)
        words += r + [BLANK] * (-len(r) % cell if r else cell)
    if len(words) > cap:
        raise ValueError(f'{text!r} needs {len(words)} words, the field holds {cap}')
    return words + [BLANK] * (cap - len(words))


def table_strings(name, x):
    _, head, row, fields = TABLES[name]
    out = []
    for r in range((len(x) - head) // row):
        for f, (off, cap, cell) in fields.items():
            p = head + r * row + off
            n = struct.unpack_from('<H', x, p)[0]
            if n == 0:
                continue
            if n > cap:
                raise ValueError(f'{name} row {r} {f}: count {n} over the field size {cap}')
            words = struct.unpack_from(f'<{n}H', x, p + 2)
            if all(w == BLANK for w in words):
                continue
            s = {'id': f'{name}:{r}.{f}', 'jp': _cells(words, cell) if cell else psi.decode(words), 'en': '', 'max': cap}
            if cell:
                s['cell'] = cell
            out.append(s)
    return out


def table_apply(name, x, strings, field, enc):
    _, head, row, fields = TABLES[name]
    b = bytearray(x)
    for s in strings:
        r, f = s['id'].split(':')[1].split('.')
        off, cap, cell = fields[f]
        p = head + int(r) * row + off
        words = _uncells(s[field], cell, cap, enc) if cell else enc(s[field])
        if len(words) > cap:
            raise ValueError(f'{s["id"]}: {len(words)} words, the field holds {cap}')
        struct.pack_into(f'<H{cap}H', b, p, len(words), *words, *[BLANK] * (cap - len(words)))
    return bytes(b)


def code_strings(name, x):
    _, base, skip, areas, fixed = CODE[name]
    tag = lambda a: f'{name}:{a:08x}'
    out = []
    for a, n, kind in fixed:
        p = a - base + skip
        words = struct.unpack_from(f'>{n}H', x, p)
        out.append({'id': tag(a), 'jp': psi.decode(words), 'en': '', 'max': n, 'order': 'be', 'kind': kind})
    for lo, hi in areas:
        area = x[lo - base + skip:hi - base + skip]
        for off, words in psi.walk(area):
            if any(w != BLANK for w in words):
                out.append({'id': tag(lo + off), 'jp': psi.decode(words), 'en': '', 'max': len(words)})
    return out


def code_apply(name, x, strings, field, enc):
    _, base, skip, _, _ = CODE[name]
    b = bytearray(x)
    for s in strings:
        p = int(s['id'].split(':')[1], 16) - base + skip
        words = enc(s[field])
        if len(words) > s['max']:
            raise ValueError(f'{s["id"]}: {len(words)} words, the field holds {s["max"]}')
        if s.get('order') == 'be':
            struct.pack_into(f'>{s["max"]}H', b, p, *words, *[BLANK] * (s['max'] - len(words)))
        else:
            struct.pack_into(f'<H{len(words)}H', b, p, len(words), *words)
    return bytes(b)


def script_strings(tag, x):
    out = []
    for t in psi.tokenize(x)[0]:
        if t.words is not None:
            op = f'{t.op:02x}' if t.sub is None else f'{t.op:02x}/{t.sub:02x}'
            s = {'id': f'{tag}:{t.off:05x}', 'op': op, 'jp': psi.decode(t.words), 'en': ''}
            if t.op == 0x1D:
                s['max'] = 15  # script-format.md: choice labels past 15 words are dropped
            out.append(s)
    return out


def script_apply(x, strings, field, enc):
    return psi.rebuild(x, {int(s['id'].split(':')[1], 16): enc(s[field]) for s in strings})


def dat_leaves(disc):
    """{DAT name: {leaf path: bytes}} of one disc's pristine tree."""
    return {n: dict(dat.walk((ORIG / f'd{disc}/{n}.DAT').read_bytes(), n)) for n in DATS}


def locate():
    """Over both discs: {leaf hash: [locations like d1:SYSTEM/5.0]} and {location: bytes}."""
    where, data = {}, {}
    for disc in (1, 2):
        for n, leaves in dat_leaves(disc).items():
            for p, x in leaves.items():
                where.setdefault(hashlib.sha1(x).digest(), []).append(f'd{disc}:{p}')
                data[f'd{disc}:{p}'] = x
    return where, data


def extract_all():
    """{relative json path: document}, from the pristine tree only."""
    where, data = locate()
    docs = {}
    copies = lambda x: where[hashlib.sha1(x).digest()]
    done = set()
    for loc, x in data.items():
        if x[:8] != b'PSI22.00' or loc in done:
            continue
        done.update(copies(x))
        num = int(loc.split('/')[1])
        strings = script_strings(f's{num}', x)
        if strings:
            docs[f'scn/{num:04}.json'] = {'source': loc, 'copies': copies(x), 'strings': strings}
    for name, (leaf, *_) in TABLES.items():
        x = data[f'd1:{leaf}']
        docs[f'table/{name}.json'] = {'source': f'd1:{leaf}', 'copies': copies(x), 'strings': table_strings(name, x)}
    for name, (fname, *_) in CODE.items():
        x = (ORIG / f'd1/{fname}').read_bytes()
        d2 = EXE[2] if fname == EXE[1] else fname
        assert (ORIG / f'd2/{d2}').read_bytes() == x, f'{fname} differs between discs'
        docs[f'code/{name}.json'] = {'source': f'd1:{fname}', 'copies': [f'd1:{fname}', f'd2:{d2}'], 'strings': code_strings(name, x)}
    return docs


def load():
    """Every script/ document as {relative path: document}."""
    return {p.relative_to(OUT).as_posix(): json.loads(p.read_text(encoding='utf-8')) for p in sorted(OUT.rglob('*.json'))}


def text_files(disc, field='jp', enc=psi.encode, docs=None):
    """Disc files rebuilt from script/ with `field` as the text: {file name: bytes}. Field 'jp' gives the original."""
    docs = docs or load()
    pre = f'd{disc}:'
    leaves = dat_leaves(disc)
    repl = {n: {} for n in DATS}
    files = {}
    for rel, doc in docs.items():
        group, stem = rel.split('/')
        here =[c[len(pre):] for c in doc['copies'] if c.startswith(pre)]
        if not here:
            continue
        if group == 'code':
            x = (ORIG / f'd{disc}/{here[0]}').read_bytes()
            files[here[0]] = code_apply(stem[:-5], x, doc['strings'], field, enc)
            continue
        x = leaves[here[0].split('/')[0]][here[0]]
        new = (script_apply(x, doc['strings'], field, enc) if group == 'scn'
               else table_apply(stem[:-5], x, doc['strings'], field, enc))
        for p in here:
            repl[p.split('/')[0]][p] = new
    for n in DATS:
        files[f'{n}.DAT'] = dat.rebuild((ORIG / f'd{disc}/{n}.DAT').read_bytes(), n, repl[n])
    return files


def main():
    if OUT.exists() and '--force' not in sys.argv:
        sys.exit(f'{OUT} exists; --force overwrites it and every translation in it')
    n = 0
    for rel, doc in extract_all().items():
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
        n += len(doc['strings'])
    print(n, 'strings')


if __name__ == '__main__':
    main()

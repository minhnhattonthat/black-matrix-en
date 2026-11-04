"""text_sweep.py: Japanese runs (tools/recon_text.py filter, both byte orders) that extract.py doesn't cover, over every
leaf and file of both discs. Writes tests/text_noise.tsv: every line is a hit reviewed as not text (docs/re/text.md).
usage: text_sweep.py [--write]: exit 1 if the hits differ from that list, --write replaces it. tests/test_extract.py runs the same check."""
import hashlib
import sys
from pathlib import Path

import extract
import psi
import recon_text

NOISE = Path(__file__).resolve().parents[1] / 'tests/text_noise.tsv'


def covered(rel, x):
    """Byte ranges of x that extract.py owns, for one script/ document path."""
    group, stem = rel.split('/')
    name = stem[:-5]
    if group == 'scn':
        return [(0, len(x))]
    if group == 'table':
        _, head, row, fields = extract.TABLES[name]
        return [(head + r * row + off, head + r * row + off + 2 + 2 * cap)
                for r in range((len(x) - head) // row) for off, cap, _ in fields.values()]
    _, base, skip, areas, fixed = extract.CODE[name]
    out = [(a - base + skip, a - base + skip + 2 * n) for a, n, _ in fixed]
    for lo, hi in areas:
        out += [(lo - base + skip, hi - base + skip)]
    return out


def uncovered(x, ranges):
    """Runs in x outside ranges, as (order, offset, text)."""
    marks = bytearray(len(x))
    for a, b in ranges:
        marks[a:b] = b'\1' * (b - a)
    for order in ('le', 'be'):
        for off, s in recon_text.scan(x, order):
            if not any(marks[off:off + 2 * len(s)]):
                yield order, off, s


def picture(x):
    """Scripts (their text is tokenized, not scanned) and leaves whose bytes are pixels, cell maps or sound."""
    return (x[:8] == b'PSI22.00' or x[:4] in (b'pBAV', b'pQES', b'MHA ', b'MHD2', b'SCP\0')
            or (x[0] in (0, 1, 0x11, 0x91) and x[1:4] == bytes(3) and x[4:8] == b'\x10\0\0\0'))


def sweep(locs):
    """Noise lines for the distinct leaves in locs {location: bytes}; ranges come from extract_all's documents."""
    owned = {}
    for rel, doc in extract.load().items():
        for c in doc['copies']:
            owned[c] = rel
    seen, out = set(), []
    for loc, x in locs.items():
        h = hashlib.sha1(x).digest()
        if h in seen or picture(x):
            continue
        seen.add(h)
        ranges = covered(owned[loc], x) if loc in owned else []
        out += [f'{loc}\t{off:#x}\t{order}\t{s}' for order, off, s in uncovered(x, ranges)]
    return out


def all_locations():
    _, data = extract.locate()
    for disc in (1, 2):
        for p in sorted((extract.ORIG / f'd{disc}').iterdir()):
            if p.suffix in ('.BIN',) or p.name in extract.EXE.values():
                data[f'd{disc}:{p.name}'] = p.read_bytes()
    return data


def main():
    lines = sweep(all_locations())
    print(len(lines), 'hits outside the extracted text')
    if '--write' in sys.argv:
        NOISE.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        return
    new = set(lines) ^ set(NOISE.read_text(encoding='utf-8').splitlines())
    if new:
        sys.exit('differs from the reviewed list:\n' + '\n'.join(sorted(new)))


if __name__ == '__main__':
    main()

"""Which text window each script text opens in: the last `16 (#n)` before it, walking each script's tokens in order.
usage: recon_windows.py   prints per window number: texts, longest JP row, most rows, which scripts; and any text with no 16 before it."""
import collections
import struct
import sys

import dat
import psi

ROOT = 'work/orig/d1/SCENARIO.DAT'


def walk(b):
    """Yield (window number or None, token) for each text token."""
    cur = None
    for t in psi.tokenize(b)[0]:
        if t.op == 0x16:
            # E operand: `1, pad, imm32, 0` when constant
            ops = [v for k, v in t.parts if k == 'a']
            cur = struct.unpack('<I', ops[0])[0] if len(ops) == 1 else 'expr'
        elif t.op == 0x19:
            cur = None
        if t.words is not None:
            yield cur, t


def main():
    stat = collections.defaultdict(lambda: [0, 0, 0, set()])
    for n, b in enumerate(dat.unpack(open(ROOT, 'rb').read())):
        if b[:8] != b'PSI22.00':
            continue
        for w, t in walk(b):
            key = (w, f'{t.op:02x}' if t.sub is None else f'{t.op:02x}/{t.sub:02x}')
            rows = psi.decode(t.words).split('\n')
            s = stat[key]
            s[0] += 1
            s[1] = max(s[1], max(len(r) for r in rows))
            s[2] = max(s[2], len(rows))
            s[3].add(n)
    for k, s in sorted(stat.items(), key=lambda kv: -kv[1][0]):
        print(k, 'texts', s[0], 'longest', s[1], 'rows', s[2], 'scripts', len(s[3]), sorted(s[3])[:6])


if __name__ == '__main__':
    main()

"""hexw.py: hex + Shift-JIS view of a DAT leaf or file, words little-endian (big with --be).
usage: hexw.py [--disc N] [--be] LEAF[:COUNT[:START]].. where LEAF is SYSTEM/5.0 or a file name like 3RD.BIN"""
import sys
from pathlib import Path

import dat
import pak

ROOT = Path(__file__).resolve().parents[1]


def leaves(disc, name):
    """{path: bytes} of every leaf of one DAT."""
    out = {}
    for i, f in enumerate(dat.unpack((ROOT / f'work/orig/d{disc}/{name}.DAT').read_bytes())):
        if f:
            out.update({p: x for p, _, x in pak.walk(f, f'{name}/{i}')})
    return out


def char(w):
    try:
        c = bytes((w >> 8, w & 255)).decode('cp932') if w >= 0x8140 else '..'
    except UnicodeDecodeError:
        return '..'
    return c if len(c) == 1 else '..'


def main():
    args = sys.argv[1:]
    disc, be = 1, False
    if args[0] == '--disc':
        disc, args = int(args[1]), args[2:]
    if args[0] == '--be':
        be, args = True, args[1:]
    for spec in args:
        k, *rest = spec.split(':')
        n, s = (int(v, 0) for v in (rest + ['0x100', '0'][len(rest):]))
        x = leaves(disc, k.split('/')[0])[k] if '/' in k else (ROOT / f'work/orig/d{disc}/{k}').read_bytes()
        print(k, hex(len(x)))
        for i in range(s, min(s + n, len(x)), 16):
            row = x[i:i + 16]
            t = ''.join(char(row[j] << 8 | row[j + 1] if be else row[j] | row[j + 1] << 8) for j in range(0, len(row) - 1, 2))
            print(f'{i:06x} {row.hex(" ", 2)} {t}')


if __name__ == '__main__':
    main()

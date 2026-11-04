"""Recon: compare the two discs' data files and summarise each .DAT archive.
usage: recon_dat.py   (needs work/extracted/disc1|disc2 from disc.py x)"""
import hashlib, os, re, struct, sys

ROOT = 'work/extracted'
KANA = re.compile(rb'(?:[\x82][\x9f-\xf1]|[\x83][\x40-\x96]){4,}')


def sha(b):
    return hashlib.sha1(b).hexdigest()[:10]


def table(data):
    """Parse the 00-style table: u32 count, u32 shift, count x (u16 off, u16 size). None if it doesn't hold."""
    count, shift = struct.unpack_from('<II', data)
    if shift != 11 or not 0 < count < 2000 or 8 + 4 * count > 2048 * 8:
        return None
    ents = [struct.unpack_from('<HH', data, 8 + 4 * i) for i in range(count)]
    pos = None
    for off, size in ents:
        if size == 0:
            continue
        if pos is not None and off != pos:
            return None
        pos = off + size
    return ents


def main():
    for name in sorted(os.listdir(f'{ROOT}/disc1')):
        p1, p2 = f'{ROOT}/disc1/{name}', f'{ROOT}/disc2/{name}'
        names = name
        if not os.path.isfile(p1):
            continue
        a = open(p1, 'rb').read()
        b = open(p2, 'rb').read() if os.path.exists(p2) else None
        same = 'same' if a == b else ('DIFF' if b is not None else 'disc1 only')
        print(f'{names:14} {len(a):10d} {sha(a)} {same} kana-runs={len(KANA.findall(a))} head={a[:16].hex()}')
        if name.endswith('.DAT'):
            for d, blob in (('d1', a), ('d2', b)):
                if blob is None:
                    continue
                ents = table(blob)
                if ents is None:
                    print(f'  {d}: not the 00-style table')
                    continue
                last = max(o + s for o, s in ents)
                nonempty = sum(1 for o, s in ents if s)
                print(f'  {d}: {len(ents)} entries, {nonempty} non-empty, last sector {last}, file sectors {len(blob) // 2048}')
            if b is not None and a != b:
                ea, eb = table(a), table(b)
                if ea and eb and len(ea) == len(eb):
                    diff = [i for i in range(len(ea))
                            if a[ea[i][0] * 2048:(ea[i][0] + ea[i][1]) * 2048] != b[eb[i][0] * 2048:(eb[i][0] + eb[i][1]) * 2048]]
                    print(f'  entries differing between discs: {len(diff)}: {diff[:60]}')


if __name__ == '__main__':
    sys.exit(main())

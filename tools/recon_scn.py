"""Recon: dump a SCENARIO.DAT sub-file as hex + decoded Shift-JIS runs, and summarise headers.
usage: recon_scn.py sum | recon_scn.py dump N [START [LEN]]"""
import re, struct, sys
sys.path.insert(0, 'tools')
import dat

SJIS = re.compile(rb'(?:[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]|[\x20-\x7e])+')


def main():
    d = open('work/extracted/disc1/SCENARIO.DAT', 'rb').read()
    files = dat.unpack(d)
    if sys.argv[1] == 'sum':
        kinds = {}
        for i, f in enumerate(files):
            kinds.setdefault(f[:8], []).append(i)
        for k, v in kinds.items():
            print(k, len(v), v[:30])
        for i, f in enumerate(files[:80]):
            if f[:3] == b'PSI':
                print(i, len(f), struct.unpack_from('<II', f, 8), len(SJIS.findall(f)))
    else:
        f = files[int(sys.argv[2])]
        start = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0
        n = int(sys.argv[4], 0) if len(sys.argv) > 4 else 1024
        for r in range(start, min(start + n, len(f)), 32):
            line = f[r:r + 32]
            print(f'{r:06x} {line.hex(" ", 2)}')
        print()
        for m in SJIS.finditer(f, start, start + n):
            if len(m.group()) >= 4:
                print(f'{m.start():06x} {m.group().decode("cp932", "replace")}')


if __name__ == '__main__':
    main()

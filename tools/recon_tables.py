"""Recon: find function-pointer tables (runs of code addresses) in the EXE and overlays.
usage: recon_tables.py FILE LOAD [MINRUN]   (FILE with a PS-X header is handled)"""
import struct, sys


def main():
    path, load = sys.argv[1], int(sys.argv[2], 16)
    minrun = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    d = open(path, 'rb').read()
    if d[:8] == b'PS-X EXE':
        d = d[0x800:]
    n = len(d) // 4
    w = struct.unpack_from(f'<{n}I', d)
    lo, hi = 0x80010000, 0x80200000
    i = 0
    while i < n:
        j = i
        while j < n and (lo <= w[j] < hi and w[j] & 3 == 0 or (w[j] == 0 and j > i)):
            j += 1
        if j - i >= minrun:
            nz = [x for x in w[i:j] if x]
            if len(set(nz)) >= 3:
                print(f'{load + i * 4:08x} len {j - i:4d} distinct {len(set(nz)):4d} min {min(nz):08x} max {max(nz):08x} first {" ".join(f"{x:08x}" for x in w[i:i + 4])}')
        i = max(j, i + 1)


if __name__ == '__main__':
    main()

"""List code that touches an address range, through $gp or a lui pair (mips.py xref takes one exact address).
usage: recon_gprefs.py LO HI [FILE LOAD]   e.g. 0x8007E840 0x8007E848, or a BSS span to find what sits above a buffer."""
import struct
import sys

GP = 0x8007E820
BASES = {'lui': 0}


def scan(path, load, skip, lo, hi):
    d = open(path, 'rb').read()[skip:]
    lui = {}
    for p in range(0, len(d) & ~3, 4):
        w = struct.unpack_from('<I', d, p)[0]
        op, rs, rt, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        a = load + p
        if op == 0x0F:
            lui[rt] = (imm << 16, a)
            continue
        if op in (0x09, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
            s = imm - 0x10000 if imm >= 0x8000 else imm
            t = None
            if rs == 28:
                t = GP + s
            elif rs in lui and a - lui[rs][1] < 64:
                t = (lui[rs][0] + s) & 0xFFFFFFFF
            if t is not None and lo <= t < hi:
                yield a, op, t


def main():
    lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
    path, load, skip = 'work/extracted/disc1/SLPS_029.62', 0x80010000, 0x800
    if len(sys.argv) > 3:
        path, load, skip = sys.argv[3], int(sys.argv[4], 16), 0
    for a, op, t in scan(path, load, skip, lo, hi):
        print(f'{a:08x} op{op:02x} -> {t:08x}')


if __name__ == '__main__':
    main()

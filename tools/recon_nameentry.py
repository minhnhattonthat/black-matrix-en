"""Where the name-entry screen comes from: every jal to the functions around the grid code, and what calls them.
usage: recon_nameentry.py ADDR [ADDR..]   lists jal callers of each address in the EXE and overlays."""
import struct
import sys

FILES = [('work/extracted/disc1/SLPS_029.62', 0x80010000, 0x800), ('work/extracted/disc1/2ND.BIN', 0x800EB000, 0),
         ('work/extracted/disc1/3RD.BIN', 0x80110800, 0), ('work/extracted/disc1/4TH.BIN', 0x800EB000, 0),
         ('work/extracted/disc1/5TH.BIN', 0x800EB000, 0)]


def callers(addr):
    want = 0x0C000000 | ((addr >> 2) & 0x3FFFFFF)
    for path, load, skip in FILES:
        d = open(path, 'rb').read()[skip:]
        for p in range(0, len(d) & ~3, 4):
            if struct.unpack_from('<I', d, p)[0] == want:
                yield path.rsplit('/', 1)[1], load + p


def prologue(addr, path_load=FILES[0]):
    """Walk back to the addiu sp,-N that opens the function holding addr (EXE only)."""
    path, load, skip = path_load
    d = open(path, 'rb').read()[skip:]
    p = addr - load
    while p > 0:
        w = struct.unpack_from('<I', d, p)[0]
        if w >> 16 == 0x27BD and w & 0x8000:
            return load + p
        p -= 4
    return None


if __name__ == '__main__':
    for a in sys.argv[1:]:
        a = int(a, 16)
        f = prologue(a)
        print(f'{a:08x} in function {f:08x}')
        for name, c in callers(f):
            print(f'  {name} {c:08x}')

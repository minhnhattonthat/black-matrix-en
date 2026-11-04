"""Recon: every call to the DAT loaders (0x80018154, 0x80018250: a0 DAT, a1 entry, a2 dest) with constant a0/a1, in the EXE and overlays.
DAT numbers: order in the EXE table (0 SYSTEM, 1 SOUND?, 2 SCENARIO, 3 EVENT?, 4 BATTLE?, as seen in the output)."""
import struct, sys
sys.path.insert(0, 'tools')
import mips

FILES = [('EXE', None, None), ('2ND', 'work/extracted/disc1/2ND.BIN', 0x800EB000), ('3RD', 'work/extracted/disc1/3RD.BIN', 0x80110800),
         ('4TH', 'work/extracted/disc1/4TH.BIN', 0x800EB000), ('5TH', 'work/extracted/disc1/5TH.BIN', 0x800EB000)]
LOAD = {0x80018154, 0x80018250}
for name, path, load in FILES:
    if path:
        c = open(path, 'rb').read()
    else:
        c, load = mips.load_exe()
    n = len(c) // 4
    w = struct.unpack_from(f'<{n}I', c)
    for i, x in enumerate(w):
        if x >> 26 != 3 or (0x80000000 | ((x & 0x3FFFFFF) << 2)) not in LOAD:
            continue
        a0 = a1 = None
        for j in range(max(0, i - 8), min(n, i + 2)):
            y = w[j]
            if y >> 26 == 9 and (y >> 21) & 31 == 0:  # addiu r, zero, imm
                rt = (y >> 16) & 31
                if rt == 4:
                    a0 = y & 0xFFFF
                if rt == 5:
                    a1 = y & 0xFFFF
        print(f'{name} {load + i * 4:08x} dat={a0} entry={a1}')

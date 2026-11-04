"""Recon: find the movie-name pointer table in the EXE, then the code that indexes it."""
import struct, sys
sys.path.insert(0, 'tools')
import mips

c, l = mips.load_exe()
n = len(c) // 4
w = struct.unpack_from(f'<{n}I', c)
names = {0x80010f7c: 'DEMO02', 0x80010fa4: 'STAFF', 0x800111ac: 'PROLOGUE', 0x800111c4: 'OPENING', 0x80011198: '0101'}
for i, x in enumerate(w):
    if x in names:
        print(hex(l + i * 4), names[x])
tab = next(l + i * 4 for i, x in enumerate(w) if x == 0x800111c4)
print('table', hex(tab), [hex(v) for v in w[(tab - l) // 4:(tab - l) // 4 + 34]][:4])
for pc, kind in mips.xrefs(c, l, tab):
    print(hex(pc), kind)
for t in (tab - 4, tab + 4, tab - 8):
    for pc, kind in mips.xrefs(c, l, t):
        print('near', hex(t), hex(pc), kind)

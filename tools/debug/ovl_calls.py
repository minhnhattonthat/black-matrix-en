"""Recon: where the EXE calls into overlay space (>= 0x800EB000) or loads overlays; also every op handler's non-fetch calls.
Prints: `jal`s and `lui+addiu` constants reaching overlay entry candidates, with the containing op handler if known."""
import struct, sys
sys.path.insert(0, 'tools')
import mips

c, l = mips.load_exe()
n = len(c) // 4
w = struct.unpack_from(f'<{n}I', c)
tabs = {'main': (0x80076F90, 0x31), '08': (0x80077054, 0x3F), '09': (0x80077150, 0x32), '0a': (0x80077218, 0x46), '0b': (0x80077334, 0x18)}
handlers = {}
for k, (b, m) in tabs.items():
    for i, h in enumerate(struct.unpack_from(f'<{m}I', c, b - l)):
        if h:
            handlers.setdefault(h, []).append(f'{k}/{i:02x}')
order = sorted(handlers)


def owner(pc):
    best = None
    for h in order:
        if h <= pc:
            best = h
        else:
            break
    return ','.join(handlers[best]) if best and pc - best < 0x400 else '-'


for i, x in enumerate(w):
    pc = l + i * 4
    if x >> 26 == 3:
        t = 0x80000000 | ((x & 0x3FFFFFF) << 2)
        if t >= 0x800EB000:
            print(f'{pc:08x} jal {t:08x} owner {owner(pc)}')
print('--- handler calls')
for h in order:
    calls = []
    for j in range(0, 80):
        x = w[(h - l) // 4 + j]
        if x >> 26 == 3:
            calls.append(f'{0x80000000 | ((x & 0x3FFFFFF) << 2):x}')
        if x == 0x03E00008:
            break
    print(','.join(handlers[h]), f'{h:x}', ' '.join(calls))

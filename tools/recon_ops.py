"""Recon: derive each script handler's operand signature from the order of its calls to the fetch helpers.
Walks a handler linearly from its entry to the first `jr $ra` beyond the last forward branch.
usage: recon_ops.py [OP_HEX ...]   no args = every table"""
import struct, sys
sys.path.insert(0, 'tools')
import mips

FETCH = {0x8004f74c: 'w', 0x8004f768: 'L', 0x8004f7b0: 'U', 0x8004f7f8: 'E'}
# base table plus the four sub-tables selected by ops 8..11 (dispatch at 0x8004fe4c)
TABLES = {'main': (0x80076f90, 0x31), 'op8': None}


def handler_sig(code, load, entry, limit=800):
    sig, calls = [], []
    i = 0
    maxbranch = entry
    while i < limit:
        pc = entry + i * 4
        off = pc - load
        if off < 0 or off + 4 > len(code):
            break
        w = struct.unpack_from('<I', code, off)[0]
        op, rs, rt, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if op == 3:
            t = (pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
            if t in FETCH:
                sig.append(FETCH[t])
            else:
                calls.append(t)
        if op in (4, 5, 6, 7) or (op == 1 and rt in (0, 1)):
            t = pc + 4 + mips.s16(imm) * 4
            maxbranch = max(maxbranch, t)
        if op == 2:
            t = (pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
            if entry < t < entry + limit * 4:
                maxbranch = max(maxbranch, t)
        if w == 0x03E00008 and pc >= maxbranch:
            break
        i += 1
    return ''.join(sig), calls


def main():
    code, load = mips.load_exe()
    want = {int(x, 16) for x in sys.argv[1:]}
    n = 0xE0
    tab = struct.unpack_from(f'<{n}I', code, 0x80076f90 - load)
    for op, h in enumerate(tab):
        if want and op not in want:
            continue
        if h == 0 or not 0x80010000 <= h < 0x80080000:
            continue
        sig, calls = handler_sig(code, load, h)
        print(f'{op:02x} {h:08x} {sig or "-":12} calls {" ".join(f"{c:08x}" for c in calls[:8])}')


if __name__ == '__main__':
    main()

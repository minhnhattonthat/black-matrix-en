"""RE helpers for the PS1 EXE and overlays.
usage: mips.py dis ADDR COUNT [FILE LOAD]   disassemble (default: the Disc 1 EXE)
       mips.py xref ADDR [FILE LOAD]        lui/addiu|ori|load/store pairs and j/jal that reach ADDR
       mips.py str TEXT [FILE]              find a Shift-JIS string and pointers to it
Not named re.py: with tools/ on the path that shadows the stdlib."""
import struct, sys
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

EXE = 'work/extracted/disc1/SLPS_029.62'


def load_exe(path=EXE):
    """(bytes, load address) with the 0x800 PS-X header skipped."""
    d = open(path, 'rb').read()
    if d[:8] != b'PS-X EXE':
        raise ValueError('not a PS-X EXE')
    return d[0x800:], struct.unpack_from('<I', d, 0x18)[0]


def md():
    return Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)


def dis(code, load, addr, count):
    off = addr - load
    for i in range(count):
        word = code[off + i * 4:off + i * 4 + 4]
        if len(word) < 4:
            break
        got = list(md().disasm(word, addr + i * 4))
        print(f'{addr + i * 4:08x}: {word[::-1].hex()}  ' + (f'{got[0].mnemonic} {got[0].op_str}' if got else '.word'))


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def xrefs(code, load, target):
    """Addresses of code that builds or calls target. Tracks lui per register over a short window."""
    out = []
    n = len(code) // 4
    words = struct.unpack_from(f'<{n}I', code)
    hi = {}
    for i, w in enumerate(words):
        pc = load + i * 4
        op = w >> 26
        rs, rt, imm = (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if op == 0x0F:  # lui
            hi[rt] = (imm << 16, i)
        elif rs in hi and i - hi[rs][1] < 32:
            base = hi[rs][0]
            if op in (0x09, 0x08) or 0x20 <= op <= 0x2B:  # addiu/addi, loads, stores
                if (base + s16(imm)) & 0xFFFFFFFF == target:
                    out.append((pc, 'lui+imm'))
            elif op == 0x0D and (base | imm) == target:  # ori
                out.append((pc, 'lui+ori'))
        if op in (2, 3) and ((pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2)) == target:
            out.append((pc, 'jal' if op == 3 else 'j'))
        if w == target:
            out.append((pc, 'data word'))
    return out


def main():
    cmd = sys.argv[1]
    if cmd == 'dis':
        addr, count = int(sys.argv[2], 16), int(sys.argv[3])
        if len(sys.argv) > 5:
            code, load = open(sys.argv[4], 'rb').read(), int(sys.argv[5], 16)
        else:
            code, load = load_exe()
        dis(code, load, addr, count)
    elif cmd == 'xref':
        target = int(sys.argv[2], 16)
        if len(sys.argv) > 4:
            code, load = open(sys.argv[3], 'rb').read(), int(sys.argv[4], 16)
        else:
            code, load = load_exe()
        for pc, kind in xrefs(code, load, target):
            print(f'{pc:08x} {kind}')
    elif cmd == 'str':
        path = sys.argv[3] if len(sys.argv) > 3 else EXE
        d = open(path, 'rb').read()
        needle = sys.argv[2].encode('cp932')
        p = -1
        while (p := d.find(needle, p + 1)) >= 0:
            print(hex(p))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()

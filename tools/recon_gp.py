"""Recon: list instructions touching a $gp-relative slot; helps find every user of a script global.
usage: recon_gp.py OFFSET_HEX [FILE LOAD]   gp = 0x8007e820"""
import struct, sys
sys.path.insert(0, 'tools')
import mips

GP = 28


def main():
    off = int(sys.argv[1], 16)
    if len(sys.argv) > 3:
        code, load = open(sys.argv[2], 'rb').read(), int(sys.argv[3], 16)
    else:
        code, load = mips.load_exe()
    n = len(code) // 4
    words = struct.unpack_from(f'<{n}I', code)
    for i, w in enumerate(words):
        op, rs, imm = w >> 26, (w >> 21) & 31, w & 0xFFFF
        if rs == GP and imm == off and (0x20 <= op <= 0x2B or op == 0x09):
            print(f'{load + i * 4:08x} op {op:#04x} rt {(w >> 16) & 31}')


if __name__ == '__main__':
    main()

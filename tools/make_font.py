"""make_font.py: asm/font7x14.bin from the X11 misc-fixed 7x14 BDF. 95 glyphs (0x20-0x7E), 14 bytes each, one byte per
row, pixels in bits 7..1. The half-width hook (asm/halfwidth.asm) puts two of them in one 14-px cell.
usage: make_font.py work/dl/font/7x14.bdf   Source and licence: docs/fonts.md."""
import sys
from pathlib import Path

W, H = 7, 14
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'asm/font7x14.bin'


def parse(bdf):
    lines = iter(bdf.splitlines())
    descent, glyphs, code = 0, {}, 0
    for line in lines:
        if line.startswith('FONT_DESCENT'):
            descent = int(line.split()[1])
        elif line.startswith('ENCODING'):
            code = int(line.split()[1])
        elif line.startswith('BBX'):
            bw, bh, bx, by = map(int, line.split()[1:])
        elif line == 'BITMAP':
            cell = bytearray(H)
            top = H - descent - by - bh
            for r in range(bh):
                bits = int(next(lines)[:2], 16) >> bx
                if 0 <= top + r < H:
                    cell[top + r] = bits & 0xFE
            glyphs[code] = bytes(cell)
    return glyphs


def main():
    glyphs = parse(Path(sys.argv[1]).read_text(encoding='latin-1'))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(b''.join(glyphs[c] for c in range(0x20, 0x7F)))
    print(OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()

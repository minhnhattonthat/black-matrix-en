"""Recon: locate the dialogue font (14x14 1bpp, 28 bytes per glyph) in the DATs and decode its index table.
usage: recon_font.py RAM.bin  -> work/recon/font.png + stdout (table stats, where the font lives on disc)"""
import struct, sys
sys.path.insert(0, 'tools')
import dat, mips
from PIL import Image

FONT_RAM = 0x801A281C
INDEX = 0x800736BC


def main():
    code, load = mips.load_exe()
    n = 192 * 0x70
    idx = struct.unpack_from(f'<{n}H', code, INDEX - load)
    used = [(i, v) for i, v in enumerate(idx) if v]
    print('index entries used', len(used), 'max glyph', max(v for _, v in used))
    def sjis(i):
        hi = 0x81 + i // 192
        lo = 0x40 + i % 192
        return hi, lo
    for i, v in used[:40]:
        hi, lo = sjis(i)
        try:
            print(f'{hi:02x}{lo:02x} {bytes((hi, lo)).decode("cp932")} -> {v}', end=' | ')
        except UnicodeDecodeError:
            print(f'{hi:02x}{lo:02x} -> {v}', end=' | ')
    print()
    ram = open(sys.argv[1], 'rb').read()
    off = FONT_RAM - 0x80000000
    count = max(v for _, v in used)
    font = ram[off:off + count * 28]
    probe = font[28 * 100:28 * 140]
    for name in ('SYSTEM', 'EVENT', 'SCENARIO', 'BATTLE'):
        files = dat.unpack(open(f'work/extracted/disc1/{name}.DAT', 'rb').read())
        for i, f in enumerate(files):
            p = f.find(probe)
            if p >= 0:
                print(f'font bytes found in {name}/{i} at {p:#x} (glyph 0 at {p - 28 * 100:#x}), sub size {len(f)}')
    cols = 64
    rows = count // cols + 1
    im = Image.new('L', (cols * 15, rows * 15), 40)
    for g in range(count):
        for y in range(14):
            v = struct.unpack_from('>H', font, g * 28 + y * 2)[0] if g * 28 + y * 2 + 2 <= len(font) else 0
            for x in range(16):
                if v & (0x8000 >> x):
                    im.putpixel(((g % cols) * 15 + x % 15, (g // cols) * 15 + y), 255)
    im.save('work/recon/font.png')
    print('glyphs', count, 'font bytes', count * 28, 'end', hex(FONT_RAM + count * 28))


if __name__ == '__main__':
    main()

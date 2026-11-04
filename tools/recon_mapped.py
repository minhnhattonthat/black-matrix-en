"""Recon: draw every mapped picture (kind bit 0x10) through its cell map, so scrambled sheets become readable.
Map at extra_off: u16 cols, u16 rows, u16 cell words = 0x8000 | page<<10 | y<<6 | x<<1, in 16 px cells; x counts within a texture page.
usage: recon_mapped.py -> work/recon/mapped/<n>.png + sheet_NN.png, labelled with the picture number from gfx_index.tsv"""
import os, struct, sys
sys.path.insert(0, 'tools')
import dat, pak, recon_gfx
from PIL import Image, ImageDraw

OUT = 'work/recon/mapped'
os.makedirs(OUT, exist_ok=True)
paths = {}
for line in open('work/recon/gfx_index.tsv', encoding='utf-8'):
    c = line.rstrip('\n').split('\t')
    for p in c[5].split(' '):
        paths[p] = int(c[0])
done, words = {}, set()
for disc in ('1', '2'):
    for name in ('SYSTEM', 'BATTLE', 'EVENT'):
        files = dat.unpack(open(f'work/extracted/disc{disc}/{name}.DAT', 'rb').read())
        for i, f in enumerate(files):
            if not f:
                continue
            for path, _, b in pak.walk(f, f'{name}/{i}'):
                info = recon_gfx.blob_info(b)
                if info is None or not struct.unpack_from('<I', b)[0] & 0x10:
                    continue
                n = paths.get(f'd{disc}:{path}')
                if n is None or n in done:
                    continue
                extra = struct.unpack_from('<I', b, 12)[0]
                cols, rows = struct.unpack_from('<HH', b, extra)
                sheet = recon_gfx.render(b, info)
                per_page = 8 if info[0] else 16  # a texture page is 128 px wide at 8 bits, 256 at 4
                im = Image.new('RGB', (cols * 16, rows * 16))
                for r in range(rows):
                    for c in range(cols):
                        w = struct.unpack_from('<H', b, extra + 4 + (r * cols + c) * 2)[0]
                        words.add(w >> 12)
                        x = (((w >> 10) & 7) * per_page + ((w >> 1) & 31)) * 16
                        y = ((w >> 6) & 15) * 16
                        im.paste(sheet.crop((x, y, x + 16, y + 16)), (c * 16, r * 16))
                im.save(f'{OUT}/{n:05d}.png')
                done[n] = path
print('mapped pictures', len(done), 'high nibbles of cell words', sorted(words))
names = sorted(done)
per = 20
for s in range(0, len(names), per):
    sheet = Image.new('RGB', (5 * 324, 4 * 260), (40, 0, 40))
    for j, n in enumerate(names[s:s + per]):
        im = Image.open(f'{OUT}/{n:05d}.png')
        im.thumbnail((320, 240))
        x, y = j % 5 * 324, j // 5 * 260
        sheet.paste(im, (x, y + 16))
        ImageDraw.Draw(sheet).text((x + 2, y + 2), f'#{n} {done[n]}', fill=(255, 255, 0))
    sheet.save(f'{OUT}/sheet_{s // per:02d}.png')
print('sheets', (len(names) + per - 1) // per)

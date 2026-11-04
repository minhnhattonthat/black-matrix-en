"""Recon: labelled contact sheets of work/recon/gfx for the graphics sweep. Each cell shows the picture number.
usage: recon_sheets.py [--per 48] -> work/recon/sheets/s<NN>.png, work/recon/sheets/index.tsv"""
import os, sys
from PIL import Image, ImageDraw

CELL_W, CELL_H, COLS = 212, 170, 6


def main():
    per = 48
    os.makedirs('work/recon/sheets', exist_ok=True)
    rows = [l.rstrip('\n').split('\t') for l in open('work/recon/gfx_index.tsv', encoding='utf-8')]
    def key(r):
        p = r[5].split()[0].split(':')[1]
        top = p.split('.')[0].split('/')
        return (top[0], int(top[1]), int(r[0]))
    rows.sort(key=key)
    idx = open('work/recon/sheets/index.tsv', 'w', encoding='utf-8')
    for s in range(0, len(rows), per):
        chunk = rows[s:s + per]
        h = CELL_H * ((len(chunk) + COLS - 1) // COLS)
        sheet = Image.new('RGB', (CELL_W * COLS, h), (70, 0, 70))
        d = ImageDraw.Draw(sheet)
        for i, r in enumerate(chunk):
            im = Image.open(f'work/recon/gfx/{int(r[0]):05d}.png')
            scale = min((CELL_W - 4) / im.width, (CELL_H - 16) / im.height, 2)
            if scale != 1:
                im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.NEAREST if scale >= 1 else Image.LANCZOS)
            x, y = (i % COLS) * CELL_W + 2, (i // COLS) * CELL_H + 14
            sheet.paste(im, (x, y))
            d.text((x, y - 12), r[0], fill=(255, 255, 0))
        name = f's{s // per:02d}'
        sheet.save(f'work/recon/sheets/{name}.png')
        idx.write(f"{name}\t{chunk[0][5].split()[0]}\t{chunk[-1][5].split()[0]}\t{' '.join(r[0] for r in chunk)}\n")
    print('sheets', (len(rows) + per - 1) // per, 'pictures', len(rows))


if __name__ == '__main__':
    main()

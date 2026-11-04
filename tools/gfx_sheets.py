"""Every redrawn picture as built, labelled by leaf, for the graphics QA read: work/qa/gfx/sheet_NN.png.
usage: gfx_sheets.py"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import gfx

OUT = Path(__file__).resolve().parents[1] / 'work/qa/gfx'
WIDE, PER_SHEET = 4, 12


def views():
    """(leaf path, RGB image) of each distinct redrawn picture; other edits (tables) have no picture."""
    seen = {}
    for disc in (1, 2):
        for dat_name, leaves in gfx.replacements(disc).items():
            for path, leaf in leaves.items():
                if leaf not in seen and gfx.is_pic(leaf):
                    seen[leaf] = path
    for leaf, path in sorted(seen.items(), key=lambda kv: kv[1]):
        p = gfx.Pic(leaf)
        yield path, Image.fromarray(p.rgb()[p.screen() if p.mapped else p.px].astype(np.uint8)[..., :3])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob('sheet_*.png'):
        old.unlink()
    all_views = list(views())
    for i in range(0, len(all_views), PER_SHEET):
        page = all_views[i:i + PER_SHEET]
        cell_w, cell_h = 322, 256 + 14
        sheet = Image.new('RGB', (WIDE * cell_w, -(-len(page) // WIDE) * cell_h), (40, 0, 40))
        d = ImageDraw.Draw(sheet)
        for j, (path, im) in enumerate(page):
            x, y = j % WIDE * cell_w, j // WIDE * cell_h
            im.thumbnail((320, 256))
            sheet.paste(im, (x, y + 14))
            d.text((x + 2, y + 1), path, fill=(255, 255, 0))
        sheet.save(OUT / f'sheet_{i // PER_SHEET:02d}.png')
    print(len(all_views), 'pictures,', -(-len(all_views) // PER_SHEET), 'sheets')


if __name__ == '__main__':
    main()

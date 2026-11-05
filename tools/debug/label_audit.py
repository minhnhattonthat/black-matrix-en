"""Audit every row of gfx/labels.tsv against the sprites the game cuts from its sheet. Static: reads the pristine and the redrawn leaves.
  CUT    Japanese art split by a cleared rect: the part outside is still on the sheet.
  NOREC  no record of the sheet's tables holds the text whole: the screen cuts it, or never shows it.
  STALE  a record still points at a rect that a `pack` row moved away from.
usage: label_audit.py [--shots DIR]   (exit 1 on any fault not in KNOWN)"""
import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import dat  # noqa: E402
import gfx  # noqa: E402
import gfx_labels as gl  # noqa: E402

EIGHT = np.ones((3, 3), bool)
# Read by eye on the crops: art that only touches a cleared Japanese glyph by a pixel and is itself whole.
KNOWN = {('BATTLE/0.1', 192, 192), ('SYSTEM/3.1', 0, 0), ('SYSTEM/4.1', 131, 0), ('SYSTEM/4.1', 80, 0)}


def records(b):
    """The (x, y, w, h) records of a sprite table leaf or a sheet's own tail; [] if there is no table."""
    if len(b) < 16:
        return []
    size, at = (8, 4) if gfx.is_pic(b) else (4, 0)
    off = struct.unpack_from('<I', b, 12)[0]
    n = struct.unpack_from('<I', b, off)[0] if off and off + 4 <= len(b) else 0
    if not 0 < n < 500 or off + 4 + n * size > len(b):
        return []
    return [tuple(b[off + 4 + i * size + at:off + 8 + i * size + at]) for i in range(n)]


def sheet_tables(path, px, leaves):
    """Records of the group's tables that could cut this sheet: inside it. One table can serve several sheets (EVENT/66.5) or a corner (SYSTEM/15.3), so judge per record."""
    out = []
    for p, b in leaves.items():
        if p.startswith(path.rsplit('.', 1)[0] + '.'):
            out += [(p, r) for r in records(b) if r[2] and r[3] and r[0] + r[2] <= px.shape[1] and r[1] + r[3] <= px.shape[0]]
    return out


def ink_box(new, r):
    """Bounding box (x0, y0, x1, y1) of the row's text on the redrawn sheet, within its rect."""
    a = new[r['y']:r['y'] + r['h'], r['x']:r['x'] + r['w']] != 0
    if not a.any():
        return None
    ys, xs = np.where(a)
    return r['x'] + xs.min(), r['y'] + ys.min(), r['x'] + xs.max() + 1, r['y'] + ys.max() + 1


def audit(shots=None):
    leaves = {}
    for n in gfx.GFX_DATS:
        leaves.update(dict(dat.walk(open(os.path.join(gfx.ORIG, f'd1/{n}.DAT'), 'rb').read(), n)))
    new_leaves = {}
    for n in gfx.GFX_DATS:
        new_leaves.update(gfx.replacements(1)[n])
    bad, advice = [], []
    for path, rows in gl.rows().items():
        old = gfx.Pic(leaves[path]).px
        new = gfx.Pic(new_leaves[path]).px
        built = gl.packed(rows)
        cleared = np.zeros_like(old, bool)
        for r in rows:
            cleared[r['y']:r['y'] + r['h'], r['x']:r['x'] + r['w']] = True
        for r in built:
            if 'strip=' in r['style']:
                for c in r['style'].split('strip=')[1].split(',')[0].split(';'):
                    x, y = map(int, c.split('+')[:2])
                    cleared[y:y + 16, x:x + 16] = True
        comp, count = ndimage.label(old != 0, structure=EIGHT)
        for i in range(1, count + 1):
            m = comp == i
            inside, outside = (m & cleared).sum(), (m & ~cleared).sum()
            if inside and outside:
                ys, xs = np.where(m & ~cleared)
                if (path, xs.min(), ys.min()) in KNOWN:
                    continue
                bad.append(('CUT', path, f'art at x{xs.min()}-{xs.max()} y{ys.min()}-{ys.max()}: {outside} px left beside a cleared rect'))
                if shots:
                    x0, y0 = max(0, xs.min() - 8), max(0, ys.min() - 8)
                    crop = np.hstack([old[y0:ys.max() + 9, x0:xs.max() + 41], new[y0:ys.max() + 9, x0:xs.max() + 41]])
                    Image.fromarray((crop.astype('u1') * 17).clip(0, 255).astype('u1')).resize((crop.shape[1] * 4, crop.shape[0] * 4), Image.NEAREST).save(
                        os.path.join(shots, f"cut_{path.replace('/', '_')}_{xs.min()}_{ys.min()}.png"))
        tables = sheet_tables(path, old, leaves)
        if not tables:
            advice.append(('NOTABLE', path, 'no sibling table covers this sheet: CLIP and NOREC not checked'))
        for r in built:
            if not r['text'] or 'strip=' in r['style'] or 'pack' in r['style']:
                continue
            box = ink_box(new, r)
            if tables and box:
                x0, y0, x1, y1 = box
                hits = [t for t in tables if t[1][0] < x1 and x0 < t[1][0] + t[1][2] and t[1][1] < y1 and y0 < t[1][1] + t[1][3]]
                whole = [t for t in hits if t[1][0] <= x0 and t[1][1] <= y0 and x1 <= t[1][0] + t[1][2] and y1 <= t[1][1] + t[1][3]]
                # tables of a group mix several sheets, so a partial hit proves nothing: only "no record holds it whole" does
                if not r['rec'] and not whole:
                    bad.append(('NOREC', path, f"{r['text']!r} ink {box}: records touching it {[t[1] for t in hits]}"))
        moved = [r for r in built if 'pack' in r['style'] and r['text']]
        if moved:
            old_rects = [tuple(map(int, next(s for s in r['style'].split(',') if s.startswith('from='))[5:].split('+'))) for r in moved]
            for p, b in leaves.items():
                if p.startswith(path.rsplit('.', 1)[0] + '.'):
                    for rec in records(new_leaves.get(p, b)):
                        if rec in old_rects and rec not in [(r['x'], r['y'], r['w'], r['h']) for r in moved]:  # a new shelf rect can equal an old one
                            bad.append(('STALE', path, f'{p} still has record {rec}'))
    return bad, advice


def pairs(out, per_page=60, zoom=2, pad=10):
    """Every row with its surroundings, Japanese | English: art wholly inside a cleared rect (a menu arrow) shows only to the eye. Colours are CLUT 0's."""
    leaves = {}
    for n in gfx.GFX_DATS:
        leaves.update(dict(dat.walk(open(os.path.join(gfx.ORIG, f'd1/{n}.DAT'), 'rb').read(), n)))
        leaves.update(gfx.replacements(1)[n] and {('new', k): v for k, v in gfx.replacements(1)[n].items()})
    tiles = []
    for path, rows in gl.rows().items():
        old, new = gfx.Pic(leaves[path]), gfx.Pic(leaves[('new', path)])
        for r in rows:
            if 'pack' in r['style']:  # moved away: the old rect is empty by design and the new one is read in game
                continue
            box = (max(0, r['x'] - pad), max(0, r['y'] - 2), r['x'] + r['w'] + pad, r['y'] + r['h'] + 2)
            parts = []
            for p in (old, new):
                rgb = p.rgb()[p.px % len(p.rgb())][..., :3].copy()
                rgb[p.px == 0] = (60, 0, 60)
                parts.append(rgb[box[1]:box[3], box[0]:box[2]])
            tile = np.zeros((36, 260, 3), 'u1')
            for i, q in enumerate(parts):
                q = q[:36, :128]
                tile[:q.shape[0], i * 130:i * 130 + q.shape[1]] = q
            tiles.append(tile)
    for i in range(0, len(tiles), per_page):
        page = tiles[i:i + per_page]
        page += [np.zeros_like(tiles[0])] * (-len(page) % 2)
        im = np.vstack([np.hstack(page[j:j + 2]) for j in range(0, len(page), 2)])
        Image.fromarray(im).resize((im.shape[1] * zoom, im.shape[0] * zoom), Image.NEAREST).save(os.path.join(out, f'pairs_{i // per_page:02d}.png'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots')
    a = ap.parse_args()
    if a.shots:
        os.makedirs(a.shots, exist_ok=True)
        pairs(a.shots)
    bad, advice = audit(a.shots)
    for line in sorted(bad) + sorted(advice):
        print(*line, sep='\t')
    print(f'{len(bad)} faults, {len(advice)} notes')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

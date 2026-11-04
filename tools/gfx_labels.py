"""Sprite-sheet labels redrawn in English, from gfx/labels.tsv. Each row: sheet leaf, rect, text, style, sprite-table records to re-point.
Rects come from the sprite tables: a table leaf ends in `u32 count, (x, y, w, h) bytes` at header word 3; SYSTEM/5.5 keeps its own at
extra_off as `u32 count, (u16 id, u16 clut, x, y, w, h)`. An empty text just clears the rect. Text is drawn with X11 misc-fixed bitmaps made
proportional, in the original label's own colour per row, so gradients survive."""
import struct
from pathlib import Path

import numpy as np
from scipy import ndimage

import gfx

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'fonts'
LADDER = ['9x15B', '8x13B', '7x13B', '6x13B', '6x12', '6x10', '5x8']


class Bdf:
    """Glyphs as bool arrays, trimmed to their ink so a monospaced font sets proportionally."""
    cache = {}

    def __init__(self, name):
        self.h, self.descent = 0, 0
        self.glyphs = {}
        code, bbx, rows = None, None, None
        for line in (FONTS / f'{name}.bdf').read_text(encoding='latin-1').splitlines():
            if line.startswith('FONTBOUNDINGBOX'):
                _, h, _, d = map(int, line.split()[1:])
                self.h, self.descent = h, -d
            elif line.startswith('ENCODING'):
                code = int(line.split()[1])
            elif line.startswith('BBX'):
                bbx = tuple(map(int, line.split()[1:]))
            elif line == 'BITMAP':
                rows = []
            elif line == 'ENDCHAR':
                if code is not None and code < 0x7F:
                    self.glyphs[code] = (bbx, rows)
                rows = None
            elif rows is not None:
                rows.append(int(line, 16) << (8 * (len(line) // 2) - bbx[0]) >> (8 * (len(line) // 2) - bbx[0]) if False else int(line, 16) >> (4 * len(line) - bbx[0]))

    @classmethod
    def get(cls, name):
        if name not in cls.cache:
            cls.cache[name] = cls(name)
        return cls.cache[name]

    def glyph(self, ch):
        (w, h, bx, by), rows = self.glyphs[ord(ch)]
        a = np.zeros((self.h, w + bx), bool)
        top = self.h - self.descent - by - h
        for r, bits in enumerate(rows):
            for c in range(w):
                if bits >> (w - 1 - c) & 1 and 0 <= top + r < self.h:
                    a[top + r, bx + c] = True
        cols = np.where(a.any(axis=0))[0]
        return a[:, cols[0]:cols[-1] + 1] if len(cols) else None

    def text(self, s, gap=1):
        """Bool array of the string, trimmed vertically."""
        space = max(2, self.h // 4)
        parts = []
        for ch in s:
            g = None if ch == ' ' else self.glyph(ch)
            if g is None:
                parts.append(np.zeros((self.h, space), bool))
            else:
                parts.append(g)
                parts.append(np.zeros((self.h, gap), bool))
        if parts and not parts[-1].any() and s[-1] != ' ':
            parts.pop()
        a = np.concatenate(parts, axis=1)
        rows = np.where(a.any(axis=1))[0]
        return a[rows[0]:rows[-1] + 1]


def fit(lines, w, h, ladder=LADDER, gap=1):
    """The biggest font whose lines fit w x h. Returns one bool array per line; raises if even the smallest doesn't fit."""
    for name in ladder:
        f = Bdf.get(name)
        arrs = [f.text(s, gap) for s in lines]
        total = sum(a.shape[0] for a in arrs) + (len(arrs) - 1) * 2
        if max(a.shape[1] for a in arrs) <= w and total <= h:
            return arrs
    if gap:
        return fit(lines, w, h, ladder, 0)
    raise ValueError(f'{lines} does not fit {w}x{h}')


def row_colours(px, x, y, w, h, skip=()):
    """The most common non-zero index on each row of a rect; rows without ink take the nearest row's."""
    out = [0] * h
    for r in range(h):
        c = np.bincount(px[y + r, x:x + w].ravel(), minlength=256)
        c[0] = 0
        for s in skip:
            c[s] = 0
        out[r] = int(c.argmax()) if c.any() else 0
    known = [i for i, v in enumerate(out) if v]
    if not known:
        return [15] * h
    return [out[min(known, key=lambda k: abs(k - r))] for r in range(h)]


def draw(px, row, ref, ladder=LADDER):
    """Draw one row's text into px. ref: the untouched pixels, for colours."""
    x, y, w, h, text, style = row['x'], row['y'], row['w'], row['h'], row['text'], row['style']
    if not text:
        return
    fg, out, src = None, None, (x, y, w, h)
    for part in style.split(','):
        if part.startswith('c'):
            fg = int(part[1:])
        elif part.startswith('o'):
            out = int(part[1:])
        elif part.startswith('from='):
            src = tuple(map(int, part[5:].split('+')))
        elif part.startswith('f'):
            ladder = [part[1:]]
    skip = (out,) if out else ()
    cols = [fg] * src[3] if fg else row_colours(ref, *src, skip)
    arrs = fit(text.split('|'), w, h, ladder)
    total = sum(a.shape[0] for a in arrs) + (len(arrs) - 1) * 2
    ty = y + (h - total) // 2
    for a in arrs:
        ax = x + (w - a.shape[1]) // 2
        if out is not None:
            grown = np.zeros((a.shape[0] + 2, a.shape[1] + 2), bool)
            for dy in (0, 1, 2):
                for dx in (0, 1, 2):
                    grown[dy:dy + a.shape[0], dx:dx + a.shape[1]] |= a
            gy, gx = ty - 1, ax - 1
            for r, c in zip(*np.where(grown)):
                if y <= gy + r < y + h and x <= gx + c < x + w:
                    px[gy + r, gx + c] = out
        for r, c in zip(*np.where(a)):
            px[ty + r, ax + c] = cols[min(ty + r - y, len(cols) - 1)]
        ty += a.shape[0] + 2


def set_records(leaf, index, rect):
    """A sprite table with one record's rect changed. index: a number, or `x,y` of the rect the record has now."""
    b = bytearray(leaf)
    off = struct.unpack_from('<I', b, 12)[0]
    # SYSTEM/5.5: the table sits in the sheet's own tail, 8-byte records with the rect last
    size, at = (8, 4) if gfx.is_pic(leaf) else (4, 0)
    n = struct.unpack_from('<I', b, off)[0]
    if isinstance(index, str):
        x, y = map(int, index.split(','))
        hits = [i for i in range(n) if b[off + 4 + i * size + at] == x and b[off + 4 + i * size + at + 1] == y]
        assert len(hits) == 1, f'{index}: {len(hits)} records'
        index = hits[0]
    assert index < n
    b[off + 4 + index * size + at:off + 4 + index * size + at + 4] = bytes(rect)
    return bytes(b)


def draw_strip(px, row, ref):
    """Text across 16-px cell sprites the game draws on a 14-px pitch (its one-kanji-per-cell labels): each cell holds the next 14 columns."""
    cells = [tuple(map(int, c.split('+'))) for c in row['style'].split('strip=')[1].split(',')[0].split(';')]
    for x, y in cells:
        px[y:y + 16, x:x + 16] = 0
    if not row['text']:
        return
    parts = row['style'].split(',')
    ladder = [p[1:] for p in parts if p.startswith('f') and not p.startswith('from=')] or LADDER
    fg = next((int(p[1:]) for p in parts if p.startswith('c')), None)
    out = next((int(p[1:]) for p in parts if p.startswith('o')), None)
    a = fit([row['text']], 14 * len(cells), 14, ladder)[0]
    pad = (14 * len(cells) - a.shape[1]) // 2
    full = np.zeros((16, 14 * len(cells)), bool)
    top = (16 - a.shape[0]) // 2
    full[top:top + a.shape[0], pad:pad + a.shape[1]] = a
    halo = ndimage.binary_dilation(full, structure=np.ones((3, 3))) & ~full if out is not None else np.zeros_like(full)
    for i, (x, y) in enumerate(cells):
        cols = [fg] * 16 if fg else row_colours(ref, x, y, 16, 16)
        for r, c in zip(*np.where(halo[:, i * 14:(i + 1) * 14])):
            px[y + r, x + 1 + c] = out
        for r, c in zip(*np.where(full[:, i * 14:(i + 1) * 14])):
            px[y + r, x + 1 + c] = cols[r]


def rows():
    """gfx/labels.tsv grouped by sheet path, in file order. A `rec` column re-points table records at the row's rect."""
    out = {}
    for line in (ROOT / 'gfx/labels.tsv').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        c = (line.split('\t') + [''] * 8)[:8]
        out.setdefault(c[0], []).append({'x': int(c[1]), 'y': int(c[2]), 'w': int(c[3]), 'h': int(c[4]), 'text': c[5], 'style': c[6], 'rec': c[7]})
    return out


def packed(sheet_rows):
    """Rows styled `pack,fNAME` get a new rect wide enough for their text: shelves of 16 px, widest first, x in 2-px steps."""
    todo = [r for r in sheet_rows if 'pack' in r['style'] and r['text']]
    if not todo:
        return sheet_rows
    name = next(p[1:] for p in todo[0]['style'].split(',') if p.startswith('f'))
    f = Bdf.get(name)
    left, room = {}, {}
    for r in sorted(todo, key=lambda r: -f.text(r['text']).shape[1]):
        w = -(-(f.text(r['text']).shape[1] + 1) // 2) * 2
        y = next(y for y in range(0, 160, 16) if room.get(y, 0) + w <= 128)
        left[id(r)] = (room.get(y, 0), y, w, 16)
        room[y] = room.get(y, 0) + w
    out = []
    for r in sheet_rows:
        if id(r) in left:
            x, y, w, h = left[id(r)]
            out.append(dict(r, x=x, y=y, w=w, h=h, style=f"{r['style']},from={r['x']}+{r['y']}+{r['w']}+{r['h']}"))
        else:
            out.append(r)
    return out


def sheet_font(sheet_rows):
    """One size per sheet: the biggest font every label fits, ignoring rows that name their own size (fN)."""
    for name in LADDER:
        f = Bdf.get(name)
        ok = True
        for r in sheet_rows:
            if not r['text'] or any(p.startswith('f') and not p.startswith('from=') for p in r['style'].split(',')):
                continue
            lines = r['text'].split('|')
            arrs = [f.text(s) for s in lines]
            if max(a.shape[1] for a in arrs) > r['w'] or sum(a.shape[0] + 2 for a in arrs) - 2 > r['h']:
                ok = False
                break
        if ok:
            return [name]
    return LADDER


def redraw_sheet(leaf, sheet_rows):
    p = gfx.Pic(leaf)
    ref = p.px.copy()
    # clear everything first: a relocated label lands where another used to be
    for r in sheet_rows:
        p.px[r['y']:r['y'] + r['h'], r['x']:r['x'] + r['w']] = 0
    sheet_rows = packed(sheet_rows)
    ladder = sheet_font([r for r in sheet_rows if 'strip=' not in r['style']])
    for r in sheet_rows:
        if 'strip=' in r['style']:
            draw_strip(p.px, r, ref)
        else:
            draw(p.px, r, ref, ladder)
    return p.bytes()


def table_edits(rows_):
    """{table path: [(record index, rect)]} from the rows' rec columns."""
    out = {}
    for sheet in rows_.values():
        for r in packed(sheet):
            for ref in filter(None, r['rec'].split(';')):
                t, i = ref.rsplit(':', 1)
                out.setdefault(t, []).append((i if ',' in i else int(i), (r['x'], r['y'], r['w'], r['h'])))
    return out

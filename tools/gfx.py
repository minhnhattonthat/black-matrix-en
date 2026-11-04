"""Picture leaves of the DATs: decode to palette indices, edit, write back byte-compatible. Format: docs/re/graphics.md.
A Pic keeps every byte of the leaf except the pixels (and the colours or cell map if a redraw asks), so a redraw can't
touch anything else. replacements(disc) is what the build calls."""
import hashlib
import pickle
import struct
from pathlib import Path

import numpy as np

import dat

ROOT = Path(__file__).resolve().parents[1]
ORIG = ROOT / 'work/orig'
GFX_DATS = 'SYSTEM BATTLE EVENT'.split()
CELL = 16


class Pic:
    def __init__(self, leaf):
        self.leaf = bytes(leaf)
        kind, ten, self.off, self.extra = struct.unpack_from('<4I', leaf)
        assert ten == 0x10 and not kind & ~0x91, 'not a picture'
        self.kind = kind
        self.bits8 = bool(kind & 1)
        self.cw, self.ch = struct.unpack_from('<HH', leaf, 0x10)
        assert self.off == 0x14 + 2 * self.cw * self.ch, 'not a picture'
        self.w16, self.h = struct.unpack_from('<HH', leaf, self.off)
        self.colors = np.frombuffer(leaf, '<u2', self.cw * self.ch, 0x14).copy()
        raw = np.frombuffer(leaf, 'u1', self.w16 * self.h * 2, self.off + 4)
        if self.bits8:
            self.px = raw.reshape(self.h, self.w16 * 2).copy()
        else:
            row = raw.reshape(self.h, self.w16 * 2)
            self.px = np.zeros((self.h, self.w16 * 4), 'u1')
            self.px[:, ::2] = row & 15
            self.px[:, 1::2] = row >> 4
        self.mapped = bool(kind & 0x10)
        if self.mapped:
            self.cols, self.rows = struct.unpack_from('<HH', leaf, self.extra)
            self.map = np.frombuffer(leaf, '<u2', self.cols * self.rows, self.extra + 4).reshape(self.rows, self.cols).copy()

    @property
    def per_page(self):
        return 8 if self.bits8 else 16  # a texture page is 128 px wide at 8 bits, 256 at 4

    def rgb(self, clut=0):
        """The colours as an (n, 3) uint8 array; clut picks a row of a 16-colour sheet."""
        c = self.colors
        if not self.bits8:
            c = c[clut * self.cw:(clut + 1) * self.cw]
        return np.stack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3], axis=1).astype('u1')

    def cell_xy(self, word):
        return ((word >> 10 & 7) * self.per_page + (word >> 1 & 31)) * CELL, (word >> 6 & 15) * CELL

    def screen(self):
        """A mapped picture drawn through its cell map, as palette indices (rows*16, cols*16)."""
        out = np.zeros((self.rows * CELL, self.cols * CELL), 'u1')
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = self.cell_xy(int(self.map[r, c]))
                out[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] = self.px[y:y + CELL, x:x + CELL]
        return out

    def set_screen(self, idx):
        """Store an edited screen: cells with the same pixels share one slot, as the game's own pictures do. The sheet keeps
        its height and grows in whole 16-px columns only if the distinct cells need it. Slots stay in the sheet's own order."""
        per_col = self.h // CELL
        cells, words = {}, np.zeros_like(self.map)
        for r in range(self.rows):
            for c in range(self.cols):
                k = idx[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL].tobytes()
                n = cells.setdefault(k, len(cells))
                cx, cy = (n // per_col, n % per_col)
                words[r, c] = int(self.map.flat[0]) & 0xF001 | cx // self.per_page << 10 | cy << 6 | (cx % self.per_page) << 1
        cols = -(-len(cells) // per_col)
        # the sheet's width in 16-bit words must stay a whole number of cells; keep the original width if that's enough
        width = max(self.px.shape[1], cols * CELL)
        px = np.zeros((self.h, width), 'u1')
        for k, n in cells.items():
            x, y = n // per_col * CELL, n % per_col * CELL
            px[y:y + CELL, x:x + CELL] = np.frombuffer(k, 'u1').reshape(CELL, CELL)
        self.px, self.map = px, words
        self.w16 = width // (2 if self.bits8 else 4)

    def bytes(self):
        """The leaf with this object's pixels (and cell map), everything else byte for byte. A grown sheet moves what follows it."""
        raw = self.px.tobytes() if self.bits8 else (self.px[:, ::2] | self.px[:, 1::2] << 4).tobytes()
        old_end = self.off + 4 + struct.unpack_from('<H', self.leaf, self.off)[0] * self.h * 2
        tail = self.leaf[old_end:]
        head = bytearray(self.leaf[:self.off + 4])
        struct.pack_into('<H', head, self.off, self.w16)
        if self.mapped:
            at = self.extra - old_end
            assert at >= 0
            tail = tail[:at + 4] + self.map.astype('<u2').tobytes() + tail[at + 4 + self.cols * self.rows * 2:]
            struct.pack_into('<I', head, 12, self.off + 4 + len(raw) + at)
        elif self.extra:  # a sprite table in the sheet's tail: same distance from the pixels
            struct.pack_into('<I', head, 12, self.off + 4 + len(raw) + self.extra - old_end)
        return bytes(head) + raw + tail


def body(leaf):
    """What the picture index in work/recon/gfx_index.tsv hashes: header, colours and pixels, not the cell map."""
    off = struct.unpack_from('<I', leaf, 8)[0]
    w16, h = struct.unpack_from('<HH', leaf, off)
    return leaf[:off + 4 + w16 * h * 2]


def key(leaf):
    return hashlib.sha1(body(leaf)).hexdigest()


def is_pic(b):
    if len(b) < 0x18:
        return False
    kind, ten, off, _ = struct.unpack_from('<4I', b)
    if kind & ~0x91 or ten != 0x10 or off < 0x14 or off + 4 > len(b):
        return False
    cw, ch = struct.unpack_from('<HH', b, 0x10)
    if off != 0x14 + 2 * cw * ch:
        return False
    w16, h = struct.unpack_from('<HH', b, off)
    return bool(w16 and h and w16 <= 1024 and h <= 512 and off + 4 + w16 * h * 2 <= len(b))


def leaves(disc):
    """{DAT: {path: bytes}} of the pristine tree, picture leaves only."""
    out = {}
    for n in GFX_DATS:
        out[n] = {p: b for p, b in dat.walk((ORIG / f'd{disc}/{n}.DAT').read_bytes(), n) if is_pic(b)}
    return out


def locate():
    """{gfx_index picture hash: [(disc, dat, path)]}: every copy on both discs."""
    where = {}
    for disc in (1, 2):
        for n, ls in leaves(disc).items():
            for p, b in ls.items():
                where.setdefault(key(b), []).append((disc, n, p))
    return where


def source_key():
    """Changes when anything that shapes the redraws changes: the cache in work/gfx hangs on it."""
    h = hashlib.sha1()
    for p in sorted([*(ROOT / 'gfx').rglob('*'), *(ROOT / 'tools').glob('gfx*.py'), *(ROOT / 'fonts').glob('*')]):
        if p.is_file() and p.name not in ('movies.tsv', 'gfx_movies.py', 'gfx_sheets.py'):  # those don't touch the pictures
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def compute():
    """{(disc, dat): {path: new leaf}} for every picture redraw and sprite-table edit, every copy on both discs."""
    import gfx_art
    import gfx_cards
    import gfx_labels
    all_leaves, where, by_hash = {}, {}, {}
    for disc in (1, 2):
        for n in GFX_DATS:
            for p, b in dat.walk((ORIG / f'd{disc}/{n}.DAT').read_bytes(), n):
                all_leaves[(disc, n, p)] = b
                if is_pic(b):
                    where.setdefault(key(b), []).append((disc, n, p))
                by_hash.setdefault(hashlib.sha1(b).digest(), []).append((disc, n, p))
    first = {}
    for (disc, n, p), b in all_leaves.items():
        first.setdefault(p, b)
    out = {}

    def put(loc, new):
        out.setdefault(loc[:2], {})[loc[2]] = new

    def copies(path):
        return where[key(first[path])]

    label_rows = gfx_labels.rows()
    for path, rows in label_rows.items():
        for loc in copies(path):
            put(loc, gfx_labels.redraw_sheet(all_leaves[loc], rows))
    for table, edits in gfx_labels.table_edits(label_rows).items():
        for loc in by_hash[hashlib.sha1(first[table]).digest()]:
            base = out.get(loc[:2], {}).get(loc[2], all_leaves[loc])
            for i, rect in edits:
                base = gfx_labels.set_records(base, i, rect)
            put(loc, base)
    cards = gfx_cards.battle_rows()
    maker = gfx_cards.Cards([Pic(first[p]) for p in cards])
    for path, row in cards.items():
        new = maker.redraw(first[path], *row)
        for loc in copies(path):
            assert all_leaves[loc] == first[path], f'{loc} differs from {path}'
            put(loc, new)
    for path, fn in gfx_art.redraws(first).items():
        new = fn(first[path])
        for loc in copies(path):
            assert all_leaves[loc] == first[path], f'{loc} differs from {path}'
            put(loc, new)
    return out


def replacements(disc):
    """{DAT name: {path: new leaf}} for one disc, cached in work/gfx by source_key()."""
    cache = ROOT / f'work/gfx/{source_key()}.pkl'
    if cache.exists():
        got = pickle.loads(cache.read_bytes())
    else:
        got = compute()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(got))
    return {n: got.get((disc, n), {}) for n in GFX_DATS}

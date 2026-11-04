"""Full-screen cards redrawn in English: battle cards (torn paper + cut-up letters + blood), from the originals, the fonts in fonts/ and gfx/cards.tsv.
Everything is computed from the dump at build time, so no game art sits in the repo.
usage: gfx_cards.py OUT.png [NUMBER..]  a contact sheet for looking at them"""
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage
from scipy.spatial import cKDTree

import gfx

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'fonts'
SS = 4  # letters are drawn at 4x and shrunk


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


SERIF, SANS, NARROW = 'LiberationSerif-Bold.ttf', 'LiberationSans-Bold.ttf', 'LiberationSansNarrow-Bold.ttf'


def table(name):
    rows = []
    for line in (ROOT / 'gfx' / name).read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            rows.append(line.split('\t'))
    return rows


def blood_mask(a):
    """Blood on a card: red pixels, plus the black core connected to them."""
    a = a.astype(int)
    red = (a[..., 0] - a[..., 1:].max(axis=2)) > 14
    dark = a.max(axis=2) < 34
    lab, n = ndimage.label(red | dark, structure=np.ones((3, 3)))
    hit = np.unique(lab[red])
    core = np.isin(lab, hit[hit > 0])
    # a black glyph that merely touches blood stays out: only thick black (opening by 2) counts as a splat
    thick = ndimage.binary_opening(core & dark, iterations=3)
    thick = ndimage.binary_dilation(thick, iterations=2) & core
    return ndimage.binary_dilation(red, iterations=1) & (red | dark) | thick


def clone_fill(p, mask, detail_box=(150, 8, 310, 60), ignore=None):
    """Fill mask smoothly: the surrounding colours diffused in, plus grain mirrored from a clean part of the art (none if detail_box is None).
    ignore: pixels left as they are but not used as a source, such as the glow of lettering that stays."""
    p = p.astype(float)
    bad = ndimage.binary_dilation(mask, iterations=2)
    known = (~(bad if ignore is None else bad | ignore)).astype(float)
    low = np.zeros_like(p)
    for s in (24, 12, 6):  # wide first, then keep what the narrower blur knows
        w = ndimage.gaussian_filter(known, s)[..., None]
        blur = ndimage.gaussian_filter(p * known[..., None], (s, s, 0)) / np.maximum(w, 1e-3)
        low = np.where(w > 0.08, blur, low)
    grain = 0
    if detail_box:
        x0, y0, x1, y1 = detail_box
        patch = p[y0:y1, x0:x1]
        patch = patch - ndimage.gaussian_filter(patch, (6, 6, 0))
        h, w_ = p.shape[:2]
        tile = np.concatenate([patch, patch[:, ::-1]], axis=1)
        tile = np.concatenate([tile, tile[::-1]], axis=0)
        grain = np.tile(tile, (h // tile.shape[0] + 1, w_ // tile.shape[1] + 1, 1))[:h, :w_]
    soft = ndimage.gaussian_filter(bad.astype(float), 1.5)[..., None]
    return (p * (1 - soft) + (low + grain) * soft).clip(0, 255).astype('u1')


class Cards:
    """Reads every battle card once: the shared clean paper comes from all of them."""
    FIXED = [(14, 8, 150, 62), (8, 118, 140, 168), (40, 165, 316, 236)]  # always-lettered bands: chapter, label, win line

    def __init__(self, pics):
        self.rng = random.Random(1)
        stack = np.stack([p.rgb()[p.screen()] for p in pics]).astype(int)
        self.paper = self.make_paper(stack, pics)

    def make_paper(self, stack, pics):
        bloods = np.stack([blood_mask(s.astype('u1')) for s in stack])
        s = np.ma.array(stack, mask=np.repeat(bloods[..., None], 3, 3))
        p = np.ma.filled(np.ma.median(s, axis=0), 128).astype(float)
        bright = np.percentile(stack, 88, axis=0)
        # paper is lighter than the scraps: where most cards had a scrap, the bright tail shows the paper between them
        p = np.maximum(p, bright - 6)
        # what's still dark and blotchy in the lettered bands: replace from clean paper
        mask = np.zeros(p.shape[:2], bool)
        grey = p.mean(axis=2)
        smooth = ndimage.uniform_filter(grey, 25)
        for x0, y0, x1, y1 in self.FIXED + [(60, 62, 310, 118)]:
            r = np.zeros_like(mask)
            r[y0:y1, x0:x1] = True
            mask |= r & (grey < 118)
        mask = ndimage.binary_closing(mask, iterations=2)
        mask = ndimage.binary_opening(mask, iterations=1)
        return clone_fill(p, mask)

    def letter(self, ch, h, rng, fontname):
        """One cut-out letter at 4x, RGBA."""
        size = h * SS
        f = font(fontname, int(size * 0.95))
        l, t, r, b = f.getbbox(ch)
        gw, gh = r - l, b - t
        pad = int(size * 0.13)
        W, H = gw + 2 * pad + rng.randint(0, size // 10), int(size * 1.02) + rng.randint(-size // 12, size // 12)
        im = Image.new('RGBA', (W + 16 * SS, H + 16 * SS), (0, 0, 0, 0))
        # the scrap: a rough polygon
        ox, oy = 8 * SS, 8 * SS
        n = 6
        pts = []
        J = max(2, size // 22)
        for i in range(n):
            pts.append((ox + i * W / n + rng.randint(-J, J), oy + rng.randint(-J, J)))
        for i in range(n):
            pts.append((ox + W + rng.randint(-J, J), oy + i * H / n + rng.randint(-J, J)))
        for i in range(n):
            pts.append((ox + W - i * W / n + rng.randint(-J, J), oy + H + rng.randint(-J, J)))
        for i in range(n):
            pts.append((ox + rng.randint(-J, J), oy + H - i * H / n + rng.randint(-J, J)))
        style = rng.choice('dddll')  # dark letters on mid grey or light letters with a dark outline on dark grey
        g = rng.randint(118, 150) if style == 'd' else rng.randint(62, 92)
        mask = Image.new('L', im.size, 0)
        ImageDraw.Draw(mask).polygon(pts, fill=255)
        # dark bleed round the edge, like the photocopied originals
        halo = mask.filter(ImageFilter.GaussianBlur(SS * 1.1))
        im.paste((24, 24, 24, 255), (0, 0), halo.point(lambda v: min(255, int(v * 0.85))))
        inner = mask.filter(ImageFilter.MinFilter(2 * SS + 1)).filter(ImageFilter.GaussianBlur(SS * 0.7))
        im.paste((g, g, g, 255), (0, 0), inner)
        d = ImageDraw.Draw(im)
        tx, ty = ox + (W - gw) / 2 - l, oy + (H - gh) / 2 - t
        if style == 'd':
            d.text((tx + SS * 0.6, ty + SS * 0.6), ch, font=f, fill=(g + 40, g + 40, g + 40, 255))
            d.text((tx, ty), ch, font=f, fill=(20, 20, 20, 255))
        else:
            d.text((tx, ty), ch, font=f, fill=(226, 226, 226, 255), stroke_width=max(2, SS // 2 + 1), stroke_fill=(16, 16, 16, 255))
        # grain from the letter itself
        im = im.rotate(rng.uniform(-5, 5), Image.BICUBIC)
        return im, W, H, ox, oy

    def line(self, text, x0, y0, x1, y1, h, align, rng, tracking=0):
        """Scrap layers for one line, or None if it doesn't fit in x0..x1. tracking: px at 1x between letters (may be negative)."""
        parts, x = [], 0.0
        fonts = [SERIF, SERIF, SANS]
        for word_i, word in enumerate(text.split(' ')):
            if word_i:
                x += h * 0.38
            for ch in word:
                im, W, H, ox, oy = self.letter(ch, h, rng, rng.choice(fonts))
                parts.append((im, x, H, oy, ox))
                x += W / SS + tracking
        width = x - tracking
        if width > x1 - x0:
            return None
        px = {'l': x0, 'r': x1 - width, 'c': (x0 + x1 - width) / 2}[align]
        return [(im, px + x_, (y0 + y1) / 2 - H / SS / 2 + rng.uniform(-1.2, 1.2), oy, ox) for im, x_, H, oy, ox in parts]

    def fit(self, text, box, align, rng, hmax, hmin=9):
        """The largest letter height that fits box, on one line or wrapped to two when the box is tall enough."""
        x0, y0, x1, y1 = box
        for h in range(hmax, hmin - 1, -1):
            for track in (0, -1, -2):
                got = self.line(text, x0, y0, x1, y1, h, align, rng, track)
                if got:
                    return got
            words = text.split(' ')
            if y1 - y0 >= 2 * h and len(words) > 1:
                for cut in sorted(range(1, len(words)), key=lambda c: abs(len(' '.join(words[:c])) - len(' '.join(words[c:])))):
                    a, b = ' '.join(words[:cut]), ' '.join(words[cut:])
                    mid = (y0 + y1) / 2
                    for track in (0, -1):
                        one = self.line(a, x0, y0, x1, mid, h, 'l' if align == 'c' else align, rng, track)
                        two = self.line(b, x0, mid, x1, y1, h, 'r' if align == 'c' else align, rng, track)
                        if one and two:
                            return one + two
        raise ValueError(f'{text!r} does not fit {box}')

    def compose(self, pic, top, title, label, win):
        orig = pic.rgb()[pic.screen()]
        blood = blood_mask(orig)
        seed = sum(map(ord, top + title + win))
        rng = random.Random(seed)
        canvas = Image.new('RGBA', (320 * SS, 240 * SS), (0, 0, 0, 0))
        def place(items):
            for im, x, y, oy, ox in items:
                canvas.alpha_composite(im, (max(0, int(x * SS - ox)), max(0, int(y * SS - oy))))
        place(self.fit(top, (12, 12, 300, 56), 'l', rng, 28))
        if title:
            place(self.fit(title, (10, 60, 312, 118), 'c', rng, 36))
        if label:
            place(self.fit(label, (8, 124, 300, 160), 'l', rng, 22))
        if win:
            place(self.fit(win, (8, 170, 312, 232), 'r', rng, 32))
        small = canvas.resize((320, 240), Image.LANCZOS)
        under = self.paper.copy()
        under[blood] = orig[blood]
        out = Image.fromarray(under).convert('RGBA')
        out.alpha_composite(small)
        rgb = np.array(out.convert('RGB'))
        # blood stays over the letters only as a stain: they have to stay readable, and the English fills more of the card
        ink = np.array(small)[..., 3, None] / 255.0
        red = (blood & ((orig[..., 0].astype(int) - orig[..., 1:].max(axis=2)) > 24))[..., None]
        return (rgb * (1 - red * ink * 0.45) + orig * red * ink * 0.45).astype('u1')

    def redraw(self, leaf, top, title, label, win):
        p = gfx.Pic(leaf)
        rgb = self.compose(p, top, title, label, win)
        p.set_screen(nearest(p, rgb))
        return p.bytes()


def nearest(pic, rgb):
    """Palette index per pixel, from the colours this picture's pixels already use (so never a newly transparent one)."""
    pal = pic.rgb().astype(float)
    used = np.unique(pic.screen())
    tree = cKDTree(pal[used])
    _, i = tree.query(rgb.reshape(-1, 3).astype(float))
    return used[i].reshape(rgb.shape[:2]).astype('u1')


def battle_rows():
    """{leaf path: (top, title, label, win)} from gfx/cards.tsv"""
    return {r[0]: tuple((r + [''] * 5)[i].strip() for i in range(1, 5)) for r in table('cards.tsv')}


def main():
    ls = {}
    for disc in (2, 1):
        for n, m in gfx.leaves(disc).items():
            ls.update(m)
    rows = battle_rows()
    c = Cards([gfx.Pic(ls[p]) for p in rows])
    want = [f'BATTLE/{w}.0' for w in sys.argv[2:]] or list(rows)
    per = 4
    W = 322 * per
    H = 244 * (-(-len(want) * 2 // per))
    sheet = Image.new('RGB', (W, H), (60, 0, 60))
    for j, n in enumerate(want):
        new = gfx.Pic(c.redraw(ls[n], *rows[n]))
        old = gfx.Pic(ls[n])
        k = j * 2
        sheet.paste(Image.fromarray(old.rgb()[old.screen()], 'RGB'), (k % per * 322, k // per * 244))
        k += 1
        sheet.paste(Image.fromarray(new.rgb()[new.screen()], 'RGB'), (k % per * 322, k // per * 244))
    sheet.save(sys.argv[1])


if __name__ == '__main__':
    main()

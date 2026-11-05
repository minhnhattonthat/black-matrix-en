"""Full-screen pictures other than the battle cards: chapter and end cards, time cards, mini-game manuals, ending lines, master select.
Old lettering is erased (diffusion from the surrounding art plus a little of the art's grain), new lettering drawn, the result mapped back to the
colours the picture already uses. redraws() is what gfx.compute() calls. Text sits here, one table per kind.
usage: gfx_art.py OUT.png [PATH..]  a before/after sheet"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import gfx
from gfx_cards import SERIF, clone_fill, font, nearest
from gfx_labels import Bdf

CHAPTERS = {  # chapter card leaf: spine word, number, title lines, title box (x0, y0, x1, y1)
    'EVENT/130.0': ('1', "Pandora's|Garden", (200, 160, 312, 236)),
    'EVENT/131.0': ('2', 'Golgotha|Prison', (200, 141, 318, 224)),
    'EVENT/132.0': ('3', 'Temple|of the Sun', (196, 166, 293, 230)),
    'EVENT/133.0': ('4', 'On the|Road', (203, 178, 312, 230)),
    'EVENT/134.0': ('5', 'City of|Greed', (203, 172, 312, 230)),
    'EVENT/135.0': ('6', 'City of|Gluttony', (203, 166, 312, 230)),
    'EVENT/136.0': ('7', 'Over the Hills|of Narcis|Tezetta...', (194, 132, 312, 224)),
    'EVENT/137.0': ('8', 'Two|Equalities', (203, 147, 312, 230)),
    'EVENT/138.0': ('9', 'Noah, Land|of Slaves', (197, 153, 312, 230)),
    'EVENT/139.0': ('10', 'Souls|Reborn', (191, 172, 305, 230)),
    'EVENT/140.0': ('11', 'Guided to|the End...', (185, 153, 312, 230)),
    'EVENT/141.0': ('', 'And Then,|to Heaven...', (178, 153, 312, 230)),
}
ENDS = {  # chapter end card leaf: first line
    'EVENT/142.0': "Chapter 1: Pandora's Garden",
    'EVENT/143.0': 'Chapter 2: Golgotha Prison',
    'EVENT/144.0': 'Chapter 3: Temple of the Sun',
    'EVENT/145.0': 'Chapter 4: On the Road',
    'EVENT/146.0': 'Chapter 5: City of Greed',
    'EVENT/147.0': 'Chapter 6: City of Gluttony',
    'EVENT/148.0': 'Chapter 7: Over the Hills of Narcis Tezetta...',
    'EVENT/149.0': 'Chapter 8: Two Equalities',
    'EVENT/150.0': 'Chapter 9: Noah, Land of Slaves',
    'EVENT/151.0': 'Chapter 10: Souls Reborn',
    'EVENT/152.0': 'Chapter 11: Guided to the End...',
}
TIMES = {'EVENT/106.0': 'The Next Day', 'EVENT/107.0': 'Three Days Later', 'EVENT/114.0': 'One Week Later'}
ENDINGS = {  # ending line leaf: lines, box
    'EVENT/299.0': ('And so she became|the second Eve.', (20, 90, 300, 150)),
    'EVENT/300.0': ('And so he became|the second Adam.', (20, 90, 300, 150)),
    'EVENT/303.0': ('And so you became|the new Satan.', (20, 90, 300, 150)),
}
START = 'Press START to begin!'
MANUALS = {  # leaf: heading, list of (x, y, w, text, colour); erase boxes for coloured lettering
    'EVENT/71.0': ('Fishing', [(36, 66, 240, 'Wait for a fish to bite. When one does, stop the cursor with the O button: where it stops decides the fish you catch. When the float appears, mash O to reel it in.')], []),
    'EVENT/72.0': ('Hunting', [(34, 62, 232, 'Time your shots at the beasts that come out of the trees. It ends when you run out of arrows or bring one beast down.'),
                               (42, 134, 220, 'D-pad ... Move'), (42, 150, 220, 'O button ... Shoot')], []),
    'EVENT/73.0': ('Chopping Wood', [(50, 82, 216, 'While the axe is being raised, press O with good timing to bring it down and split the log.')], []),
    'EVENT/74.0': ('Cooking', [(26, 54, 256, 'Ingredients appear in cooking order.'),
                               (66, 72, 216, 'Press the button that matches the ingredient in the bubble.'),
                               (62, 112, 150, 'Cook red ingredients', (248, 80, 72)), (62, 129, 150, 'Cook green ingredients', (64, 216, 88)),
                               (62, 146, 150, 'Cook pink ingredients', (248, 128, 192)), (62, 163, 150, 'Cook blue ingredients', (88, 120, 248))],
                [(60, 110, 212, 180)]),
    'EVENT/75.0': ('Whack-a-Mole', [(46, 46, 90, 'D-pad: Right'), (46, 65, 40, 'Up'), (46, 83, 40, 'Left'), (46, 101, 40, 'Down'),
                                    (24, 152, 170, 'Hit the moles with the buttons shown above, as many as you can.')], []),
    'EVENT/76.0': ('Mouse Count', [(36, 62, 236, 'When the game starts, mice run around the screen. Count them, then enter the number when they stop.'),
                                   (46, 140, 220, 'D-pad ... Up/down picks a number'), (46, 158, 220, 'O button ... Confirm')], []),
    'EVENT/77.0': ('Laundry', [(28, 56, 250, 'Mash left and right on the D-pad in turn to make the hero wash. When it looks clean, press O to show your master. If your master nods, it gets hung up to dry. If not, keep washing it.')], []),
    'EVENT/78.0': ('Meal', [(26, 56, 256, 'First pick the dish: left/right on the D-pad, then O. When the game starts, roll the D-pad round and round to make the hero eat, in either direction. Eat it before your opponent to win.')], []),
}


def screen_rgb(p):
    return p.rgb()[p.screen() if p.mapped else p.px]


def store(p, rgb):
    idx = nearest_px(p, rgb)
    if p.mapped:
        p.set_screen(idx)
    else:
        p.px = idx
    return p.bytes()


def nearest_px(p, rgb):
    if p.mapped:
        return nearest(p, rgb)
    from scipy.spatial import cKDTree
    used = np.unique(p.px)
    pal = p.rgb().astype(float)
    _, i = cKDTree(pal[used]).query(rgb.reshape(-1, 3).astype(float))
    return used[i].reshape(rgb.shape[:2]).astype('u1')


def boxes_mask(shape, boxes):
    m = np.zeros(shape[:2], bool)
    for x0, y0, x1, y1 in boxes:
        m[y0:y1, x0:x1] = True
    return m


def whitish(rgb, box, lum=70, sat=40):
    """Pixels inside box that look like pale, unsaturated lettering."""
    a = rgb.astype(int)
    m = np.zeros(rgb.shape[:2], bool)
    x0, y0, x1, y1 = box
    r = a[y0:y1, x0:x1]
    m[y0:y1, x0:x1] = (r.max(axis=2) > lum) & (r.max(axis=2) - r.min(axis=2) < sat)
    return ndimage.binary_dilation(m, iterations=2)


def lettering(size, lines, name, pt, fill, edge=None, glow=None, align='c', spacing=0):
    """RGBA picture of the lines, cropped to its ink."""
    W, H = size
    f = font(name, pt)
    pad = 6
    canvas = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(canvas)
    y = pad
    asc, desc = f.getmetrics()
    for line in lines:
        w = f.getlength(line)
        x = {'c': (W - w) / 2, 'r': W - w - pad, 'l': pad}[align]
        d.text((x, y), line, font=f, fill=255)
        y += asc + desc + spacing
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if glow:
        halo = canvas.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))
        out.paste(glow + (255,), (0, 0), halo)
    if edge:
        hard = canvas.filter(ImageFilter.MaxFilter(3))
        out.paste(edge + (255,), (0, 0), hard)
    out.paste(tuple(fill) + (255,), (0, 0), canvas)
    bb = out.getbbox()
    return out.crop(bb) if bb else out


def over(rgb, im, x, y):
    base = Image.fromarray(rgb).convert('RGBA')
    base.alpha_composite(im, (max(0, int(x)), max(0, int(y))))
    return np.array(base.convert('RGB'))


def fit_pt(lines, w, h, name=SERIF, pts=range(40, 7, -1), spacing=0):
    for pt in pts:
        f = font(name, pt)
        asc, desc = f.getmetrics()
        if max(f.getlength(s) for s in lines) <= w and len(lines) * (asc + desc + spacing) <= h:
            return pt
    raise ValueError(f'{lines} does not fit {w}x{h}')


def title_colour(rgb, box):
    """The lettering's colour: the most saturated, brightest pixels of the box."""
    x0, y0, x1, y1 = box
    r = rgb[y0:y1, x0:x1].reshape(-1, 3).astype(int)
    score = r.max(axis=1) * 2 - r.min(axis=1)
    top = r[np.argsort(score)[-max(20, len(r) // 25):]]
    return tuple(int(v) for v in top.mean(axis=0))


def chapter(leaf, num, title, box):
    p = gfx.Pic(leaf)
    rgb = screen_rgb(p)
    colour = title_colour(rgb, box)
    x0, y0, x1, y1 = box
    # spine: the small white kana, then the black chapter kanji on the grey band
    kana = whitish(rgb, (3, 14, 17, 138), lum=120, sat=40)
    a = rgb.astype(int)
    black = np.zeros(rgb.shape[:2], bool)
    black[136:218, 4:38] = a[136:218, 4:38].max(axis=2) < 70
    black = ndimage.binary_dilation(black, iterations=2)
    mask = kana | black | boxes_mask(rgb.shape, [box])
    detail = (max(40, x0 - 70), max(20, y0 - 60), max(100, x0 - 10), y0)
    rgb = clone_fill(rgb, mask, detail)
    # spine: name rotated, as on a video box
    words = lettering((130, 12), ['BLACK/MATRIX CROSS'], 'LiberationSansNarrow-Bold.ttf', 9, (232, 232, 232)).rotate(-90, expand=True)
    rgb = over(rgb, words, 4, 14)
    if num:
        word = lettering((36, 14), ['CHAPTER'], 'LiberationSansNarrow-Bold.ttf', 9, (10, 10, 10))
        rgb = over(rgb, word, 21 - word.width / 2, 142)
        n = lettering((60, 60), [num], SERIF, 40, (10, 10, 10))
        rgb = over(rgb, n, 21 - n.width / 2, 160)
    else:
        for i, s in enumerate(('FINAL', 'CHAPTER')):
            word = lettering((36, 14), [s], 'LiberationSansNarrow-Bold.ttf', 11 if not i else 9, (10, 10, 10))
            rgb = over(rgb, word, 21 - word.width / 2, 160 + i * 16)
    lines = title.split('|')
    pt = fit_pt(lines, 188, 106, pts=range(30, 11, -1))
    im = lettering((320, 110), lines, SERIF, pt, colour, edge=(14, 14, 20), align='r')
    rgb = over(rgb, im, 316 - im.width, min(238 - im.height, (y0 + y1) / 2 - im.height / 2 + 8))
    return store(p, rgb)


def end_card(leaf, line):
    p = gfx.Pic(leaf)
    rgb = screen_rgb(p)
    # rows of bright lettering: the last run is `To be continued...`, which stays; the rest goes
    a = rgb[40:200, 30:290].astype(int)
    bright = a.min(axis=2) > 150
    rows = np.where(bright.sum(axis=1) > 2)[0] + 40
    runs = np.split(rows, np.where(np.diff(rows) > 1)[0] + 1)
    top, keep = int(runs[0][0]), int(runs[-1][0])
    # the glow round the lettering sets the card's colour
    ring = ndimage.binary_dilation(bright, iterations=3) & ~bright
    sat = a[ring]
    glow = tuple(int(v) for v in sat[np.argsort(sat.max(axis=1) - sat.min(axis=1))[-200:]].mean(axis=0))
    rgb = clone_fill(rgb, boxes_mask(rgb.shape, [(30, top - 5, 290, keep - 3)]), (70, 30, 250, top - 8),
                     boxes_mask(rgb.shape, [(30, keep - 4, 290, keep + 16)]))
    lines = [line]
    if len(line) > 34:
        cut = line.rfind(' ', 0, len(line) // 2 + 6)
        lines = [line[:cut], line[cut + 1:]]
    im = lettering((320, 40), lines, SERIF, 13, (246, 244, 244), edge=glow)
    rgb = over(rgb, im, 160 - im.width / 2, top - 2)
    end = lettering((200, 40), ['END'], SERIF, 26, (250, 248, 248), edge=glow, glow=glow)
    rgb = over(rgb, end, 160 - end.width / 2, (top + im.height + keep) / 2 - end.height / 2)
    return store(p, rgb)


def time_card(leaf, text):
    p = gfx.Pic(leaf)
    rgb = screen_rgb(p)
    rgb[:] = rgb[0, 0]
    pt = fit_pt([text], 280, 60)
    im = lettering((320, 70), [text], SERIF, min(pt, 30), (208, 208, 208))
    return store(p, over(rgb, im, 160 - im.width / 2, 120 - im.height / 2))


def ending(leaf, text, box):
    p = gfx.Pic(leaf)
    rgb = screen_rgb(p)
    rgb = clone_fill(rgb, whitish(rgb, box, lum=40, sat=256), (0, 0, 60, 60))
    lines = text.split('|')
    im = lettering((320, 60), lines, SERIF, 18, (240, 240, 240), spacing=2)
    return store(p, over(rgb, im, 160 - im.width / 2, (box[1] + box[3]) / 2 - im.height / 2))


def bitmap(rgb, x, y, w, text, colour=(240, 240, 240), name='6x13B', line_h=14):
    """Wrapped pixel text with a one-pixel shadow. Raises if a word can't fit."""
    f = Bdf.get(name)
    rows, cur = [], ''
    for word in text.split(' '):
        trial = (cur + ' ' + word).strip()
        if f.text(trial).shape[1] <= w:
            cur = trial
        else:
            rows.append(cur)
            cur = word
    rows.append(cur)
    out = rgb.copy()
    for i, row in enumerate(rows):
        a = f.text(row)
        top = y + i * line_h + (line_h - 2 - a.shape[0] if a.shape[0] < line_h - 2 else 0)
        for dy, dx, c in ((1, 1, (10, 6, 6)), (0, 0, colour)):
            view = out[top + dy:top + dy + a.shape[0], x + dx:x + dx + a.shape[1]]
            view[a[:view.shape[0], :view.shape[1]]] = c
    return out


def manual(leaf, heading, blocks, boxes):
    p = gfx.Pic(leaf)
    rgb = screen_rgb(p)
    mask = whitish(rgb, (6, 2, 200, 54), lum=70, sat=60) | whitish(rgb, (196, 16, 296, 46), lum=70, sat=60)
    if heading == 'Whack-a-Mole':
        mask |= whitish(rgb, (8, 40, 136, 58), lum=60, sat=60) | whitish(rgb, (8, 58, 86, 118), lum=60, sat=60) | whitish(rgb, (8, 152, 190, 192), lum=60, sat=60)
    else:  # everything but the portrait disc at the lower right
        mask |= whitish(rgb, (8, 46, 288, 150), lum=60, sat=60) | whitish(rgb, (8, 150, 224, 192), lum=60, sat=60)
    if heading == 'Cooking':  # the speech bubble and the button icons stay
        mask[70:104, 26:64] = False
        mask[108:182, 44:60] = False
    mask |= whitish(rgb, (30, 192, 216, 214), lum=70, sat=60) | boxes_mask(rgb.shape, boxes)
    rgb = clone_fill(rgb, mask, None)
    im = lettering((200, 40), [heading], SERIF, 22 if len(heading) < 10 else 18, (226, 226, 226), edge=(16, 16, 16))
    rgb = over(rgb, im, 100 - im.width / 2, 12)
    im = lettering((90, 24), ['Controls'], SERIF, 13, (170, 170, 170))
    rgb = over(rgb, im, 244 - im.width / 2, 24)
    rgb = bitmap(rgb, 46, 198, 170, START, (226, 226, 226), '6x10')
    for b in blocks:
        rgb = bitmap(rgb, b[0], b[1], b[2], b[3], *b[4:])
    return store(p, rgb)


def master_select(leaf):
    p = gfx.Pic(leaf)
    rgb = p.rgb()[p.px]
    box = (70, 192, 570, 278)
    a = rgb.astype(int)
    m = np.zeros(rgb.shape[:2], bool)
    r = a[box[1]:box[3], box[0]:box[2]]
    m[box[1]:box[3], box[0]:box[2]] = (r[..., 2] > 150) & (r[..., 2] - r[..., 1] > 24)
    rgb = clone_fill(rgb, ndimage.binary_dilation(m, iterations=3), (60, 300, 200, 400))
    im = lettering((560, 70), ['Choose your master'], SERIF, 42, (226, 222, 255), edge=(70, 50, 200), glow=(50, 34, 170))
    return store(p, over(rgb, im, 320 - im.width / 2, 212))


def master_confirm(leaf):
    p = gfx.Pic(leaf)
    pal = p.rgb(0).astype(float)
    p.px[:] = np.where(p.px != 0, 0, p.px)  # re-keep only the heart, below
    old = gfx.Pic(leaf)
    p.px[64:112, 88:120] = old.px[64:112, 88:120]
    for (x, y, w, h), lines, pt in (((0, 0, 216, 64), ['Is this the', 'master you want?'], 24), ((0, 64, 64, 32), ['Yes'], 24),
                                    ((0, 96, 88, 32), ['No'], 24), ((0, 128, 168, 56), ['Left/Right: Select', 'O button: Confirm'], 15)):
        im = lettering((w, h), lines, SERIF, pt, (230, 230, 255), glow=(50, 30, 190), align='l')
        a = np.array(im)
        ox, oy = x + (w - im.width) // 2, y + (h - im.height) // 2  # the Japanese fills its rect; ink cropped smaller must stay on its centre
        rgba = a.reshape(-1, 4).astype(float)
        d = ((rgba[:, None, :3] - pal[None, 1:]) ** 2).sum(axis=2).argmin(axis=1) + 1
        d[rgba[:, 3] < 40] = 0
        p.px[oy:oy + im.height, ox:ox + im.width] = d.reshape(im.height, im.width)
    return p.bytes()


def redraws(leaves):
    """{leaf path: fn(leaf) -> new leaf}"""
    out = {}
    for path, row in CHAPTERS.items():
        out[path] = lambda b, r=row: chapter(b, *r)
    for path, line in ENDS.items():
        out[path] = lambda b, r=line: end_card(b, r)
    for path, text in TIMES.items():
        out[path] = lambda b, r=text: time_card(b, r)
    for path, row in ENDINGS.items():
        out[path] = lambda b, r=row: ending(b, *r)
    for path, row in MANUALS.items():
        out[path] = lambda b, r=row: manual(b, *r)
    out['SYSTEM/21'] = master_select
    out['SYSTEM/20.0'] = master_confirm
    return out


def main():
    ls = {}
    for disc in (2, 1):
        for m in gfx.leaves(disc).values():
            ls.update(m)
    table = redraws(ls)
    want = sys.argv[2:] or list(table)
    per = 4
    sheet = Image.new('RGB', (322 * per, 244 * (-(-len(want) * 2 // per))), (60, 0, 60))
    for j, path in enumerate(want):
        old = gfx.Pic(ls[path])
        new = gfx.Pic(table[path](ls[path]))
        for k, q in ((j * 2, old), (j * 2 + 1, new)):
            im = Image.fromarray(q.rgb(0)[q.screen() if q.mapped else q.px], 'RGB')
            if im.height > 240:
                im = im.resize((320, 240)) if im.width > 320 else im.crop((0, 0, 320, 240))
            sheet.paste(im, (k % per * 322, k // per * 244))
    sheet.save(sys.argv[1])
    print(Path(sys.argv[1]), sheet.size)


if __name__ == '__main__':
    main()

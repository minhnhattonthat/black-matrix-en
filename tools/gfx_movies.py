"""Text burned into movies: find the runs of frames with lettering, list them for reading, re-encode them with English (gfx/movies.tsv).
usage: gfx_movies.py decode NAME            frames of work/orig/d<N>/MOVIE/NAME.STR into work/movies/NAME/f/
       gfx_movies.py runs NAME              runs of frames with white lettering, a sheet of each run's sharpest frame -> work/movies/NAME/runs.png, runs.tsv
       gfx_movies.py encode NAME            work/movies/NAME/out.STR (jPSXdec partial replace; the build calls this through replaced())
       gfx_movies.py check NAME             decode out.STR into work/movies/NAME/o/ to read it"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / 'tools/jpsxdec/jpsxdec_v2.0/jpsxdec.jar'
DISC = {p.stem: d for d in (2, 1) for p in (ROOT / f'work/orig/d{d}/MOVIE').glob('*.STR')}  # 0101, OPENING: the same file on both discs


def workdir(name):
    return ROOT / f'work/movies/{name}'


def decode(name):
    d = workdir(name)
    (d / 'f').mkdir(parents=True, exist_ok=True)
    src = d / f'{name}.STR'
    src.write_bytes((ROOT / f'work/orig/d{DISC[name]}/MOVIE/{name}.STR').read_bytes())
    subprocess.run(['java', '-jar', str(JAR), '-f', src.name, '-x', f'{name}.idx'], cwd=d, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['java', '-jar', str(JAR), '-x', f'{name}.idx', '-i', '0', '-dir', 'f', '-vf', 'png', '-quality', 'high', '-noaud'],
                   cwd=d, check=True, stdout=subprocess.DEVNULL)


def frames(name):
    return sorted((workdir(name) / 'f').glob('*.png'))


def lettering_mask(a, lum=120, sat=46):
    a = a.astype(int)
    return (a.max(axis=2) > lum) & (a.max(axis=2) - a.min(axis=2) < sat)


def runs(name):
    fs = frames(name)
    energy = []
    boxes = []
    for f in fs:
        a = np.array(Image.open(f).convert('RGB'))
        m = lettering_mask(a)
        m = ndimage.binary_opening(m, structure=np.ones((1, 2)))
        energy.append(int(m.sum()))
        ys, xs = np.where(m)
        boxes.append((xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None)
    energy = np.array(energy)
    on = energy > 18
    lab, n = ndimage.label(ndimage.binary_closing(on, iterations=4))
    rows = []
    for i, s in enumerate(ndimage.find_objects(lab)):
        lo, hi = s[0].start, s[0].stop
        peak = lo + int(energy[lo:hi].argmax())
        rows.append((i, lo, hi, peak, int(energy[peak]), boxes[peak]))
    with open(workdir(name) / 'runs.tsv', 'w', encoding='utf-8', newline='\n') as w:
        for r in rows:
            w.write('\t'.join(map(str, r)) + '\n')
    per = 6
    h = Image.open(fs[0]).height
    sheet = Image.new('RGB', (per * 322, (-(-len(rows) // per)) * (h + 14)), (40, 0, 40))
    d = ImageDraw.Draw(sheet)
    for j, r in enumerate(rows):
        x, y = j % per * 322, j // per * (h + 14)
        sheet.paste(Image.open(fs[r[3]]).convert('RGB'), (x, y + 14))
        d.text((x + 2, y + 1), f'{r[0]}: {r[1]}-{r[2]} peak {r[3]}', fill=(255, 255, 0))
    sheet.save(workdir(name) / 'runs.png')
    print(len(rows), 'runs')


def table(name=None):
    """Rows of gfx/movies.tsv: (movie, lo, hi, box, align, English rows)."""
    rows = []
    for line in (ROOT / 'gfx/movies.tsv').read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            m, lo, hi, box, align, en, _jp = line.split('\t')
            if name in (None, m):
                rows.append((m, int(lo), int(hi), box, align, en.split('|')))
    return rows


def load(name, n):
    return np.array(Image.open(workdir(name) / f'f/{name}.STR[0][{n:04d}].png').convert('RGB')).astype(float)


def lum(a):
    return a @ np.array([0.299, 0.587, 0.114])


def smear(a, sx, sy):
    return ndimage.gaussian_filter(a, (sy, sx) + (0,) * (a.ndim - 2))


def lettering_rows(ref, low=90):
    """(y0, y1, x0, x1) of each row of lettering in a sharp frame's box. low: red lettering has little luminance."""
    on = ref > low
    count = on.sum(axis=1)
    rows = []
    lab, _ = ndimage.label(count > 0)
    for s in ndimage.find_objects(lab):
        y0, y1 = s[0].start, s[0].stop
        cuts = [y0]
        if y1 - y0 >= 20:  # a name touching the small print under it
            cut = y0 + 8 + int(count[y0 + 8:y1 - 8].argmin())
            if count[cut] < count[y0:y1].max() * .15:
                cuts.append(cut)
        cuts.append(y1)
        for a, b in zip(cuts, cuts[1:]):
            xs = np.where(on[a:b].any(axis=0))[0]
            if b - a >= 4 and len(xs):
                rows.append((a, b, int(xs[0]), int(xs[-1]) + 1))
    return rows


def text_size(text, font):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1]


def render_rows(size, jp_rows, lines, align, peak):
    """English over the Japanese rows: same row centres and anchor edge, a size from the row's height, RGB float."""
    w, h = size
    assert len(lines) == len(jp_rows), f'{len(jp_rows)} rows on screen, table has {lines}: {jp_rows}'
    im = Image.new('RGB', size)
    d = ImageDraw.Draw(im)
    for line, (y0, y1, x0, x1) in zip(lines, jp_rows):
        colour = (peak, peak, peak)
        if line.startswith('red:'):
            line, colour = line[4:], (int(peak), 0, 0)
        colour = tuple(int(c) for c in colour)
        pt = max(10, y1 - y0)
        room = w - 16
        while True:
            font = ImageFont.truetype(str(ROOT / 'fonts/LiberationSans-Bold.ttf'), pt)
            tw, _ = text_size(line, font)
            if tw <= room or pt <= 8:
                break
            pt -= 1
        assert tw <= room, f'{line}: {tw} px, room {room}'
        x = {'L': x0, 'R': x1 - tw, 'C': (x0 + x1 - tw) // 2}[align]
        x = max(4, min(x, w - tw - 4))
        d.text((x, (y0 + y1) // 2), line, font=font, fill=colour, anchor='lm')
    return np.array(im).astype(float)


SX = [0, .5, 1, 1.5, 2, 3, 4, 6, 8, 11, 15, 20, 28, 40]
SY = [0, .5, 1, 1.5, 2, 3, 4, 6, 8]
TAIL = 22  # blur and fade run on past the frames with readable lettering
BOX = {'L': (0, 160), 'R': (160, 320), 'F': (0, 320), 'A': (168, 320)}  # A: the ad's panel, right of its art


def card(name, lo, hi, side, align, lines, out):
    """Lettering on a black panel: fit each frame as fade x blur of the sharpest frame, then give the English the same fade and blur."""
    x0, x1 = BOX[side]
    box = lambda a: a[:, x0:x1]
    nums = range(max(0, lo - TAIL), hi + TAIL + 1)
    sharp = max(range(lo, hi + 1), key=lambda n: float(np.abs(np.diff(lum(box(load(name, n))), axis=1)).sum()))
    ref = lum(box(load(name, sharp)))
    ref[ref < 16] = 0
    peak = np.percentile(ref[ref > 0], 99)
    en = render_rows((x1 - x0, ref.shape[0]), lettering_rows(ref, 50 if any(s.startswith('red:') for s in lines) else 90), lines, align, peak)
    grid = [(sx, sy) for sx in SX for sy in SY]
    jp_grid = np.stack([smear(ref, sx, sy).ravel() for sx, sy in grid]).astype(np.float32)
    en_grid = [smear(en, sx, sy).astype(np.float32) for sx, sy in grid]
    norm = (jp_grid * jp_grid).sum(axis=1)
    done = 0
    for n in nums:
        a = load(name, n)
        y = lum(box(a)).ravel().astype(np.float32)
        dots = jp_grid @ y
        i = int((dots * dots / norm).argmax())
        k = float(np.clip(dots[i] / norm[i], 0, 1.1))
        if k * peak < 4:
            continue
        jp = jp_grid[i] * k
        far = jp < 2
        art = np.percentile(y[far], 99.5) if far.any() else 0
        bg = np.zeros_like(en) if art < 24 else np.clip(box(a) - jp.reshape(ref.shape)[..., None], 0, 255)
        a[:, x0:x1] = np.clip(bg + k * en_grid[i], 0, 255)
        Image.fromarray(a.astype(np.uint8)).save(out / f'{n:04d}.png')
        done += 1
    return done


def caption(w, h, lines, top=False):
    """English along the bottom (or top) of a w x h frame and the dark halo behind it, both 0-1."""
    font = ImageFont.truetype(str(ROOT / 'fonts/LiberationSerif-Bold.ttf'), 13)
    im = Image.new('L', (w, h))
    d = ImageDraw.Draw(im)
    bottom = 15 * len(lines) if top else h - 4
    for i, line in enumerate(reversed(lines)):
        tw, _ = text_size(line, font)
        assert tw <= w - 16, f'{line}: {tw} px'
        d.text(((w - tw) // 2, bottom - i * 15), line, font=font, fill=255, anchor='ls')
    en = np.array(im).astype(float) / 255
    backing = np.clip(ndimage.gaussian_filter(ndimage.binary_dilation(en > .2, iterations=2).astype(float), 1.5) * 1.3, 0, 1)
    return en, backing


def voice(name, lo, hi, align, lines, out):
    """A spoken line: English over the frames it is heard on. align T: at the top, clear of DEMO02's words in the bottom corners."""
    h, w = load(name, lo).shape[:2]
    en, backing = caption(w, h, lines, align == 'T')
    for n in range(lo, hi + 1):
        frame = load(name, n) * (1 - backing[..., None]) + en[..., None] * 235
        Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(out / f'{n:04d}.png')
    return hi + 1 - lo


def subtitle(name, lo, hi, lines, out):
    """A vertical subtitle over moving fire: paint it out stroke by stroke, then lay English along the bottom with the same fade."""
    frames = {n: load(name, n) for n in range(lo, hi + 1)}
    x0 = 240  # the subtitles stay right of the pentagram
    white = {n: f.min(axis=2) for n, f in frames.items()}
    level = np.array([np.percentile(w[:, x0:], 99) for w in white.values()])
    bright = [n for n, v in zip(frames, level) if v >= np.percentile(level, 50)]
    med = np.median(np.stack([white[n] for n in bright]), axis=0)
    mask = med > 72
    mask[:, :x0] = False
    ref = med * mask
    fill = ndimage.binary_dilation(mask, iterations=2)

    h, w = med.shape
    en, backing = caption(w, h, lines)

    sigmas = [0, 1, 2, 3, 4, 6]
    fits = []
    for n, f in frames.items():
        known = ~fill & (white[n] < 50)  # the white rings must not bleed into the fill
        weight = ndimage.gaussian_filter(known.astype(float), 2.5) + 1e-6
        patched = ndimage.gaussian_filter(f * known[..., None], (2.5, 2.5, 0)) / weight[..., None]
        bg = f.copy()
        bg[fill] = patched[fill]
        y = (white[n] - bg.min(axis=2)).ravel()
        best = max((float(smear(ref, s, s).ravel() @ y) ** 2 / float((smear(ref, s, s) ** 2).sum()), s) for s in sigmas)[1]
        layer = smear(ref, best, best)
        fits.append((n, bg, float(layer.ravel() @ y) / float((layer * layer).sum()), best))
    ks = ndimage.median_filter(np.clip([f[2] for f in fits], 0, 1.1), size=5)
    done = 0
    for (n, bg, _k, s), k in zip(fits, ks):
        t, b = smear(en, s, s), smear(backing, s, s)
        frame = bg * (1 - k * b[..., None]) + k * t[..., None] * 235
        Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(out / f'{n:04d}.png')
        done += 1
    return done


def typed(name, lo, hi, lines, out):
    """Black lettering typed onto a white card: the English types in at the rate the Japanese did."""
    meds = {n: float(np.median(lum(load(name, n)))) for n in range(lo, hi + 1)}
    ink = {n: float(np.clip(meds[n] - lum(load(name, n)) - 16, 0, None).sum()) for n in meds}
    total = max(ink.values())
    font = ImageFont.truetype(str(ROOT / 'fonts/LiberationSerif-Bold.ttf'), 15)
    h, w = load(name, lo).shape[:2]
    chars = sum(len(s) for s in lines)
    done = 0
    for n in meds:
        if ink[n] <= 0:
            continue
        left = ink[n] / total * chars
        im = Image.new('L', (w, h))
        d = ImageDraw.Draw(im)
        y = h // 2 - 9 * (len(lines) - 1)
        for line in lines:
            x = (w - font.getlength(line)) / 2
            for i, c in enumerate(line):
                d.text((x + font.getlength(line[:i]), y), c, font=font, fill=int(255 * min(1, max(0, left))), anchor='lm')
                left -= 1
            y += 18
        frame = meds[n] * (1 - np.array(im).astype(float) / 255)
        Image.fromarray(np.stack([frame] * 3, axis=2).astype(np.uint8)).save(out / f'{n:04d}.png')
        done += 1
    return done


def cache_key(name):
    return hashlib.sha1(repr(table(name)).encode() + Path(__file__).read_bytes()).hexdigest()


def encode(name):
    """work/movies/NAME/out.STR: the original movie with every row of the table re-encoded."""
    d = workdir(name)
    if not (d / 'f').is_dir():
        decode(name)
    out = d / 'new'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    for _m, lo, hi, box, align, lines in table(name):
        if box == 'S':
            done = subtitle(name, lo, hi, lines, out)
        elif box == 'T':
            done = typed(name, lo, hi, lines, out)
        elif box == 'V':
            done = voice(name, lo, hi, align, lines, out)
        else:
            done = card(name, lo, hi, box, align, lines, out)
        print(name, lo, hi, 'frames', done, flush=True)
    # whole frames: a partial replace keeps the frame's quantiser and lettering came out grey and blocky on busy frames
    # spoken lines take the frame's whole sectors: a black frame's data is under 1 KB, too little for any text (jPSXdec dies at quantiser 63)
    spoken = {n for _m, lo, hi, box, _a, _l in table(name) if box == 'V' for n in range(lo, hi + 1)}
    xml = ['<?xml version="1.0"?>', '<str-replace version="0.3">']
    xml += [f'<replace frame="{int(f.stem)}"{"" if int(f.stem) in spoken else " size-limit=" + chr(34) + "original non-zero" + chr(34)}>new/{f.name}</replace>'
            for f in sorted(out.glob('*.png'))]
    xml.append('</str-replace>')
    (d / 'replace.xml').write_text('\n'.join(xml) + '\n', encoding='utf-8')
    target = d / 'out.STR'
    shutil.copyfile(ROOT / f'work/orig/d{DISC[name]}/MOVIE/{name}.STR', target)
    subprocess.run(['java', '-jar', str(JAR), '-f', target.name, '-x', 'out.idx'], cwd=d, check=True, stdout=subprocess.DEVNULL)
    r = subprocess.run(['java', '-jar', str(JAR), '-x', 'out.idx', '-i', '0', '-replaceframes', 'replace.xml'],
                       cwd=d, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (d / 'replace.log').write_text(r.stdout + r.stderr, encoding='utf-8')
    (d / 'out.key').write_text(cache_key(name))
    return target


def replaced(disc):
    """{file name: bytes} of this disc's re-encoded movies, for the build; jPSXdec runs only when the table or this script changed."""
    files = {}
    for name in sorted({row[0] for row in table()}):
        if not (ROOT / f'work/orig/d{disc}/MOVIE/{name}.STR').exists():
            continue
        key = workdir(name) / 'out.key'
        if not key.exists() or key.read_text() != cache_key(name):
            encode(name)
        files[f'{name}.STR'] = (workdir(name) / 'out.STR').read_bytes()
    return files


def check(name):
    """Decode out.STR into work/movies/NAME/o/ to read the result."""
    d = workdir(name)
    subprocess.run(['java', '-jar', str(JAR), '-x', 'out.idx', '-i', '0', '-dir', 'o', '-vf', 'png', '-quality', 'high', '-noaud'],
                   cwd=d, check=True, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    {'decode': decode, 'runs': runs, 'encode': encode, 'check': check}[sys.argv[1]](sys.argv[2])

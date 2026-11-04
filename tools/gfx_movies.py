"""Text burned into movies: find the runs of frames with lettering, list them for reading, and later re-encode them with English.
usage: gfx_movies.py decode NAME            frames of work/orig/d<N>/MOVIE/NAME.STR into work/movies/NAME/f/
       gfx_movies.py runs NAME              runs of frames with white lettering, a sheet of each run's sharpest frame -> work/movies/NAME/runs.png, runs.tsv"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / 'tools/jpsxdec/jpsxdec_v2.0/jpsxdec.jar'
DISC = {'STAFF': 2, 'DEMO01': 2, 'DEMO02': 2, 'PROLOGUE': 1}


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


if __name__ == '__main__':
    {'decode': decode, 'runs': runs}[sys.argv[1]](sys.argv[2])

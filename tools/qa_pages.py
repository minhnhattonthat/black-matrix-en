"""Tour sheets with no current verdict, as pages of the frames nobody has read, for a reader without codex: 45 battles show the same help box, and a rebuild reshoots every sheet.
A frame differing from a read one by at most TOLERANCE pixels is the same frame: a changed word differs by more, a changed letter may not, so check a one-letter fix by zoom. Frames with an issue must be fixed or noted, since a rerun won't show them again.
usage: qa_pages.py pages            work/qa/pages/pNNN.png (6 unread frames each, full size), work/qa/pages/frames.tsv (sheet id, page, cell 1-6)
       qa_pages.py read             after reading every page: files its frames in work/qa/read/
       qa_pages.py verdicts NAME BAD.tsv   after `read`: work/qa/verdicts/NAME.tsv, ok for every sheet qa_gate wants, issue for those holding a frame BAD.tsv lists (page<TAB>cell<TAB>note)"""
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from skill import SKILL

ROOT = Path(__file__).resolve().parents[1]
MANIFEST, VERDICTS, PAGES, READ = (ROOT / p for p in ('work/qa/manifest.tsv', 'work/qa/verdicts', 'work/qa/pages', 'work/qa/read'))
TOLERANCE = 12
PER_PAGE = 6
STEP = 8  # the coarse grid that rules most frames out before a full compare


def cells(img):
    """The frames of one sheet.py sheet: 320x240 or 640x480 with a 2 px gutter; anything else (a gfx page) stays whole."""
    w, h = img.size
    for cw, ch in ((322, 242), (642, 482)):
        if w % cw == 0 and h % ch == 0:
            return [img.crop((x, y, x + cw - 2, y + ch - 2)) for y in range(0, h, ch) for x in range(0, w, cw)]
    return [img]


def same(a, b):
    return a.shape == b.shape and int((np.abs(a.astype(int) - b).max(axis=2) > 24).sum()) <= TOLERANCE


class Seen:
    """Frames by shape, with a coarse grid per frame so a lookup only fully compares the near ones."""

    def __init__(self):
        self.frames, self.grids = {}, {}

    def find(self, a):
        """Index of a frame like a among those of its shape, or None."""
        have = self.frames.get(a.shape, [])
        if not have:
            return None
        near = np.abs(self.grids[a.shape][:len(have)].astype(int) - a[::STEP, ::STEP]).max(axis=3)
        for i in np.nonzero((near > 24).sum(axis=(1, 2)) <= TOLERANCE)[0]:
            if same(have[i], a):
                return int(i)
        return None

    def add(self, a):
        have = self.frames.setdefault(a.shape, [])
        grid = a[::STEP, ::STEP]
        if a.shape not in self.grids:
            self.grids[a.shape] = np.zeros((64, *grid.shape), grid.dtype)
        elif len(have) == len(self.grids[a.shape]):
            self.grids[a.shape] = np.concatenate([self.grids[a.shape], np.zeros_like(self.grids[a.shape])])
        self.grids[a.shape][len(have)] = grid
        have.append(a)


def todo():
    """(sheet id, path) of each sheet qa_gate.py still wants read."""
    gate = [sys.executable, '-X', 'utf8', str(Path(SKILL) / 'scripts/qa_gate.py'), 'todo', str(MANIFEST), str(VERDICTS), '--size', '100000']
    out = subprocess.run(gate, capture_output=True, text=True, encoding='utf-8').stdout
    return [tuple(line.split('\t')) for line in out.splitlines() if line.count('\t') == 1]


def pages():
    PAGES.mkdir(parents=True, exist_ok=True)
    for old in PAGES.glob('*'):
        old.unlink()
    read = Seen()
    for f in READ.glob('*.png'):
        read.add(np.asarray(Image.open(f).convert('RGB')))
    sheets = todo()
    new, unread, rows, known = Seen(), [], [], 0  # rows: (sheet id, index into unread)
    index = {}  # frame shape: where in `unread` each of new's frames of that shape is
    for sheet, path in sheets:
        for cell in cells(Image.open(ROOT / path).convert('RGB')):
            a = np.asarray(cell)
            if a.max() < 16:
                continue  # black frame
            if read.find(a) is not None:
                known += 1
                continue
            hit = new.find(a)
            if hit is None:
                hit = len(new.frames.get(a.shape, []))
                new.add(a)
                index.setdefault(a.shape, []).append(len(unread))
                unread.append(cell)
            rows.append((sheet, index[a.shape][hit]))
    for start in range(0, len(unread), PER_PAGE):
        group = unread[start:start + PER_PAGE]
        w, h = max(c.width for c in group), max(c.height for c in group)
        page = Image.new('RGB', (min(3, len(group)) * (w + 2), ((len(group) + 2) // 3) * (h + 2)), (80, 0, 80))
        for k, c in enumerate(group):
            page.paste(c, (k % 3 * (w + 2), k // 3 * (h + 2)))
        page.save(PAGES / f'p{start // PER_PAGE:03d}.png')
    with open(PAGES / 'frames.tsv', 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(f'{sheet}\t{hit // PER_PAGE}\t{hit % PER_PAGE + 1}\n' for sheet, hit in rows)
    # a sheet of only black or read frames has no row: its verdict comes from this list
    (PAGES / 'sheets.txt').write_text(''.join(f'{s}\n' for s, _ in sheets), encoding='utf-8')
    for k, cell in enumerate(unread):
        cell.save(PAGES / f'frame{k:04d}.png')
    print(len(sheets), 'sheets,', known, 'frames already read,', len(rows), 'to read,', len(unread), 'distinct,', (len(unread) + PER_PAGE - 1) // PER_PAGE, 'pages')


def file_read():
    READ.mkdir(parents=True, exist_ok=True)
    base = len(list(READ.glob('*.png')))
    frames = sorted(PAGES.glob('frame*.png'))
    for k, f in enumerate(frames):
        shutil.copy(f, READ / f'r{base + k:05d}.png')
    print(len(frames), 'frames filed,', base + len(frames), 'read in all')


def verdicts(name, bad):
    notes = {}
    for line in Path(bad).read_text(encoding='utf-8').splitlines():
        if line.strip():
            page, cell, note = line.split('\t')
            notes[page.lstrip('p0') or '0', cell] = note
    hits = {}
    for line in (PAGES / 'frames.tsv').read_text(encoding='utf-8').splitlines():
        sheet, page, cell = line.split('\t')
        if (page, cell) in notes:
            hits.setdefault(sheet, []).append(notes[page, cell])
    out = [f"{s}\tissue\t{'; '.join(dict.fromkeys(hits[s]))}\n" if s in hits else f'{s}\tok\t\n'
           for s in (PAGES / 'sheets.txt').read_text(encoding='utf-8').split()]
    (VERDICTS / f'{name}.tsv').write_text(''.join(out), encoding='utf-8')
    print(len(out), 'verdicts,', len(hits), 'issues')


if __name__ == '__main__':
    probe = np.zeros((16, 16, 3), np.uint8)
    other = probe.copy()
    other[0, 0] = 255
    assert same(probe, other) and not same(probe, np.full((16, 16, 3), 255, np.uint8))
    seen = Seen()
    seen.add(probe)
    assert seen.find(other) == 0 and seen.find(np.full((16, 16, 3), 255, np.uint8)) is None
    if sys.argv[1:2] == ['pages']:
        pages()
    elif sys.argv[1:2] == ['read']:
        file_read()
    elif sys.argv[1:2] == ['verdicts']:
        verdicts(*sys.argv[2:4])
    else:
        sys.exit(__doc__)

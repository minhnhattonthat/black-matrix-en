"""Picture redraws: the format code is byte-exact on every picture, and a redraw changes only pixels, cell map and sprite rects."""
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import gfx  # noqa: E402
import gfx_labels  # noqa: E402


@pytest.fixture(scope='module')
def pics():
    return {(d, p): b for d in (1, 2) for m in gfx.leaves(d).values() for p, b in m.items()}


def test_every_picture_roundtrips(pics):
    for (d, p), b in pics.items():
        assert gfx.Pic(b).bytes() == b, (d, p)


def test_screen_roundtrips_on_a_mapped_picture(pics):
    for b in [b for (d, p), b in pics.items() if p in ('BATTLE/11.0', 'EVENT/71.0', 'EVENT/106.0') and d == 1]:
        a = gfx.Pic(b)
        want = a.screen()
        a.set_screen(want)
        assert np.array_equal(gfx.Pic(a.bytes()).screen(), want)


def test_set_screen_grows_the_sheet_when_it_must(pics):
    a = gfx.Pic(pics[(1, 'EVENT/106.0')])  # a short sheet: few distinct cells
    noise = np.random.RandomState(1).randint(1, 200, (a.rows * 16, a.cols * 16)).astype('u1')
    a.set_screen(noise)
    b = gfx.Pic(a.bytes())
    assert np.array_equal(b.screen(), noise)
    assert b.px.shape[1] > 64 and b.px.shape[0] == a.h


def test_label_rows_fit_their_sheets_and_their_rects(pics):
    for path, rows in gfx_labels.rows().items():
        p = gfx.Pic(pics[(1, path)])
        for r in gfx_labels.packed(rows):
            assert r['x'] + r['w'] <= p.px.shape[1] and r['y'] + r['h'] <= p.px.shape[0], (path, r)
        gfx_labels.redraw_sheet(pics[(1, path)], rows)  # raises if a text doesn't fit


def test_redraws_change_only_pixels_map_and_rects():
    got = {}
    for d in (1, 2):
        got[d] = gfx.replacements(d)
        orig = {p: b for n in gfx.GFX_DATS for p, b in gfx.dat.walk((gfx.ORIG / f'd{d}/{n}.DAT').read_bytes(), n)}
        for name, leaves in got[d].items():
            for p, new in leaves.items():
                old = orig[p]
                if gfx.is_pic(old):
                    a, b = gfx.Pic(old), gfx.Pic(new)
                    assert (a.kind, a.cw, a.ch, a.h) == (b.kind, b.cw, b.ch, b.h), p
                    assert np.array_equal(a.colors, b.colors), p
                    if a.mapped:
                        assert (a.cols, a.rows) == (b.cols, b.rows), p
                else:  # a sprite table: only (x, y, w, h) records in its rect list move
                    assert len(old) == len(new), p
                    off = struct.unpack_from('<I', old, 12)[0]
                    n = struct.unpack_from('<I', old, off)[0]
                    assert old[:off + 4] == new[:off + 4] and old[off + 4 + 4 * n:] == new[off + 4 + 4 * n:], p
    # both discs carry the same SYSTEM and BATTLE redraws
    assert got[1]['SYSTEM'].keys() == got[2]['SYSTEM'].keys() and got[1]['BATTLE'].keys() == got[2]['BATTLE'].keys()


def test_font_files_are_listed_with_a_licence():
    listed = (ROOT / 'docs/fonts.md').read_text(encoding='utf-8')
    for f in (ROOT / 'fonts').glob('*'):
        if f.suffix in ('.ttf', '.bdf'):
            assert f.name in listed, f.name

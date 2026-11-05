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
import gfx_movies  # noqa: E402


@pytest.fixture(scope='module')
def pics():
    return {(d, p): b for d in (1, 2) for m in gfx.leaves(d).values() for p, b in m.items()}


def test_a_strip_cell_with_a_tighter_pitch_holds_fewer_columns():
    px = np.zeros((16, 64), 'u1')
    gfx_labels.draw_strip(px, {'text': 'MMMMMM', 'style': 'c8,f6x10,strip=0+0+12;16+0;32+0'}, px)
    # read back in the game's order: 12 columns from the first cell, then 14 and 14; no column is lost at a boundary
    seen = np.hstack([px[:, 1:13], px[:, 17:31], px[:, 33:47]])
    want = gfx_labels.fit(['MMMMMM'], 40, 14, ['6x10'])[0]
    assert (seen.any(axis=0).sum(), seen.sum()) == (want.any(axis=0).sum(), want.sum() * 8)


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


def test_movie_table_runs_do_not_overlap_and_rows_split():
    rows = gfx_movies.table()
    assert {r[0] for r in rows} <= set(gfx_movies.DISC)
    for name in gfx_movies.DISC:
        spans = sorted((r[1], r[2]) for r in rows if r[0] == name)
        assert all(a[1] + gfx_movies.TAIL < b[0] for a, b in zip(spans, spans[1:]) if b[0] - a[1] > 2 * gfx_movies.TAIL)
    ref = np.zeros((60, 100))
    ref[10:24, 5:50] = 200  # a name
    ref[24, 5:7] = 200  # touching the small print under it
    ref[25:36, 5:40] = 200
    ref[45:55, 60:90] = 200
    assert [(y0, y1) for y0, y1, _, _ in gfx_movies.lettering_rows(ref)] == [(10, 24), (24, 36), (45, 55)]


def test_spoken_subtitles_fit_and_take_turns():
    spoken = [r for r in gfx_movies.table() if r[3] == 'V']
    assert {r[0] for r in spoken} == {'0101', 'DEMO01', 'DEMO02'}
    for r in spoken:
        assert r[1] <= r[2] and r[4] in 'BT' and len(r[5]) <= 2
        gfx_movies.caption(320, 176, r[5], r[4] == 'T')  # asserts the width
    for name in {r[0] for r in spoken}:
        spans = sorted((r[1], r[2]) for r in spoken if r[0] == name)
        assert all(a[1] < b[0] for a, b in zip(spans, spans[1:]))


def test_font_files_are_listed_with_a_licence():
    listed = (ROOT / 'docs/fonts.md').read_text(encoding='utf-8')
    for f in (ROOT / 'fonts').glob('*'):
        if f.suffix in ('.ttf', '.bdf'):
            assert f.name in listed, f.name

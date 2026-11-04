"""The warp's fixed offsets and the scene list must match the scripts. Needs the extracted disc (work/extracted), so it skips on a clean clone."""
import csv
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
SCN = ROOT / 'work/extracted/disc1/SCENARIO.DAT'
pytestmark = pytest.mark.skipif(not SCN.exists(), reason='needs work/extracted (tools/disc.py)')


@pytest.fixture(scope='module')
def leaves():
    import dat
    return dat.unpack(SCN.read_bytes())


def starts(b):
    import psi
    toks, _, _ = psi.tokenize(b)
    return {t.off: t for t in toks}


def test_script5_anchors(leaves):
    """warp.lua writes into script 5 at these offsets, and reads its disc operand at 0xB54."""
    t = starts(leaves[5])
    assert (t[0xB4E].op, t[0xB4E].sub) == (8, 4)
    assert struct.unpack_from('<I', leaves[5], 0xB54)[0] == 1
    assert 0xB5A in t and 0xC72 in t  # jump source and target
    assert (t[0xD52].op, t[0xD52].sub) == (9, 0x29)  # chain goes over this data load
    assert (t[0xBB6].op, t[0xBB6].sub) == (9, 0x31)  # master select


def test_stub_room(leaves):
    """The stub at 0x7780 must clear every script; the font block starts at 0x7800. The build holds English to the same bound."""
    import extract
    assert extract.SCRIPT_MAX + 0x10 == 0x7780
    assert max(0x10 + struct.unpack_from('<I', b, 12)[0] for b in leaves if b) < 0x7780


def test_scene_list(leaves):
    rows = list(csv.DictReader(open(ROOT / 'tools/debug/scenes.tsv', encoding='utf-8', newline=''), delimiter='\t', quoting=csv.QUOTE_NONE))
    assert len({r['name'] for r in rows}) == len(rows)
    for r in rows:
        assert r['disc'] in ('1', '2'), r['name']
        if r['proof'] != '-':
            assert 0 <= int(r['proof']) <= int(r['frames']), r['name']
        if r['script'] == '-':
            assert r['route'] != '-', r['name']
            continue
        t = starts(leaves[int(r['script'])])
        for col in ('pc', 'until'):
            if r[col] != '-':
                assert int(r[col], 16) in t, f"{r['name']}: {col} {r[col]} is not an op start"


def test_coverage(leaves):
    """Every battle script, chapter card and end card has a scene."""
    rows = list(csv.DictReader(open(ROOT / 'tools/debug/scenes.tsv', encoding='utf-8', newline=''), delimiter='\t', quoting=csv.QUOTE_NONE))
    names = {r['name'] for r in rows}
    scripts = {int(r['script']) for r in rows if r['script'] != '-'}
    for i, b in enumerate(leaves):
        if b and any(t.op == 0xB and t.sub == 1 for t in starts(b).values()):
            assert i in scripts, f'battle script {i} has no scene'
    for ch in range(1, 13):
        assert f'ch{ch:02d}_card' in names
    for ch in range(1, 12):
        assert f'ch{ch:02d}_end' in names

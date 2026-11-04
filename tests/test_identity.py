"""Unpack -> repack with no edits gives the original bytes, on both discs, as images and as archives.
The controls prove the build really reads its inputs and that a file can change or grow without disturbing the rest."""
import hashlib
import shutil
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build
import dat
import disc as disclib
import pak

pytestmark = pytest.mark.skipif(not (build.rom(1).exists() and build.rom(2).exists()), reason='needs the dump in rom/')
OUT = ROOT / 'work/id'
DATS = 'SYSTEM SCENARIO BATTLE EVENT SOUND'.split()
PINNED = dict(reversed(l.split(None, 1)) for l in (ROOT / 'rom.sha1').read_text(encoding='utf-8').splitlines() if l and l[0] != '#')


@pytest.fixture(scope='module', autouse=True)
def drop_images():
    yield
    shutil.rmtree(OUT, ignore_errors=True)  # 2 GB of images, on every commit


def sha1(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha1').hexdigest()


@pytest.mark.parametrize('n', build.DISCS)
def test_rebuilt_disc_is_identical(n):
    out = build.make_image(n, {}, OUT / f'identity{n}.bin')
    assert sha1(out) == PINNED[f'rom/Black-Matrix + (Japan) (Disc {n}).bin']
    assert sha1(out) == sha1(build.rom(n))


@pytest.mark.parametrize('n', build.DISCS)
@pytest.mark.parametrize('name', DATS)
def test_archives_repack_identically_at_every_level(n, name):
    d = (build.ORIG / f'd{n}/{name}.DAT').read_bytes()
    assert dat.pack(dat.unpack(d)) == d
    assert pak.rebuild(d) == d


def test_pack_refuses_what_the_table_cannot_hold():
    with pytest.raises(struct.error):
        pak.pack([bytes(0x10000 << 4)], 4)


def test_pack_reparses_and_pads_a_changed_child():
    c = pak.pack([b'abc', b'', b'x' * 17], 4, 2048)
    assert len(c) == 2048 and pak.parse(c) == [(32, 16), (48, 0), (48, 32)]
    assert c[32:48] == b'abc' + bytes(13)


def files(path):
    return {p: (lba, size, form2) for p, lba, size, _, form2 in disclib.Disc(path).files()}


def test_a_changed_file_only_touches_its_own_sectors():
    orig = (build.ORIG / 'd1/SYSTEM.CNF').read_bytes()
    out = build.make_image(1, {'SYSTEM.CNF': orig.replace(b'BOOT', b'boot', 1)}, OUT / 'changed1.bin')
    a, b = disclib.Disc(build.rom(1)), disclib.Disc(out)
    assert a.sectors == b.sectors
    lba = files(out)['/SYSTEM.CNF'][0]
    assert b.read(lba, 4) == b'boot'
    with open(build.rom(1), 'rb') as f, open(out, 'rb') as g:
        assert f.read(lba * 2352) == g.read(lba * 2352)
        f.seek((lba + 1) * 2352), g.seek((lba + 1) * 2352)
        assert hashlib.sha1(f.read()).digest() == hashlib.sha1(g.read()).digest()


def test_a_grown_file_moves_the_rest_and_keeps_their_bytes():
    orig = (build.ORIG / 'd1/2ND.BIN').read_bytes()
    out = build.make_image(1, {'2ND.BIN': orig + bytes(2048 * 5)}, OUT / 'grown1.bin')
    a, b = files(build.rom(1)), files(out)
    assert b['/2ND.BIN'][1] == a['/2ND.BIN'][1] + 2048 * 5
    moved = [p for p in a if a[p][0] > a['/2ND.BIN'][0]]
    assert moved and all(b[p][0] == a[p][0] + 5 and b[p][1:] == a[p][1:] for p in moved)
    first = min(a[p][0] for p in moved)
    x, y = disclib.Disc(build.rom(1)), disclib.Disc(out)
    assert y.sectors == x.sectors + 5
    x.f.seek(first * 2352), y.f.seek((first + 5) * 2352)
    # every later sector, minus the 16-byte sync and address that must change; only the MOVIE directory may differ
    diff = [s for s in range(first, x.sectors) if x.f.read(2352)[16:] != y.f.read(2352)[16:]]
    assert diff == [a['/MOVIE/OPENING.STR'][0] - 1]

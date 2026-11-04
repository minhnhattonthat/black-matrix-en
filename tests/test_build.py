"""The English build, made here from script/, against the original: text lint, nothing written outside text slots, scripts keep every op,
no Japanese left outside the reviewed noise. References/pipeline.md, Checks."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build
import dat
import engine
import extract
import fit
import gfx
import lint
import psi
import romdiff
import text_sweep

pytestmark = pytest.mark.skipif(not (extract.ORIG / 'd1.xml').exists(), reason='needs the dump, unpacked by build.py')


@pytest.fixture(scope='module')
def docs():
    return build.documents()


@pytest.fixture(scope='module')
def built(docs):
    return {n: build.disc_files(n, docs) for n in build.DISCS}


def _slots(rel, doc, x):
    """Byte offsets of x the text of one table or code document may change."""
    group, stem = rel.split('/')
    if group == 'code':
        _, base, skip, _, _ = extract.CODE[stem[:-5]]
        for s in doc['strings']:
            p = int(s['id'].split(':')[1], 16) - base + skip
            yield from range(p, p + 2 * s['max'] + (0 if s.get('order') == 'be' else 2))
    else:
        _, head, row, fields = extract.TABLES[stem[:-5]]
        for s in doc['strings']:
            r, f = s['id'].split(':')[1].split('.')
            p = head + int(r) * row + fields[f][0]
            yield from range(p, p + 2 + 2 * fields[f][1])


def test_lint_is_clean(docs):
    assert lint.errors(docs) == []


def test_lint_catches_what_it_is_for():
    doc = lambda **k: {'scn/0.json': {'strings': [{'id': 's0:0', 'jp': 'あ', 'en': 'x', 'box': '17x3', **k}]}}
    assert lint.errors(doc()) == []
    assert 'no English' in lint.errors(doc(en=''))[0]
    assert 'control words' in lint.errors(doc(jp='あ{0020}'))[0]
    assert 'stray' in ' '.join(lint.errors(doc(en='x{')))
    assert 'ordinal' in lint.errors(doc(jp='あ{0020}', en='{0020}th'))[0]
    assert 'blank' in lint.errors(doc(en='x '))[0]
    assert 'Japanese' in ' '.join(lint.errors(doc(en='あ')))
    assert 'a row has' in lint.errors(doc(en='x' * 35))[0]


def test_wrap_is_balanced_only_in_a_box():
    assert fit.wrap('aaaa bbbb cccc dddd eeee ffff gggg hhhh', 11, 3) == ['aaaa bbbb cccc dddd', 'eeee ffff gggg hhhh']
    assert fit.wrap('aaaa bbbb cc', 5) == ['aaaa bbbb', 'cc']
    assert fit.wrap('aaaa bbbb cc', 5, 3) == ['aaaa', 'bbbb cc']


@pytest.mark.parametrize('n', build.DISCS)
def test_exe_and_overlays_change_only_text_slots_and_hooks(docs, built, n):
    for rel, doc in docs.items():
        if not rel.startswith('code/'):
            continue
        name = [c[3:] for c in doc['copies'] if c.startswith(f'd{n}:')][0]
        orig = (extract.ORIG / f'd{n}/{name}').read_bytes()
        allowed = set(_slots(rel, doc, orig))
        if name == extract.EXE[n]:
            allowed |= {i for lo, hi in engine.RANGES for i in range(lo - engine.BASE, hi - engine.BASE)}
        errs, _ = romdiff.check(orig, built[n][name], allowed, [])
        assert errs == [], name


@pytest.mark.parametrize('n', build.DISCS)
def test_dat_leaves_change_only_where_text_lives(docs, built, n):
    owner = {c[3:]: rel for rel, d in docs.items() for c in d['copies'] if c.startswith(f'd{n}:')}
    pictures = gfx.replacements(n)
    for name, leaves in extract.dat_leaves(n).items():
        new = dict(dat.walk(built[n][f'{name}.DAT'], name))
        assert new.keys() == leaves.keys(), name
        for p, x in leaves.items():
            rel = owner.get(p)
            if p in pictures.get(name, {}):  # gfx.py's own tests hold what a redraw may change
                assert new[p] == pictures[name][p], p
            elif p == 'SYSTEM/0.0':  # the font's tail takes the long strings
                lo = engine.LONG_RAM - engine.FONT_RAM
                assert new[p][:lo] == x[:lo] and len(new[p]) == len(x)
            elif rel is None:
                assert new[p] == x, p
            elif rel.startswith('table/'):
                assert romdiff.check(x, new[p], set(_slots(rel, docs[rel], x)), [])[0] == [], p
            else:
                a, b = psi.tokenize(x)[0], psi.tokenize(new[p])[0]
                assert [(t.op, t.sub, t.words is None, len(t.targets)) for t in a] == [(t.op, t.sub, t.words is None, len(t.targets)) for t in b], p
                for s, t in zip(a, b):
                    assert not t.words or not any(0x8200 <= w < 0xFC00 for w in t.words), f'{p}:{t.off:x} still has Japanese'
                    # every operand but jumps and text stays as it was
                    assert [q for q in s.parts if q[0] not in 'LT'] == [q for q in t.parts if q[0] not in 'LT'], f'{p}:{s.off:x}'


@pytest.mark.parametrize('n', build.DISCS)
def test_no_japanese_outside_the_text_but_the_reviewed_noise(built, n):
    locs = {f'd{n}:{name}': x for name, x in built[n].items() if not name.endswith('.DAT')}
    for name in extract.DATS:
        locs.update({f'd{n}:{p}': x for p, x in dat.walk(built[n][f'{name}.DAT'], name)})
    noise = set(text_sweep.NOISE.read_text(encoding='utf-8').splitlines())
    # the list is deduped over both discs and offsets move with a leaf: compare by what the run says
    known = {l.split('\t')[3] for l in noise}
    assert [l for l in text_sweep.sweep(locs) if l.split('\t')[3] not in known] == []


def test_no_branch_lands_inside_a_patched_span():
    exe = (extract.ORIG / f'd1/{extract.EXE[1]}').read_bytes()
    code = exe[0x800:]
    spans = [(lo, hi) for lo, hi in engine.RANGES if hi - lo > 4 and (lo, hi) not in engine.FREE]
    hits = []
    for i in range(0, len(code) & ~3, 4):
        w = struct.unpack_from('<I', code, i)[0]
        op, pc = w >> 26, 0x80010000 + i
        if op in (2, 3):
            t = (pc & 0xF0000000) | (w & 0x3FFFFFF) << 2
        elif op in (1, 4, 5, 6, 7):
            t = pc + 4 + (struct.unpack('<h', struct.pack('<H', w & 0xFFFF))[0] << 2)
        else:
            continue
        hits += [(hex(pc), hex(t)) for lo, hi in spans if lo < t < hi]
    assert hits == []

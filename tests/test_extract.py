"""Extraction against the original discs: every string re-encodes to the original bytes and every Japanese run is either
extracted or in the reviewed list of non-text hits (tests/text_noise.tsv)."""
import hashlib
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build
import dat
import extract
import psi
import recon_ptr
import text_sweep

pytestmark = pytest.mark.skipif(not (extract.ORIG / 'd1.xml').exists(), reason='needs the dump, unpacked by build.py')


@pytest.fixture(scope='module')
def docs():
    return extract.load()


@pytest.fixture(scope='module')
def scripts():
    d = (extract.ORIG / 'd1/SCENARIO.DAT').read_bytes()
    return dict(dat.walk(d, 'SCENARIO'))


def test_script_folder_matches_a_fresh_extraction(docs):
    fresh = extract.extract_all()
    assert docs.keys() == fresh.keys()
    for rel, doc in fresh.items():
        have = docs[rel]
        assert have['copies'] == doc['copies'], rel
        assert [{k: v for k, v in s.items() if k != 'en'} for s in have['strings']] == \
               [{k: v for k, v in s.items() if k != 'en'} for s in doc['strings']], rel


@pytest.mark.parametrize('n', build.DISCS)
def test_every_file_rebuilds_from_the_jp_text(docs, n):
    files = extract.text_files(n, 'jp', psi.encode, docs)
    assert len(files) == 9  # EXE, four overlays, four DATs
    for name, data in files.items():
        assert hashlib.sha1(data).digest() == hashlib.sha1((extract.ORIG / f'd{n}/{name}').read_bytes()).digest(), name


def test_no_japanese_run_is_left_outside_the_extracted_text():
    lines = text_sweep.sweep(text_sweep.all_locations())
    assert sorted(lines) == sorted(text_sweep.NOISE.read_text(encoding='utf-8').splitlines())
    # the only hits in a file with text: two copies of one EXE table, both byte orders
    text = {c for d in extract.load().values() for c in d['copies']}
    assert sum(l.split('\t')[0] in text for l in lines) == 8


@pytest.mark.parametrize('name', extract.CODE)
def test_every_string_code_points_at_is_extracted(docs, name):
    fname, base, skip, areas, _ = extract.CODE[name]
    x = (extract.ORIG / f'd1/{fname}').read_bytes()[skip:]
    refs, words = recon_ptr.code_refs(x[:len(x) & ~3])
    data = set(words)
    have = {int(s['id'].split(':')[1], 16) for s in docs[f'code/{name}.json']['strings']}
    missed = []
    for off, ws in psi.walk(x):
        a = base + off
        pointed = refs[a] or (a in data and len(ws) > 1)
        if pointed and a not in have and any(w != extract.BLANK for w in ws):
            missed.append((hex(a), psi.decode(ws)))
    assert not missed


def test_every_script_is_fully_tokenized_and_rebuilds(scripts):
    assert len(scripts) == 524
    for p, x in scripts.items():
        toks, end, want = psi.tokenize(x)
        assert end == want, p
        assert psi.rebuild(x) == x, p


def test_every_text_operand_is_extracted(docs, scripts):
    have = {s['id'] for rel, d in docs.items() if rel.startswith('scn/') for s in d['strings']}
    want = {f's{p.split("/")[1]}:{t.off:05x}' for p, x in scripts.items() for t in psi.tokenize(x)[0] if t.words is not None}
    assert have == want
    assert len(want) == 9066


def test_longer_text_keeps_every_jump_on_its_token(scripts):
    x = scripts['SCENARIO/226']
    toks = psi.tokenize(x)[0]
    jumps = [t for t in toks if t.targets]
    assert jumps
    new = psi.rebuild(x, {t.off: list(t.words) + [0x8140] * 3 for t in toks if t.words is not None})
    after = psi.tokenize(new)[0]
    assert [t.op for t in after] == [t.op for t in toks] and len(new) % 2048 == 0
    at = {t.off: i for i, t in enumerate(toks)}
    at_new = {t.off: i for i, t in enumerate(after)}
    for a, b in zip(toks, after):
        for t, u in zip(a.targets, b.targets):
            assert at[t + psi.CODE_BASE] == at_new[u + psi.CODE_BASE]
    assert struct.unpack_from('<I', new, 12)[0] == psi.tokenize(new)[1] - psi.CODE_BASE


def test_encode_inverts_decode_and_refuses_ascii():
    words = [0x8140, 0x10, 0x21, 0x82A0, 0x83C3]
    assert psi.encode(psi.decode(words)) == words
    with pytest.raises(ValueError):
        psi.encode('A')


def test_a_fixed_field_refuses_overflow_and_pads(docs):
    x = dict(extract.dat_leaves(1)['SYSTEM'])['SYSTEM/5.0']
    s = {'id': 'weapon:0.name', 'en': 'ナイフナイフ'}
    new = extract.table_apply('weapon', x, [s], 'en', psi.encode)
    assert struct.unpack_from('<H', new, 0x10)[0] == 6 and new[:0x10] == x[:0x10] and new[0x22:] == x[0x22:]
    s['en'] = 'ナ' * 9
    with pytest.raises(ValueError):
        extract.table_apply('weapon', x, [s], 'en', psi.encode)


def test_a_cell_field_keeps_its_rows():
    w = extract._uncells('あ\nい', 19, 38, psi.encode)
    assert len(w) == 38 and w[0] == 0x82A0 and w[19] == 0x82A2 and w[1] == w[37] == extract.BLANK
    assert extract._cells(w, 19) == 'あ\nい'

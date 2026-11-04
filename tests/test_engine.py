"""The half-width engine: encoding, font, and the assembled hook run under unicorn with exact-PC checks."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import engine

FONT = (ROOT / 'asm/font7x14.bin').read_bytes()
RET = 0x80000100  # where hw_glyph returns to in the tests
LOOKUP = 0x8002A8DC  # the original Shift-JIS glyph lookup


def test_encode_pairs_letters_and_passes_the_rest():
    assert engine.encode('Ab') == [0x4162]
    assert engine.encode('Abc') == [0x4162, 0x6320]
    assert engine.encode('Ab\ncd') == [0x4162, 0x10, 0x6364]
    assert engine.encode('A{0021}b') == [0x4120, 0x21, 0x6220]
    assert engine.encode('あ') == [0x82A0]
    assert engine.encode('A　') == [0x4120, 0x8140]
    assert engine.decode(engine.encode('Ab{0021}\nc')) == 'Ab{0021}\nc '
    with pytest.raises(ValueError):
        engine.encode('é')


def test_no_pair_word_can_read_as_a_control_or_a_kanji():
    letters = [chr(c) for c in range(0x20, 0x7F) if chr(c) != '{']  # { opens a control word, so it is never text
    for a in letters:
        for b in letters:
            assert 0x2000 <= engine.encode(a + b)[0] < 0x8000


def test_long_strings_share_a_word_and_lay_out():
    long = engine.Long()
    assert long.add([0x4162]) == 0x30
    assert long.add([0x6364, 0x10]) == 0x31
    assert long.add([0x4162]) == 0x30
    ix, data = long.blobs()
    assert ix == struct.pack('<2H', 0, 2)
    assert data == struct.pack('<5H', 1, 0x4162, 2, 0x6364, 0x10)
    for i in range(engine.LONG_LAST - 0x31):
        long.add([i])
    with pytest.raises(ValueError):
        long.add([0x9999])


def test_too_long_code_string_goes_to_the_long_table():
    import extract
    x = (ROOT / 'work/orig/d1/SLPS_029.62').read_bytes() if (ROOT / 'work/orig/d1/SLPS_029.62').exists() else None
    if x is None:
        pytest.skip('needs the unpacked dump')
    s = {'id': 'slps:80076298', 'jp': '破損', 'en': 'Corrupted', 'max': 2}
    with pytest.raises(ValueError):
        extract.code_apply('slps', x, [s], 'en', engine.encode)
    long = engine.Long()
    new = extract.code_apply('slps', x, [s], 'en', engine.encode, long)
    p = 0x80076298 - engine.BASE
    assert struct.unpack_from('<3H', new, p) == (2, 0x30, 0x8140)  # count stays, padded with the blank
    assert long.items == [tuple(engine.encode('Corrupted'))]


def test_font_fits_the_half_cell():
    assert len(FONT) == 95 * 14
    assert not any(b & 1 for b in FONT)  # bits 7..1 only: the cell has 7 columns per letter
    assert not any(FONT[:14])  # glyph 0 is a blank: the hook falls back to it


def compose(left, right):
    """Python model of what the hook writes: 14 u16 rows, the rasteriser draws bits 15..2."""
    a, b = FONT[(left - 0x20) * 14:][:14], FONT[(right - 0x20) * 14:][:14]
    return struct.pack('<14H', *[x << 8 | y << 1 for x, y in zip(a, b)])


armips = pytest.mark.skipif(not engine.ARMIPS.exists() or not (ROOT / 'work/orig/d1/SLPS_029.62').exists(),
                            reason='needs armips and the unpacked dump')


@pytest.fixture(scope='module')
def patched():
    orig = (ROOT / 'work/orig/d1/SLPS_029.62').read_bytes()
    return orig, engine.apply(orig)


def glyph_run(exe, word):
    """Run hw_glyph(a0=buffer, a1=word) to its return or the original lookup; returns (pc, the 28 buffer bytes). kseg0 maps to low
    memory in unicorn."""
    from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
    from unicorn.mips_const import UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_RA, UC_MIPS_REG_PC
    syms = dict(reversed(l.split()) for l in (engine.WORK / 'out.sym').read_text().splitlines() if ' ' in l)
    low = engine.BASE & 0x1FFFFFFF
    buf = 0x80190000
    mu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
    mu.mem_map(0, 0x200000)
    mu.mem_write(low + 0x800, exe[0x800:])
    mu.reg_write(UC_MIPS_REG_A0, buf)
    mu.reg_write(UC_MIPS_REG_A1, word)
    mu.reg_write(UC_MIPS_REG_RA, RET)
    seen = []
    mu.hook_add(UC_HOOK_CODE, lambda m, a, *_: (seen.append(a), a == LOOKUP and m.emu_stop()))
    mu.emu_start(int(syms['hw_glyph'], 16), RET, count=2000)
    return seen[-1] if seen[-1] == LOOKUP else mu.reg_read(UC_MIPS_REG_PC), bytes(mu.mem_read(buf & 0x1FFFFFFF, 28))


@armips
def test_patch_is_in_place(patched):
    orig, new = patched
    assert orig != new  # engine.apply itself fails on a write outside its ranges
    assert struct.unpack_from('<I', new, 0x8002A66C - engine.BASE)[0] >> 26 == 3  # still a jal
    assert new[0x80073AE8 - engine.BASE:][:len(FONT)] == FONT


@armips
@pytest.mark.parametrize('pair', ['Ab', 'Wm', ' .', '~}', 'y '])
def test_hook_composes_two_letters(patched, pair):
    pc, buf = glyph_run(patched[1], engine.encode(pair)[0])
    assert pc == RET and buf == compose(ord(pair[0]), ord(pair[1]))


@armips
def test_out_of_range_pair_draws_blank(patched):
    pc, buf = glyph_run(patched[1], 0x0101)
    assert pc == RET and buf == bytes(28)


@armips
def test_shift_jis_goes_to_the_original_lookup(patched):
    assert glyph_run(patched[1], 0x82A0)[0] == LOOKUP

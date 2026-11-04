"""The wrap the build uses and the limits the batch check holds English to."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import engine
import extract
import fit


def test_wrap_stays_inside_the_row_and_leaves_the_arrow_room():
    text = ' '.join(['word'] * 40)
    rows = fit.wrap(text, 17, 3)
    assert all(fit.width(r) <= 34 for r in rows)
    assert all(fit.width(r) <= 32 for r in rows[2::3])
    assert ' '.join(rows) == text


def test_macro_counts_as_a_name_and_pads_its_cell():
    assert fit.width('abc{0021}') == 4 + 12
    assert fit.width('{0021}!') == 13
    assert fit.wrap('x' * 30 + ' {0021}', 17) == ['x' * 30, '{0021}']


def test_check_limits():
    assert fit.check('short', '17x3') == []
    assert fit.check('word ' * 90, '17x3')  # past two pages
    assert fit.check('x' * 40, '17x3')  # a word no row can hold
    assert fit.check('a ' * 48 + 'stub', '17x3') == []  # a little over a page is what paging is for
    assert fit.check('x' * 13, '12ch')
    assert fit.check('x' * 12, '12ch') == []
    assert fit.check('{0023} got it', '16ch')


def test_a_row_that_fills_the_box_gets_no_break_after_it():
    assert extract.box_words('x' * 34 + ' yy', '17x3', engine.encode).count(0x10) == 0
    assert extract.box_words('x' * 30 + ' yyyyy', '17x3', engine.encode).count(0x10) == 1

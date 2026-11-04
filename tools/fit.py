"""fit.py: how English sits in a box. A box is CxR: C cells of 14 px, two letters to a cell, R rows to a page (docs/re/windows.md).
The build wraps at spaces, so English needs no line breaks; \\n forces one. Past R rows the game waits at the arrow and pages by itself."""
import re

MACRO = re.compile(r'\{[0-9A-F]{4}\}')
MACRO_LETTERS = 12  # a name or item inserted at run time: a default name is shorter, six kana take 12 letters' room
ARROW_LETTERS = 2  # the page-wait arrow covers the end of a page's last row
MAX_PAGES = 2
STUB_LETTERS = 12  # a last page shorter than this makes the player press a button for one word


def width(row):
    """Letters' room a row takes. A run before a macro is padded to a whole cell."""
    w, parts = 0, MACRO.split(row)
    for i, p in enumerate(parts):
        w += len(p) + (len(p) % 2 if i < len(parts) - 1 else 0)
        if i < len(parts) - 1:
            w += MACRO_LETTERS
    return w


def _greedy(para, cols, page, first, limit):
    """Rows of one paragraph starting at row number `first`: at most `limit` letters, a page's last row (every `page`th) short of the arrow."""
    rows, cur = [], ''
    for word in para.split(' '):
        t = f'{cur} {word}' if cur else word
        room = min(limit, cols * 2 - (ARROW_LETTERS if page and (first + len(rows) + 1) % page == 0 else 0))
        if width(t) <= room or not cur:
            cur = t
        else:
            rows.append(cur)
            cur = word
    return rows + [cur]


def wrap(text, cols, page=None):
    """Wrap at spaces. A box (`page` given) is balanced: the narrowest rows that take no more rows than greedy, so no last row holds one orphaned
    word. A word longer than a row stays alone on it (check() then fails it)."""
    rows = []
    for para in text.split('\n'):
        best = _greedy(para, cols, page, len(rows), cols * 2)
        if page and len(best) > 1:
            for limit in range(cols * 2 - 1, 0, -1):
                t = _greedy(para, cols, page, len(rows), limit)
                if len(t) > len(best):
                    break
                best = t
        rows += best
    return rows


def check(text, limit):
    """Problems of a text against '17x3' (box) or '30ch' (one field). Empty when it fits."""
    if limit.endswith('ch'):
        n = int(limit[:-2])
        return [f'{width(text)} letters, the limit is {n}'] if width(text.replace('\n', '')) > n else []
    if 'r' in limit:  # 38r2: a fixed field of 2 rows of 38 letters, wrapped at build (extract._uncells), no paging
        letters, nrows = map(int, limit.split('r'))
        rows = wrap(text, letters // 2)
        bad = [f'"{r[:20]}" is {width(r)} letters, a row has {letters}' for r in rows if width(r) > letters]
        return bad + ([f'{len(rows)} rows, the field has {nrows}'] if len(rows) > nrows else [])
    cols, nrows = map(int, limit.split('x'))
    rows = wrap(text, cols, nrows)
    bad = []
    if len(rows) > nrows * MAX_PAGES:
        bad.append(f'{len(rows)} rows: more than {MAX_PAGES} pages of {nrows}')
    for r in rows:
        if width(r) > cols * 2:
            bad.append(f'"{r[:20]}" is {width(r)} letters, a row has {cols * 2}')
    if len(rows) > nrows and sum(width(r) for r in rows[nrows:]) < STUB_LETTERS:
        bad.append(f'second page holds only "{" ".join(rows[nrows:])}": cut a few letters so it stays on one page')
    return bad

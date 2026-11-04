"""Nested containers inside the .DAT files: u32 count, u32 shift (4 = 16-byte units), count x (u16 off, u16 size).
Same shape as the outer .DAT (shift 11). parse() returns None unless the entries chain and fit, so ordinary data
isn't mistaken for a container. walk() yields every leaf with its path."""
import struct


def parse(d):
    """[(start, size)] byte ranges, or None if d isn't a container."""
    if len(d) < 16:
        return None
    count, shift = struct.unpack_from('<II', d)
    if shift not in (4, 11) or not 0 < count < 0x400 or 8 + 4 * count > len(d):
        return None
    ents = [struct.unpack_from('<HH', d, 8 + 4 * i) for i in range(count)]
    pos = None
    for off, size in ents:
        if size == 0:
            continue
        if pos is not None and off != pos:
            return None
        if off << shift < 8 + 4 * count:
            return None
        pos = off + size
    if pos is None or pos << shift > len(d) + (1 << shift):
        return None
    return [(o << shift, s << shift) for o, s in ents]


def walk(d, path=''):
    """Yield (path, base offset within d, bytes) for each leaf."""
    def rec(b, base, p):
        ents = parse(b)
        if ents is None:
            yield p, base, b
            return
        for i, (o, s) in enumerate(ents):
            if s:
                yield from rec(b[o:o + s], base + o, f'{p}.{i}')
    yield from rec(d, 0, path)

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


def pack(children, shift, align=None):
    """Inverse of parse: a container from its children, each padded with zeros to the unit, the whole to align.
    Holds for every container on both discs (tests/test_identity.py): the header pads to the next unit, an empty
    entry stores the running offset, padding is zero. A table field past u16 raises struct.error."""
    unit = 1 << shift
    up = lambda n, u: -(-n // u) * u
    out = bytearray(up(8 + 4 * len(children), unit))
    struct.pack_into('<II', out, 0, len(children), shift)
    for i, c in enumerate(children):
        size = up(len(c), unit)
        struct.pack_into('<HH', out, 8 + 4 * i, len(out) >> shift, size >> shift)
        out += c + bytes(size - len(c))
    return bytes(out) + bytes(up(len(out), align or unit) - len(out))


def rebuild(d, align=2048, repl=None, path=''):
    """Unpack and repack every level of d, leaves named in repl {walk() path: bytes} replaced.
    align: the unit of the container d sits in."""
    ents = parse(d)
    if ents is None:
        return repl.get(path, d) if repl else d
    shift = 11 if d[4] == 11 else 4
    return pack([rebuild(d[o:o + s], 1 << shift, repl, f'{path}.{i}') for i, (o, s) in enumerate(ents)], shift, align)


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

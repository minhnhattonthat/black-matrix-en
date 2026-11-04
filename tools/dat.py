"""Black/Matrix .DAT archive: u32 count, u32 sector shift (11),
count x (u16 sector offset, u16 sector count), padded to whole sectors.
Same layout as Black/Matrix 00's dat.py (verified here by recon_dat.py: all entries chain, last sector = file size).
Empty entries store the running offset, so pack(unpack(x)) == x for all five DATs on both discs."""
import struct

import pak

SECTOR = 2048


def table(data: bytes) -> list[tuple[int, int]]:
    count, shift = struct.unpack_from('<II', data)
    if shift != 11:
        raise ValueError(f'unexpected sector shift {shift}')
    return [struct.unpack_from('<HH', data, 8 + 4 * i) for i in range(count)]


def unpack(data: bytes) -> list[bytes]:
    return [data[o * SECTOR:(o + s) * SECTOR] for o, s in table(data)]


def pack(entries: list[bytes]) -> bytes:
    return pak.pack(entries, 11)


def walk(data: bytes, name: str):
    """Every leaf of a .DAT as (path like SYSTEM/5.0, bytes)."""
    for i, f in enumerate(unpack(data)):
        if f:
            for p, _, x in pak.walk(f, f'{name}/{i}'):
                yield p, x


def rebuild(data: bytes, name: str, repl: dict) -> bytes:
    """The .DAT with the leaves in repl {path: bytes} replaced."""
    return pack([pak.rebuild(f, SECTOR, repl, f'{name}/{i}') for i, f in enumerate(unpack(data))])

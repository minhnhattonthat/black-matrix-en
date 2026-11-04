"""Black/Matrix .DAT archive: u32 count, u32 sector shift (11),
count x (u16 sector offset, u16 sector count), padded to whole sectors.
Same layout as Black/Matrix 00's dat.py (verified here by recon_dat.py: all entries chain, last sector = file size).
Empty entries keep the offset they were stored with, so unpack() returns them for byte-exact repacking."""
import struct

SECTOR = 2048


def table(data: bytes) -> list[tuple[int, int]]:
    count, shift = struct.unpack_from('<II', data)
    if shift != 11:
        raise ValueError(f'unexpected sector shift {shift}')
    return [struct.unpack_from('<HH', data, 8 + 4 * i) for i in range(count)]


def unpack(data: bytes) -> list[bytes]:
    return [data[o * SECTOR:(o + s) * SECTOR] for o, s in table(data)]

"""Read a MODE2/2352 PS1 disc image without unpacking it.
usage: disc.py list BIN | disc.py x BIN OUTDIR [NAME_SUBSTRING]
Library: Disc(path).files() -> [(path, lba, size, xa_attr, is_form2)]; .read(lba, size) -> Form 1 user data."""
import os, struct, sys

SECTOR = 2352


class Disc:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.sectors = os.path.getsize(path) // SECTOR

    def raw(self, lba):
        self.f.seek(lba * SECTOR)
        return self.f.read(SECTOR)

    def read(self, lba, size):
        out = bytearray()
        for i in range((size + 2047) // 2048):
            out += self.raw(lba + i)[24:24 + 2048]
        return bytes(out[:size])

    def files(self):
        pvd = self.read(16, 2048)
        assert pvd[1:6] == b'CD001', 'no ISO9660 volume at sector 16'
        root = pvd[156:190]
        out = []
        self._walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '', out)
        return out

    def _walk(self, lba, size, path, out):
        data = self.read(lba, size)
        i = 0
        while i < size:
            n = data[i]
            if n == 0:  # records never cross a sector; zero means skip to the next one
                i = (i // 2048 + 1) * 2048
                continue
            rec = data[i:i + n]
            i += n
            loc, length = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
            namelen = rec[32]
            name = rec[33:33 + namelen]
            if name in (b'\0', b'\1'):
                continue
            p = path + '/' + name.decode('latin1').split(';')[0]
            if rec[25] & 2:
                self._walk(loc, length, p, out)
                continue
            xa = rec[33 + namelen + (namelen + 1) % 2:]
            attr = struct.unpack_from('>H', xa, 4)[0] if len(xa) >= 14 and xa[6:8] == b'XA' else 0
            out.append((p, loc, length, attr, bool(attr & 0x1000)))


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    d = Disc(path)
    if cmd == 'list':
        pvd = d.read(16, 2048)
        print('volume', pvd[40:72].decode('latin1').strip(), 'sectors', d.sectors)
        for p, lba, size, attr, form2 in d.files():
            print(f'{lba:7d} {size:11d} {attr:04x} {"F2" if form2 else "  "} {p}')
    elif cmd == 'x':
        out = sys.argv[3]
        want = sys.argv[4] if len(sys.argv) > 4 else ''
        for p, lba, size, attr, form2 in d.files():
            if want not in p or form2:  # Form 2 movie/audio files need raw sectors, skip them here
                continue
            dest = os.path.join(out, p.lstrip('/'))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as w:
                w.write(d.read(lba, size))
            print(dest, size)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()

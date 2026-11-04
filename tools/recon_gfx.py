"""Recon: render every picture leaf (the game's own blobs + TIMs), dedupe by content, index them for the graphics sweep.
Blob: u32 kind (0 = 4-bit, 1 = 8-bit), u32 0x10, u32 pixel_off, u32 extra_off; @0x10 u16 clut_w, clut_h, colours;
@pixel_off u16 width in 16-bit words, u16 height, pixels low nibble first.
usage: recon_gfx.py -> work/recon/gfx/<n>.png, work/recon/gfx_index.tsv; prints what it skipped and why."""
import collections, hashlib, os, struct, sys
sys.path.insert(0, 'tools')
import dat, pak, recon_tim
from PIL import Image


def blob_info(b):
    if len(b) < 0x18:
        return None
    kind, ten, off, _ = struct.unpack_from('<4I', b)
    # bit 0 = 8-bit pixels, 0x10 = a cell map follows the pixels (full-screen pictures), 0x80 = seen with 0x11 only
    if kind & ~0x91 or ten != 0x10 or off < 0x14 or off + 4 > len(b):
        return None
    kind &= 1
    cw, ch = struct.unpack_from('<HH', b, 0x10)
    if off != 0x14 + 2 * cw * ch:
        return None
    w16, h = struct.unpack_from('<HH', b, off)
    if not w16 or not h or w16 > 1024 or h > 512:
        return None
    if off + 4 + w16 * h * 2 > len(b):
        return None
    return kind, w16, h, off, cw * ch


def render(b, info):
    kind, w16, h, off, ncol = info
    pal = []
    for i in range(ncol):
        v = struct.unpack_from('<H', b, 0x14 + i * 2)[0]
        pal.append(((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3))
    data = off + 4
    if kind == 0:
        im = Image.new('RGB', (w16 * 4, h))
        px = im.load()
        for y in range(h):
            for i in range(w16 * 2):
                v = b[data + y * w16 * 2 + i]
                for k, idx in ((0, v & 15), (1, v >> 4)):
                    px[i * 2 + k, y] = pal[idx] if idx < ncol else (0, 0, 0)
    else:
        im = Image.new('RGB', (w16 * 2, h))
        px = im.load()
        for y in range(h):
            for i in range(w16 * 2):
                idx = b[data + y * w16 * 2 + i]
                px[i, y] = pal[idx] if idx < ncol else (0, 0, 0)
    return im


def main():
    os.makedirs('work/recon/gfx', exist_ok=True)
    seen, skipped = {}, collections.Counter()
    for disc in ('1', '2'):
        for name in ('SYSTEM', 'BATTLE', 'EVENT', 'SOUND', 'SCENARIO'):
            files = dat.unpack(open(f'work/extracted/disc{disc}/{name}.DAT', 'rb').read())
            for i, f in enumerate(files):
                if not f:
                    continue
                for path, _, b in pak.walk(f, f'{name}/{i}'):
                    info = blob_info(b)
                    if info is None:
                        t = recon_tim.tim_at(b, 0)
                        if t is None:
                            skipped[(name, b[:4].hex())] += 1
                            continue
                        h = hashlib.sha1(b[:t[0]]).hexdigest()
                        if h not in seen:
                            n = len(seen)
                            recon_tim.render(b, t).save(f'work/recon/gfx/{n:05d}.png')
                            seen[h] = {'n': n, 'kind': f'tim{t[1]}', 'w': t[3][2], 'h': t[3][3], 'paths': []}
                        seen[h]['paths'].append(f'd{disc}:{path}')
                        continue
                    h = hashlib.sha1(b[:info[3] + 4 + info[1] * info[2] * 2]).hexdigest()
                    if h not in seen:
                        n = len(seen)
                        render(b, info).save(f'work/recon/gfx/{n:05d}.png')
                        seen[h] = {'n': n, 'kind': f'b{info[0]}', 'w': info[1], 'h': info[2], 'paths': []}
                    seen[h]['paths'].append(f'd{disc}:{path}')
    with open('work/recon/gfx_index.tsv', 'w', encoding='utf-8') as w:
        for s in seen.values():
            w.write(f"{s['n']}\t{s['kind']}\t{s['w']}\t{s['h']}\t{len(s['paths'])}\t{' '.join(s['paths'][:8])}\n")
    print('distinct pictures', len(seen), 'instances', sum(len(s['paths']) for s in seen.values()))
    print('skipped leaves by (dat, head):')
    for k, n in skipped.most_common(40):
        print(' ', n, k)


if __name__ == '__main__':
    main()

"""Recon: find every valid TIM at any 4-aligned offset of every DAT leaf, dedupe by content, render to PNG, index.
usage: recon_tim.py -> work/recon/tim/<n>.png, work/recon/tim_index.tsv (n, w, h, bpp, size, first path, copies, paths)"""
import hashlib, os, struct, sys
sys.path.insert(0, 'tools')
import dat, pak
from PIL import Image


def tim_at(d, p):
    """(total size, bpp mode, clut (x,y,w,h,bytes offset), img (x,y,w,h,offset)) or None."""
    if p + 8 > len(d) or d[p:p + 4] != b'\x10\0\0\0':
        return None
    flags = struct.unpack_from('<I', d, p + 4)[0]
    mode = flags & 7
    if flags & ~0xF or mode > 3:
        return None
    q = p + 8
    clut = None
    if flags & 8:
        if mode > 1 or q + 12 > len(d):
            return None
        size, cx, cy, cw, ch = struct.unpack_from('<IHHHH', d, q)
        if size != 12 + cw * ch * 2 or cw == 0 or ch == 0 or cx >= 1024 or cy >= 512 or q + size > len(d):
            return None
        clut = (cx, cy, cw, ch, q + 12)
        q += size
    elif mode < 2:
        return None
    if q + 12 > len(d):
        return None
    size, x, y, w, h = struct.unpack_from('<IHHHH', d, q)
    if size != 12 + w * h * 2 or w == 0 or h == 0 or w > 1024 or h > 512 or x >= 1024 or y >= 512 or q + size > len(d):
        return None
    return q + size - p, mode, clut, (x, y, w, h, q + 12)


def render(d, t):
    size, mode, clut, (x, y, w, h, off) = t
    pal = None
    if clut:
        cx, cy, cw, ch, co = clut
        n = min(cw * ch, 1 << (4 if mode == 0 else 8))
        pal = [struct.unpack_from('<H', d, co + i * 2)[0] for i in range(n)]

    def rgb(v):
        return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3)
    if mode == 0:
        W = w * 4
        im = Image.new('RGB', (W, h))
        px = im.load()
        for j in range(h):
            for i in range(w * 2):
                b = d[off + j * w * 2 + i]
                for k, idx in ((0, b & 15), (1, b >> 4)):
                    px[i * 2 + k, j] = rgb(pal[idx] if idx < len(pal) else 0)
    elif mode == 1:
        W = w * 2
        im = Image.new('RGB', (W, h))
        px = im.load()
        for j in range(h):
            for i in range(W):
                idx = d[off + j * w * 2 + i]
                px[i, j] = rgb(pal[idx] if idx < len(pal) else 0)
    elif mode == 2:
        im = Image.new('RGB', (w, h))
        px = im.load()
        for j in range(h):
            for i in range(w):
                px[i, j] = rgb(struct.unpack_from('<H', d, off + (j * w + i) * 2)[0])
    else:
        W = w * 2 // 3
        im = Image.new('RGB', (W, h))
        px = im.load()
        for j in range(h):
            for i in range(W):
                o = off + j * w * 2 + i * 3
                px[i, j] = (d[o], d[o + 1], d[o + 2])
    return im


def main():
    os.makedirs('work/recon/tim', exist_ok=True)
    seen = {}
    for disc in ('1', '2'):
        for name in ('SYSTEM', 'BATTLE', 'EVENT', 'SOUND', 'SCENARIO'):
            files = dat.unpack(open(f'work/extracted/disc{disc}/{name}.DAT', 'rb').read())
            for i, f in enumerate(files):
                if not f:
                    continue
                for path, _, b in pak.walk(f, f'{name}/{i}'):
                    p = 0
                    while p + 8 <= len(b):
                        t = tim_at(b, p)
                        if t is None:
                            p += 4
                            continue
                        blob = b[p:p + t[0]]
                        h = hashlib.sha1(blob).hexdigest()
                        where = f'd{disc}:{path}@{p:#x}'
                        if h in seen:
                            seen[h]['paths'].append(where)
                        else:
                            n = len(seen)
                            x, y, w, hh, _o = t[3]
                            seen[h] = {'n': n, 'mode': t[1], 'w': w, 'h': hh, 'x': x, 'y': y, 'paths': [where]}
                            try:
                                render(b[p:p + t[0]] if False else b, t).save(f'work/recon/tim/{n:05d}.png')
                            except Exception as e:
                                print('render failed', where, e)
                        p += (t[0] + 3) & ~3
    with open('work/recon/tim_index.tsv', 'w', encoding='utf-8') as w:
        w.write('n\tw16\th\tmode\tvram\tcopies\tpaths\n')
        for s in seen.values():
            w.write(f"{s['n']}\t{s['w']}\t{s['h']}\t{s['mode']}\t{s['x']},{s['y']}\t{len(s['paths'])}\t{' '.join(s['paths'][:6])}\n")
    print('distinct TIMs', len(seen), 'instances', sum(len(s['paths']) for s in seen.values()))


if __name__ == '__main__':
    main()

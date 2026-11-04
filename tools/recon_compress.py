"""Recon: is anything compressed? Byte entropy per leaf type, plus a trial of Black/Matrix 00's LZ decoder (lz.py there) on each
unclassified leaf. The EXE gets the same 00 decoder signature search. usage: recon_compress.py"""
import collections, math, struct, sys
sys.path.insert(0, 'tools')
import dat, pak, recon_gfx


def entropy(b):
    if not b:
        return 0
    c = collections.Counter(b)
    return -sum(v / len(b) * math.log2(v / len(b)) for v in c.values())


rows = collections.defaultdict(list)
high = []
for disc in ('1', '2'):
    for name in ('SYSTEM', 'BATTLE', 'EVENT', 'SOUND', 'SCENARIO'):
        files = dat.unpack(open(f'work/extracted/disc{disc}/{name}.DAT', 'rb').read())
        for i, f in enumerate(files):
            if not f:
                continue
            for path, _, b in pak.walk(f, f'{name}/{i}'):
                if recon_gfx.blob_info(b):
                    kind = 'picture'
                else:
                    kind = b[:4].hex() if b[:4].isascii() and b[:4].rstrip(b'\0').isalnum() else b[:8].hex()
                e = entropy(b)
                rows[kind].append(e)
                if e > 7.3 and kind != 'picture' and len(b) > 256:
                    high.append((round(e, 2), len(b), f'd{disc}:{path}', b[:16].hex()))
for k, v in sorted(rows.items(), key=lambda kv: -len(kv[1]))[:25]:
    print(f'{k:18s} n={len(v):5d} mean {sum(v) / len(v):.2f} max {max(v):.2f}')
print('non-picture leaves with entropy > 7.3:', len(high))
for h in sorted(high, reverse=True)[:60]:
    print(' ', *h)

"""Recon: which data uses the EXE's LZ? Decoder 0x800248A0 (same scheme as Black/Matrix 00's lz.py), encoder 0x800246C0.
Lists callers of both, then tries the decoder on every DAT entry and leaf; a real stream's length word fits and it ends inside the leaf.
usage: recon_lz.py"""
import collections, struct, sys
sys.path.insert(0, 'tools')
import dat, pak


def unpack(src, cap=0x200000):
    """(data, packed bytes read) or None when the stream runs out or exceeds cap (a guard: garbage rarely ends cleanly)."""
    out, p, flags, count, nibbles, half, limit = bytearray(), 3, 0, 0, 0, False, None
    try:
        while limit is None or len(out) < limit:
            if count & 7 == 0:
                flags = src[p]
                p += 1
            else:
                flags >>= 1
            count += 1
            if flags & 1:
                out.append(src[p] ^ ~len(out) & 0xFF)
                p += 1
            else:
                if half:
                    nibbles >>= 4
                else:
                    nibbles = src[p]
                    p += 1
                half = not half
                d = src[p] + 1
                p += 1
                if d > len(out):
                    return None
                for _ in range((nibbles & 15) + 2):
                    out.append(out[-d])
            if limit is None and len(out) >= 4:
                limit = struct.unpack_from('<I', out)[0] * 4
                if not 4 < limit <= cap:
                    return None
    except IndexError:
        return None
    return bytes(out[:limit]), p


code = open('work/extracted/disc1/SLPS_029.62', 'rb').read()[0x800:]
words = struct.unpack_from(f'<{len(code) // 4}I', code)
for name, f in (('decoder', 0x800248A0), ('encoder', 0x800246C0), ('encoder wrapper', 0x800249D0)):
    print(name, hex(f), 'jal from', [hex(0x80010000 + i * 4) for i, w in enumerate(words) if w >> 26 == 3 and (0x80000000 | (w & 0x3FFFFFF) << 2) == f][:12])
for ov in ('2ND', '3RD', '4TH', '5TH'):
    raw = open(f'work/extracted/disc1/{ov}.BIN', 'rb').read()
    hits = [i * 4 for i, w in enumerate(struct.unpack_from(f'<{len(raw) // 4}I', raw)) if w >> 26 == 3 and (0x80000000 | (w & 0x3FFFFFF) << 2) == 0x800248A0]
    print(ov, 'decoder calls at file offsets', [hex(h) for h in hits][:8])

found = collections.Counter()
rows = []
seen = set()
for disc in ('1', '2'):
    for name in ('SYSTEM', 'BATTLE', 'EVENT', 'SOUND', 'SCENARIO'):
        for i, f in enumerate(dat.unpack(open(f'work/extracted/disc{disc}/{name}.DAT', 'rb').read())):
            if not f:
                continue
            for path, _, b in [(f'{name}/{i}', 0, f), *pak.walk(f, f'{name}/{i}')]:
                if len(b) < 32 or id(b) in seen:
                    continue
                r = unpack(b)
                if r and len(b) - 4096 <= r[1] <= len(b) and len(r[0]) > r[1]:
                    found[name] += 1
                    rows.append(f'd{disc}:{path}\tpacked {r[1]}/{len(b)}\tunpacked {len(r[0])}\thead {b[:8].hex()}\tout {r[0][:12].hex()}')
print('leaves that decode cleanly', dict(found))
open('work/recon/lz_leaves.tsv', 'w').write('\n'.join(rows))
for r in rows[:25]:
    print(' ', r)

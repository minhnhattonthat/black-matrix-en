"""Recon: where each overlay loads, and how the EXE and overlays reach their Japanese strings.
Load: search the RAM dumps of a run for the overlay's bytes, else fall back to the best-scoring LOADS guess. Reach: count lui+addiu/ori
pairs and u32 data words landing inside each strong run (work/recon/text_d1.tsv), start or middle; the rest are reached by base + index or
not at all. Writes work/recon/ptr_<file>.tsv. usage: recon_ptr.py [RAM.bin ...]"""
import collections, struct, sys

LOADS = {'2ND.BIN': 0x800EB000, '3RD.BIN': 0x80110800, '4TH.BIN': 0x800EB000, '5TH.BIN': 0x800EB000}  # votes in recon_prefix.py


def code_refs(code):
    """Absolute addresses built by lui + addiu/ori in the same register, within 24 instructions; and all the words."""
    out = collections.Counter()
    words = struct.unpack_from(f'<{len(code) // 4}I', code)
    last = {}
    for i, w in enumerate(words):
        op = w >> 26
        if op == 0xF:
            last[(w >> 16) & 31] = (w & 0xFFFF, i)
        elif op in (9, 0xD):
            rs = (w >> 21) & 31
            if rs in last and i - last[rs][1] < 24:
                lo = w & 0xFFFF
                out[((last[rs][0] << 16) + (lo - 0x10000 if op == 9 and lo & 0x8000 else lo)) & 0xFFFFFFFF] += 1
    return out, words


def main():
    rams = [open(p, 'rb').read() for p in sys.argv[1:]]
    runs = collections.defaultdict(list)
    for line in open('work/recon/text_d1.tsv', encoding='utf-8'):
        c = line.rstrip('\n').split('\t')
        if c[0] in ('SLPS_029.62', *LOADS):
            runs[c[0]].append((int(c[1], 16), c[2], c[3]))
    for name, rows in runs.items():
        raw = open(f'work/extracted/disc1/{name}', 'rb').read()
        if name.startswith('SLPS'):
            code, load = raw[0x800:], struct.unpack_from('<I', raw, 0x18)[0]
            rows = [(o - 0x800, a, b) for o, a, b in rows]
            how = 'header'
        else:
            code, load, how = raw, LOADS[name], 'guess'
            for r in rams:
                at = r.find(raw[0x1000:0x1100])  # past the head: variables there change at run time
                if at >= 0:
                    load, how = 0x80000000 + at - 0x1000, 'RAM dump'
                    break
        refs, words = code_refs(code)
        data = collections.Counter(w for w in words if load <= w < load + len(code))
        all_refs = set(refs) | set(data)
        kinds = collections.Counter()
        with open(f'work/recon/ptr_{name}.tsv', 'w', encoding='utf-8') as w:
            for o, order, text in rows:
                a = load + o
                inside = any(t in all_refs for t in range(a, a + len(text) * 2, 2))
                k = 'count' if a - 2 in all_refs else 'start' if a in all_refs else 'inside' if inside else 'none'
                kinds[k] += 1
                w.write(f'{o:#x}\t{a:#x}\t{order}\t{k}\t{text}\n')
        print(f'{name}: load {load:08x} ({how}) runs {len(rows)} reached {dict(kinds)}')


if __name__ == '__main__':
    main()

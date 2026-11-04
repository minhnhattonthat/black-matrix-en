"""Recon: are strings in the EXE/overlays stored as u16 count + words, reached through the count word? And which code loads each overlay.
usage: recon_prefix.py -> counts per file, then the overlay name strings with what refers to them."""
import collections, struct, sys
sys.path.insert(0, 'tools')
import recon_ptr

runs = collections.defaultdict(list)
for line in open('work/recon/text_d1.tsv', encoding='utf-8'):
    c = line.rstrip('\n').split('\t')
    if c[0] in ('SLPS_029.62', *recon_ptr.LOADS):
        runs[c[0]].append((int(c[1], 16), c[2], c[3]))
for name, rows in runs.items():
    raw = open(f'work/extracted/disc1/{name}', 'rb').read()
    is_exe = name.startswith('SLPS')
    base = 0x800 if is_exe else 0
    code = raw[base:]
    load = struct.unpack_from('<I', raw, 0x18)[0] if is_exe else recon_ptr.LOADS[name]
    refs, words = recon_ptr.code_refs(code)
    targets = set(refs) | set(words)
    prefixed = reached = 0
    samples = []
    for o, order, text in rows:
        if o < 2 or order != 'le':
            continue
        n = struct.unpack_from('<H', raw, o - 2)[0]
        if n and n <= len(text) + 1:
            prefixed += 1
            if load + o - base - 2 in targets:
                reached += 1
        if len(samples) < 4:
            samples.append(f'{o:#x} prev={raw[o - 4:o].hex()} next={raw[o + len(text) * 2:o + len(text) * 2 + 4].hex()} {text[:14]}')
    print(f'{name}: runs {len(rows)} with count word before {prefixed}, of those pointed at {reached}')
    for s in samples:
        print('   ', s)

    if not is_exe:  # every pointer to a count word votes for one load address; the true one stands out
        votes = collections.Counter()
        counts = [o - 2 for o, order, text in rows if o >= 2 and order == 'le' and 0 < struct.unpack_from('<H', raw, o - 2)[0] <= len(text) + 1]
        for t in targets:
            if 0x80000000 <= t < 0x80200000:
                for c in counts:
                    if not (t - c) & 3:
                        votes[t - c] += 1
        print('    load votes', [(hex(k), v) for k, v in votes.most_common(3)], 'of', len(counts))
        # second, independent vote: jal targets landing on function prologues (addiu $sp,$sp,-n)
        pro = [i * 4 for i, w in enumerate(words) if w >> 16 == 0x27BD and w & 0x8000]
        jals = {0x80000000 | (w & 0x3FFFFFF) << 2 for w in words if w >> 26 == 3}
        jv = collections.Counter(t - p for t in jals for p in pro)
        print('    jal votes', [(hex(k), v) for k, v in jv.most_common(3)], 'prologues', len(pro), 'at 0x800eb000:', jv[0x800EB000])

exe = open('work/extracted/disc1/SLPS_029.62', 'rb').read()
code = exe[0x800:]
refs, words = recon_ptr.code_refs(code)
for nm in (b'2ND.BIN', b'3RD.BIN', b'4TH.BIN', b'5TH.BIN'):
    o = exe.find(nm)
    a = 0x80010000 + o - 0x800
    data = [0x80010000 + i * 4 for i, w in enumerate(words) if w == a]
    print(nm.decode(), f'file {o:#x} ram {a:#x} in lui/addiu pairs {refs.get(a, 0)}, as data at', [hex(x) for x in data[:6]])

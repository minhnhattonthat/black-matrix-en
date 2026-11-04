"""Readable listing of scenario scripts (Disc 1 SCENARIO.DAT; same on Disc 2).
usage: psidump.py ID [ID..]   print those scripts
       psidump.py             write all of them to work/debug/all.txt (oplist.py, rareops.py and gen_scenes.py read it)
Expressions print in RPN: #n constant, a[n] u16 var (0x80087348), b[n] u16 var (0x80086B48), c[n] u32 var (0x80087748), op<xx> binary op."""
import os, struct, sys
sys.path.insert(0, 'tools')
import dat, psi

NAMES = {0x01: 'set', 0x02: 'jz', 0x03: 'jmp', 0x10: 'CHAIN', 0x11: 'CALL', 0x12: 'RET', 0x14: 'text', 0x15: 'vtext',
         0x1D: 'choice', 0x20: 'menu'}


def show_expr(b, p):
    out = []
    while True:
        item = struct.unpack_from('<H', b, p)[0]
        p += 2
        if item == 0:
            return ' '.join(out), p
        if item == 1:
            p += (4 - p & 3) & 3
            out.append('#%d' % struct.unpack_from('<i', b, p)[0])
            p += 4
        elif item in (2, 3, 4):
            out.append('%s[%d]' % ('abc'[item - 2], struct.unpack_from('<H', b, p)[0]))
            p += 2
        else:
            out.append('op%02x' % item)


def show(b, t):
    p = t.off + (4 if t.sub is not None else 2)
    sig = psi.SUB[t.op][t.sub] if t.sub is not None else psi.OPS[t.op]
    args = []
    if t.op == 1:  # set: kind word, index word, value
        kind, idx = struct.unpack_from('<HH', b, p)
        e, _ = show_expr(b, p + 4)
        return f'{t.off:6x}  01 set {"abc"[kind - 2]}[{idx}] = {e}'
    for c in sig:
        if c == 'w':
            args.append('w%d' % struct.unpack_from('<H', b, p)[0])
            p += 2
        elif c == 'E':
            e, p = show_expr(b, p)
            args.append('(' + e + ')')
        elif c == 'L':
            p += (4 - p & 3) & 3
            args.append('->%x' % (struct.unpack_from('<I', b, p)[0] + psi.CODE_BASE))
            p += 4
        elif c == 'T':
            n = struct.unpack_from('<H', b, p)[0]
            p += 2 + 2 * n
            args.append(repr(psi.decode(t.words)))
    name = f'{t.op:02x}/{t.sub:02x}' if t.sub is not None else f'{t.op:02x}'
    if t.op in NAMES:
        name += ' ' + NAMES[t.op]
    return f'{t.off:6x}  {name} ' + ' '.join(args)


def listing(leaves, i):
    toks, _, _ = psi.tokenize(leaves[i])
    return [f'=== script {i}'] + [show(leaves[i], t) for t in toks]


def main():
    leaves = dat.unpack(open('work/extracted/disc1/SCENARIO.DAT', 'rb').read())
    if len(sys.argv) > 1:
        for i in map(int, sys.argv[1:]):
            print('\n'.join(listing(leaves, i)))
        return
    os.makedirs('work/debug', exist_ok=True)
    with open('work/debug/all.txt', 'w', encoding='utf-8') as f:
        for i, b in enumerate(leaves):
            if b:
                f.write('\n'.join(listing(leaves, i)) + '\n')


if __name__ == '__main__':
    main()

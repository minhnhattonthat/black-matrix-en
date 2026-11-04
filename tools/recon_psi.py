"""Recon: tokenize every SCENARIO.DAT file and report the first failure per unknown op, jump checks and coverage.
usage: recon_psi.py [FILE.DAT]"""
import collections, sys
sys.path.insert(0, 'tools')
import dat, psi


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'work/extracted/disc1/SCENARIO.DAT'
    files = dat.unpack(open(path, 'rb').read())
    fails = collections.Counter()
    first = {}
    ok = 0
    ends = collections.Counter()
    badjumps = 0
    ops = collections.Counter()
    texts = 0
    for i, f in enumerate(files):
        if not f or f[:8] != b'PSI22.00':
            continue
        try:
            toks, p, end = psi.tokenize(f)
        except (KeyError, ValueError, Exception) as e:
            key = str(e).split(' at ')[0]
            fails[key] += 1
            first.setdefault(key, (i, str(e)))
            continue
        ok += 1
        ends[p - end] += 1
        starts = {t.off for t in toks}
        for t in toks:
            ops[(t.op, t.sub)] += 1
            if t.words is not None:
                texts += 1
            for tg in t.targets:
                if tg + psi.CODE_BASE not in starts and tg + psi.CODE_BASE != p:
                    badjumps += 1
    print('ok', ok, 'failed', sum(fails.values()), 'ends-vs-header', dict(ends), 'bad jumps', badjumps, 'text tokens', texts)
    for k, n in fails.most_common(40):
        print(n, k, first[k])
    print(sorted(((f'{o:02x}' + (f'/{s:02x}' if s is not None else ''), n) for (o, s), n in ops.items()), key=lambda x: x[0]))


if __name__ == '__main__':
    main()

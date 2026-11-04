"""Recon: from recon_text.py's TSVs, keep strong text runs, group identical leaves (by content) across both discs.
usage: recon_textmap.py -> work/recon/textmap.tsv and a digest on stdout"""
import collections, hashlib, os, sys
sys.path.insert(0, 'tools')
import dat, pak


def strong(s):
    hira = sum(1 for c in s if 0x3041 <= ord(c) <= 0x3093)
    kata = sum(1 for c in s if 0x30A1 <= ord(c) <= 0x30F6)
    pad = s.endswith('　')
    if hira >= 2:
        return True
    return kata >= 3 and (pad or (len(s) >= 4 and kata * 2 >= len(s) and all(not 0x4E00 <= ord(c) < 0xA000 for c in s)))


def leaf_hashes(disc):
    out = {}
    root = f'work/extracted/disc{disc}'
    for name in sorted(os.listdir(root)):
        d = open(os.path.join(root, name), 'rb').read()
        if not name.endswith('.DAT'):
            out[name] = hashlib.sha1(d).hexdigest()
            continue
        for i, f in enumerate(dat.unpack(d)):
            if f:
                for p, _, b in pak.walk(f, f'{name[:-4]}/{i}'):
                    out[p] = hashlib.sha1(b).hexdigest()
    return out


def main():
    groups = {}
    for disc in ('1', '2'):
        hashes = leaf_hashes(disc)
        runs = collections.defaultdict(list)
        for line in open(f'work/recon/text_d{disc}.tsv', encoding='utf-8'):
            p, off, order, s = line.rstrip('\n').split('\t')
            if strong(s):
                runs[p].append((int(off, 16), order, s))
        for p, r in runs.items():
            g = groups.setdefault(hashes[p], {'paths': [], 'runs': r})
            g['paths'].append(f'd{disc}:{p}')
    rows = sorted(groups.values(), key=lambda g: -len(g['runs']))
    with open('work/recon/textmap.tsv', 'w', encoding='utf-8') as w:
        for g in rows:
            w.write(f"{len(g['runs'])}\t{len(g['paths'])}\t{g['paths'][0]}\t{' '.join(g['paths'][1:12])}\n")
            for off, order, s in g['runs']:
                w.write(f'\t{off:#x}\t{order}\t{s}\n')
    print('distinct leaves with strong text', len(rows), 'runs', sum(len(g['runs']) for g in rows))
    for g in rows[:70]:
        print(len(g['runs']), len(g['paths']), g['paths'][0], '|', g['runs'][0][2][:24], '|', g['runs'][len(g['runs']) // 2][2][:24])


if __name__ == '__main__':
    main()

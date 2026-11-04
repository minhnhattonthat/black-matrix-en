"""Recon: one line per DAT sub-file: size, magic, nested table shape, TIM count, Shift-JIS runs in both byte orders.
usage: recon_survey.py DATNAME [disc]   -> work/recon/survey_<name>_d<disc>.tsv and a stdout digest"""
import collections, os, re, struct, sys
sys.path.insert(0, 'tools')
import dat

KANA_LE = re.compile(rb'(?:[\x40-\xfc][\x81-\x84\x88-\x9f]){4,}')  # byte-swapped SJIS words
KANA_BE = re.compile(rb'(?:[\x81-\x84\x88-\x9f][\x40-\xfc]){4,}')


def is_kana(s):
    return sum(1 for c in s if 0x3041 <= ord(c) <= 0x30FE) >= 2


def runs(d):
    """(count BE-order runs with kana, count LE-order runs with kana, first sample of each)."""
    be, le, sb, sl = 0, 0, None, None
    for m in KANA_BE.finditer(d):
        try:
            s = m.group().decode('cp932')
        except UnicodeDecodeError:
            continue
        if is_kana(s):
            be += 1
            sb = sb or s[:16]
    for m in KANA_LE.finditer(d):
        b = bytearray(m.group())
        b[0::2], b[1::2] = b[1::2], b[0::2]
        try:
            s = bytes(b).decode('cp932')
        except UnicodeDecodeError:
            continue
        if is_kana(s):
            le += 1
            sl = sl or s[:16]
    return be, le, sb, sl


def tims(d):
    n = 0
    for off in range(0, len(d) - 8, 4):
        if d[off:off + 4] == b'\x10\0\0\0' and d[off + 4] in (0, 1, 2, 3, 8, 9) and d[off + 5:off + 8] == b'\0\0\0':
            n += 1
    return n


def main():
    name, disc = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '1'
    files = dat.unpack(open(f'work/extracted/disc{disc}/{name}.DAT', 'rb').read())
    os.makedirs('work/recon', exist_ok=True)
    head = collections.Counter()
    with open(f'work/recon/survey_{name}_d{disc}.tsv', 'w', encoding='utf-8') as w:
        w.write('idx\tsize\thead\ttims\tkana_be\tkana_le\tsample\n')
        for i, f in enumerate(files):
            if not f:
                continue
            be, le, sb, sl = runs(f)
            t = tims(f)
            h = f[:16].hex(' ', 4)
            w.write(f'{i}\t{len(f)}\t{h}\t{t}\t{be}\t{le}\t{sl or sb or ""}\n')
            head[f[:4]] += 1
            if be or le or t:
                print(f'{i:4d} {len(f):9d} {h}  tim {t:3d} be {be:4d} le {le:4d} {sl or sb or ""}')
    print(head.most_common(12))


if __name__ == '__main__':
    main()

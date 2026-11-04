"""Recon: walk every DAT leaf, the EXE and the overlays; classify leaves; list Japanese text runs outside PSI scripts.
Reads both byte orders with a strict filter: every character must be kana, JIS level 1 kanji or common punctuation.
usage: recon_text.py [disc] -> work/recon/text_d<disc>.tsv (where, offset, order, text), leaves_d<disc>.tsv"""
import os, struct, sys, unicodedata
sys.path.insert(0, 'tools')
import dat, pak

PUNCT = set('　、。，．・：；？！ー～…‥（）「」『』【】＋－×＝％＆☆★○●◎□■△▲▽▼→←↑↓々／＿〇♂♀')


def ok_char(c):
    o = ord(c)
    return 0x3041 <= o <= 0x3093 or 0x30A1 <= o <= 0x30F6 or c in PUNCT or 0xFF10 <= o <= 0xFF19 or 0xFF21 <= o <= 0xFF5A


def kanji1(hi, lo):
    return 0x88 <= hi <= 0x97 or (hi == 0x98 and lo <= 0x72)


def word_char(hi, lo):
    """The character for a Shift-JIS code, or None when it's outside the strict set."""
    if not (0x81 <= hi <= 0x98 and 0x40 <= lo <= 0xFC and lo != 0x7F):
        return None
    try:
        c = bytes((hi, lo)).decode('cp932')
    except UnicodeDecodeError:
        return None
    if len(c) != 1:
        return None
    return c if (kanji1(hi, lo) or ok_char(c)) else None


def scan(d, order, minlen=3):
    """Yield (offset, text) for each 2-byte-aligned run; a run needs kana or >=4 kanji to count as text."""
    n = len(d) & ~1
    for start in (0, 1):
        i = start
        while i + 1 < n:
            hi, lo = (d[i + 1], d[i]) if order == 'le' else (d[i], d[i + 1])
            if word_char(hi, lo) is None:
                i += 2
                continue
            j, out = i, []
            while j + 1 < n:
                hi, lo = (d[j + 1], d[j]) if order == 'le' else (d[j], d[j + 1])
                c = word_char(hi, lo)
                if c is None:
                    break
                out.append(c)
                j += 2
            s = ''.join(out)
            kana = sum(1 for c in s if 0x3041 <= ord(c) <= 0x30F6)
            kanji = sum(1 for c in s if unicodedata.category(c) == 'Lo' and ord(c) >= 0x4E00)
            if len(s) >= minlen and (kana * 3 >= len(s) or kana >= 2 and len(s) < 6) and s.strip('　'):
                yield i, s
            i = j + 2


def kind(b):
    if b[:8] == b'PSI22.00':
        return 'psi'
    if b[:4] == b'\x10\0\0\0' and b[4] in (0, 1, 2, 3, 8, 9) and b[5:8] == b'\0\0\0':
        return 'tim'
    return 'data'


def main():
    disc = sys.argv[1] if len(sys.argv) > 1 else '1'
    root = f'work/extracted/disc{disc}'
    os.makedirs('work/recon', exist_ok=True)
    out = open(f'work/recon/text_d{disc}.tsv', 'w', encoding='utf-8')
    leaves = open(f'work/recon/leaves_d{disc}.tsv', 'w', encoding='utf-8')
    total = {}
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        d = open(path, 'rb').read()
        if name.endswith('.DAT'):
            files = dat.unpack(d)
            items = []
            for i, f in enumerate(files):
                if f:
                    items.extend(pak.walk(f, f'{name[:-4]}/{i}'))
        else:
            items = [(name, 0, d)]
        for p, base, b in items:
            k = kind(b)
            leaves.write(f'{p}\t{len(b)}\t{k}\t{b[:16].hex()}\n')
            if k in ('psi', 'tim'):
                continue
            n = 0
            for order in ('le', 'be'):
                for off, s in scan(b, order):
                    out.write(f'{p}\t{off:#x}\t{order}\t{s}\n')
                    n += 1
            if n:
                total[p] = n
    out.close()
    leaves.close()
    for p, n in sorted(total.items(), key=lambda x: -x[1])[:80]:
        print(n, p)
    print('leaves with text', len(total), 'runs', sum(total.values()))


if __name__ == '__main__':
    main()

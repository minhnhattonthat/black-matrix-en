"""Recon: free-space candidates. RAM: ranges that stay one value in every dump of a run (work/qa/ng3/ram_*.bin).
EXE: zero runs. A candidate is not free space until trap-tested (phase 5). Also a histogram of text control words.
usage: recon_free.py"""
import collections, glob, sys
sys.path.insert(0, 'tools')
import dat, psi

dumps = [open(p, 'rb').read() for p in sorted(glob.glob('work/qa/ng3/ram_*.bin'))]
print('dumps', len(dumps), 'size', hex(len(dumps[0])))
start = None
for i in range(0, len(dumps[0]), 256):
    blank = all(d[i:i + 256].count(d[i]) == len(d[i:i + 256]) for d in dumps)
    if blank and start is None:
        start = i
    if not blank and start is not None:
        if i - start >= 0x1000:
            print(f'  RAM blank in all dumps: 80{start:06x}-80{i:06x} ({i - start:#x})')
        start = None
if start is not None:
    print(f'  RAM blank in all dumps: 80{start:06x}-end')

exe = open('work/extracted/disc1/SLPS_029.62', 'rb').read()
i = 0x800
while i < len(exe):
    if exe[i] == 0:
        j = i
        while j < len(exe) and exe[j] == 0:
            j += 1
        if j - i >= 0x400:
            print(f'  EXE zeros: file {i:#x} ram {0x80010000 + i - 0x800:#x} len {j - i:#x}')
        i = j
    else:
        i += 1

ctrl, hist, longest = collections.Counter(), collections.Counter(), 0
for f in dat.unpack(open('work/extracted/disc1/SCENARIO.DAT', 'rb').read()):
    if not f or f[:8] != b'PSI22.00':
        continue
    for t in psi.tokenize(f)[0]:
        if t.words is None:
            continue
        hist[(t.op, t.sub)] += 1
        longest = max(longest, len(t.words))
        for w in t.words:
            if w < 0x8000:
                ctrl[w] += 1
print('longest text word count', longest)
print('non-SJIS words:', sorted((hex(k), v) for k, v in ctrl.items()))

"""Recon: walk a file for counted strings (u16 count + count text words) and flag which ones code or data points at.
usage: recon_counted.py FILE [--min N] -> offset, RAM address, count, ref kinds, text. A string is any run of valid text
words behind a matching count; greedy from the low end, so a false hit in code can only hide what overlaps it."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import psi
from recon_ptr import code_refs

LOADS = {'2ND.BIN': 0x800EB000, '3RD.BIN': 0x80110800, '4TH.BIN': 0x800EB000, '5TH.BIN': 0x800EB000, 'SLPS_029.62': 0x80010000}


def main():
    name = sys.argv[1]
    minn = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    d = (ROOT / 'work/orig/d1' / name).read_bytes()
    base = LOADS[name]
    if name.startswith('SLPS'):
        d = d[0x800:]
    refs, words = code_refs(d[:len(d) & ~3])
    data = set(words)
    for off, ws in psi.walk(d, minn):
        a = base + off
        kinds = ('c' if refs[a] else '-') + ('d' if a in data else '-') + ('C' if refs[a + 2] else '-') + ('D' if a + 2 in data else '-')
        print(f'{off:#07x} {a:#x} {len(ws):4} {kinds} {psi.decode(ws)!r}')


if __name__ == '__main__':
    main()

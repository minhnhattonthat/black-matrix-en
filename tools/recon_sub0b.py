"""Recon: find which overlay and load address hold the 0b/NN handlers, then print each one's fetch signature.
usage: recon_sub0b.py"""
import struct, sys
sys.path.insert(0, 'tools')
import mips, recon_ops

ENTRY = {4: 0x8012d3c4, 5: 0x8012d45c, 6: 0x8012d4b8, 7: 0x8012d518, 8: 0x8012d574, 9: 0x8012d5d0, 0xa: 0x8012d604,
         0xb: 0x8012d6f4, 0xc: 0x8012d7b0, 0xd: 0x8012d870, 0xe: 0x8012d930, 0x10: 0x8012da2c, 0x11: 0x8012db54,
         0x12: 0x8012dc88, 0x13: 0x8012de78, 0x14: 0x8012df58, 0x15: 0x8012e010, 0x16: 0x8012e0a0, 0x17: 0x8012e198}


def main():
    best = None
    for name in ('2ND', '3RD', '4TH', '5TH'):
        d = open(f'work/extracted/disc1/{name}.BIN', 'rb').read()
        # every handler starts with addiu $sp,$sp,-N; the entry spacing fixes the load address uniquely
        for off in range(0, len(d) - 4, 4):
            if struct.unpack_from('<I', d, off)[0] >> 16 != 0x27BD:
                continue
            load = ENTRY[4] - off
            hits = 0
            for a in ENTRY.values():
                o = a - load
                if 0 <= o < len(d) - 4 and struct.unpack_from('<I', d, o)[0] >> 16 == 0x27BD:
                    hits += 1
            if best is None or hits > best[0]:
                best = (hits, name, load)
    print('best', best[0], 'of', len(ENTRY), best[1], hex(best[2]))
    code = open(f'work/extracted/disc1/{best[1]}.BIN', 'rb').read()
    for sub, a in sorted(ENTRY.items()):
        sig, calls = recon_ops.handler_sig(code, best[2], a)
        print(f'{sub:02x} {a:08x} {sig or "-":10} calls {" ".join(f"{c:08x}" for c in calls[:6])}')


if __name__ == '__main__':
    main()

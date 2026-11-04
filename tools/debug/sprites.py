"""What a screen really cuts from its sprite sheets: warp to a scene, dump RAM, list every textured GPU primitive still in RAM.
Answers "how big is this label's sprite", which the sheet alone can't. Packets found by shape, so stale ones from earlier frames show too.
usage: sprites.py SCENE [--build] [--page X,Y]   -> prints  x y w h  u v  clut  tpage(for quads)"""
import argparse
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from skill import SKILL  # noqa: E402
import warp  # noqa: E402


def scan(ram):
    """Yield (x, y, w, h, u, v, clut, tpage) from each primitive-shaped run of words."""
    words = struct.unpack(f'<{len(ram) // 4}I', ram[:len(ram) // 4 * 4])
    for i in range(1, len(words) - 9):
        tag = words[i - 1]
        size = tag >> 24
        code = words[i] >> 24
        if size == 3 and code in (0x74, 0x75, 0x76, 0x77, 0x7C, 0x7D, 0x7E, 0x7F):  # fixed 8 or 16: 2 words + a tag
            pass
        if size == 4 and code in (0x64, 0x65, 0x66, 0x67):  # free-size sprite
            xy, uv, wh = words[i + 1:i + 4]
            w, h = wh & 0xFFFF, wh >> 16
            if 0 < w <= 256 and 0 < h <= 256:
                yield xy & 0xFFFF, xy >> 16, w, h, uv & 255, uv >> 8 & 255, uv >> 16, None
        if size == 9 and code in (0x2C, 0x2D, 0x2E, 0x2F):  # textured quad: colour, (xy, uv)x4
            xy0, uv0, xy1, uv1, xy2, uv2, xy3, uv3 = words[i + 1:i + 9]
            x0, y0 = xy0 & 0xFFFF, xy0 >> 16
            x3, y3 = xy3 & 0xFFFF, xy3 >> 16
            u0, v0, u3, v3 = uv0 & 255, uv0 >> 8 & 255, uv3 & 255, uv3 >> 8 & 255
            if 0 <= x3 - x0 <= 320 and 0 <= y3 - y0 <= 240:
                yield x0, y0, x3 - x0, y3 - y0, u0, v0, uv0 >> 16, uv1 >> 16


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scene')
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--every', type=int, default=300)
    a = ap.parse_args()
    row = next(s for s in warp.scenes() if s['name'] == a.scene)
    out = os.path.join(ROOT, 'work/qa/sprites', a.scene)
    cmd = [sys.executable, '-X', 'utf8', os.path.join(SKILL, 'scripts/emu.py'), warp.cue(row['disc'], a.build), '--out', out,
           '--script', os.path.join(ROOT, 'tools/debug/warp.lua'), '--var', f"SCENE='{a.scene}'", '--frames', '60000', '--timeout', '280',
           '--script', os.path.join(SKILL, 'scripts/lua/probes/ramdump.lua'), '--var', f'RAM_EVERY={a.every}']
    if a.build:
        cmd += ['--var', f"SCENES='{warp.built_scenes().replace(os.sep, '/')}'"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=ROOT)
    if r.returncode:
        sys.exit(f'emu.py exit {r.returncode}: {r.stdout[-400:]}')
    dumps = sorted(f for f in os.listdir(out) if f.startswith('ram_') and f.endswith('.bin'))
    seen = set()
    for d in dumps[-1:]:  # the last dump is the screen the scene ends on
        for rec in scan(open(os.path.join(out, d), 'rb').read()):
            if rec not in seen:
                seen.add(rec)
    print(f'# {a.scene}: {dumps[-1]}, {len(seen)} primitives; x y w h u v clut tpage')
    for rec in sorted(seen, key=lambda r: (r[7] or 0, r[6], r[5], r[4])):
        print(*rec)


if __name__ == '__main__':
    main()

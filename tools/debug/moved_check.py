"""Does the game find files by name? Builds Disc N with 2ND.BIN grown by SHIFT sectors (every later file moves), runs
scenes on the original and the moved image with tools/lua/cdlog.lua, and compares the sets of CD reads.
A read of the moved image must be an original LBA + SHIFT (below 2ND.BIN: the same LBA); anything else is a baked-in
address, and the file it points at could not move. Fails too if a scene doesn't arrive on both images.
usage: moved_check.py [--disc N] [--shift S] NAME [NAME..]   scenes from tools/debug/scenes.tsv. Output: work/qa/moved/"""
import argparse, concurrent.futures as cf, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/debug')]
import build
import disc as disclib
from skill import SKILL
from warp import scenes

OUT = ROOT / 'work/qa/moved'


def run(cue, scene, tag):
    out = OUT / f'{scene}_{tag}'
    subprocess.run([sys.executable, '-X', 'utf8', os.path.join(SKILL, 'scripts/emu.py'), str(cue), '--out', str(out), '--debugger',
                    '--script', str(ROOT / 'tools/debug/warp.lua'), '--var', f"SCENE='{scene}'",
                    '--script', str(ROOT / 'tools/lua/cdlog.lua'), '--frames', '60000', '--timeout', '280'],
                   cwd=ROOT, capture_output=True)
    log = (out / 'log.txt').read_text(encoding='utf-8', errors='replace')
    return [int(m) for m in re.findall(r'^SETLOC \d+ (\d+)', log, re.M)], 'ARRIVED' in log or 'END' in log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='+')
    ap.add_argument('--disc', type=int, default=1)
    ap.add_argument('--shift', type=int, default=5)
    a = ap.parse_args()
    known = {s['name'] for s in scenes()}
    assert set(a.names) <= known, set(a.names) - known
    second = (build.unpack(a.disc).parent / f'd{a.disc}/2ND.BIN').read_bytes()
    moved = build.make_image(a.disc, {'2ND.BIN': second + bytes(2048 * a.shift)}, OUT / f'd{a.disc}.bin')
    orig_cue = build.rom(a.disc, 'cue')
    files = disclib.Disc(build.rom(a.disc)).files()
    start = next(l for p, l, *_ in files if p == '/2ND.BIN')
    owner = lambda s: next((p for p, l, sz, *_ in files if l <= s < l + (sz + 2047) // 2048), 'dir/other')

    def scene(name):
        with cf.ThreadPoolExecutor(2) as ex:
            (x, xok), (y, yok) = ex.map(lambda t: run(*t), [(orig_cue, name, 'o'), (moved.with_suffix('.cue'), name, 'm')])
        # sets: the read order isn't stable, the drive re-seeks during XA playback depending on timing
        bad = sorted({u + a.shift if u > start else u for u in x} ^ set(y))
        return name, x, y, xok and yok, bad

    fail = False
    seen = set()
    with cf.ThreadPoolExecutor(2) as ex:
        for name, x, y, ok, bad in ex.map(scene, a.names):
            seen |= {owner(u) for u in x}
            status = 'ok' if ok and not bad else 'FAIL'
            fail |= status == 'FAIL'
            print(f'{status}\t{name}\treads {len(x)}/{len(y)}\tunexplained LBAs {[(v, owner(v)) for v in bad[:8]]}')
    print('files read:', ' '.join(sorted(seen)))
    moved.unlink(), moved.with_suffix('.cue').unlink()
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()

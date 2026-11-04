"""Warp to scenes from a cold boot. Scene list: tools/debug/scenes.tsv. Lua side: tools/debug/warp.lua.
usage: warp.py NAME [NAME..] [--build]   one or more scenes, by name (fnmatch patterns allowed)
       warp.py --all [--jobs N] [--build]   every scene; writes work/qa/warp/report.tsv and exits 1 on any failure
--build uses build/disc<N>/black-matrix-plus_en.cue instead of the original dump. Shots: work/qa/warp/<name>/."""
import argparse, concurrent.futures as cf, csv, fnmatch, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from skill import SKILL


def scenes():
    with open(os.path.join(ROOT, 'tools/debug/scenes.tsv'), encoding='utf-8', newline='') as f:
        return list(csv.DictReader((l for l in f if l.strip() and not l.startswith('#')), delimiter='\t', quoting=csv.QUOTE_NONE))


def cue(disc, build):
    if build:
        return os.path.join(ROOT, f'build/disc{disc}/black-matrix-plus_en.cue')
    return os.path.join(ROOT, f'rom/Black-Matrix + (Japan) (Disc {disc}).cue')


def run(s, build):
    out = os.path.join(ROOT, 'work/qa/warp', s['name'])
    cmd = [sys.executable, '-X', 'utf8', os.path.join(SKILL, 'scripts/emu.py'), cue(s['disc'], build), '--out', out,
           '--script', os.path.join(ROOT, 'tools/debug/warp.lua'), '--var', f"SCENE='{s['name']}'", '--frames', '60000',
           '--timeout', '280', '--sheet']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=ROOT)
    arrived = ''
    log = os.path.join(out, 'log.txt')
    if os.path.exists(log):
        arrived = ' | '.join(l.strip() for l in open(log, encoding='utf-8', errors='replace') if l.startswith(('ARRIVED', 'END', 'EXPECT')))
    ok = r.returncode == 0 and ('ARRIVED' in arrived or s['script'] == '-')
    return s['name'], ok, r.returncode, arrived


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('--build', action='store_true')
    a = ap.parse_args()
    rows = scenes()
    pick = rows if a.all else [s for s in rows if any(fnmatch.fnmatch(s['name'], n) for n in a.names)]
    if not pick:
        sys.exit('no such scene; names are in tools/debug/scenes.tsv')
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda s: run(s, a.build), pick))
    os.makedirs(os.path.join(ROOT, 'work/qa/warp'), exist_ok=True)
    report = os.path.join(ROOT, 'work/qa/warp/report.tsv')
    lines = {}
    if not a.all and os.path.exists(report):
        for line in open(report, encoding='utf-8', errors='replace'):
            cols = line.rstrip('\n').split('\t')
            if len(cols) >= 2:
                lines[cols[1]] = line.rstrip('\n')
    for name, ok, rc, arrived in res:
        line = f"{'ok' if ok else 'FAIL'}\t{name}\trc={rc}\t{arrived}"
        lines[name] = line
        print(line)
    with open(report, 'w', encoding='utf-8', newline='\n') as f:
        for s in rows:
            if s['name'] in lines:
                f.write(lines[s['name']] + '\n')
    sys.exit(0 if all(r[1] for r in res) else 1)


if __name__ == '__main__':
    main()

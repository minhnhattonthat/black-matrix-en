"""marker_sheets.py: one review sheet per group of warp scenes (final.png or proof.png of each), plus the distinct text windows the
scenes logged (tools/lua/winlog.lua). usage: marker_sheets.py OUT NAME [NAME..]   names may be fnmatch patterns. Prints the tile order."""
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

from skill import SKILL

ROOT = Path(__file__).resolve().parents[1]
WARP = ROOT / 'work/qa/warp'


def main():
    out, pats = sys.argv[1], sys.argv[2:]
    names = sorted(p.name for p in WARP.iterdir() if p.is_dir() and any(fnmatch.fnmatch(p.name, x) for x in pats))
    shots = [str(WARP / n / ('proof.png' if (WARP / n / 'proof.png').exists() else 'final.png')) for n in names]
    subprocess.run([sys.executable, '-X', 'utf8', str(Path(SKILL) / 'scripts/sheet.py'), *shots, '--max', '12', '--cols', '4', '--div', '1',
                    '--out', out], check=True)
    print(' '.join(names))
    wins = {}
    for n in names:
        log = WARP / n / 'log.txt'
        if log.exists():
            for m in re.finditer(r'WIN (\S+) cols=(\d+) rows=(\d+) a3=(-?\d+) st=(\S+)', log.read_text(errors='replace')):
                wins.setdefault(m.groups(), []).append(n)
    for k, v in sorted(wins.items(), key=lambda kv: (-int(kv[0][1]), kv[0][2])):
        print(f'{k[1]:>3}x{k[2]} x={k[3]} st={k[4]} ra={k[0]}  {v[0]} +{len(v) - 1}')


if __name__ == '__main__':
    main()

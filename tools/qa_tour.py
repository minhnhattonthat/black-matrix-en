"""Tour sheets for qa_gate.py: work/qa/tour/<scene>.png at full size from work/qa/warp/, plus gfx_sheets.py pages. Half-size sheets make the 7-px font look broken to a reader.
Run after `warp.py --all --build`, then `qa_gate.py init work/qa/manifest.tsv work/qa/tour --glob "*.png"`, then qa_review.py.
usage: qa_tour.py"""
import shutil
import subprocess
import sys
from pathlib import Path

from skill import SKILL

ROOT = Path(__file__).resolve().parents[1]
TOUR = ROOT / 'work/qa/tour'


def main():
    TOUR.mkdir(parents=True, exist_ok=True)
    for old in TOUR.glob('*.png'):
        old.unlink()
    sheet = str(Path(SKILL) / 'scripts/sheet.py')
    for line in (ROOT / 'tools/debug/scenes.tsv').read_text(encoding='utf-8').splitlines()[1:]:
        name = line.split('\t')[0]
        shots = ROOT / 'work/qa/warp' / name
        if name and not name.startswith('#') and any(shots.glob('f*.png')):
            subprocess.run([sys.executable, '-X', 'utf8', sheet, str(shots), '--div', '1', '--changed', '0.02', '--max', '6', '--cols', '3',
                            '--out', str(TOUR / f'{name}.png')], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tools/gfx_sheets.py')], check=True)
    for f in (ROOT / 'work/qa/gfx').glob('sheet_*.png'):
        shutil.copy(f, TOUR / f'gfx_{f.name}')
    print(len(list(TOUR.glob('*.png'))), 'sheets')


if __name__ == '__main__':
    main()

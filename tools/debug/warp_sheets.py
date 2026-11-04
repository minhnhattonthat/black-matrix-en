"""One intentional proof tile per scene, labelled in an index, for reading every scene at a glance.
usage: warp_sheets.py [--cols 8] [--max 48]   writes work/qa/warp/proof.png, proof_2.png.. and proof.tsv (tile order per page)
Uses proof.png when the scene's proof column requests a mid-run frame, otherwise final.png. Never picks a camp/title frame merely because it compresses poorly."""
import argparse, csv, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from skill import SKILL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cols', default='8')
    ap.add_argument('--max', type=int, default=48)
    a = ap.parse_args()
    with open(os.path.join(ROOT, 'tools/debug/scenes.tsv'), encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))
    base = os.path.join(ROOT, 'work/qa/warp')
    picks = []
    for r in rows:
        n = r['name']
        shot = 'proof.png' if r['proof'] != '-' else 'final.png'
        path = os.path.join(base, n, shot)
        if not os.path.exists(path):
            sys.exit(f'no {shot} for {n}; rerun tools/debug/warp.py {n}')
        picks.append(path)
    with open(os.path.join(base, 'proof.tsv'), 'w', encoding='utf-8') as f:
        for i, (r, p) in enumerate(zip(rows, picks)):
            n = r['name']
            f.write(f'{i // a.max + 1}\t{i % a.max + 1}\t{n}\t{os.path.basename(p)}\n')
    sys.exit(subprocess.run([sys.executable, '-X', 'utf8', os.path.join(SKILL, 'scripts/sheet.py'), *picks, '--cols', a.cols, '--max', str(a.max), '--out', os.path.join(base, 'proof.png')],
                            stdout=subprocess.DEVNULL).returncode)


if __name__ == '__main__':
    main()

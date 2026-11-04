"""Independent read of the warp proof sheets: codex exec, read-only, one verdict per tile, per page.
Run warp_sheets.py first. Writes work/qa/warp/review/p<N>.txt; skips pages already done, so a rerun resumes.
usage: warp_review.py [--force]   --force re-reads every page after new proof shots."""
import argparse, csv, os, subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--force', action='store_true')
args = parser.parse_args()
BASE = 'work/qa/warp'
OUT = f'{BASE}/review'
os.makedirs(OUT, exist_ok=True)
with open('tools/debug/scenes.tsv', encoding='utf-8', newline='') as f:
    notes = {r['name']: r['note'] for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE)}
pages = {}
with open(f'{BASE}/proof.tsv', encoding='utf-8') as f:
    for page, tile, name, _ in csv.reader(f, delimiter='\t'):
        pages.setdefault(int(page), []).append((tile, name))
# one line: codex.cmd goes through cmd.exe, which cuts an argument at its first newline
HEAD = ('This contact sheet comes from a Japanese PlayStation game, one frame per tile, read left to right and top to bottom, numbered from 1. '
        'Each scene below names what its tile is meant to show. For each tile, one line: number, scene, verdict, then what you actually see in a few words. '
        'Verdict is OK if the tile plainly shows the stated screen, WRONG if it shows something else (a black or empty frame, a title or menu instead of the scene, the same picture as a neighbour that should differ), '
        'UNSURE if you cannot tell. A movie tile is OK only if it shows video rather than a menu or black frame. Do not edit anything and do not ask questions. End with the line DONE and the count of tiles you saw. Scenes: ')
for page, tiles in sorted(pages.items()):
    out = f'{OUT}/p{page}.txt'
    if os.path.exists(out) and not args.force:
        continue
    img = f'{BASE}/proof{"" if page == 1 else f"_{page}"}.png'
    prompt = HEAD + ' | '.join(f'{t} {n}: {notes[n]}' for t, n in tiles)
    r = subprocess.run(['codex.cmd', 'exec', '-s', 'read-only', '--skip-git-repo-check', '--ephemeral', '-o', out, '-i', img, '--', prompt],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
    print(out, 'rc', r.returncode, r.stderr[-300:] if r.returncode else '', flush=True)

"""Visual QA of the tour's sheets: codex exec, read-only and fresh, with docs/visual-qa-brief.md; verdicts in work/qa/verdicts/<chunk>.tsv for qa_gate.py.
Asks about the sheets `qa_gate.py todo` lists, so a rerun after a rebuild reads only the ones that changed.
usage: qa_review.py [--size N]"""
import argparse
import subprocess
import sys
from pathlib import Path

from skill import SKILL

ROOT = Path(__file__).resolve().parents[1]
MANIFEST, VERDICTS = ROOT / 'work/qa/manifest.tsv', ROOT / 'work/qa/verdicts'
BRIEF = ('You are the visual-QA reviewer of a Japanese PlayStation game translated into English. Each image is one contact sheet of screenshots from a '
         'QA tour; the ids below name them in order. An issue is: Japanese still visible (kana or kanji, however small), text overflowing a box or clipped by '
         'a frame or running off screen, garbage tiles, wrong or missing glyphs, broken line breaks (a word split mid-line, a one-word last line), or an empty '
         'box where text belongs. Not issues: text still typing out, a box mid-fade, a scene still loading after a warp, a green box where a dialogue portrait '
         'belongs (warped scenes do this on the original too), a black frame, English logos, kanji beside English words in a bonus demo movie (kept by decision), '
         'a title or win line stacked over two or three lines on a chapter or battle card (card lettering, not a paragraph), `Belphe` (a character, not clipped), '
         'and label rows overlapping on a raw sprite sheet in gfx_sheet ids (the sheet layout, not the screen). '
         'Reply with one line per id and nothing else: id, a tab, ok or issue, a tab, what and where for an issue. Read every image; do not edit anything; '
         'do not ask questions; do not guess at an image you cannot see, say so as an issue.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=6)
    size = ap.parse_args().size
    VERDICTS.mkdir(parents=True, exist_ok=True)
    gate = [sys.executable, '-X', 'utf8', str(Path(SKILL) / 'scripts/qa_gate.py')]
    r = subprocess.run(gate + ['todo', str(MANIFEST), str(VERDICTS), '--size', '100000'], capture_output=True, text=True, encoding='utf-8')
    todo = [line.split('\t')[-1].strip() for line in r.stdout.splitlines() if line.strip()]
    paths = {}
    for line in MANIFEST.read_text(encoding='utf-8').splitlines():
        c = line.split('\t')
        paths[c[1]] = c[0]
    stamp = sum(1 for _ in VERDICTS.glob('*.tsv'))
    for i in range(0, len(todo), size):
        chunk = [p for p in todo[i:i + size] if p in paths]
        if not chunk:
            continue
        ids = [paths[p] for p in chunk]
        out = VERDICTS / f'r{stamp:03d}_{i // size:03d}.tsv'
        raw = out.with_suffix('.raw')
        cmd = ['codex.cmd', 'exec', '-s', 'read-only', '--skip-git-repo-check', '--ephemeral', '-o', str(raw)]
        for p in chunk:
            cmd += ['-i', p]
        # one line: codex.cmd goes through cmd.exe, which cuts an argument at its first newline
        cmd += ['--', BRIEF + ' Ids, in image order: ' + ' '.join(ids)]
        run = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL, cwd=ROOT)
        got = {}
        if raw.exists():
            for line in raw.read_text(encoding='utf-8').splitlines():
                c = line.strip().split('\t')
                if len(c) >= 2 and c[0] in ids and c[1] in ('ok', 'issue'):
                    got[c[0]] = c[1:]
        out.write_text(''.join(f"{k}\t{v[0]}\t{v[1] if len(v) > 1 else ''}\n" for k, v in got.items()), encoding='utf-8')
        print(out.name, len(got), 'of', len(ids), 'issues', sum(v[0] == 'issue' for v in got.values()), 'rc', run.returncode, flush=True)


if __name__ == '__main__':
    main()

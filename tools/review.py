"""review.py: independent translation review, per docs/reviewer-brief.md: codex exec, read-only, one report per chunk of 4 batches.
Writes work/qa/review/pairs/<chunk>.txt and work/qa/review/<chunk>.txt. Skips a chunk whose report exists, so a rerun resumes; delete a report to re-review it.
usage: review.py [--jobs 3] [CHUNK..]   CHUNK is like c00; prints each chunk's Critical and Important counts when done."""
import argparse
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import batches

OUT = batches.ROOT / 'work/qa/review'
SIZE = 4
# one line: codex.cmd goes through cmd.exe, which cuts an argument at its first newline
PROMPT = ('Follow docs/reviewer-brief.md for the pairs file {pairs}. Read glossary.md, docs/style-reference.md and docs/synopsis.md first. '
          'The file is in story order, so each entry\'s neighbours are its context. Greek letters in the Japanese are kanji the font lacks: see docs/translator-brief.md. '
          'Ruling: Purica is a child and Michette, Kurreshes, Laila and Abel have no stated age, so sexual lines about them are deliberately rendered as non-sexual: never flag that as an error. '
          'A box holds about 95 letters a page, and English must stay near the length of the original, so do not ask for additions the box cannot hold. '
          'Do not edit anything. Your final message is the report in the format the brief gives. End with the line DONE.')


def chunks():
    names = sorted(p.name[:4] for p in batches.TL.glob('b[0-9][0-9][0-9].out.tsv'))
    return {f'c{i // SIZE:02}': names[i:i + SIZE] for i in range(0, len(names), SIZE)}


def pairs(names):
    lines = []
    for name in names:
        out = batches.read_out(name)
        lines.append(f'# {name}')
        for row in (batches.TL / f'{name}.tsv').read_text(encoding='utf-8').splitlines():
            sid, who, _, _, jp = row.split('\t')
            lines += [f'>> {sid} | {who or "-"} | {jp}', out[sid].replace('\n', ' / ')]
    return '\n'.join(lines) + '\n'


def run(chunk, names):
    out, path = OUT / f'{chunk}.txt', OUT / 'pairs' / f'{chunk}.txt'
    path.write_text(pairs(names), encoding='utf-8', newline='\n')
    if out.exists():
        return chunk, 'done before'
    cmd = ['codex.cmd', 'exec', '-s', 'read-only', '--skip-git-repo-check', '--ephemeral', '-o', str(out), '--',
           PROMPT.format(pairs=path.relative_to(batches.ROOT).as_posix())]
    r = subprocess.run(cmd, cwd=batches.ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
    return chunk, f'rc {r.returncode}' + (' ' + r.stderr[-200:] if r.returncode else '')


def counts(text):
    """(critical, important) findings: the bullet lines under each heading."""
    parts = re.split(r'^#+\s*(Critical|Important|Minor)\b.*$', text, flags=re.M)
    got = dict(zip(parts[1::2], parts[2::2]))
    n = lambda k: len(re.findall(r'^\s*(?:[-*]|\d+\.)\s+\S', got.get(k, ''), flags=re.M))
    return n('Critical'), n('Important')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('chunk', nargs='*')
    a = ap.parse_args()
    (OUT / 'pairs').mkdir(parents=True, exist_ok=True)
    todo = {k: v for k, v in chunks().items() if not a.chunk or k in a.chunk}
    with ThreadPoolExecutor(a.jobs) as ex:
        for chunk, res in ex.map(lambda kv: run(*kv), todo.items()):
            report = OUT / f'{chunk}.txt'
            c = counts(report.read_text(encoding='utf-8')) if report.exists() else '-'
            print(chunk, todo[chunk][0], '..', todo[chunk][-1], res, 'critical, important:', c, flush=True)


if __name__ == '__main__':
    assert counts('### Critical\n- a\n- b\n#### Important (x)\n- c\n### Minor\n- d\n') == (2, 1)
    main()

"""polish.py: the polish pass over docs/polish.md (references/translation.md, Review): codex exec, read-only, proposes each Minor's fix, this script holds it to the batch rules.
usage: polish.py split [--size 40]   unticked lines -> work/qa/polish/pNN.txt: the note, then each id's speaker, limit, Japanese and current English
       polish.py run [--jobs 4]      codex on every chunk without a work/qa/polish/pNN.out
       polish.py apply               valid fixes -> work/qa/polish/fixes.tsv (feed to fix_lines.py), ticks docs/polish.md, prints what was refused; refused lines stay unticked
Output of a chunk, tab-separated: `L<line>  fixed` or `L<line>  waived: reason`, and `<id>  <English>` per changed string."""
import argparse
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

import batches
import extract
import fit

POLISH, OUT = batches.ROOT / 'docs/polish.md', batches.ROOT / 'work/qa/polish'
ID = re.compile(r'\b(?:s\d+:[0-9a-f]+|[0-9a-z_]+:[0-9a-z_.]+)')
STUB = 6
# one line: codex.cmd goes through cmd.exe, which cuts an argument at its first newline
PROMPT = ('You do the polish pass of a Japanese->English game translation. Read glossary.md, docs/style-reference.md and docs/synopsis.md, then the file {path}. Each L<number> entry is a reviewer note, '
          'followed by every string it names: id, speaker, limit, JP, then the current EN. The note may be stale: judge against the current EN. For each L entry decide: apply the fix (the note\'s suggestion, or better) '
          'or waive it (already fixed, or the suggestion is worse or breaks the rules). A suggestion that covers part of a line is worked into the whole line; a note naming several ids gets each its own line in that speaker\'s voice. '
          'Rules: plain ASCII only, straight quotes; keep every {{XXXX}} control word exactly as many times as the JP has it; a literal backslash-n is a forced break, keep the ones the current EN has unless the fix needs otherwise; '
          'stay within the limit (17x3 means about 95 letters a page, longer text flows to more pages; NNch is a hard letter count); names per the glossary; do not make the line much longer than the current EN. '
          'Purica is a child and Michette, Kurreshes, Laila and Abel have no stated age, so sexual lines about them are deliberately non-sexual: keep that. Morals are inverted in this world: wicked is praise. '
          'Do not edit anything. Your final message is only tab-separated lines: for each entry a line `L<number><TAB>fixed` or `L<number><TAB>waived: reason`, and after a fixed one a line `<id><TAB><new English>` for each changed string. Answer every L entry.')


def unticked():
    return [(i, line) for i, line in enumerate(POLISH.read_text(encoding='utf-8').splitlines(), 1) if line.startswith('- [ ]')]


def strings():
    return {s['id']: (rel, s) for rel, doc in extract.load().items() for s in doc['strings']}


def ids_in(line, known):
    return list(dict.fromkeys(m for m in ID.findall(line) if m in known))


def entry(no, line, known):
    out = [f'L{no} {line[6:]}']
    for sid in ids_in(line, known):
        rel, s = known[sid]
        out.append(f'  {sid} | {batches.speaker(s) or "-"} | {batches.form_limit(rel, s)[1]} | JP: {s["jp"]!r}\n  EN: {s["en"]!r}')
    return '\n'.join(out)


def bad_fix(rel, s, en, avoid):
    """Why a fix can't go in: the rules lint holds the whole script to."""
    form, limit = batches.form_limit(rel, s)
    bad = batches.problems((s['id'], '', form, limit, s['jp'].replace('\n', ' / ')), en, avoid)
    if s.get('box'):
        cols, page = map(int, s['box'].split('x'))
        rows = fit.wrap(en.split('\n')[-1], cols, page)
        if len(rows) > 1 and fit.width(rows[-1]) < STUB:
            bad.append(f'last row is only "{rows[-1]}"')
    return bad


def parse(text):
    """({line: verdict}, {id: English}) of one chunk's output."""
    verdicts, fixes = {}, {}
    for row in text.splitlines():
        if '\t' not in row:
            continue
        k, v = row.split('\t', 1)
        k, v = k.strip().strip('`'), v.strip().strip('`')
        if re.fullmatch(r'L\d+', k):
            verdicts[int(k[1:])] = v
        elif k:
            fixes[k] = v
    return verdicts, fixes


def split(size):
    OUT.mkdir(parents=True, exist_ok=True)
    known, todo = strings(), unticked()
    for old in OUT.glob('p[0-9][0-9].txt'):
        old.unlink()
    for n in range(0, len(todo), size):
        text = '\n\n'.join(entry(no, line, known) for no, line in todo[n:n + size]) + '\n'
        (OUT / f'p{n // size:02}.txt').write_text(text, encoding='utf-8', newline='\n')
    no_id = [no for no, line in todo if not ids_in(line, known)]
    print(len(todo), 'lines,', -(-len(todo) // size), 'chunks; lines naming no known id:', no_id)


def run_one(path):
    out = path.with_suffix('.out')
    if out.exists():
        return path.name, 'done before'
    cmd = ['codex.cmd', 'exec', '-s', 'read-only', '--skip-git-repo-check', '--ephemeral', '-o', str(out), '--',
           PROMPT.format(path=path.relative_to(batches.ROOT).as_posix())]
    r = subprocess.run(cmd, cwd=batches.ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
    return path.name, f'rc {r.returncode}' + (' ' + r.stderr[-200:] if r.returncode else '')


def run(jobs):
    with ThreadPoolExecutor(jobs) as ex:
        for name, res in ex.map(run_one, sorted(OUT.glob('p[0-9][0-9].txt'))):
            print(name, res, flush=True)


def apply():
    known, avoid = strings(), batches.avoid_terms()
    verdicts, fixes = {}, {}
    for path in sorted(OUT.glob('p[0-9][0-9].out')):
        v, f = parse(path.read_text(encoding='utf-8'))
        verdicts.update(v)
        fixes.update(f)
    good, refused = {}, {}
    for sid, en in fixes.items():
        if sid not in known:
            refused[sid] = ['unknown id']
            continue
        bad = bad_fix(*known[sid], en.replace('\\n', '\n'), avoid)
        if bad:
            refused[sid] = bad
        else:
            good[sid] = en
    lines = POLISH.read_text(encoding='utf-8').splitlines()
    ticked = unanswered = held = 0
    for no, line in unticked():
        verdict = verdicts.get(no)
        names = ids_in(line, known)
        if verdict is None or not (verdict == 'fixed' or verdict.startswith('waived')):
            unanswered += 1
            print(f'L{no}: no verdict: {verdict}')
        elif any(s in refused for s in names):
            held += 1
        else:
            lines[no - 1] = '- [x]' + line[5:] + (' - ' + verdict if verdict != 'fixed' else '')
            ticked += 1
    (OUT / 'fixes.tsv').write_text(''.join(f'{k}\t{v}\n' for k, v in good.items()), encoding='utf-8', newline='\n')
    POLISH.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    for sid, why in refused.items():
        print(f'{sid}: {why}  {fixes[sid]!r}')
    print(f'{len(good)} fixes, {len(refused)} refused, {ticked} lines ticked, {held} held by a refusal, {unanswered} unanswered')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('split', 'run', 'apply'))
    ap.add_argument('--size', type=int, default=40)
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    {'split': lambda: split(a.size), 'run': lambda: run(a.jobs), 'apply': apply}[a.cmd]()


if __name__ == '__main__':
    assert parse('L3\tfixed\ns8:1\t`A\\nB`\nnoise\nL4\twaived: no\n') == ({3: 'fixed', 4: 'waived: no'}, {'s8:1': 'A\\nB'})
    main()

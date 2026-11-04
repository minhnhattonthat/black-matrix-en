"""story.py: the story pass (references/translation.md, Review): one reviewer per chapter, codex exec, read-only, per docs/story-reviewer-brief.md.
usage: story.py split              work/qa/story/chapters/NAME.txt from every scn string, chapters per docs/synopsis.md; then run qa_gate.py init on them
       story.py run [--jobs 4]     codex on each chapter with no work/qa/story/reports/NAME.txt; delete a report to re-review; prints each one's counts
       story.py verdicts           work/qa/story/verdicts/NAME.tsv from each report's Assessment
       story.py read NAME [--part N]  the chapter's English, duplicates skipped, ~30k characters a part: for reading in-session when codex can't run"""
import argparse
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

import batches
import extract
from review import counts

OUT = batches.ROOT / 'work/qa/story'
CHAPTERS, REPORTS, VERDICTS = OUT / 'chapters', OUT / 'reports', OUT / 'verdicts'
# (name, first script, last script): docs/synopsis.md's Story. The prologue exists once per master, so it splits by script group.
PARTS = [('00_wake', 8, 44), ('01_home', 45, 96), ('02_book_raid', 97, 125), ('03_golgotha', 126, 149), ('04_ribeira', 150, 202),
         ('05_pandemonium', 203, 227), ('06_kederon', 228, 248), ('07_pandemonium2', 249, 283), ('08_canaan', 284, 326), ('09_begild', 327, 366),
         ('10_sodom', 367, 411), ('11_moses_noah', 412, 443), ('12_underworld', 444, 477), ('13_showdown', 478, 523), ('14_ending', 524, 9999)]
# one line: codex.cmd goes through cmd.exe, which cuts an argument at its first newline
PROMPT = ('Follow docs/story-reviewer-brief.md for the chapter file {path}. Read docs/synopsis.md, docs/style-reference.md and glossary.md first. '
          'Lines headed by a # script number; a block of near-identical scripts is the same scene once per master (each in that master\'s voice) or per route: the player sees one, so read them as alternatives, not a sequence. '
          'Greek letters in the Japanese are kanji the font lacks: see docs/translator-brief.md. '
          'Ruling: Purica is a child and Michette, Kurreshes, Laila and Abel have no stated age, so sexual lines about them are deliberately rendered as non-sexual: never flag that. '
          'A box holds about 95 letters a page and English must stay near the length of the original, so do not ask for additions the box cannot hold. '
          'Do not edit anything. Your final message is the report in the format the brief gives. End with the line DONE.')


def chapter(no):
    return next(name for name, a, b in PARTS if a <= no <= b)


def text_of(strings):
    lines = []
    for s in strings:
        if batches.PUNCT.match(s['jp']) or not s['jp'].strip():
            continue
        lines += [f'>> {s["id"]} | {batches.speaker(s) or "-"} | ' + s['jp'].replace('\n', ' / '), s['en'].replace('\n', ' / ')]
    return lines


def split():
    CHAPTERS.mkdir(parents=True, exist_ok=True)
    docs, out = extract.load(), {}
    for rel in sorted(r for r in docs if r.startswith('scn/')):
        no = int(rel[4:8])
        out.setdefault(chapter(no), []).extend([f'\n# script {no}'] + text_of(docs[rel]['strings']))
    for name, lines in out.items():
        (CHAPTERS / f'{name}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        print(name, len(lines) // 2, 'lines')


def read_view(name, part, size=30000):
    """A chapter's English for one reader: `offset|speaker|EN` per string, an English line already shown in this chapter skipped (the per-master copies). Prints one part of about size characters."""
    seen, parts, cur, chars = set(), [], [], 0
    docs = extract.load()
    for rel in sorted(r for r in docs if r.startswith('scn/') and chapter(int(r[4:8])) == name):
        cur.append(f'# {int(rel[4:8])}')
        for s in docs[rel]['strings']:
            if batches.PUNCT.match(s['jp']) or not s['jp'].strip() or s['en'] in seen:
                continue
            seen.add(s['en'])
            line = f'{s["id"].split(":")[1].lstrip("0")}|{(batches.speaker(s) or "-")[:6]}|' + s['en'].replace('\n', ' ')
            cur.append(line)
            chars += len(line)
        if chars > size:
            parts.append(cur)
            cur, chars = [], 0
    parts.append(cur)
    print(f'[{name} part {part + 1} of {len(parts)}]')
    print('\n'.join(parts[part]))


def run_one(path):
    out = REPORTS / path.name
    if out.exists():
        return path.stem, 'done before'
    cmd = ['codex.cmd', 'exec', '-s', 'read-only', '--skip-git-repo-check', '--ephemeral', '-o', str(out), '--',
           PROMPT.format(path=path.relative_to(batches.ROOT).as_posix())]
    r = subprocess.run(cmd, cwd=batches.ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
    return path.stem, f'rc {r.returncode}' + (' ' + r.stderr[-200:] if r.returncode else '')


def run(jobs):
    REPORTS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(jobs) as ex:
        for name, res in ex.map(run_one, sorted(CHAPTERS.glob('*.txt'))):
            report = REPORTS / f'{name}.txt'
            print(name, res, 'critical, important:', counts(report.read_text(encoding='utf-8')) if report.exists() else '-', flush=True)


def assessment(text):
    """('ok' | 'issue', note) from a report's Assessment section; a report without one is an issue."""
    part = re.split(r'^#+\s*Assessment\b.*$', text, flags=re.M)
    m = re.search(r'\b(ok|issue)\b(.*)', part[-1]) if len(part) > 1 else None
    return (m[1], m[2].strip(' -`')) if m else ('issue', 'no Assessment in the report')


def verdicts():
    VERDICTS.mkdir(parents=True, exist_ok=True)
    for path in sorted(REPORTS.glob('*.txt')):
        word, note = assessment(path.read_text(encoding='utf-8'))
        (VERDICTS / f'{path.stem}.tsv').write_text(f'{path.stem}\t{word}\t{note}\n', encoding='utf-8', newline='\n')
        print(path.stem, word, note[:100])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('split', 'run', 'verdicts', 'read'))
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--part', type=int, default=0)
    ap.add_argument('name', nargs='?')
    a = ap.parse_args()
    {'split': split, 'run': lambda: run(a.jobs), 'verdicts': verdicts, 'read': lambda: read_view(a.name, a.part)}[a.cmd]()


if __name__ == '__main__':
    assert assessment('### Issues\nok\n### Assessment\n`ok`\nDONE') == ('ok', '')
    assert assessment('### Assessment\nissue - two voices drift\n')[0] == 'issue'
    assert chapter(8) == '00_wake' and chapter(557) == '14_ending'
    main()

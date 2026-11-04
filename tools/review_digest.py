"""review_digest.py: reads work/qa/review/c*.txt. Prints every Critical and Important finding; `--polish` appends the Minors to docs/polish.md as `- [ ] ...` lines."""
import re
import sys

import batches

OUT = batches.ROOT / 'work/qa/review'
POLISH = batches.ROOT / 'docs/polish.md'


def sections(text):
    parts = re.split(r'^#+\s*(Critical|Important|Minor|Assessment)\b.*$', text, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def findings(body):
    return [m.strip() for m in re.findall(r'^\s*(?:[-*]|\d+\.)\s+(.+)$', body or '', flags=re.M)]


minors = []
for path in sorted(OUT.glob('c[0-9][0-9].txt')):
    got = sections(path.read_text(encoding='utf-8'))
    for k in ('Critical', 'Important'):
        for f in findings(got.get(k)):
            print(f'[{path.stem} {k[0]}] {f}')
    minors += findings(got.get('Minor'))
if '--polish' in sys.argv:
    have = POLISH.read_text(encoding='utf-8') if POLISH.exists() else '# Polish pass\n\nMinor findings, ticked `[x]` when fixed or `waived: reason`.\n\n'
    POLISH.write_text(have + ''.join(f'- [ ] {m}\n' for m in minors if m not in have), encoding='utf-8', newline='\n')
    print(len(minors), 'minors in docs/polish.md')

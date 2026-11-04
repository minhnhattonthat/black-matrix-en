"""fix_lines.py: put hand-written corrections into the batch outputs. Input lines: id<TAB>English, each one written by a person or reviewer-approved, never generated.
usage: fix_lines.py FILE   prints how many lines changed and any id no batch holds; then run batches.py merge on the batches it names."""
import sys

import batches

fixes = dict(l.rstrip('\n').split('\t', 1) for l in open(sys.argv[1], encoding='utf-8') if l.strip())
names = []
for path in sorted(batches.TL.glob('b[0-9][0-9][0-9].out.tsv')):
    lines = path.read_text(encoding='utf-8').splitlines()
    changed = False
    for i, line in enumerate(lines):
        sid = line.split('\t', 1)[0]
        if sid in fixes:
            lines[i] = f'{sid}\t{fixes.pop(sid)}'
            changed = True
    if changed:
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        names.append(path.name[:4])
print(' '.join(names))
if fixes:
    sys.exit(f'no batch holds: {" ".join(fixes)}')

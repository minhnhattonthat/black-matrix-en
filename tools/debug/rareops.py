"""Recon: where the rare script ops are used (these tend to be screen launchers), from work/debug/all.txt.
usage: rareops.py [MAX_USES]   default 40 uses; prints op, count, first 14 sites as script:offset args."""
import re, sys
from collections import defaultdict

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
sid, d = None, defaultdict(list)
for ln in open('work/debug/all.txt', encoding='utf-8'):
    m = re.match(r'=== script (\d+)', ln)
    if m:
        sid = int(m.group(1))
        continue
    p = ln.split()
    if len(p) > 1:
        d[p[1]].append(f"{sid}:{p[0]}{' ' + ' '.join(p[2:])[:30] if len(p) > 2 else ''}")
for k in sorted(d):
    if len(d[k]) <= limit:
        print(k, len(d[k]), ' | '.join(d[k][:14]))

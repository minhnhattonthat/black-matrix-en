"""Recon: list sites of ops by name or arg pattern from work/debug/all.txt.
usage: oplist.py REGEX [LIMIT]   prints `script off text` for lines matching REGEX."""
import re, sys

rx = re.compile(sys.argv[1])
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 60
sid, n = None, 0
for ln in open('work/debug/all.txt', encoding='utf-8'):
    m = re.match(r'=== script (\d+)', ln)
    if m:
        sid = int(m.group(1))
    elif rx.search(ln):
        print(sid, ln.strip()[:100])
        n += 1
        if n >= limit:
            print('...')
            break

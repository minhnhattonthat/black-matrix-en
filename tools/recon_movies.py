"""Recon: dump each movie's raw sectors (Form 2, so disc.py x skips them) and sample a frame every 2 s into contact sheets.
Same-content movies on both discs are done once. usage: recon_movies.py -> work/recon/movies/<name>_NN.png"""
import hashlib, os, subprocess, sys
sys.path.insert(0, 'tools')
import disc

OUT = 'work/recon/movies'
os.makedirs(OUT, exist_ok=True)
seen = {}
for n in ('1', '2'):
    d = disc.Disc(f'rom/Black-Matrix + (Japan) (Disc {n}).bin')
    for p, lba, size, attr, form2 in d.files():
        if not p.endswith('.STR'):
            continue
        d.f.seek(lba * disc.SECTOR)
        raw = d.f.read(size // 2048 * disc.SECTOR)
        # the sector address differs per disc, so hash past each sector's 16-byte sync + address
        h = hashlib.sha1(b''.join(raw[i + 16:i + disc.SECTOR] for i in range(0, len(raw), disc.SECTOR))).hexdigest()
        name = os.path.basename(p)[:-4]
        if h in seen:
            print(f'd{n} {name} same as {seen[h]}')
            continue
        seen[h] = f'd{n}_{name}'
        path = f'{OUT}/d{n}_{name}.str'
        open(path, 'wb').write(raw)
        r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'psxstr', '-i', path, '-vf', 'fps=1/2,scale=212:-1,tile=6x5',
                            '-fps_mode', 'passthrough', f'{OUT}/d{n}_{name}_%02d.png'], capture_output=True, text=True)
        os.remove(path)  # rebuildable, and large
        print(f'd{n} {name} {size // 2048 / 150:.0f}s rc={r.returncode} {r.stderr[:200]}')

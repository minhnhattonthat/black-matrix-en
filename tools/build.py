"""build.py: both discs -> build/disc<N>/black-matrix-plus_en.bin + .cue.
Checks the dump, unpacks it once into work/orig/ (never edited), then rebuilds each disc with mkpsxiso. Changed files
go in work/tree/d<N>/ and the layout points at them, so the pristine dump stays clean.
make_image with no changes gives the original disc byte for byte: tests/test_identity.py keeps that true.
usage: build.py [--marker] [--qa=ID=TEXT]..   --marker builds every string as its marker (tools/marker.py); --qa replaces one string
for a width or stress test."""
import shutil
import subprocess
import sys
from pathlib import Path

import check_rom
import engine
import extract
import gfx
import gfx_movies
import marker

ROOT = Path(__file__).resolve().parents[1]
MK = ROOT / 'tools/mkpsxiso'
ORIG = ROOT / 'work/orig'
DISCS = (1, 2)


def rom(disc, ext='bin'):
    return ROOT / f'rom/Black-Matrix + (Japan) (Disc {disc}).{ext}'


def output(disc):
    return ROOT / f'build/disc{disc}/black-matrix-plus_en.bin'


def unpack(disc):
    """The pristine tree work/orig/d<N> and its layout. An interrupted dump leaves no layout, so it reruns."""
    xml = ORIG / f'd{disc}.xml'
    if not xml.exists():
        shutil.rmtree(ORIG / f'd{disc}', ignore_errors=True)
        ORIG.mkdir(parents=True, exist_ok=True)
        tmp = xml.with_suffix('.tmp')
        subprocess.run([MK / 'dumpsxiso.exe', '-q', '-x', ORIG / f'd{disc}', '-s', tmp, rom(disc, 'cue')], check=True)
        tmp.replace(xml)
    return xml


def make_image(disc, files, out):
    """Build one disc to out (.bin, .cue beside it). files: {base name: new bytes}; the rest come from the dump."""
    text = unpack(disc).read_text(encoding='utf-8')
    # work/tree is the real build's, read by warp.py and release.py: a test's image must not wipe it
    tree = ROOT / f'work/tree/d{disc}' if out == output(disc) else out.with_suffix('.tree')
    shutil.rmtree(tree, ignore_errors=True)
    tree.mkdir(parents=True)
    for name, data in files.items():
        (tree / name).write_bytes(data)
        tag = f'<file name="{name}" '
        assert text.count(tag) == 1, f'{name} is not on disc {disc}'
        text = text.replace(tag, f'{tag}source="{(tree / name).as_posix()}" ')
    layout = ORIG / f'd{disc}.build.xml'  # beside the dump: the layout's paths are relative to it
    layout.write_text(text, encoding='utf-8', newline='\n')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)  # a locked image (emulator running) fails here, before anything is half written
    subprocess.run([MK / 'mkpsxiso.exe', '-y', '-q', '-o', out, '-c', out.with_suffix('.cue'), layout], check=True)
    if not out.exists():
        sys.exit(f'mkpsxiso wrote no {out}')
    return out


def documents(marked=False, qa=()):
    """script/ with each string's `out` set: its marker, or its English, or the Japanese while it has none. qa: (id, text) overrides."""
    docs = extract.load()
    if marked:
        marker.build_docs(docs)
    else:
        for doc in docs.values():
            for s in doc['strings']:
                s['out'] = s['en'] or s['jp']
    over = dict(qa)
    for doc in docs.values():
        for s in doc['strings']:
            if s['id'] in over:
                s['out'] = over.pop(s['id'])
    assert not over, f'no such string: {list(over)}'
    return docs


def disc_files(disc, docs):
    """Every file a disc's text changes, with the EXE's hooks in."""
    long = engine.Long()
    files = extract.text_files(disc, 'out', engine.encode, docs, long, gfx.replacements(disc))
    exe = extract.EXE[disc]
    files[exe] = engine.apply(files[exe])
    return files


def main():
    check_rom.check()
    qa = [a[5:].split('=', 1) for a in sys.argv[1:] if a.startswith('--qa=')]
    # \n in a --qa text is the line break
    docs = documents('--marker' in sys.argv, [(k, v.replace('\\n', '\n')) for k, v in qa])
    for disc in DISCS:
        print(make_image(disc, disc_files(disc, docs) | gfx_movies.replaced(disc), output(disc)))


if __name__ == '__main__':
    main()

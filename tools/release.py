"""release.py: the release gate (references/pipeline.md, Release), stops at the first failure: build, tests, smoke, jp_left, screen tour, qa_gate on every manifest, polish.md all ticked, patches, re-apply and compare, zip.
A changed build stops at qa_gate with its changed sheets: read them (qa_review.py or by hand), write verdicts, run this again.
Debug off: the warp tool only pokes RAM from Lua (docs/re/debug-tool.md) and this script builds with no --marker or --qa, so nothing of it is on the disc.
Publishing is the owner's call: this ends at release/<zip>. The playable images stay in build/.
usage: release.py [--version 1.0] [--force]   --force overwrites that version's files"""
import argparse
import hashlib
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

import build
import check_rom
from skill import SKILL

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'release'
TEMPLATE = ROOT / 'docs/release-readme.txt'
KNOWN = ROOT / 'tests/jp_known.txt'
TOOLS = Path(SKILL) / 'scripts'
PY = [sys.executable, '-X', 'utf8']
WINDOW = str(1 << 30)  # past the larger disc: the layout moves by a few sectors, and a smaller window would miss every match behind it


def step(name, *cmd):
    print('==', name, flush=True)
    if subprocess.run([str(c) for c in cmd], cwd=ROOT).returncode:
        sys.exit(f'release stopped: {name} failed')


def hashes(path):
    """(size, CRC32, MD5, SHA-1) of a file, as text."""
    crc, md5, sha = 0, hashlib.md5(), hashlib.sha1()
    with open(path, 'rb') as f:
        while chunk := f.read(1 << 22):
            crc = zlib.crc32(chunk, crc)
            md5.update(chunk)
            sha.update(chunk)
    return str(path.stat().st_size), f'{crc:08X}', md5.hexdigest().upper(), sha.hexdigest().upper()


def unticked(text):
    return [line for line in text.splitlines() if line.startswith('- [ ]')]


def tour():
    """The screen tour, once per build: a rerun after reading its sheets keeps them, a changed disc shoots them again."""
    stamp = ROOT / 'work/qa/tour.stamp'
    built = ' '.join(hashes(build.output(disc))[3] for disc in build.DISCS)
    if stamp.exists() and stamp.read_text(encoding='utf-8') == built:
        print('== tour: current for this build', flush=True)
        return
    step('tour', *PY, ROOT / 'tools/debug/warp.py', '--all', '--jobs', '3', '--build')
    step('tour sheets', *PY, ROOT / 'tools/qa_tour.py')
    step('qa_gate init', *PY, TOOLS / 'qa_gate.py', 'init', 'work/qa/manifest.tsv', 'work/qa/tour', '--glob', '*.png')
    stamp.write_text(built, encoding='utf-8')


def gates():
    step('build', *PY, ROOT / 'tools/build.py')
    step('tests', *PY, ROOT / 'tools/check.py')
    for disc in build.DISCS:
        step(f'smoke disc {disc}', *PY, TOOLS / 'emu.py', build.output(disc).with_suffix('.cue'), '--out', f'work/qa/smoke{disc}', '--route', 'tools/routes/boot.txt', '--smoke')
    for disc in build.DISCS:
        tree = ROOT / f'work/tree/d{disc}'
        for f in sorted(p for p in tree.iterdir() if p.suffix == '.BIN' or p.name.startswith('SLPS')):
            step(f'jp_left d{disc} {f.name}', *PY, TOOLS / 'jp_left.py', f, '--sjis', '--min', '4', '--orig', ROOT / f'work/orig/d{disc}' / f.name, '--known', KNOWN)
    tour()
    for manifest in sorted((ROOT / 'work/qa').rglob('manifest.tsv')):
        step(f'qa_gate {manifest.parent.name}', *PY, TOOLS / 'qa_gate.py', 'check', manifest, manifest.parent / 'verdicts')
    left = unticked((ROOT / 'docs/polish.md').read_text(encoding='utf-8'))
    if left:
        sys.exit(f'release stopped: {len(left)} unticked lines in docs/polish.md')


def patch(disc, name):
    """Encode, then apply to the clean dump and compare with the build."""
    source, built, out = build.rom(disc), build.output(disc), OUT / name
    step(f'xdelta disc {disc}', 'xdelta3', '-e', '-f', '-9', '-S', 'djw', '-B', WINDOW, '-s', source, built, out)
    back = OUT / f'reapply{disc}.bin'
    step(f're-apply disc {disc}', 'xdelta3', '-d', '-f', '-B', WINDOW, '-s', source, out, back)
    same = hashes(back) == hashes(built)
    back.unlink()
    if not same:
        sys.exit(f'release stopped: the patched disc {disc} differs from the build')
    print('re-applied, identical', name, flush=True)


def readme(version, names):
    """The player's README, with this build's hashes."""
    fields = {'version': version}
    for disc in build.DISCS:
        for tag, values in (('base', hashes(build.rom(disc))), ('patched', hashes(build.output(disc)))):
            fields |= {f'{tag}{disc}_{k}': v for k, v in zip(('size', 'crc', 'md5', 'sha1'), values)}
            fields[f'{tag}{disc}_sha1_lower'] = values[3].lower()
        fields[f'patch{disc}'] = names[disc - 1]
    return TEMPLATE.read_text(encoding='utf-8').format(**fields)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--version', default='1.0')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    names = [f'Black-Matrix-Plus_EN_v{a.version}_Disc{disc}.xdelta' for disc in build.DISCS]
    final = OUT / f'Black-Matrix-Plus_EN_v{a.version}.zip'
    if not a.force and (final.exists() or any((OUT / n).exists() for n in names)):
        sys.exit(f'{final.name} or its patches exist: --force to overwrite')
    check_rom.check()
    gates()
    OUT.mkdir(exist_ok=True)
    for disc, name in zip(build.DISCS, names):
        patch(disc, name)
    text = readme(a.version, names)
    (OUT / 'README.txt').write_text(text, encoding='utf-8', newline='\r\n')
    with zipfile.ZipFile(final, 'w', zipfile.ZIP_STORED) as z:
        for name in names + ['README.txt']:
            z.write(OUT / name, name)
    print(final, *hashes(final))


if __name__ == '__main__':
    assert unticked('- [ ] a\n- [x] b\n') == ['- [ ] a']
    main()

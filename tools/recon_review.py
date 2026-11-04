"""Independent read of the graphics sweep: codex exec, read-only, lists every picture with Japanese on the contact sheets, per chunk.
Each cell is labelled with its picture number. Writes work/recon/review/<chunk>.txt; skips chunks already done, so a rerun resumes.
usage: recon_review.py"""
import glob, os, subprocess

OUT = 'work/recon/review'
os.makedirs(OUT, exist_ok=True)
# one line: codex.cmd goes through cmd.exe, which cuts an argument at its first newline
PROMPT = ('These contact sheets come from a Japanese PlayStation game. Each cell is one picture, labelled with its number. '
          'List every cell that shows Japanese text (kana or kanji), however small or faint, including kanji used as labels on menus, '
          'buttons, maps and signs. Ignore English, and ignore art with no writing. One line per cell: picture number, then the Japanese '
          'you can read (write ? for what you cannot read). Be thorough: a missed cell ships untranslated. Do not edit anything and do not ask '
          'questions. End with the line DONE and the number of sheets you saw. Do not guess at a cell you cannot see; say so.')
sheets = sorted(glob.glob('work/recon/sheets/s*.png')) + sorted(glob.glob('work/recon/mapped/sheet_*.png'))
for i in range(0, len(sheets), 6):
    chunk = sheets[i:i + 6]
    out = f'{OUT}/chunk{i // 6:02d}.txt'
    if os.path.exists(out):
        continue
    cmd = ['codex.cmd', 'exec', '-s', 'read-only', '--skip-git-repo-check', '--ephemeral', '-o', out]
    for s in chunk:
        cmd += ['-i', s]
    cmd += ['--', PROMPT]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
    print(out, [os.path.basename(s) for s in chunk], 'rc', r.returncode, r.stderr[-300:] if r.returncode else '', flush=True)

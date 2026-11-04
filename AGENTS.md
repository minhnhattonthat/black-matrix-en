# Black/Matrix + (PlayStation) English translation

Skill: translate-retro-game; `python tools/skill.py` prints its folder. Read its SKILL.md before ROM, text or QA work. `"$(python tools/skill.py)"` works in bash and PowerShell; never paste a `plugins/cache/<hash>` path. After a clone: `git config core.hooksPath tools/hooks`.

## Commands (run from repo root)
- Build:    `python -X utf8 tools/build.py` -> build/disc1/black-matrix-plus_en.cue, build/disc2/... (phase 3 writes it; checks the dump against `rom.sha1` first)
- Check:    `python -X utf8 tools/check.py` (tests + lint; the pre-commit hook runs this)
- Smoke:    `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/disc1/black-matrix-plus_en.cue --out work/qa/smoke --route tools/routes/boot.txt --smoke` (before a build exists: `"rom/Black-Matrix + (Japan) (Disc 1).cue"`)
- Warp:     `python -X utf8 tools/debug/warp.py NAME [NAME..]` (`--all --jobs 3`; `--build` uses built discs; scenes: `tools/debug/scenes.tsv`; never ask the user to play to a scene)
- Release:  `python -X utf8 tools/release.py` (phase 9 writes it; patch + verify; never publish without the user)
- Clean:    `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)

## Paths
- Original ROM: `rom/Black-Matrix + (Japan) (Disc 1|2).bin/.cue` (gitignored; .bin SHA-1s in `rom.sha1`, checked by `tools/check_rom.py`). Emulator: this repo's own PCSX-Redux in `tools/pcsx/` (nightly 30264.20261103.29, `fetch_emu.py pcsx`; gitignored). BIOS: `tools/bios/scph5500.bin` (`fetch_emu.py psx-bios`). Savestates: `work/states/`.
- Text: `script/` (format set in phase 4). Tables: `tbl/`. Glossary: `glossary.md`. RE notes index: `docs/re/README.md`. Fonts and their licences: `docs/fonts.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- Subagents: dispatch the `.claude/agents/` types (translator, reviewer, visual-qa, playtester), never general-purpose: their short tool list cuts each agent's start-up context from ~43k to ~9k tokens.
- Emulator runs are headless only: `emu.py` / `play.py` drive PCSX-Redux with `-no-ui`. Never open its GUI window (D8).
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Two discs: every build, test and release step covers both. Japanese game: confirm is circle, cancel is cross (`--mash-key circle`).

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.

# Black/Matrix + English translation

Unofficial English fan translation of **Black/Matrix +** (PlayStation, Flight-Plan / NEC Interchannel): the source text
and tools that build the patch. Work in progress: see `docs/status.md`.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| <Dialogue / story> | <Translated> |
| <Menus, items, skills, system messages> | <Translated> |
| <Title screen, logos, graphics with text> | <Translated / Left in Japanese> |
| <Name entry> | <Translated / Japanese kana only> |
| <Songs, voiced lines, credits roll> | <Left in Japanese> |

Known issues: <none known / see [Issues](../../issues)>.

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `tools/` | Python build chain: extract, insert, lint, release. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |
| `.claude/agents/` | Subagent types (translator, reviewer, visual QA, playtester) with only the tools each needs. |

## Build your own patched ROM

Needs Python 3.12+ and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/black-matrix-en
cd black-matrix-en
git config core.hooksPath tools/hooks
# copy your dump to: rom/Black-Matrix + (Japan) (Disc 1).bin  (511863408 bytes)
#                    rom/Black-Matrix + (Japan) (Disc 2).bin  (686497056 bytes)
#   (SHA-1s in rom.sha1; the build refuses any other dump)
python -X utf8 tools/build.py                          # -> build/disc1/, build/disc2/
python -X utf8 tools/check.py                          # tests + text lint
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Flight-Plan / NEC Interchannel's and is
included only so the translation can be checked against it. Black/Matrix + is (c) Flight-Plan / NEC Interchannel; this
project is not affiliated with them.
Do not share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.

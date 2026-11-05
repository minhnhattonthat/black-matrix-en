# Black/Matrix + English translation

Unofficial English fan translation of **Black/Matrix +** (PlayStation, Flight-Plan / NEC Interchannel): the source text
and tools that build the patch. Current state: `docs/status.md`.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue and narration, every route | Translated |
| Menus, items, skills, help, system messages | Translated |
| Chapter and battle cards, manuals, master select | Translated |
| Movies | Every spoken line subtitled in English (`PROLOGUE`, `0101`, `DEMO01`, `DEMO02`); the other movies have no speech |
| Name entry | Translated: Latin page first, kana pages kept |
| Staff roll | Translated; some readings are guesses, listed in `docs/decisions.md` D17 |
| Voices and songs | Left in Japanese |
| Kanji beside the English words in the bonus movie `DEMO02` | Left in Japanese (D16) |

Tested headless in PCSX-Redux with the SCPH-5500 BIOS: every scene reached by the debug warps, not a full playthrough.
Known limits: see `docs/status.md`, Not verified. Bugs: [Issues](../../issues).

## Base discs (Redump)

| Disc | Size | CRC32 / MD5 / SHA-1 |
|---|---|---|
| [Black-Matrix + (Japan) (Disc 1)](http://redump.org/discs/quicksearch/aae3c19ff5c68a686d1f76c2360e43d4f20ffd88/) | 511863408 | 32A0EBEC / BAFD29A79E950B66C56D9FB2FEB36C1A / AAE3C19FF5C68A686D1F76C2360E43D4F20FFD88 |
| [Black-Matrix + (Japan) (Disc 2)](http://redump.org/discs/quicksearch/d6a6b3f7eb39f7e36ab5361fae3e3402351c636e/) | 686497056 | CC7D430A / 1C10AFD30766BC799EEE5795F4C83606 / D6A6B3F7EB39F7E36AB5361FAE3E3402351C636E |

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

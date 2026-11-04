# Disc layout and containers

Dumps: `rom.sha1`. Serial SLPS-02962 (Disc 1), SLPS-02963 (Disc 2). The game's in-game title is
"ブラックマトリクス・クロス" (Black/Matrix Cross); the cover logo reads BLACK/MATRIX with a cross, hence "+".
The volume ID is empty. Image is one MODE2/2352 track. `tools/disc.py list BIN` prints the file table.

| | Disc 1 | Disc 2 |
|---|---|---|
| Sectors used | 217,629 | 291,878 |
| Free to a 74-min disc (333,000) | ~115,000 sectors (~230 MB) | ~41,000 sectors (~82 MB) |
| EXE | `SLPS_029.62` | `SLPS_029.63`, byte-identical to Disc 1's (**verified** with `cmp`) |

Files: `2ND.BIN 3RD.BIN 4TH.BIN 5TH.BIN` (overlays), `BATTLE.DAT EVENT.DAT SCENARIO.DAT SOUND.DAT SYSTEM.DAT`,
`PCM*.XA` (voice/music Form 2), `MOVIE/*.STR` (Form 2).

**verified** (`tools/recon_dat.py`): 2ND-5TH, BATTLE, SCENARIO, SOUND, SYSTEM are byte-identical across discs. Only
`EVENT.DAT`, `SYSTEM.CNF`, the EXE's name and the movies/XA differ. Disc 1 EVENT has 247 entries, Disc 2 has 310.

The EXE holds every file's name (`\SYSTEM.DAT;1`, `\MOVIE\0101.STR;1`, offsets 0xBDC-0xD00 and 0x177C-0x19D8) and finds
files by name, so any file can grow and move. **verified** by `tools/debug/moved_check.py`, which grows `2ND.BIN` by 5
sectors and compares CD reads (`tools/lua/cdlog.lua`) with the original: 11 scenes on both discs, no read left at an old LBA.
Reads covered 2ND, 3RD, 4TH, all five DATs, PCMSE, PCM12, OPENING, PROLOGUE and 1207; the other files share the name
tables. Boot reads the directory (LBA 16-22), then each DAT's header. No LBA of a DAT, XA or movie appears as a word in the EXE.

## Rebuild (`tools/build.py`)

`dumpsxiso` + `mkpsxiso` 2.30 give both discs back byte for byte, and `tests/test_identity.py` keeps that true on every
commit. The layout keeps the disc's order and dates, plus the 150 dummy sectors at the end. A changed file only touches its
own sectors; a grown one shifts later files and the MOVIE directory record (LBA 141,526 on Disc 1) and nothing else (same test).

## .DAT archive (`tools/dat.py`)

`u32 count, u32 11, count × (u16 sector offset, u16 sector count)`, 2048-byte sectors, padded to whole sectors.
**verified** by `recon_dat.py`: every non-empty entry chains and the last one ends at the file's size on all five DATs of
both discs. Empty entries (size 0) store the running offset, so `dat.pack` derives them. **verified**: `dat.pack(dat.unpack(x)) == x` on all ten DATs.

| DAT | Disc 1 entries (non-empty) | Disc 2 |
|---|---|---|
| SYSTEM | 206 (206) | same |
| SCENARIO | 562 (524) | same |
| BATTLE | 340 (327) | same |
| EVENT | 247 (231) | 310 (177) |
| SOUND | 32 (23) | same |

u16 limits: an archive can hold 0xFFFF sectors (~134 MB), far more than needed.

## Nested containers (`tools/pak.py`)

Same shape with `shift 4` (16-byte units): `u32 count, u32 4, count × (u16 off, u16 size)`. They nest. **verified**: the
walker's chain check accepts them and produces leaves that start with known magics (below). **verified**: `pak.rebuild`
repacks all 1,525 nested containers byte for byte from one rule: header padded to the next unit, entries chained, empty
entries at the running offset, zero padding up to the parent's unit. So a leaf can change size. A table field past u16
(about 1 MiB for `shift 4`) raises. Whether the game's load buffers accept a bigger container is a separate limit (below).

## Leaf types (`work/recon/leaves_d*.tsv`, `tools/recon_text.py`)

| Head | Count (Disc 1) | What |
|---|---|---|
| `PSI22.00` | 524 | Scenario script, [script-format.md](script-format.md) |
| `00/01/11/91 000000 10000000` + valid image head | ~7,700 | Picture blob, [graphics.md](graphics.md) |
| `00/01 000000 10000000` + other shape | ~1,500 | Sprite cell/animation tables (no image head; words like `0x70C0` are GPU tpage/clut pairs) |
| `SCP\0`, `MHA `, `MHD2` | 170 / 160 / 114 | **guess** model/motion data; no Japanese runs found in them |
| `pBAV`, `pQES` | 64 / 46 | Sound (PSX VAB, SEQ) |
| `Armor Item Data`, `Status Data`, `Weapon...`, `Magic...`, `Move...`, `Shop...`, `HELP`, `BATTLE ENEMY PARAM`, `ATTR`, `LvUp`, `SWeapon`, `BIT\0` | few | Game data tables, [text.md](text.md) |

## RAM map (SLPS_029.62, **verified** by the xrefs named)

| Address | What | Evidence |
|---|---|---|
| 0x80010000-0x8007F000 | EXE text+data (0x800 header skipped in the file) | PS-X header |
| 0x8007E820 | `$gp` | `addiu $gp` at 0x8006BC7C |
| 0x80096 3B8 | Macro table: 16 words per code 0x20-0x2F | 0x80028460 |
| 0x800965B8 | Glyph cache state, 256 entries | 0x80029E38 |
| 0x800B5538 | Text buffer the script ops copy into, `u16 count, words` | 0x800504DC |
| 0x800EB000 | `2ND.BIN` load address for the 0b/04.. handlers (battle) | `tools/recon_sub0b.py`: 15 of 19 entries are prologues |
| 0x8019B000 | Scenario script buffer (`+0x10` = code base) | 0x8004FC18 |
| 0x801A2800 | Font block start (SYSTEM/0 part 0; glyphs at 0x801A281C) | 0x80013214, 0x8002A8E0 |
| 0x801FFF00 | Stack top | `SYSTEM.CNF` |

Overlay loads, **verified** by `tools/recon_prefix.py` ([text.md](text.md)): 2ND, 4TH and 5TH at 0x800EB000, 3RD at 0x80110800.

## Free space

- **Disc:** the rows above. Space isn't the limit on either disc unless movies get bigger.
- **Script buffer: the hard limit.** The font starts 0x780C (30,732) bytes after the script code base and the largest
  scenario, SCENARIO/226, is 27,548 bytes: only **3,184 bytes (11.5%)** to spare. Decide in phase 5 how to fit English:
  half-width pairs keep one word per two letters, which is about Japanese size; or move the font.
- **RAM candidates, not proven free** (`tools/recon_free.py`: ranges one value in all 6 dumps of `work/qa/ng3`, a run from cold boot through the
  prologue, frames 20,000-40,000, no battle, overlay or menu loaded): 0x801D6000-0x801FD000 (0x27000, the best, right below the stack), 0x801CD800-0x801D5800 (0x8000),
  0x8019BF00-0x801A2800 (0x6900, script buffer tail: scripts use it, not free), 0x800BB100-0x800D0000 (0x14F00), 0x800D8100-0x800EB000 (0x12F00, just under the overlay area).
  Battle and menu screens aren't covered, so repeat the dump there and trap-test before use (phase 5, per the skill).
- **Overlay tails:** 2ND ends 0x80131B4C, 4TH 0x8010042A, 5TH 0x800F1A28, 3RD 0x8011BF70. Never write into a tail without checking it's unused.
- **EXE zero runs, candidates:** RAM 0x80073AE8 (0x71A), 0x8007CB19 (0x106B), 0x8007DEA4 (0x421), 0x8007E89F (0x761). The last two sit next to `$gp`; zero runs near it are likely live variables.

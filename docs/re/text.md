# Text outside the scripts

Encoding everywhere checked: **little-endian Shift-JIS** words, except the EXE's name-entry data, which is big-endian (see
below). Found by `tools/recon_text.py` (both byte orders, strict character filter over every leaf) and grouped by content
in `tools/recon_textmap.py` → `work/recon/textmap.tsv` (one group per distinct leaf: offset, order, text). Runs shorter
than 3 characters and kanji-only runs are not listed by that filter: phase 4 extracts by record layout, not by scan.

## Data tables (`STATUS` = layout not read yet; phase 4 reads each record format)

| Leaf | Copies | Holds | Sample |
|---|---|---|---|
| `SYSTEM/5.0`, `.1`, `.2`, `.3` | also `SYSTEM/14.0.0-3` | Item/weapon, skills, armor, accessory names and descriptions (360+253+150+71 runs) | ナイフ, ハードレザー, リリム |
| `SYSTEM/6` | - | Shop/help text; starts `Armor Item Data` | ○ボタンを押すとアイテムの購入… |
| `SYSTEM/10`, `11`, `12` | - | `Status Data`: unit names, 58 rows, 0x50 bytes per row (0x20, 0x70, 0xC0…), 12-byte name field padded with `　` | アベル, レブロブス, ピリポ |
| `SYSTEM/13.1`, `.3`, `BATTLE/0.9`, `EVENT/80.3` (+7 copies) | | Help pages, `HELP` head | 所持しているアイテムの閲覧と… |
| `SYSTEM/15.4` | | Level-up screen | 今回の戦闘で得た各ポイントです |
| `BATTLE/5.0`, `6.0`, `7.0` | | `BATTLE ENEMY PARAM`, names of enemies by chapter | カロン, ウリエル, パイモン |

Each table carries its name in ASCII at the head. Padded fields use `　` (0x8140): fixed widths are in the tables.

## EXE and overlays

| File | Load | Strong runs | Holds |
|---|---|---|---|
| `SLPS_029.62` | 0x80010000 (header) | 166 | Config help, memory-card messages (0x63xxx), name-entry grid (0x19DC, **big-endian**), 7 default names at 0x1C14 (`ゼロ＿＿＿＿`, 12 bytes each, big-endian, padded with `＿`), EXE data |
| `3RD.BIN` | 0x80110800 | 100 | Shops: greetings (0xAAE6..) per shopkeeper, buy/sell |
| `5TH.BIN` | 0x800EB000 | 18 | Level-up |
| `2ND.BIN` | 0x800EB000 | 12 | Battle menus (0x437xx-0x44xxx) |
| `4TH.BIN` | 0x800EB000 | 3 | Save/load/config (0x12567) |

**Load addresses verified** by two independent votes (`tools/recon_prefix.py`): pointers to count words, and `jal` targets landing on
function prologues; each load wins by a wide margin (2ND 401 of 603 prologues, 3RD 31 of 48, 4TH 137 of 197, 5TH 18 of 30). 2ND, 4TH and 5TH
share 0x800EB000, so only one is in RAM at a time.

### Pointer format

**Verified** (`tools/recon_ptr.py` → `work/recon/ptr_<file>.tsv`): a string is `u16 count, count × u16 words`, the same shape as script text, and
code or a table holds the address of the **count word**. Reached that way, or by a table entry at the string itself:

| File | Runs | Via count word | Direct | No pointer found |
|---|---|---|---|---|
| EXE | 213 | 60 | 9 | 144 |
| 3RD | 107 | 38 | 0 | 69 |
| 2ND | 20 | 7 | 0 | 13 |
| 5TH | 19 | 7 | 0 | 12 |
| 4TH | 6 | 2 | 0 | 4 |

The rest, not resolved here, are the three shapes seen in those lists: fixed-width cells in one run (`買　う売　る`, `は　いいいえ`), so the run is
reached at its head or by base + index; a table of strings walked by count (shop greetings, 0xAAE6..: **guess**); and false hits, where a
run is really data (`５ＤＳｂｑあけだはまろ` at EXE 0x6DD1C). Phase 4 decides each one, with the caution from `platform-ps1.md` that literal
copies use `$gp`-relative loads. Overlay strings sit among code, so they can only grow where the overlay has room or where pointers are remapped.

## Pictures that are text

See [graphics.md](graphics.md).

## Compression

**Nothing on disc is compressed, as far as tested.** Pictures, text and scripts all decode directly from the leaves as stored (**verified** by
`recon_psi.py` and the sweep). Non-picture leaves have byte entropy well below packed data (`tools/recon_compress.py`): only one tops 7.3 bits, `SYSTEM/34`
(4 KB: `u16 951`, then index + value u16 pairs, a table).

The EXE does hold Black/Matrix 00's LZ scheme: decoder 0x800248A0 (skips 3 bytes, literals XORed with the inverted position, shared length nibbles), encoder
0x800246C0. Both are called from one job routine at 0x800249B8 that picks a direction from a struct field; no overlay calls them. Trial decoding every DAT entry and
leaf (`tools/recon_lz.py`, a real stream's length word must fit and it must end near the leaf's end) gives **0 hits**. **Guess**: saves, since only a save needs both directions.
Not ruled out: a stream starting inside a leaf. Phase 3's identity build doesn't depend on this, and a text edit that hits packed data would show as text that didn't change.

## Movies

`MOVIE/*.STR` (see graphics survey): `PROLOGUE` subtitles, `STAFF` credits and two demo ads are burned in. Replacing them needs jPSXdec.

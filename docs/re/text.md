# Text outside the scripts

Encoding everywhere checked: **little-endian Shift-JIS** words, except the EXE's name-entry data, which is big-endian (see
below). Found by `tools/recon_text.py` (both byte orders, strict character filter over every leaf) and grouped by content
in `tools/recon_textmap.py` → `work/recon/textmap.tsv` (one group per distinct leaf: offset, order, text).

## Extraction (`tools/extract.py` → `script/`)

12,132 strings: 9,066 script, 2,883 table, 183 code. **Verified** by `tests/test_extract.py` on every commit:
- **Roundtrip:** `extract.text_files(disc, 'jp')` rebuilds the EXE, the four overlays and the four text DATs of each disc from
  `script/` through the same code the English will use, byte for byte. `script/` matches a fresh extraction.
- **Coverage:** every text operand of every script is extracted. Every counted string that code or data points at is extracted. Every
  Japanese run the scan finds outside the extracted text, over every leaf and file of both discs except pictures, models and sound, is in
  `tests/text_noise.tsv`: 359 hits, reviewed by eye as unreadable, none a word (the longest is the EXE's `５ＤＳｂｑあけだはまろ` table, 8 hits, the rest in
  `EVENT/8x.2` and similar binaries). An earlier counted-string sweep (`psi.walk`, kanji-only and short strings too) of every non-picture leaf found text only in the tables below.
- **Not proven:** glyph codes built as immediates in code. The marker build shows those as the Japanese that stays.

## Data tables

`u16 count, words` fields in fixed rows, the layouts in `extract.TABLES`, proven by the roundtrip. A name field's count is its length and the rest
is `　` (0x8140), so a name fits `max` words. Description and help fields always count their full capacity and hold rows of a fixed width (`cell`).
`script/` shows those rows split by `\n`, without their padding.

| Leaf | Copies | Rows × bytes | Fields (words) |
|---|---|---|---|
| `SYSTEM/5.0` Weapon | `14.0.0` | 145 × 0x8E | name 8, desc 38 (2 rows of 19) |
| `SYSTEM/5.1` SWeapon (**guess**: summons) | `14.0.1` | 57 × 0x88 | name 7, desc 19, effect 38 (2 × 19) |
| `SYSTEM/5.2` Armor | `14.0.2` | 112 × 0x6E | name 8, desc 38 (2 × 19) |
| `SYSTEM/5.3` Magic | `14.0.3` | 32 × 0x4E | name 8 at +2, desc 28 |
| `SYSTEM/10`, `11`, `12` Status | - | 0x50, head 0x10 | name 6 at +0xE |
| `BATTLE/5.0`, `6.0`, `7.0` Enemies | - | 0x50, head 0x40 | name 6 at +0xE |
| `SYSTEM/6`, `13.3`, `15.4`, `BATTLE/0.9`, `EVENT/80.3` (`81-86.3`, and on Disc 2) Help | - | 0x74, head 0x10 | text 57 (3 × 19) |

Each table carries its name in ASCII at the head (`SYSTEM/6` wrongly says `Armor Item Data`). Help sentences repeat between the help tables; the
enemy names repeat between the three enemy tables. The tables are separate on disc, so `script/` keeps each.

## EXE and overlays

String areas are in `extract.CODE`, by RAM address. `max` for these is the original length: they sit among other strings and code, so growing means moving them
and remapping the pointer (phase 5).

| File | Load | Strings | Holds |
|---|---|---|---|
| `SLPS_029.62` | 0x80010000 (header) | 99 | Config help, memory-card messages, unit menu. **Big-endian, no count:** name-entry grid (0x800111DC, 270 words: three pages of 90. Hiragana, katakana, then Latin in the original; the page number just indexes them, so the English build stores Latin first), `かなカナ英字戻る終了` (0x800113FC), 7 default names (0x80011414, every 16 bytes, 6 words padded with `＿`) |
| `3RD.BIN` | 0x80110800 | 56 | Shops: greetings by shopkeeper, buy/sell, camp menu, blood rituals |
| `2ND.BIN` | 0x800EB000 | 19 | Battle menus, status names |
| `5TH.BIN` | 0x800EB000 | 7 | Level-up |
| `4TH.BIN` | 0x800EB000 | 2 | Camp menu (a copy of the `3RD` rows, last cell differs) |

Macro `{0023}` appears in `を買います`-type strings (**guess**: the item name). The save file name is ASCII (`BISLPS-02962BMCROSS`, EXE file offsets 0x1D4C and 0x26CC) and stays as it is, and beside the first copy `ＦＩＬＥ` is fullwidth, big-endian and already English. Neither is in `script/`. How the card's title is built isn't read yet: check the load and save screens in phase 8.

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

Those counts are the raw scan's. By counted string (`tools/recon_counted.py`), the ones with no pointer of their own are the shapes seen in those lists: fixed-width
cells in one string (`買　う売　る`, `は　いいいえ`), so code indexes into it; and strings walked in sequence from a neighbour (shop greetings at 3RD 0xAAE4, 5 with no pointer: **guess**). The false hits are data (`５ＤＳｂｑあけだはまろ` at EXE 0x6DD1C). Overlay strings sit among code, so they can only grow where the overlay has room or where pointers are remapped, with the caution from `platform-ps1.md` that literal copies use `$gp`-relative loads.

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

# Text windows and limits (the width gate)

A window is C cells of 14 px by R rows. In English each cell holds two letters (`asm/halfwidth.asm`, `font.md`). Limits below are enforced by `tools/fit.py` through `tools/batches.py check`.

**Verified** on the stress build (`tools/stress_build.py`, scene `dlg_portrait`, sheets `work/qa/p5/dp.png`, `dp2.png`, `dp2_2.png`) and from the marker shots of the camp, home and config scenes (`work/qa/p5/w1.png`, `w2.png`), read by eye at full size.

| Variant | Window | Letters | How measured |
|---|---|---|---|
| Portrait dialogue (`16 (#0)`) | 17×3 | 34 a row, 32 on a page's last row | filled to the limit: `'1'*34`, `'2'*34`, `'3'*32` |
| No-portrait dialogue, diary (`16 (#1)`, `(#2)`) | 19×3 | 38, last 36 | `home_diary`, `'1'*38`.. |
| Short window (`16 (#3)`) | 19×2 | 38, last 36 | config help box |
| Choice (`1d`) | 15 wide | 30 (15 words; the rest are dropped, `script-format.md`) | `home_confirm` marker |
| Script menu (`20`) | 19 | 38 | title of a choice list |
| Unit, enemy names | 6 words | 12 | status screen `[927]The qui` |
| Weapon, armor names | 8 words | 16 | item list 8×9 |
| Summon names | 7 words | 14 | skill list 7×10 |
| Magic names | field 8 words, list 7 cells | 14 (**guess** from the list window; magic list not seen with markers) | |
| Help, description rows | 19 | 38, up to the field's rows | |
| Battle commands | 3 cells | 6 | `2nd:8012ed48` |
| Camp menu | 5 cells | 10 | `camp_system` |
| Name-entry names | 6 words | as typed | `name_entry` |

## Paging (verified)
A text with more rows than its window **pages by itself**: it waits at the arrow, clears, and goes on, with or without `0x0010` in it (`dp2.png`: nine rows in three pages; a text with no break in two). So rows aren't a hard limit. A full row wraps by itself, and a `0x0010` right after one leaves a blank row, so `extract.box_words` drops it. The wrap in `fit.py` works at spaces and keeps a page's last row clear of the arrow. The checker allows two pages and rejects a stub second page.

## Glyphs (verified)
Torture line (every ASCII glyph, `dp.png`) reads in the portrait box, no missing glyph, nothing touching. `7×14` is 7 px wide in a 7 px half cell: no shadow is drawn in this font, so nothing overlaps.

## Sizes
- **Script buffer:** `extract.SCRIPT_MAX` (0x7770): English at about 2.6-3 times the Japanese letters takes 1.3-1.5 times its text bytes. The worst script, 226, has 5,546 bytes of text and 3,028 to spare, so about 1.5x. `extract.script_apply` fails the build past that.
- **Long strings:** EXE and overlay strings have no room to grow, so one too long becomes a control word 0x30-0xFF (`engine.Long`), its text in the top 10 KB of the font. `Status (long)`, `Long string replac..` in `w1.png` are that path, in game. The font loses its last 365 glyphs, all kanji.
- **Run-time names:** a default name's cell spacing drops from 18 to 14 px (0x8002CC1C), so pairs read as a word: `Abel ____` in the name row. Letters typed on the grid are squeezed to pairs by `hw_setmacro`.

## Non-text strings found by the marker build
`slps:800111dc` (the name-entry grid, `kind: grid`), `slps:800113fc` (its menu), `slps:80011414..` (default names): real text, not marked. They take hand-placed English in phase 7, with the Latin page first if it can go there.

## Not covered
- **Marker tour on the current build:** 45 of 168 scenes (the tour was stopped by the system for low memory). Earlier marker build: the 43 menu, home and system scenes (`work/qa/p5/tour1.log`, sheets `a*.png`, `bui*.png`, `m_*.png`). So battle windows after `battle_157_b16` and the story scenes past chapter 12's card aren't seen with markers on this build.
- `LV 1 縦` on the status screen, the 武器/鎧/アクセサリ/消耗品 labels and the Japanese buttons in `w1.png` didn't take markers: expected to be pictures (`graphics.md`), to confirm in phase 8.

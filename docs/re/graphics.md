# Graphics text survey

Static sweep of every picture on both discs (`tools/recon_gfx.py` → `tools/recon_sheets.py`, mapped pictures → `tools/recon_mapped.py`): 1,437
distinct pictures (13,153 instances), read as labelled contact sheets. Picture numbers `#n` are from `work/recon/gfx_index.tsv`, which lists
each picture's paths; regenerate with those tools. Skips are printed by `recon_gfx.py`: everything it skips is scripts, sound, sprite cell
tables, model data or game data tables, not pictures. Sheets show one palette only, so a mostly-dark picture can hide faint text: phase 8
checks each row in a zoomed cold-boot shot. Second read of all 47 sheets: see "Independent read" at the end.

## Picture format

    u32 kind, u32 0x10, u32 pixel_off, u32 extra_off
    @0x10 u16 clut_w, u16 clut_h, colours
    @pixel_off u16 width_in_16bit_words, u16 height, pixels (low nibble first at 4 bits)

Kind bit 0 = 8 bits per pixel, else 4. Bit 0x10 = a cell map at `extra_off`: `u16 cols, u16 rows`, then u16 cell words, for screens built from
a tile sheet (20 × 15 cells of 16 px). Cell word = `0x8000 | page<<10 | y<<6 | x<<1`, x and y in 16-px cells, one page = 128 px at 8 bits.
**Verified**: `recon_mapped.py` draws all 322 mapped pictures as whole, legible screens. Repeats in the map reuse a cell, so **redrawn text
may need more distinct cells than the sheet has spare**: count them per picture in phase 5. Bit 0x80 seen only with 0x11. Same layout as Black/Matrix 00's `gfx.py` for kinds 0 and 1.

## Japanese pictures (status: all to redraw per D5)

Menus and system

| # | Where | Size | Holds |
|---|---|---|---|
| 223 | BATTLE/0.1 | 256×256 4bpp | Battle UI: ガード, 通常, 潜在, 待機, 配置, ステータス, command labels |
| 0 | SYSTEM/0.2 | 128×224 4bpp | Window frames plus small labels |
| 6 | SYSTEM/3.1 | 128×256 4bpp | SAVE/LOAD head in English, Japanese file-slot prompts: `新規作成`, `ファイルが壊れています`, `容量がありません` |
| 7 | SYSTEM/4.1 | 256×144 4bpp | Config: `MESSAGE`, `VOLUME`, `VOICE`, `SE`, `VIBRATE`, `HELP`, `EXIT` already English, but the values and help (`ヘルプ表示項目設定`, ショップ, 状態, アイテム...) are Japanese |
| 10 | SYSTEM/5.5, /14.0.5 | 128×176 4bpp | Menu labels: レベルアップ, 買う 売る, 装備, 自動振分, 魔法, 剣血, 不参加 ... |
| 60 | SYSTEM/15.1 | 256×256 4bpp | Battle report: `コマンド時間`, `ターン数` next to English BATTLE REPORT, BONUS, RANK |
| 65 | SYSTEM/17.1 | 256×256 4bpp | Sound test track list: 闘, 鎮魂歌, ゾンビスプレー, 戦闘, 近親者アメーバー ... |
| 66 | SYSTEM/20.0 | 248×248 4bpp | Master confirm: `このご主人様でよろしいですか？`, はい, いいえ, `←→キーで選択`, `○ボタンで決定` |
| 67 | SYSTEM/21 | 320×480 8bpp | Master select background with `あなたのご主人様を選んでください` |
| 75 | SYSTEM/29.1 | 256×256 4bpp | Disc swap: `DISC 1を入れてください`, `DISC 2を...`, `DISCをチェックしています`, `DISCがちがいます！` |

| 223, 6 (more) | same as above | #223 also `ミス！ 石化 どく マヒ`; #6 also `メモリカード`, `差込口`, `章`, `最終`, `データが`, `空き` |
| 739 | EVENT/0-5.0 | Small `メニュー` beside the English stats and season names |
| 740 | EVENT/0-5.1 | Home activity menu, large: 釣り, 狩り, まき割り, 畑仕事, 料理, 洗濯, 掃除, 食事, 話す, 中へ, 外へ, 寝る, 読書, 街へ, 散歩 |
| 811 | EVENT/62-64.2 | Mini-game counter `匹` |
| 816 | EVENT/65.3 | Mouse count: `数値選択`, `決定` |
| 818 | EVENT/66-69.2 | Laundry: `ガンコなよごれ服`, `油よごれ服`, `泥よごれ服` |

Cards and story screens (full-screen, mapped, over art: hardest redraws)

| # | Where | Holds |
|---|---|---|
| 238-354 | BATTLE/11-65 `.0` (**50 cards**, disc-identical) | Torn-paper battle title cards in cut-up lettering with blood: `第2章-1 脱出 / 勝利条件 / 敵の全撃退` and so on through `第12章-1`, `自由戦闘 <town>にて`, `最終戦闘 新世紀`. Numbers: 238, 240, 243, 246, 249, 252, 255, 258, 261, 264, 267-270, 273, 274, 277, 280, 281, 284, 285, 287, 290, 292, 295, 298, 300, 303, 305, 306, 309, 312, 315, 318-320, 323-325, 327, 330, 331, 334, 337, 340, 343, 345, 348, 351, 354. Each needs a title and a win condition. Few distinct win lines: build from parts |
| 828-835 | EVENT/71-78.0 (Disc 1) | Mini-game manuals: 釣り, 狩り, まき割り, 料理, もぐら叩き, ネズミ数え, 洗濯, 食事, each `操作説明`, 3-6 lines of body, `スタートボタンでゲーム開始!` |
| 853, 854, 856 | EVENT/106.0, 107.0, 114.0 | Time cards: 次の日, 三日後, 一週間後 |
| 858-863, 1144-1149 | EVENT/130-135.0 (D1), 136-141.0 (D2) | Chapter title cards, 第一章 パンドラの箱庭 ... 最終章 そして天上へ…; vertical `ブラックマトリクスクロス` spine |
| 864-869, 1150-1154 | EVENT/142-147.0 (D1), 148-152.0 (D2) | Chapter end cards: `第一章 パンドラの箱庭 / 完 / To be continued...` |
| 1430, 1431 | D2 EVENT/299, 300.0 | Endings: `そして彼女は第2のイブになった`, `そして彼は第2のアダムになった`, with `GAME END` art |
| 1434 | D2 EVENT/303.0 | Ending: `そしてあなたは新たなるサタンとなった` |

## Movies (`tools/recon_movies.py`: one frame per 2 s, all 29 distinct movies read; `0101` and `OPENING` are on both discs)

Video-burned text needs re-encoding via jPSXdec (`platform-ps1.md`).

| Movie | Holds |
|---|---|
| `PROLOGUE.STR` (D1) | Vertical subtitles over a pentagram (82 s) plus the two logo cards `NECインターチャネル株式会社`, `株式会社フライト・プラン`; English end card kept |
| `STAFF.STR` (D2) | Staff roll, 180 s, every role and name in Japanese, on a moving background. **D3 asks for English credits** |
| `DEMO02.STR` (D2) | Bilingual words already (`Love 愛`, `Fortune 邂逅`, `Despair 絶望` ...), an end ad `プレイステーション用ソフト ブラック／マトリクス クロス 絶賛発売中!!` |
| `DEMO01.STR` (D2) | English credits, same end ad |

No Japanese seen in the other 25 (`0101`-`1207`; `OPENING` has only English). Phase 8 re-read all 25 at one frame per 1.3 s, none found.

Done in phase 8, `tools/gfx_movies.py` + `gfx/movies.tsv`: `PROLOGUE` (also a typed card on white at frames 5-194, missed above), `STAFF`, both ad cards. jPSXdec whole-frame `<replace size-limit="original non-zero">`: a partial replace keeps the frame's quantiser and lettering goes grey and blocky. `DEMO02`'s words keep their Japanese beside the English: the kanji sit on moving art and are decoration of a bonus movie (D16).

Speech (`tools/fmv_asr.py`, whisper large-v3 plus Silero spans): `PROLOGUE` (its burned-in text is the narration), `0101` (a priest's sermon, a child objecting), `DEMO01` (the same sermon 120 frames later), `DEMO02` (trailer lines, from the script: `s130`, `s166`, `s183`, `s467`, `s489`, `s501`, `s502`...). The other 25 distinct movies have none: whisper gives only its silence filler (`ご視聴ありがとうございました`, high no-speech score), also on each short Silero span cut out alone. An `initial_prompt` gets read back on silent stretches, so there is none. Movies run at 15 fps.

Under music (`tools/fmv_vocals.py`, Demucs; `fmv_asr.py --stems`): same result on the vocal tracks, no new line anywhere, and `DEMO02` reads cleaner. Measured with `0101`'s voice mixed into music-only movies: sentences read at 0 dB (9 of 9), mostly at -6, a third at -12. Silero's sensitivity is not measured: on short `STAFF` clips it fires at the same place at every level, so it also triggers on music there. **A word of about a second is not readable under music even at 0 dB**, so whisper can't rule those out. Silero spans whisper can't read in the movies listed as speechless: `tools/fmv_listen.py` cuts them for an ear (`work/movies/listen/`). They are short and mostly unvoiced, and the shots checked (`0103`, `0601`, `1101`, `1204`) show crows, chains, rock and lava, no people. The long steady-pitch stretches (`PROLOGUE` 1093-1180, `DEMO01` 2709-3000, `1201`, `1206`, `OPENING`) give no words. The owner listened to all 17: noise (D20).

`DEMO02` speakers: no character is on screen during any line (a frame per line read), so these come from the line's portrait in `script/scn` (`tools/faces.json`), not the picture. Frames: 201 Phillipo `s130`; 256 rough Inquisitor `s70`; 290 Rupirupi, 337 Johannes `s166`; 391 Gaius `s300`; 428 Rupirupi `s183`; 468, 530 Johannes `s467`; 562, 942 Leburobus `s204`; 647, 1372 Luca `s489`; 763 the Pope `s501`; 865 Phillipo `s188`; 974 Gaius `s301`; 1035 Prague `s128`; 1066 Rupirupi `s502`; 1104 Gaius (`やめろ`, likely `s502:02a32`) then Rupirupi `s502`; 1289 Marco `s446`; 1333 Leburobus `s502`; 1508 Phillipo `s269`; 1633 Rupirupi `s188`. Guesses: 616 `自由` Prague (`s128:03dda`, one word, many speakers), 1137 `ルピルピ` Gaius (`s502:02a0e`). Unknown, not in the script: 694 `よりによって...`, 908 `な、なぜなんですか`. Pitch doesn't separate them: the same voice ranges 120-285 Hz here.

Spoken lines are rows with box `V` in `gfx/movies.tsv`, burned along the bottom, or at the top (align `T`) where a `DEMO02` word sits in a bottom corner. They have no `size-limit`: a black frame's data is under 1 KB, and at that cap jPSXdec dies at quantiser 63 ("Can't decode a frame we just encoded"). Uncapped, the frame fills its own sectors (16,128-18,144 bytes), no sector moves.

## Already English, keep

SYSTEM/1.1 and 2.1 (#2 title menu: PUSH START, NEW GAME, LOAD GAME, CONFIG, ADVANCED, NORMAL, EASY), SYSTEM/1.2 and 2.2 (#3, #5 title art),
#63 (`ADVANCED!! NORMAL!! EASY!!`), #230 `You did it!!`, #782 and #811 and #816 and #824 (mini-game `START! READY GO! TIME UP! PERFECT! LOST GET`, `Nice! Miss!`, `LOST WIN`),
#68-73 master plates (official romanization: Dominna, Prica, Craze, Michette, Prague, Zero; see `glossary.md`).
Mapped, read: #9 `CONFIGURATION`, #62 `RANK RECORD`, #64 `SPECIAL ROOM`, #74 `NOTICE` frame, #229 `Game Over`, #1033 `Fin`, #1436 `Game End`.

## Live checks (answered by the phase 2 warp)

- **Chapter 1 battle cards:** none. The first battle (script 127, chapter 2, `BATTLE/10`) shows no card; cards begin with the next battle. Verified by the cold-boot shots in `work/qa/warp/`.
- **Runtime-drawn labels:** camp commands, SPECIAL ROOM track names and home prompts use the 14-px font, not pictures. See [debug-tool.md](debug-tool.md). The phase 5 marker tour must catch any remaining runtime strings.

## Independent read

`tools/recon_review.py`: Codex, read-only and without this table, over all 47 sheets; verdicts in [graphics-review.txt](graphics-review.txt), which also transcribes every card.
**Result:** it found all rows above except where noted, and added #739, #740, #811, #816, #818 and the extras on #6 and #223, which I then confirmed by eye and added.
Rejected after looking: #824 (cans, no writing). #57 (open book on a desk) and #1228 (sign in a room), read zoomed in phase 8: scribbles, no writing. Its readings are drafts: check against the picture before translating.
It could not read #1430, #1431, #1434 on the raw sheets, where the map scrambles them, and read them correctly on the mapped ones.

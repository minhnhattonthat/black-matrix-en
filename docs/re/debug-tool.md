# Debug tool: warp

`tools/debug/warp.py NAME..` boots cold, selects NEW GAME and jumps the script VM to a scene. No save and no playthrough. Scene list:
`tools/debug/scenes.tsv`, written by `tools/debug/gen_scenes.py`. Lua side: `tools/debug/warp.lua`. `--all` runs every scene (`work/qa/warp/report.tsv`),
`--build` uses `build/disc<N>/` instead of the dump. Shots: `work/qa/warp/<name>/`. Nothing is written to disc: every patch is to RAM.

**Verified 2026-11-04:** all 166 scenes are `ok` in `report.tsv`: 163 on one `--all` run, then the 3 fixed battles rerun cold, plus 9 of the passing scenes rerun cold for new proof frames. No single `--all` run has passed all 166 yet. Independent Codex read of `warp_sheets.py --max 40` sheets, verdicts in [warp-review.txt](warp-review.txt): 165 OK, 1 UNSURE (`home_sweep`, tile too small; `▶:メニュー` confirmed on `proof.png` at 4x).

**Limit:** a warp has only Abel in the party, not the story cast at that point. Battle fields, cards and menus are real; rosters are not. Scripts 298 and 506 allow only units that haven't joined (formation shows `0/0` and won't sortie), so their rows patch one `08/27` and one `08/19` operand to unit 0.

## How the jump works (verified: every scene reaches its target)

Boot is a fixed route to NEW GAME. Then, read from `0x8004FCA4` and the op handlers:

- **Script number** is `a[17]` (`0x8008736A`); chapter is `a[18]`. `a[]`, `b[]`, `c[]` = the VM vars at `0x80087348`, `0x80086B48`, `0x80087748`.
- **Op 10 `CHAIN (n)`** loads script `n` and restarts at `0x8019B010`. Save files keep the script number (`a[17]`), so this is also how a loaded game resumes.
- **Script 0** chains to **script 5**, which runs the init block. When script 5 has loaded, `warp.lua` writes two things into its RAM copy: a `jmp` at `0xB5A` (over the movies, card and master select) to the init block at `0xC72`, and `CHAIN target` at `0xD52`. Init then runs and chains to the target.
- **Disc:** script 5's `08/04 (#1)` asks for Disc 1. On Disc 2 the warp rewrites that operand to 2. The disc value `0x8007E8B4` must stay true, because file lookups use it (`0x80017D2C`); poking it instead hangs the next load.
- **`pc` column:** after arrival the VM's PC (`0x8007EB1C`) moves to a stub at offset `0x7000` of the script buffer (largest script ends at `0x6B9C`, the font starts at `0x780C`), which runs the listed ops and jumps to `pc`. **The current op must be cleared** (`0x8007EB3E` = 0, mode `0x8007EB16` = 1): the VM often stops between an op's fetch and its operands, and that op would read the stub as operands.
- **Event scripts crash without their overlay.** Ops `09/xx` call into `4TH.BIN` (`0x800EB000`), which `09/17` loads, and a call into an empty overlay stops the emulator (exit 124). Hence the stub `09/17,09/09` (story) or `09/17,09/01` (home).

## scenes.tsv columns

| Column | Meaning |
|---|---|
| `name` | Scene name |
| `disc` | Which disc to boot. Chapter 7 on is Disc 2. EVENT.DAT differs between discs |
| `script` | Target script, or `-` for no warp: `route` alone is the scene (title, config) |
| `pc` | Hex file offset to start at, through the stub; `-` = the script's start |
| `stub` | Ops to run first: `09/17,09/09`, or with a constant operand `08/2a(28)` |
| `until` | Hex offset: wait for the PC to pass it before `frames`, `route` and shots start counting |
| `master` | 1-6 sets `a[87]`, `a[255]` (scripts vary per master); 0 leaves them for master select |
| `vars` | `a18=3,b70=1`: VM vars to set at the chain and on arrival |
| `patch` | `OFF:WORD`: u16 written into the loaded script on arrival. `1d8:8` turns `0b/05` into `0b/08` |
| `later` | `SCRIPT@OFF:WORD`: same, when that later script has loaded |
| `route` | `FRAMES KEY;...` after arrival |
| `mash` | Press circle every N frames after the route |
| `frames`, `every` | Hold this long after arrival, shooting every N frames |
| `proof` | Frame offset for the intentional `proof.png` used in the review sheet; `-` uses `final.png` |
| `expect` | `a17=132`: RAM checked at the end, a mismatch fails the scene |

`TRACE=N` (`--var`) logs PC, op and state every N frames. Battle rows start their input at the camp op and actually sortie into the battlefield; a camp screenshot alone is not accepted as proof. `warp_sheets.py` builds the review sheets from each scene's intentional `proof.png` (or `final.png`), and `warp_review.py --force` sends those sheets to a fresh read-only Codex pass.

## Ops identified on the way

| Op | Does | Evidence |
|---|---|---|
| `10`/`11`/`12` | Chain / call / return between scripts (stack at `0x800B50C8`) | handlers |
| `08/04 (n)` | Disc check: wait for Disc n, showing `SYSTEM/29` | `0x80019D38`; scene `disc_swap` |
| `08/14 (slot, ..)` | Sets up a party slot; table at `0x800B3F48`, 16 slots of 0x50 bytes (`+0` unit id, `+1` 0xFF = empty) | handlers `0x8005234C`, `0x80048D04` |
| `08/18`, `08/19 (unit)` | Clear the forced list, force a unit into the sortie | `0x80052530`, `0x80046B60`; `battle_298_b35` |
| `08/25`, `08/26`, `08/27 (unit)` | Clear the allowed list, allow all, allow one (no effect if that unit isn't in the party) | `0x800525A8`, `0x800525D0`, `0x80046BE4` |
| `08/1b` | Battle report and level-up, loads `5TH.BIN` | `battle_report` |
| `08/1c (2, n)` | Camp menu before a battle, loads `3RD.BIN` | `camp_*` |
| `08/1d` | Save screen; the save-prompt scripts set `a[17]` to the next script first | scripts 20, 144 |
| `08/23 (2)` | Free-battle camp menu (`3RD.BIN`, same handler as `08/1c`); sortie shows the battle card | `battle_*` |
| `08/2a (n)` | Plays a movie; `n` is 1-based in the table at `0x800759AC` (name, frames): 1 OPENING, 2 PROLOGUE, 3 `0101`, 28 STAFF, 29 DEMO01, 30 DEMO02 | `movie_*` |
| `08/35`, `08/3d` | RANK RECORD (`SYSTEM/16`), SPECIAL ROOM and sound test (`SYSTEM/17`) | `rank_record`, `special_room` |
| `09/17` | Loads `4TH.BIN`, the event engine | `0x80053124` |
| `09/27 (n)` | Full-screen picture `EVENT/n`: chapter cards 130-141, end cards 142-152, time cards 106, 107 | `ch*_card` |
| `09/29` | Loads `SYSTEM/5` data, **not** master select | `0x80053638` |
| `09/31` | Master select and confirm (`SYSTEM/21`, `SYSTEM/20`) | `master_*` |
| `0b/01`, `0b/02 (id, ..)` | Battle start; `id` is the `BATTLE.DAT` entry | `battle_*` |
| `0b/05` | Battle main loop | `battle_ui` |
| `0b/08` | Game over (`BATTLE/1`) | `game_over` |

DAT numbers in `0x80018154(dat, entry, dest)`: 2 = SCENARIO, 4 = SYSTEM.

## Answers to the graphics.md live checks

- **Chapter 1 battle cards:** there are none to translate. The first battle (script 127, chapter 2, `BATTLE/10`) has no `08/23` and shows no card.
- **Duplicate battle:** `BATTLE/64` and `BATTLE/66` (Disc 2) are byte-identical, so their card is one job.
- **Runtime-drawn Japanese seen so far** (draws from the 14-px font, so strings not pictures): camp menu (`状態 儀式 アイテム ショップ 潜在一覧 システム 出撃`), SPECIAL ROOM track names, home prompts.

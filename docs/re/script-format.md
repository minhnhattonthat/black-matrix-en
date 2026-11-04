# PSI22.00 scenario scripts

Read off the interpreter in `SLPS_029.62`. **Not** the Black/Matrix 00 bytecode: same developer, different VM.
Code: `tools/psi.py`. **Verified** by `tools/recon_psi.py` on both discs' SCENARIO.DAT: all 524 files tokenize with no
unknown op, each token stream ends exactly at the header's code size, and every jump lands on a token start.
Promote to a test in phase 4 (`tests/`): the check needs `work/extracted`, so it can't run from a clean clone yet.

## File

    'PSI22.00'  u32 0  u32 code_size  code...

Loaded at 0x8019B000; the program counter starts at 0x8019B010, and jump operands are offsets from there. Code ends at
`0x10 + code_size`; the file is padded to whole sectors (2048). The u16 at each PC is an op.

## Dispatch

`0x80076F90[op]` holds the handler (0x8004FCA4 calls it). Ops `8`, `9`, `A`, `B` take a second word that selects a sub-table
(0x8004FE4C sets the mode, 0x8004FEDC etc. fetch): 8 → 0x80077054, 9 → 0x80077150, A → 0x80077218, B → 0x80077334. The
global PC is `gp+0x2FC`. Handlers are re-entered every frame until they return 0, with state kept in globals, so a
fetch can sit behind a state check; `tools/recon_ops.py` lists fetches in code order, and shared handlers need reading
(08/1c and 08/23 share 0x80051DE0: only 1c takes a second E).

## Operands

| Kind | Fetch | Form |
|---|---|---|
| `w` | 0x8004F74C | u16 |
| `L` | 0x8004F768 | Skip to a 4-byte boundary (file-relative), then u32 jump offset |
| `E` | 0x8004F7F8 | Reverse Polish: items until a `0` word. `1` = imm32 (aligned like `L`), `2` u16 var (table 0x80087348), `3` u16 var (0x80086B48), `4` u32 var (0x80087748), `>=0x80` = binary op on the stack (table 0x80012054) |
| `T` | loop on 0x8004F74C | `u16 count` + count words of text (below) |

The padding before `L` and `imm32` depends on the current address, so **inserted text can change later padding**. The
insert step must re-tokenize and emit, never patch lengths in place.

## Text

Words are **little-endian Shift-JIS**: 0x8169 `（` is stored `69 81`. A word with a zero high byte is a control code:

| Code | Meaning | Evidence |
|---|---|---|
| `0x0010` | Line break | seen between lines of every 2-line box; **guess** until the draw loop is read in phase 5 |
| `0x0020`-`0x002F` | Macro: expands to the words at `0x800963B8 + (code & 0xF) * 32` (first word = count) | 0x80028424 |

0x80028424 expands macros into a 0x800-byte stack buffer: **1,024 words per line of text**, after expansion. Then
0x80029EDC turns each word into a glyph cache slot. `0x8140` draws as a blank cell without touching the font.

Text ops (from `SUB`/`OPS` in `psi.py`):

| Op | Sig | Use |
|---|---|---|
| `14` | `T` | Text, window slot `gp` 0x8007EB2C; 2,318 uses |
| `15` | `T` | Text with voice wait (calls 0x8001AAEC); 5,818 uses; **guess**: voiced line |
| `1d` | `TL` | Menu choice: label (first 15 words, padded with `0x8140`) + jump. 282 uses |
| `20` | `T` | Builds a menu from `1d` rows; **read in phase 4**, it reads more state |
| `08/15` | `ET` | Speaker/name card: slot expression + name. 6 uses |

Counts are over all 524 scripts of Disc 1 (9,066 text tokens). 0x17/0x18 follow almost every text (wait + clear).
Control words actually used (`tools/recon_free.py`): `0x0010` 6,406 times, macro `0x0021` 16, macro `0x0020` once; nothing else below 0x8000.
Longest text is 53 words. The macro table at 0x800963B8 is filled at run time (**guess**: `0x21` is a name such as the player's).

Scripts have **no string pointers**: text is inline, and only jumps (`L`, u32 from the code base) need remapping when text changes length.

## Limits that matter

- **Choice labels: 15 words.** Words past 15 are read and dropped (0x80050ADC), so half-width pairs give 30 letters.
- **Script size: 30,732 bytes** ([disc-layout.md](disc-layout.md)).
- **Text buffer 0x800B5538:** size not measured. Neighbours start at 0x800B5108/5248 below it; find the top in phase 5.

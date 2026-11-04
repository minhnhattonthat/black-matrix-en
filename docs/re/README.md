# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dump in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| [prior-work.md](prior-work.md) | Earlier patches and sources | Searches only, no patch found |
| [disc-layout.md](disc-layout.md) | Discs, rebuild, DAT and nested containers, RAM map, overlay loads, free-space candidates | Verified (identity and moved-file tests), free space not trap-tested |
| [script-format.md](script-format.md) | PSI22.00 VM, operands, text ops, control words | Tokenizer and rebuild verified on 524 of 524 |
| [text.md](text.md) | Extraction, tables, EXE and overlay strings, pointer format, compression | Roundtrip and coverage verified by test |
| [font.md](font.md) | 14×14 font, index table, glyph cache | Verified from code |
| [windows.md](windows.md) | English limits per window, paging, script and long-string room | Width gate measured in game; marker tour partial on the current build |
| [graphics.md](graphics.md) | Picture format, every Japanese picture and movie | Static sweep and warp live checks done |
| [debug-tool.md](debug-tool.md) | Cold-boot scene warp, scene schema and VM launch ops | Verified: 166 scenes, independent read in [warp-review.txt](warp-review.txt) |

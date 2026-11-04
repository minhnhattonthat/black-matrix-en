# Dialogue font and text drawing

**Verified** by reading the code (addresses below) and by `tools/recon_font.py` finding the RAM font in SYSTEM/0.

- **Glyphs:** 14×14, 1 bit per pixel, 14 big-endian u16 rows = **28 bytes per glyph**. Bits 2-15 of each row are pixels
  (0x8002A708: the row is shifted right by 2 first, then 14 bits are expanded).
- **Storage:** `SYSTEM/0` part 0 (offset 0x20, size 0xCCE0, head `BIT\0`), glyph 1 at offset 0x1C of the part, loaded at
  0x801A2800 (glyphs from 0x801A281C). (0xCCE0 - 0x1C) / 28 = **1,872 glyphs**.
- **Index:** `u16 0x800736BC[(hi - 0x81) * 192 + (lo - 0x40)]` in the EXE gives the glyph number (1-based; 0x8002A8DC).
  0x8140 → 1, 0x8141 → 2, ... ; table entries past the Shift-JIS range hold unrelated data (the "max 65535" that
  `recon_font.py` reports is one of them), so bound lookups to `hi <= 0x98`-ish before trusting a number.
- **Cache:** 0x80029E38 gives each word a slot in a **256-entry** glyph cache at 0x800965B8; 0x8002A5F8 rasterises a slot into a
  VRAM page (4bpp: each pixel set to a colour byte; 16 slots per row, 14 rows tall). `0x8140` writes a blank without
  reading the font.
- **The cache is fresh per draw request and has 256 slots.** Every word takes a slot, repeats included. **Guess**: repeats
  are not shared; check before relying on it in the VWF decision.

The dialogue path above reads only this font, never the BIOS. A byte search for the usual `B0:51` call setup in the EXE found
nothing, which is weak evidence that nothing else uses the BIOS font.

## Other fonts

Menu labels and many titles are **pictures**, drawn from sheets ([graphics.md](graphics.md)), including their kanji.

## Engine notes for phase 5

Black/Matrix 00 shipped half-width by drawing a two-ASCII-letter word as 6×12 glyphs in one 12×12 cell; that code
(`H:\translation\black-matrix-00\asm\halfwidth.asm`, its docs) is a guide only: addresses and cell size differ here. A word
with a high byte below 0x81 passes straight to the index math at 0x8002A8DC today, so that's the natural hook. 14 px
cells fit two 7-px letters, roomier than 00's 6.

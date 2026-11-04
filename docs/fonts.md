# Fonts

Every font or glyph sheet the build reads ends up inside the released patch, so its licence must allow that. One row
per file; a font with no known licence doesn't go into a release.

| File | Source (URL, version) | Licence | Redistributable in a patch | Used for | Changes made |
|---|---|---|---|---|---|
| `fonts/LiberationSerif-Bold.ttf`, `fonts/LiberationSans-Bold.ttf` | Liberation Fonts 2.1.5 (`https://github.com/liberationfonts/liberation-fonts`), licence `fonts/LICENSE-Liberation.txt` | SIL OFL 1.1 | yes | battle, chapter and end cards, manuals, master select | none |
| `fonts/LiberationSansNarrow-Bold.ttf` | Liberation Sans Narrow 1.07.5 (`https://github.com/liberationfonts/liberation-sans-narrow`), licence `fonts/LICENSE-LiberationNarrow.txt` | SIL OFL 1.1 | yes | chapter card spine | none |
| `fonts/5x8.bdf`, `6x10.bdf`, `6x12.bdf`, `6x13B.bdf`, `7x13B.bdf`, `8x13B.bdf`, `9x15B.bdf` | X11 misc-fixed (`https://gitlab.freedesktop.org/xorg/font/misc-misc`, master) | public domain | yes | sprite-sheet labels and manual text, set proportionally by `tools/gfx_labels.py` | none |
| `asm/font7x14.bin` | X11 misc-fixed `7x14.bdf` (`https://gitlab.freedesktop.org/xorg/font/misc-misc`, master, Markus Kuhn's ucs-fonts 2006-01-05), built by `tools/make_font.py` | public domain | yes | half-width dialogue and menu font (`asm/halfwidth.asm`) | 95 glyphs 0x20-0x7E, 1 bit per pixel |

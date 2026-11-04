# Fonts

Every font or glyph sheet the build reads ends up inside the released patch, so its licence must allow that. One row
per file; a font with no known licence doesn't go into a release.

| File | Source (URL, version) | Licence | Redistributable in a patch | Used for | Changes made |
|---|---|---|---|---|---|
| `asm/font7x14.bin` | X11 misc-fixed `7x14.bdf` (`https://gitlab.freedesktop.org/xorg/font/misc-misc`, master, Markus Kuhn's ucs-fonts 2006-01-05), built by `tools/make_font.py` | public domain | yes | half-width dialogue and menu font (`asm/halfwidth.asm`) | 95 glyphs 0x20-0x7E, 1 bit per pixel |

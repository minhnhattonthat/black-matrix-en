Black/Matrix + (PlayStation) - English fan translation, v{version}

Unofficial. Not affiliated with Flight-Plan or NEC Interchannel. This zip holds patches only, no game data:
you need your own dump of both Japanese discs. Do not share patched discs.

WHAT YOU NEED
  Black-Matrix + (Japan) (Disc 1).bin and (Disc 2).bin, the Redump dumps
  (http://redump.org/discs/quicksearch/{base1_sha1_lower}/ and .../{base2_sha1_lower}/).
  Check them against the hashes below; no other dump will patch correctly.

HOW TO PATCH
  {patch1} goes on Disc 1, {patch2} on Disc 2.
  Windows: Delta Patcher (or any xdelta3 GUI): pick the .bin as the original file, the .xdelta as the patch.
  Command line:
    xdelta3 -d -s "Black-Matrix + (Japan) (Disc 1).bin" {patch1} black-matrix-plus_en_disc1.bin
    xdelta3 -d -s "Black-Matrix + (Japan) (Disc 2).bin" {patch2} black-matrix-plus_en_disc2.bin
  Each patched .bin needs a .cue with the same name beside it, holding (with that file name):
    FILE "black-matrix-plus_en_disc1.bin" BINARY
      TRACK 01 MODE2/2352
        INDEX 01 00:00:00

  Tested in PCSX-Redux (nightly 30264.20261103.29, SCPH-5500 BIOS). Start from a cold boot: savestates made on the
  Japanese game keep the old font and text. Memory-card saves from the Japanese version were not tested.

CONTROLS
  As in the Japanese game: circle confirms, cross cancels.

WHAT IS TRANSLATED
  Dialogue and narration on every route, menus, items, skills, help text, name entry (Latin letters first; the kana
  pages are kept), chapter and battle cards, manuals, staff roll, subtitles for every spoken line in the movies.
  Left in Japanese: spoken voices and songs; the kanji beside the English words in the bonus movie DEMO02.

KNOWN LIMITS
  Not seen in testing, since no one has played start to end: the magic list window, some battle rows that need a full
  party, and dialogue portraits in a real run (test warps can't draw them). Timed cutscene pages were not timed
  against the Japanese. Reports welcome: https://github.com/minhnhattonthat/black-matrix-en/issues

BASE DISCS
  Disc 1  size {base1_size}  CRC32 {base1_crc}  MD5 {base1_md5}  SHA-1 {base1_sha1}
  Disc 2  size {base2_size}  CRC32 {base2_crc}  MD5 {base2_md5}  SHA-1 {base2_sha1}

PATCHED DISCS
  Disc 1  size {patched1_size}  CRC32 {patched1_crc}  SHA-1 {patched1_sha1}
  Disc 2  size {patched2_size}  CRC32 {patched2_crc}  SHA-1 {patched2_sha1}

CREDITS
  Original game (c) Flight-Plan / NEC Interchannel.
  Translation and tools by minhnhattonthat. Made with extensive AI assistance (Claude by Anthropic, reviews by OpenAI
  Codex), so corrections are very welcome. Names follow the published English cast list where one exists; guesses
  are listed in docs/decisions.md in the source repository.
  Fonts drawn into the game: X11 misc-fixed (public domain), Liberation Serif, Sans and Sans Narrow (SIL OFL 1.1).

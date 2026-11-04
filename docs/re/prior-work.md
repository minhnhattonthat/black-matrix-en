# Earlier patches and sources

Searched 2026-11-04, web searches only: no search of Japanese forums, and the romhacking.net listing wasn't opened directly.

- **No English patch for Black/Matrix + (Cross) found**, and no script dump or tool for this version. Serial SLPS-02962/3, Flight-Plan, NEC Interchannel, 14 Dec 2000 ([PSX Datacenter](https://psxdatacenter.com/games/J/B/SLPS-02962.html)). Rerelease SLPS-03415 is a different dump ([PSX Datacenter](https://psxdatacenter.com/games/J/B/SLPS-03415.html)); `rom.sha1` pins ours.
- **Saturn original:** Sega Saturn Shiro lists a Black/Matrix English project as ongoing ([project list](https://www.segasaturnshiro.com/saturn-community-projects/saturn-translations/)). Status unknown, another version, and a different engine, so nothing to reuse.
- **Black/Matrix 00 (PS1):** Data Crystal notes a Korean patch and an unfinished English one ([wiki](https://datacrystal.tcrf.net/wiki/Black_Matrix_Zero)). The user's own finished patch is at `H:\translation\black-matrix-00`.

## What Black/Matrix 00 gives us (guide only, addresses differ)

| Same here | Different here |
|---|---|
| DAT container, picture blobs, LZ scheme, half-width trick idea (two letters in one cell) | Script VM (PSI22.00), 14-px font rather than 12, LZ unused on disc as far as tested |

Its names follow D2 only where this game's own English doesn't already settle them ([glossary](../../glossary.md)).

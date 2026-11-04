# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** Phase 1 (recon) done; next is phase 2, debug tool. Last build: none yet.
- **Done:** Step 0: PCSX-Redux nightly 30264.20261103.29 and SCPH-5500, both discs smoke-boot headless, `tools/routes/boot.txt` (title at frame ~2290, Start then circle reaches the Japanese memory-card prompt). Phase 1, all in `docs/re/` (index in its README): no earlier patch found; disc and DAT containers; PSI22.00 tokenizer passes 524 of 524 scripts; little-endian Shift-JIS, control words; strings are `u16 count + words` reached through the count word; overlay loads verified (2ND, 4TH, 5TH 0x800EB000; 3RD 0x80110800); nothing on disc compressed as far as tested; free-space candidates; picture and cell-map formats; survey of all 1,437 pictures and 29 distinct movies.
- **Next:** Phase 2: `tools/debug/` (scenes + warp) reaching every scene from cold boot. Start from `script-format.md` (the VM runs a script by number; `0x8019B000` buffer). Warp must cover the live checks in `graphics.md`, each chapter, endings, disc swap. Tools still to fetch: mkpsxiso/dumpsxiso (phase 3), armips, xdelta3, jPSXdec (needed: `PROLOGUE`, `STAFF`, demo ads; the sibling repo has a copy).
- **Costs known early:** 50 torn-paper battle cards and 23 chapter cards over art are the largest graphics job (`graphics.md`). `STAFF.STR` credits are video, so D3 means re-encoding 180 s. Script buffer leaves only 3,184 bytes on the largest scenario (`disc-layout.md`), so the phase 5 font decision must keep English near Japanese size or move the font.
- **Open bugs:** none.
- **Not verified:** the skill's keyboard check on the PCSX-Redux GUI. Two tries posting Enter to the window (no focus) showed no START on pad 1, which proves nothing either way: the posted keys may never reach the pad code without real focus. Dropped per D8, since QA is headless only. Default binding is Enter = Start (scancode 40). It matters only for a player using this repo's emulator copy.
- **Waiting on the user:** nothing.

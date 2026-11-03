# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** Step 0 (repo setup) done; next is phase 1. Last build: none yet.
- **Done:** PCSX-Redux nightly 30264.20261103.29 and SCPH-5500 fetched. Both original discs smoke-boot headless. `tools/routes/boot.txt` (Disc 1): title at frame ~2290, Start then circle reaches the memory-card slot prompt, which is Japanese. Lua probe logs. Pre-commit runs `tools/check.py`; the guard hook blocks the `sed -i` canary. `rom.sha1` pins both .bin files.
- **Next:** Phase 1 recon: research earlier patches, unpack the discs, find text encoding, pointers, compression, free space, survey graphics text. Tools still to fetch: mkpsxiso/dumpsxiso (phase 3), armips, xdelta3, jPSXdec if there are FMV subtitles, `pip install capstone`.
- **Open bugs:** none.
- **Not verified:** the skill's keyboard check on the PCSX-Redux GUI. Two tries posting Enter to the window (no focus) showed no START on pad 1, which proves nothing either way: the posted keys may never reach the pad code without real focus. Dropped per D8, since QA is headless only. Default binding is Enter = Start (scancode 40). It matters only for a player using this repo's emulator copy.
- **Waiting on the user:** nothing.

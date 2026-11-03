"""Repo invariants that hold with or without the ROM."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rom_sha1_pins_both_discs():
    lines = [l for l in (ROOT / "rom.sha1").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    assert len(lines) == 2
    for line, disc in zip(lines, ("Disc 1", "Disc 2")):
        assert re.fullmatch(r"[0-9a-f]{40}  rom/.+\.bin", line)
        assert disc in line

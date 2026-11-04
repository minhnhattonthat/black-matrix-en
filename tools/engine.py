"""engine.py: assemble asm/halfwidth.asm into an EXE, and the English text encoding that goes with it (docs/re/font.md).
A text word 0x2000-0x7FFF is two ASCII letters in one 14-px cell; control words (high byte 0) and Shift-JIS pass through."""
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIPS = ROOT / 'tools/armips/armips.exe'
WORK = ROOT / 'work/engine'
BASE = 0x8000F800  # RAM address - BASE = EXE file offset
FREE = [(0x80073AE8, 0x80074202), (0x80073788, 0x8007385A)]  # must be zero before the patch: index-table codes no glyph uses
RANGES = FREE + [(0x8002A66C, 0x8002A670), (0x80028490, 0x8002849C), (0x8002CC1C, 0x8002CC20), (0x8002CC2C, 0x8002CC30),
                 (0x8004F2F8, 0x8004F2FC)]  # the only bytes the patch may change
LONG_FIRST, LONG_LAST = 0x30, 0xFF  # control words free for long strings; the game uses 0x10 and 0x20-0x2F
# The long table replaces the font's last 365 glyphs (kanji, unused once the text is English; a Japanese string left in a build may garble).
FONT_RAM = 0x801A2800  # leaf SYSTEM/0.0, 0xCCE0 bytes, font.md
LONG_RAM, LONG_SIZE = 0x801ACCE0, 0x2800  # hw_long_ix, hw_long in the asm; index is 208 u16s
GLYPHS_LEFT = (LONG_RAM - FONT_RAM - 0x1C) // 28


class Long:
    """Strings too long for their place in the EXE or an overlay. add() gives the one word to put there instead."""

    def __init__(self):
        self.items = []

    def add(self, words):
        if tuple(words) not in self.items:
            self.items.append(tuple(words))
        word = LONG_FIRST + self.items.index(tuple(words))
        if word > LONG_LAST:
            raise ValueError('out of long-string words')
        return word

    def blobs(self):
        """(index: u16 offset of each entry in u16s, data: each entry as count + words)."""
        ix, data, at = [], [], 0
        for it in self.items:
            ix.append(at)
            data += [len(it), *it]
            at += 1 + len(it)
        return struct.pack(f'<{len(ix)}H', *ix), struct.pack(f'<{len(data)}H', *data)

    def into_font(self, font):
        """The font with the table written over its tail."""
        ix, data = self.blobs()
        blob = ix.ljust((LONG_LAST - LONG_FIRST + 1) * 2, b'\0') + data
        if len(blob) > LONG_SIZE:
            raise ValueError(f'long strings take {len(blob)} bytes, the room is {LONG_SIZE}')
        off = LONG_RAM - FONT_RAM
        return font[:off] + blob + font[off + len(blob):]


def apply(exe):
    """The EXE with the hooks in. Fails if a range the patch uses isn't free, or if it touched anything else."""
    for lo, hi in FREE:
        assert not any(exe[lo - BASE:hi - BASE]), f'{lo:#x}-{hi:#x} is not zero'
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'in.exe').write_bytes(exe)
    subprocess.run([ARMIPS, 'asm/halfwidth.asm', '-sym', 'work/engine/out.sym'], cwd=ROOT, check=True)
    out = (WORK / 'out.exe').read_bytes()
    assert len(out) == len(exe), 'the patch changed the EXE size'
    for i, (a, b) in enumerate(zip(exe, out)):
        if a != b:
            ram = BASE + i
            assert any(lo <= ram < hi for lo, hi in RANGES), f'patch wrote outside its ranges at {ram:#x}'
    return out


def encode(text):
    """English (or anything) -> text words. ASCII runs pair up, an odd run ends in a space; `\\n` = 0x0010, {XXXX} = that word,
    a double-byte character keeps its Shift-JIS word."""
    out, run, i = [], [], 0

    def flush():
        if len(run) % 2:
            run.append(0x20)
        out.extend(run[j] << 8 | run[j + 1] for j in range(0, len(run), 2))
        run.clear()

    while i < len(text):
        c = text[i]
        if c == '{':
            assert text[i + 5] == '}', text
            flush()
            out.append(int(text[i + 1:i + 5], 16))
            i += 6
            continue
        i += 1
        if c == '\n':
            flush()
            out.append(0x10)
        elif 0x20 <= ord(c) <= 0x7E:
            run.append(ord(c))
        else:
            b = c.encode('cp932')
            if len(b) != 2:
                raise ValueError(f'{c!r} in {text!r} has no glyph')
            flush()
            out.append(b[0] << 8 | b[1])
    flush()
    return out


def decode(words):
    """Inverse of encode for reading dumps: pad spaces stay."""
    out = []
    for w in words:
        if w == 0x10:
            out.append('\n')
        elif w >> 8 and w < 0x8000:
            out.append(chr(w >> 8) + chr(w & 0xFF))
        elif w < 0x100:
            out.append(f'{{{w:04X}}}')
        else:
            out.append(bytes((w >> 8, w & 0xFF)).decode('cp932', 'replace'))
    return ''.join(out)

"""PSI22.00 scenario bytecode: tokenizer and text extraction. Format notes: docs/re/script-format.md

File: 'PSI22.00', u32 0, u32 code size in bytes, then the code at +0x10 (jump operands are relative to +0x10).
Op table at 0x80076F90 in SLPS_029.62; ops 8..0xB take a second word that indexes a sub-table.
Operand kinds: w = u16; L = u32 jump, 4-byte aligned from the file start (pad word before it when needed);
T = u16 count + count u16 words of text (Shift-JIS stored as little-endian u16, 0x0010 = line break);
E = reverse-Polish expression ending in a zero word."""
import struct
from dataclasses import dataclass

CODE_BASE = 0x10
SUB_OPS = (8, 9, 0xA, 0xB)

# Read off the handlers by tools/recon_ops.py (order of fetch-helper calls), corrected by hand where a handler
# fetches through a loop or a state machine. tests/test_psi.py proves them against every scenario file.
OPS = {
    0x00: '', 0x01: 'wwE', 0x02: 'LE', 0x03: 'L', 0x04: '', 0x05: '', 0x06: 'E', 0x07: '', 0x0C: '', 0x0D: 'E', 0x0E: '',
    0x0F: 'E', 0x10: 'E', 0x11: 'E', 0x12: '', 0x14: 'T', 0x15: 'T', 0x16: 'E', 0x17: '', 0x18: '', 0x19: '',
    0x1A: 'E', 0x1B: '', 0x1C: 'EEE', 0x1D: 'TL', 0x1E: '', 0x20: 'T', 0x21: 'E', 0x22: '', 0x25: 'E', 0x27: 'EE',
    0x28: 'E', 0x29: 'EE', 0x2A: '', 0x2D: 'E', 0x2E: 'E', 0x2F: '', 0x30: '',
}
SUB = {
    8: {0x02: '', 0x04: 'E', 0x05: '', 0x0B: 'E', 0x0C: 'E', 0x0D: '', 0x0F: '', 0x10: 'EEE', 0x11: 'E', 0x13: 'E', 0x14: 'EEEE',
        0x15: 'ET', 0x16: 'E', 0x17: '', 0x18: '', 0x19: 'E', 0x1A: '', 0x1B: '', 0x1C: 'EE', 0x1D: '', 0x20: 'E',
        # 1c and 23 share a handler; only 1c fetches a second E
        0x21: 'EE', 0x23: 'E', 0x24: '', 0x25: '', 0x26: '', 0x27: 'E', 0x28: 'E', 0x29: '', 0x2A: 'E', 0x2C: '',
        0x35: '', 0x36: '', 0x38: 'E', 0x39: 'E', 0x3A: '', 0x3B: '', 0x3D: ''},
    9: {0x01: '', 0x02: '', 0x03: '', 0x04: 'E', 0x06: 'E', 0x07: '', 0x08: 'EEE', 0x09: '', 0x0A: '', 0x0B: '', 0x0C: '',
        0x0D: '', 0x0E: '', 0x0F: 'EEEEE', 0x10: 'EEE', 0x13: 'E', 0x15: 'E', 0x16: 'E', 0x17: '', 0x18: 'E', 0x19: 'EE',
        0x1A: '', 0x1B: 'EE', 0x1D: 'EEE', 0x1E: 'EEEE', 0x20: 'E', 0x21: 'EE', 0x22: 'EE', 0x23: 'EEEE', 0x24: '',
        0x25: 'EEEEEE', 0x27: 'E', 0x28: 'EEE', 0x29: '', 0x2A: '', 0x2B: 'E', 0x2C: 'EE', 0x2D: 'E', 0x2E: 'EE',
        0x2F: 'EE', 0x30: 'E', 0x31: ''},
    0xA: {0x10: 'E', 0x11: 'E', 0x12: '', 0x13: '', 0x1D: '', 0x1E: '', 0x20: '', 0x21: '', 0x22: '', 0x23: '', 0x25: 'E',
          0x26: 'E', 0x2D: 'E', 0x2E: 'E', 0x2F: 'EE', 0x3F: 'EE', 0x40: '', 0x41: '', 0x42: '', 0x43: '', 0x44: '', 0x45: ''},
    # 0b/04.. live in 2ND.BIN (loaded at 0x800EB000), signatures from tools/recon_sub0b.py
    0xB: {0x01: '', 0x02: 'EEE', 0x03: '', 0x04: 'EE', 0x05: '', 0x06: '', 0x07: '', 0x08: '', 0x09: 'E', 0x0A: 'EEEE',
          0x0B: 'EEE', 0x0C: 'EEE', 0x0D: 'EEE', 0x0E: 'EE', 0x10: 'E', 0x11: 'E', 0x12: 'EEE', 0x13: 'EEE', 0x14: 'EEE',
          0x15: 'EE', 0x16: 'EE', 0x17: 'EE'},
}


@dataclass
class Token:
    off: int        # file offset of the opcode
    op: int         # main opcode
    sub: int | None
    raw: bytes
    parts: list     # ('b', bytes) verbatim | ('a', bytes) 4-byte-aligned imm32 | ('L', target) jump | ('T', words) text
    words: tuple | None = None   # text words of a T operand
    targets: tuple = ()


def _u16(b, p):
    return struct.unpack_from('<H', b, p)[0]


def header(b):
    if b[:8] != b'PSI22.00':
        raise ValueError('not a PSI22.00 script')
    return struct.unpack_from('<I', b, 12)[0]


def expr(b, p, parts):
    start = p
    while True:
        item = _u16(b, p)
        parts.append(('b', b[p:p + 2]))
        p += 2
        if item == 0:
            return p
        if item == 1:
            if p & 3:
                p += 4 - (p & 3)
            parts.append(('a', b[p:p + 4]))
            p += 4
        elif item in (2, 3, 4):
            parts.append(('b', b[p:p + 2]))
            p += 2
        elif item < 0x80:
            raise ValueError(f'bad expression item {item:#x} at {p - 2:#x} (expr from {start:#x})')


def token_at(b, p):
    start = p
    op = _u16(b, p)
    p += 2
    sub = None
    if op in SUB_OPS:
        sub = _u16(b, p)
        p += 2
        sig = SUB[op].get(sub)
        if sig is None:
            raise KeyError(f'unknown op {op:02x}/{sub:02x} at {start:#x}')
    else:
        sig = OPS.get(op)
        if sig is None:
            raise KeyError(f'unknown op {op:02x} at {start:#x}')
    words, targets = None, []
    parts = [('b', b[start:p])]
    for c in sig:
        if c == 'w':
            parts.append(('b', b[p:p + 2]))
            p += 2
        elif c == 'E':
            p = expr(b, p, parts)
        elif c == 'L':
            if p & 3:
                p += 4 - (p & 3)
            targets.append(struct.unpack_from('<I', b, p)[0])
            parts.append(('L', targets[-1]))
            p += 4
        elif c == 'T':
            n = _u16(b, p)
            p += 2
            words = struct.unpack_from(f'<{n}H', b, p)
            parts.append(('T', words))
            p += 2 * n
    return Token(start, op, sub, b[start:p], parts, words, tuple(targets))


def tokenize(b):
    """Every token of the code area; raises on an unknown op or a token running past the end."""
    size = header(b)
    end = CODE_BASE + size
    # Code size in the header counts from the file start in the files checked so far
    toks, p = [], CODE_BASE
    while p < min(end, len(b)):
        t = token_at(b, p)
        toks.append(t)
        p += len(t.raw)
    return toks, p, end


def rebuild(b, texts=None):
    """The script again from its tokens, with texts {token offset: new words}: re-emits padding, remaps every jump,
    updates the code size and pads to the sector. With no texts it gives back b (tests/test_extract.py)."""
    toks, end, _ = tokenize(b)
    out = bytearray(b[:CODE_BASE])
    where, fixups = {end: None}, []
    for t in toks:
        where[t.off] = len(out)
        for kind, v in t.parts:
            if kind == 'b':
                out += v
            elif kind == 'T':
                ws = texts.get(t.off, v) if texts else v
                out += struct.pack(f'<H{len(ws)}H', len(ws), *ws)
            else:
                out += bytes(-len(out) & 3)
                if kind == 'L':
                    fixups.append((len(out), v))
                out += v if kind == 'a' else bytes(4)
    where[end] = len(out)
    for pos, target in fixups:
        struct.pack_into('<I', out, pos, where[target + CODE_BASE] - CODE_BASE)
    struct.pack_into('<I', out, 12, len(out) - CODE_BASE)
    return bytes(out) + bytes(-len(out) % 2048)


def is_text(w):
    """A word text can hold: canonical Shift-JIS, the line break or a macro."""
    if w == 0x10 or 0x20 <= w <= 0x2F:
        return True
    return w >= 0x8140 and decode((w,)) != f'{{{w:04X}}}'


def walk(d, minn=1, maxn=400):
    """Yield (offset, words) for each counted string, greedy from the low end. Code can look like a short string:
    only trust a hit inside a known string area or with a pointer (tools/recon_counted.py)."""
    p, n = 0, len(d) & ~1
    while p + 2 < n:
        c = _u16(d, p)
        if minn <= c <= maxn and p + 2 + 2 * c <= n:
            ws = struct.unpack_from(f'<{c}H', d, p + 2)
            if all(is_text(w) for w in ws) and any(w >= 0x8140 for w in ws):
                yield p, ws
                p += 2 + 2 * c
                continue
        p += 2


def decode(words):
    """Text words -> str. 0x0010 is a line break; anything else not canonical Shift-JIS is kept as {XXXX}."""
    out = []
    for w in words:
        if w == 0x0010:
            out.append('\n')
            continue
        hi, lo = w >> 8, w & 0xFF
        try:
            ch = bytes((hi, lo)).decode('cp932') if hi else None
        except UnicodeDecodeError:
            ch = None
        if ch is None or len(ch) != 1 or ch.encode('cp932') != bytes((hi, lo)):
            out.append(f'{{{w:04X}}}')
        else:
            out.append(ch)
    return ''.join(out)


def encode(text):
    """Inverse of decode. Raises on a character that isn't a double-byte Shift-JIS one."""
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c == '{':
            out.append(int(text[i + 1:i + 5], 16))
            assert text[i + 5] == '}', text
            i += 6
            continue
        i += 1
        if c == '\n':
            out.append(0x10)
            continue
        b = c.encode('cp932')
        if len(b) != 2:
            raise ValueError(f'{c!r} in {text!r} is not a double-byte character')
        out.append(b[0] << 8 | b[1])
    return out

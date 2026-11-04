; Half-width English for Black/Matrix + (SLPS-02962/3). Assembled by tools/engine.py. docs/re/font.md has the design.
; A text word below 0x8000 (and not a control word, whose high byte is 0) is two ASCII letters in one 14-px cell,
; 7 px each: high byte left, low byte right. Everything else about the cell grid stays as it is, so menus keep their columns.

.psx
.open "work/engine/in.exe", "work/engine/out.exe", 0x8000F800

.definelabel hw_long_ix, 0x801ACCE0     ; engine.LONG_RAM: the font's last glyphs, kanji English doesn't use
.definelabel hw_long, 0x801ACCE0 + 0x1A0

; glyph cache miss: original `jal 0x8002A8DC`, a0 = 14 u16 rows to fill, a1 = the word. Its delay slot stays.
.org 0x8002A66C
    jal   hw_glyph

; macro expansion in 0x80028424: words 0x30-0xFF become long strings, the way 0x20-0x2F are run-time macros. A string in the EXE or an
; overlay has no room to grow (they sit among code), so one too long holds just such a word (engine.Long). Original:
; addiu v0,zero,0x20 / bne v1,v0,0x80028510 / andi v0,a1,0xffff, and the bne's target needs that andi.
.org 0x80028490
    j     hw_macro
    andi  v0, a1, 0xFFFF
    nop

; Name entry: the name row's cells are 14 px apart, not 18, so a default name stored as pairs reads as one word.
.org 0x8002CC1C
    addiu s3, s3, 14
.org 0x8002CC2C
    addiu s2, s2, 14

; Name entry: its side menu's two cells of a label (0x8002CA38) sit 14 px apart too, so "Hi" "ra" reads as a word. Original: v1 = (s1 & 1) * 18.
.org 0x8002CA80
    sll   v1, v0, 4
    sll   v0, v0, 1
    subu  v1, v1, v0

; Setting a run-time macro (the player's name, an item's name): original `jal 0x80029D2C`. Delay slot stays.
.org 0x8004F2F8
    jal   hw_setmacro

; Second zero run of the index table: codes 0x81A6-0x8200.
.org 0x80073788
.area 0xD2
hw_glyph:
    andi  a1, a1, 0xFFFF
    srl   v0, a1, 15           ; not sltiu: its immediate would sign-extend
    beq   v0, zero, @@pair
    srl   t1, a1, 8            ; left letter
    j     0x8002A8DC
    nop
@@pair:
    addiu t1, t1, -0x20
    sltiu v0, t1, 0x5F
    bne   v0, zero, @@left_ok
    andi  t2, a1, 0xFF         ; right letter
    move  t1, zero
@@left_ok:
    addiu t2, t2, -0x20
    sltiu v0, t2, 0x5F
    bne   v0, zero, @@right_ok
    nop
    move  t2, zero
@@right_ok:
    sll   t3, t1, 4            ; index * 14
    sll   t1, t1, 1
    subu  t3, t3, t1
    sll   t4, t2, 4
    sll   t2, t2, 1
    subu  t4, t4, t2
    la    t5, hw_font
    addu  t3, t3, t5
    addu  t4, t4, t5
    li    t6, 14
@@row:
    lbu   v0, 0(t3)            ; left: bits 7..1 -> 15..9, the rasteriser draws bits 15..2 left to right
    lbu   v1, 0(t4)            ; right: bits 7..1 -> 8..2
    addiu t3, t3, 1
    addiu t4, t4, 1
    sll   v0, v0, 8
    sll   v1, v1, 1
    or    v0, v0, v1
    sh    v0, 0(a0)
    addiu t6, t6, -1
    bne   t6, zero, @@row
    addiu a0, a0, 2
    jr    ra
    nop
.endarea

; Zero run in the Shift-JIS index table (0x800736BC): codes 0x83D6-0x88A2, which no glyph uses. engine.py checks it is zero.
.org 0x80073AE8
.area 0x71A
hw_font:
    .incbin "asm/font7x14.bin"
.align 4

; a0 = macro number, a1 = `count, words`. Letters and digits typed on the name grid are full-width: squeeze them into half-width pairs here, so a
; name reads as text in a dialogue line, on every path that sets the macro.
hw_setmacro:
    addiu sp, sp, -0x38
    sw    ra, 0x34(sp)
    lhu   t0, 0(a1)            ; words left
    addiu t1, a1, 2            ; in
    addiu t2, sp, 0x12         ; out: a `count, words` entry at sp+0x10, 15 words as in the macro table
    move  t3, zero             ; a letter waiting for its right half
    sltiu v0, t0, 16
    beq   v0, zero, @@done_raw ; longer than a macro entry: not a name
    move  t4, zero             ; words out
@@next:
    beq   t0, zero, @@end
    lhu   v0, 0(t1)
    addiu t1, t1, 2
    addiu t0, t0, -1
    srl   v1, v0, 8
    addiu v1, v1, -0x82
    bne   v1, zero, @@other    ; only 0x82xx holds full-width letters and digits
    andi  v1, v0, 0xFF
    addiu t5, v1, -0x4F        ; 0x824F-0x8258 digits
    sltiu t6, t5, 10
    bne   t6, zero, @@ascii
    addiu t5, t5, 0x30
    addiu t5, v1, -0x60        ; 0x8260-0x8279 capitals
    sltiu t6, t5, 26
    bne   t6, zero, @@ascii
    addiu t5, t5, 0x41
    addiu t5, v1, -0x81        ; 0x8281-0x829A small letters
    sltiu t6, t5, 26
    bne   t6, zero, @@ascii
    addiu t5, t5, 0x61
@@other:
    beq   t3, zero, @@put
    nop
    sll   t3, t3, 8            ; a lone letter before another word gets a blank right half
    ori   t3, t3, 0x20
    sh    t3, 0(t2)
    addiu t2, t2, 2
    addiu t4, t4, 1
    move  t3, zero
@@put:
    sh    v0, 0(t2)
    addiu t2, t2, 2
    b     @@next
    addiu t4, t4, 1
@@ascii:
    bne   t3, zero, @@pair
    nop
    b     @@next
    move  t3, t5
@@pair:
    sll   t3, t3, 8
    or    t3, t3, t5
    sh    t3, 0(t2)
    addiu t2, t2, 2
    addiu t4, t4, 1
    b     @@next
    move  t3, zero
@@end:
    beq   t3, zero, @@go
    nop
    sll   t3, t3, 8
    ori   t3, t3, 0x20
    sh    t3, 0(t2)
    addiu t4, t4, 1
@@go:
    sh    t4, 0x10(sp)
    addiu a1, sp, 0x10
@@done_raw:
    jal   0x80029D2C
    nop
    lw    ra, 0x34(sp)
    nop
    jr    ra
    addiu sp, sp, 0x38

; v1 = word & 0xF0, a0 = the word, whose high byte is 0. t0-t4 are live in the caller; t5, t6 are not. a3 = index in u16s from t2 (0x800963B8)
; to a `count, words` entry: the code after 0x800284A4 reads it through t2.
hw_macro:
    addiu t5, zero, 0x20
    beq   v1, t5, @@macro
    nop
    sltiu t5, a0, 0x30
    bne   t5, zero, @@plain
    nop
    addiu t5, a0, -0x30
    sll   t5, t5, 1
    la    t6, hw_long_ix
    addu  t5, t5, t6
    lhu   t5, 0(t5)            ; offset in u16s from hw_long
    la    t6, hw_long
    sll   t5, t5, 1
    addu  t6, t6, t5
    subu  t6, t6, t2
    j     0x800284A4
    sra   a3, t6, 1
@@macro:
    j     0x8002849C
    nop
@@plain:
    j     0x80028510
    nop
.endarea
.close

-- emu.py probe: dump main RAM and VRAM at each frame in DUMP_FRAMES (Lua table), to OUT/ram_<f>.bin, OUT/f<f>.vram.bin.
local want = {}
for _, f in ipairs(DUMP_FRAMES or {}) do want[f] = true end
L.on_frame(function(n)
  if want[n] then
    L.dump_ram(string.format("%sram_%06d.bin", OUT, n))
    L.dump_ppu(string.format("%sf%06d", OUT, n))
    L.log(string.format("dumped %d", n))
  end
end)

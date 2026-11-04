-- winlog.lua: log every text window as it is built: "WIN <frame> <caller> cols rows x y w h ..". 0x8002A968 is the cell-grid
-- constructor (docs/re/font.md). Needs --debugger. usage: emu.py ... --debugger --script tools/lua/winlog.lua
local ffi = require("ffi")
local mem = ffi.cast("uint8_t*", PCSX.getMemPtr())
local function r32(a) return ffi.cast("uint32_t*", mem + bit.band(a, 0x1FFFFC))[0] end
local seen = {}
L.on_exec(0x8002A968, function()
  local r = PCSX.getRegisters().GPR.n
  local sp = tonumber(r.sp)
  local vals = {}
  for i = 0, 5 do vals[#vals + 1] = string.format("%d", tonumber(ffi.cast("int32_t", r32(sp + 0x10 + i * 4)))) end
  local line = string.format("WIN %08x cols=%d rows=%d a3=%d st=%s", tonumber(r.ra), tonumber(r.a1), tonumber(r.a2),
                             tonumber(ffi.cast("int32_t", r.a3)), table.concat(vals, ","))
  if not seen[line] then seen[line] = true; L.log(string.format("%d ", L.frame) .. line) end
end)

-- cdlog.lua: log each CD Setloc as "SETLOC <frame> <lba>", to see what a run reads and which reads follow a moved file.
-- Needs --debugger. usage: emu.py ... --debugger --script tools/lua/cdlog.lua; diff the log.txt of two builds.
local params, index = {}, 0

-- The hook fires before the store, so the value is still in the store instruction's source register.
local function stored()
  local regs = PCSX.getRegisters()
  local code = require("ffi").cast("uint32_t*", PCSX.getMemPtr() + bit.band(regs.pc, 0x1FFFFF))[0]
  return bit.band(tonumber(regs.GPR.r[bit.band(bit.rshift(code, 16), 31)]), 0xFF)
end

local function bcd(b) return bit.rshift(b, 4) * 10 + bit.band(b, 15) end

L.on_write(0x1F801800, 0x1F801800, function() index = bit.band(stored(), 3) end)
L.on_write(0x1F801802, 0x1F801802, function()
  if index == 0 then params[#params + 1] = stored() end
end)
L.on_write(0x1F801801, 0x1F801801, function()
  if index ~= 0 then return end
  if stored() == 2 and #params >= 3 then
    L.log(string.format("SETLOC %d %d", L.frame, (bcd(params[1]) * 60 + bcd(params[2])) * 75 + bcd(params[3]) - 150))
  end
  params = {}
end)

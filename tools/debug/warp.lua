-- Warp: cold boot -> NEW GAME -> jump the script VM to a scene from tools/debug/scenes.tsv, shoot, exit.
-- Use tools/debug/warp.py (picks the disc, runs one or all scenes), or emu.py directly:
--   emu.py <disc cue> --out work/qa/warp --script tools/debug/warp.lua --var "SCENE='ch03_card'" --frames 40000 --sheet
-- Globals: SCENE (name), SCENES (tsv path; default found from OUT), GOD=1 (pin battle HP), QUIET=1 (no shots).
-- How the jump works (docs/re/debug-tool.md): once script 5 is running, a jmp to its init and a CHAIN at the op before master
-- select are written into the script buffer. The bytes live in RAM only; nothing on disc changes.
local ffi = require("ffi")
local mem = ffi.cast("uint8_t*", PCSX.getMemPtr())
local function off(a) return bit.band(a, 0x1FFFFF) end
local function r16(a) a = off(a); return mem[a] + mem[a + 1] * 256 end
local function r32(a) return r16(a) + r16(a + 2) * 65536 end
local function w16(a, v) a = off(a); mem[a] = v % 256; mem[a + 1] = math.floor(v / 256) % 256 end
local function w32(a, v) w16(a, v % 65536); w16(a + 2, math.floor(v / 65536) % 65536) end

local VARS = { a = 0x80087348, b = 0x80086B48, c = 0x80087748 }
local function setvar(k, i, v)
  if k == "c" then w32(VARS.c + i * 4, v % 4294967296) else w16(VARS[k] + i * 2, v % 65536) end
end
local function getvar(k, i)
  if k == "c" then return r32(VARS.c + i * 4) end
  return r16(VARS[k] + i * 2)
end
local PC, SCRIPT, DISC, BUF, CODE = 0x8007EB1C, 17, 0x8007E8B4, 0x8019B000, 0x8019B010

-- scene row
local function tsv_path()
  if SCENES then return SCENES end
  return (OUT:match("^(.*)/work/") or ".") .. "/tools/debug/scenes.tsv"
end
local function load_scene()
  local f = assert(io.open(tsv_path(), "r"), "cannot open " .. tsv_path())
  local head
  for line in f:lines() do
    if line:sub(1, 1) ~= "#" and line ~= "" then
      local cols = {}
      for c in (line .. "\t"):gmatch("(.-)\t") do cols[#cols + 1] = c end
      if not head then head = cols
      elseif cols[1] == SCENE then
        local row = {}
        for i, k in ipairs(head) do row[k] = cols[i] end
        f:close()
        return row
      end
    end
  end
  f:close()
  error("no scene named " .. tostring(SCENE))
end
local S = load_scene()
local TARGET = tonumber(S.script)
local AT = S.pc ~= "-" and S.pc ~= "" and tonumber(S.pc, 16) or nil
local UNTIL = S["until"] ~= "-" and S["until"] ~= "" and tonumber(S["until"], 16) or nil
local MASTER = tonumber(S.master) or 1
local HOLD = tonumber(S.frames) or 600
local EVERY = tonumber(S.every) or 60
local PROOF = tonumber(S.proof)

local function apply_vars(spec)
  for k, i, v in (spec or ""):gmatch("([abc])(%d+)=(%-?%d+)") do setvar(k, tonumber(i), tonumber(v)) end
end
local function check_expect(spec)
  local bad = {}
  for k, i, v in (spec or ""):gmatch("([abc])(%d+)=(%-?%d+)") do
    if getvar(k, tonumber(i)) ~= tonumber(v) % 65536 then
      bad[#bad + 1] = string.format("%s[%s]=%d want %s", k, i, getvar(k, tonumber(i)), v)
    end
  end
  return bad
end

-- Patching helpers, addresses are file offsets in the loaded script
local function patch_jmp(p, target)
  w16(BUF + p, 0x03)
  local q = p + 2
  if q % 4 ~= 0 then q = q + 2 end
  w32(BUF + q, target - 0x10)
end
local function patch_chain(p, script)
  w16(BUF + p, 0x10); w16(BUF + p + 2, 0x01)
  local q = p + 4
  if q % 4 ~= 0 then q = q + 2 end
  w32(BUF + q, script); w16(BUF + q + 4, 0)
end
local function in_script(pc) return pc >= CODE and pc < 0x801A2800 end
local function has_psi() return r32(BUF) == 0x32495350 end -- 'PSI2'

-- Script 5 file offsets (asserted by test_debug.py against the disc): init block and master select
local S5_INIT, S5_SELECT = 0xC72, 0xD52

local stage, stable_pc, stable_n, arrived = "boot", 0, 0, nil
local later_done = false

local function press_route(spec)
  for step in (spec or ""):gmatch("[^;]+") do
    local fr, key = step:match("(%d+)%s+(%S+)")
    if fr then L.press(key, tonumber(fr)) end
  end
end

if S.script == "-" then -- no warp: the route is the whole scene (title, menus)
  press_route(S.route)
  stage, arrived = "scene", 0
  MASH = tonumber(S.mash) or 0
else
  -- Title route: wait for the title, Start, then NEW GAME. The menu's default depends on the card, so go up first.
  press_route("2400 -;6 start;200 -;6 up;40 -;6 circle")
  MASH, MASH_KEY = 30, "circle"
end
MASH_KEY = "circle"

L.on_frame(function(n)
  if TRACE and n % TRACE == 0 then
    L.log(string.format("trace %d stage %s a17=%d b70=%d pc=%x op=%x sub=%x state=%x main=%x disc=%d stub=%x %x %x %x", n, stage, getvar("a", SCRIPT), getvar("b", 70),
      r32(PC) - BUF, r16(0x8007EB3E), r16(0x8007EB40), r32(0x8007EB18), r32(0x8007E8D4), r32(DISC),
      r32(BUF + 0x7000), r32(BUF + 0x7004), r32(BUF + 0x7008), r32(BUF + 0x700C)))
  end
  if stage == "boot" then
    if getvar("a", SCRIPT) == 5 and has_psi() and r32(BUF + 0xB4E) == 0x00040008 then -- that op is 08/04 of script 5, so it's loaded
      -- Its operand asks for Disc 1: ask for the disc in the drive instead. The disc value itself must stay true, file
      -- lookups use it (0x80017D2C).
      w32(BUF + 0xB54, r32(DISC))
      local pc = r32(PC)
      if in_script(pc) then
        if pc == stable_pc then stable_n = stable_n + 1 else stable_pc, stable_n = pc, 0 end
        if stable_n >= 1 then
          MASH = 0
          apply_vars(S.vars)
          if MASTER > 0 then setvar("a", 87, MASTER); setvar("a", 255, MASTER - 1) end
          if TARGET == 5 then
            L.log("target is script 5: no chain")
          else
            -- PC may still be left over from script 0; 0xB5A is the op after the disc check
            patch_jmp(math.max(pc - BUF, 0xB5A), S5_INIT)
            patch_chain(S5_SELECT, TARGET)
          end
          stage = "chain"
          L.log(string.format("frame %d: patched script 5 at %x -> script %d", n, pc - BUF, TARGET))
        end
      end
    end
  elseif stage == "chain" then
    if getvar("a", SCRIPT) == TARGET and has_psi() then
      local pc = r32(PC)
      if r32(0x8007EB18) == 0 and in_script(pc) then
        apply_vars(S.vars)
        if MASTER > 0 then setvar("a", 87, MASTER); setvar("a", 255, MASTER - 1) end
        -- patch column: OFF:WORD[,OFF:WORD] u16 writes into the loaded script (swap one sub-op for another, say)
        for o, v in (S.patch or ""):gmatch("(%x+):(%x+)") do w16(BUF + tonumber(o, 16), tonumber(v, 16)) end
        if AT then
          -- Jumping past the script's own overlay and picture setup hangs the VM, so run those ops first from a stub in
          -- the buffer tail (largest script ends at 0x6B9C, the font starts at 0x780C)
          local p = 0x7000
          -- stub items: 09/17 or 08/2a(28) (one constant operand)
          for op, sub, arg in (S.stub or ""):gmatch("(%x+)/(%x+)%(?(%d*)%)?") do
            w16(BUF + p, tonumber(op, 16)); w16(BUF + p + 2, tonumber(sub, 16)); p = p + 4
            if arg ~= "" then
              w16(BUF + p, 1); p = p + 2
              if p % 4 ~= 0 then p = p + 2 end
              w32(BUF + p, tonumber(arg)); w16(BUF + p + 4, 0); p = p + 6
              if p % 4 ~= 0 then p = p + 2 end
            end
          end
          patch_jmp(p, AT)
          -- A frame can land between an op's fetch and its operands: make the fetched op a no-op, or it eats the stub
          w16(0x8007EB3E, 0); w16(0x8007EB16, 1)
          w32(PC, BUF + 0x7000)
        end
        arrived = n
        stage = UNTIL and "until" or "scene"
        L.log(string.format("ARRIVED frame %d script %d pc %x", n, TARGET, r32(PC) - BUF))
        if stage == "scene" then press_route(S.route) end
        MASH = tonumber(S.mash) or 0
      end
    end
    if n > 12000 then L.fail("never reached script " .. TARGET) end
  elseif stage == "until" then
    local pc = r32(PC) - BUF
    if getvar("a", SCRIPT) == TARGET and pc >= UNTIL and pc < 0x7000 then
      L.log(string.format("UNTIL frame %d pc %x", n, pc))
      arrived, stage = n, "scene"
      press_route(S.route)
    elseif n - arrived > 12000 then
      L.fail(string.format("pc never reached %x (at %x, script %d)", UNTIL, pc, getvar("a", SCRIPT)))
    end
  elseif stage == "scene" then
    local t = n - arrived
    -- later column: SCRIPT@OFF:WORD, u16 write once that script is loaded (a chained battle after the camp menu)
    if S.later and S.later ~= "-" and not later_done then
      local sc, o, v = S.later:match("(%d+)@(%x+):(%x+)")
      if getvar("a", SCRIPT) == tonumber(sc) and r32(0x8007EB18) == 0 then
        w16(BUF + tonumber(o, 16), tonumber(v, 16))
        later_done = true
        L.log(string.format("LATER frame %d", n))
      end
    end
    if GOD then -- shortcut: per-unit HP offset not mapped yet, grows when a battle QA route needs it
    end
    if EVERY > 0 and t % EVERY == 0 and not QUIET then L.shot(string.format("f%06d.png", n)) end
    if PROOF and t == PROOF and not QUIET then L.shot("proof.png") end
    if t >= HOLD then
      local bad = check_expect(S.expect)
      for _, b in ipairs(bad) do L.log("EXPECT FAILED " .. b) end
      L.log(string.format("END frame %d script %d pc %x op %x", n, getvar("a", SCRIPT), r32(PC) - BUF, r16(0x8007EB3E)))
      L.shot("final.png")
      if #bad > 0 then L.fail("expect failed: " .. table.concat(bad, ", ")) end
      L.finish(0)
    end
  end
end)

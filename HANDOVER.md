# Handover for Claude Code

Paste this into Claude Code (or tell it: "read HANDOVER.md, README.md,
CHANGELOG.md and docs/commissioning.md first").

## First job
1. Make this folder a git repo, commit stage 1, and push it to the empty
   GitHub repo https://github.com/qp1306/cxm-toolchanger (branch main).
   Help me install/log in to git or gh if needed.
2. Run `python3 tests/test_engine.py` (18 tests should pass) and
   `bash -n install.sh`. Confirm GitHub Actions passes after the push.

## Goals (priority order)
- Change dock positions and settings from a web page WITHOUT restarting Klipper.
- Reliable, repeatable dock X/Y calibration saved to config.
- Klipper restarts only when the engine file (klipper/cxt.cfg) changes.

## Design decisions (keep unless I agree to change them)
- All settings/docks are `cxt_*` keys in Klipper's `[save_variables]`. Writes go
  through CXT_SET / CXT_DOCK_SAVE / CXT_NUDGE (range-checked in Klipper).
  Macros read values at run time. No sync step, no backend service.
- Web page (stage 2) = static HTML/JS served by nginx, talking directly to
  Moonraker (status queries + gcode/script). All safety checks stay in Klipper.
- Every macro uses the CXT_ prefix so it coexists with the old CXM macros.
- Fail closed: any sensor mismatch -> state -2 UNKNOWN, nothing moves until
  CXT_DECLARE. Boot trusts only EMPTY when saved state AND sensor agree.
- Sensor checks need M400 after every G4, or the "debounce" doesn't wait.
- One shared dock corridor = furthest-out dock Y + clearance_y.
- Dock paths are data ([dx,dy,speed] lists) so path changes need no restart.

## Printer (real values)
- FLY Super8 Pro H723, CoreXY, TMC2240 X/Y at 32 microsteps, rotation
  distance 40 (0.00625 mm/step). Endstops at max: X 335, Y 362, retract 0.
- 4 Z motors + quad gantry level, Cartographer V4 (offset X0 Y+32).
- max_accel 4000. Carriage sensor `[gcode_button cxm_tool_detect]`,
  PRESSED = hotend present.
- Each hotend's heater/thermistor is permanently wired (separate heaters).
- A slightly misaligned slow pickup is harmless (it just doesn't latch).
- Old docks: T0 X312.000 Y67.180 (X looks hand-typed, re-measure),
  T1 X267.190 Y65.680, T2 X226.010 Y65.210.
- Old system (repo qp1306/CXM) stays installed until CXT is commissioned.
  Its known issues: debounce G4 without M400, accel hard-coded to 4000,
  1 mm safe-Y rule blocking T0, README out of date with the code.

## Status
Stage 1 written and tested in a simulator only. Not yet run on the printer.
Commissioning (docs/commissioning.md) is next, done by the owner at the printer.

## Roadmap
2. Web page: status, settings, jog + save dock, nudge buttons, single tests,
   "engine update pending" notice when the cxt.cfg version differs.
3. Repeatability test + automatic dock window search.
4. Printing: Z hop, return to position, offsets, heaters, PRINT_START.

## Rules
- Be honest and challenge my ideas; say when you don't know.
- Never run anything that moves the printer or restarts Klipper without asking.
- README.md describes the CURRENT state only; history goes in CHANGELOG.md.
- Add or update simulator tests for every engine change.

## Open hardware questions
- Does cxm_tool_detect sense the hotend, or filament in it?
- Is T0's dock X of 312.000 real?

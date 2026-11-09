# Commissioning CXT on the CXM printer

Do these in order, at the printer, with a hand near the emergency stop.
The old CXM macros can stay installed while you do this; the names don't clash.

## 1. Load the engine (the one restart)

1. `./install.sh`, check the output, then `./install.sh --apply`.
2. Add the printed `[include …]` lines to `printer.cfg`. Klipper `RESTART`.
3. `CXT_STATUS` should show `CXT engine 0.1.0` and every dock `NOT SAVED`.

## 2. Settings

Copy the values you actually use from the old CXM Settings page
(the numbers below are only the defaults):

```
CXT_SET NAME=tool_count VALUE=3
CXT_SET NAME=shift_x VALUE=-4.8
CXT_SET NAME=dodge_y VALUE=14
CXT_SET NAME=clearance_y VALUE=44
```

`clearance_y` now means: corridor = **furthest-out dock Y** + clearance.
All docks share that one corridor, so small dock-to-dock Y differences no
longer block changes.

## 3. Dock positions

Option A, copy the old values (quick, but T0's X of exactly 312.000 looks
typed rather than measured, so re-measure T0 with option B):

```
CXT_DOCK_SAVE TOOL=0 X=312.000 Y=67.180
CXT_DOCK_SAVE TOOL=1 X=267.190 Y=65.680
CXT_DOCK_SAVE TOOL=2 X=226.010 Y=65.210
```

Option B, jog and save (motors stay on, so nothing can jump):

1. `G28`. Put hotend n on the carriage by hand. `CXT_DECLARE TOOL=n`.
2. Raise Z to at least 20. Jog to the corridor in front of dock n.
3. Jog **straight in Y** until the hotend sits fully in its dock, centred,
   swing arm closed. Use 1 mm steps, then 0.1 mm.
4. `CXT_DOCK_SAVE TOOL=n`, then jog straight back out in Y.

## 4. First moves

1. `CXT_STATUS` – check the corridor Y and every dock look right.
2. Carriage holding tool n: `CXT_SELECT TOOL=-1` (release). Watch every move.
3. `CXT_SELECT TOOL=n` (pickup). Check the hotend is seated.
4. If it doesn't latch, `CXT_DECLARE` the real state, then
   `CXT_NUDGE TOOL=n AXIS=X DELTA=0.1` (or Y, or negative) and retry.
5. Repeat for each tool, then `CXT_TEST TOOLS=n CYCLES=5`,
   then `CXT_TEST TOOLS=0,1,2 CYCLES=3`.

## Things to confirm on the hardware

- Does `cxm_tool_detect` sense the **hotend**, or **filament** in it? If
  filament, a hotend with no filament will read as an empty carriage.
- Is `min_z` 20 enough clearance for every dock and the bed?

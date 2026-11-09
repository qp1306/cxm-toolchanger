# CXT – CxChanger toolchanger engine for Klipper

Single carriage extruder, up to 12 swappable hotends in CxChanger magnetic docks.

**Status: v0.1.0 – mechanical commissioning.** Tool changes work when the
printer is idle. Tool changes *during prints*, heaters and the web page are
not built yet (see Roadmap).

## How it works

```
 web page / console ──SAVE_VARIABLE──▶ [save_variables] file ◀──reads── klipper/cxt.cfg
```

- Every setting and dock position is a `cxt_*` key in Klipper's own
  `[save_variables]` store. Change one, and the next tool change uses it.
  **No Klipper restart, no sync step**, and values survive reboots.
- `klipper/cxt.cfg` is the only code. It is the only thing that needs a
  Klipper `RESTART`, and only when you upgrade it.
- All safety checks run inside Klipper at the moment of moving.

## Install

```bash
cd ~ && git clone https://github.com/qp1306/cxm-toolchanger.git
cd cxm-toolchanger
./install.sh            # dry run: shows what it will do
./install.sh --apply    # links the engine, creates [save_variables] if needed
```

Add the include lines it prints to `printer.cfg`, add the `update_manager`
block to `moonraker.conf`, then `RESTART` Klipper once. Then follow
[docs/commissioning.md](docs/commissioning.md).

## Commands

| Command | What it does |
|---|---|
| `CXT_STATUS` | Engine version, carriage state, sensor, every dock and offset |
| `CXT_DECLARE TOOL=n` | Tell Klipper what is physically mounted (`-1` = empty). Sensor must agree |
| `CXT_SELECT TOOL=n` / `T0`…`T11` | Change hotend. `TOOL=-1` / `UNTOOL` docks the mounted one |
| `CXT_DOCK_SAVE TOOL=n` | Save the current carriage XY as that dock. Add `X= Y=` to type values |
| `CXT_NUDGE TOOL=n AXIS=X DELTA=0.1` | Adjust a saved dock (max 1 mm per call) |
| `CXT_SET NAME=… VALUE=…` | Change a setting, range-checked (table below) |
| `CXT_TEST TOOLS=0,1,2 CYCLES=3` | Supervised pickup/dropoff cycles from an EMPTY carriage |

## Settings (`CXT_SET NAME=<name>`)

| Name | Default | Meaning |
|---|---|---|
| `tool_count` | 3 | Hotends in use |
| `shift_x` | -4.8 | Swing-arm X travel at the dock |
| `dodge_y` | 14 | Y dodge from the dock datum |
| `clearance_y` | 44 | Corridor = furthest-out dock Y + this. All docks share it |
| `margin_y` | 15 | Fast travel stops this far before the dodge point |
| `feed_travel` / `feed_approach` / `feed_latch` | 600 / 240 / 180 | mm/min |
| `feed_z`, `min_z` | 600, 20 | Z is lifted to at least `min_z` before an idle change |
| `samples`, `sample_ms` | 3, 60 | Sensor readings per check and real time between them |
| `print_enabled` | 0 | Allows changes during prints (stage 4, keep 0) |
| `t<n>_ox` / `_oy` / `_oz` | 0 | Nozzle offsets for tool n, applied after pickup |

Advanced: `cxt_pickup_path` / `cxt_release_path` override the dock moves as
`[[dx,dy,speed],…]` relative to the dock (speed 0 travel, 1 approach,
2 latch). Set them with `SAVE_VARIABLE`; every point is bounds-checked before
any motion. The sensor object can be changed with
`SAVE_VARIABLE VARIABLE=cxt_sensor VALUE='"gcode_button my_switch"'`.

## Safety model

- State is `-2` UNKNOWN after any failure and at boot (unless the saved state
  *and* the sensor both say EMPTY). Nothing moves until `CXT_DECLARE`.
- Before moving: sensor must match the recorded state, both docks must be
  saved, every waypoint must be inside travel, and the carriage must be
  outside the dock zone.
- After every release and pickup the sensor is read `samples` times with real
  time between readings. Any mismatch stops everything.
- There is no software "stop": a running `CXT_TEST` is stopped with the
  printer's emergency stop.

## Tests

```bash
python3 tests/test_engine.py       # or: python3 -m pytest tests
```

The tests run the real macros in a small simulator (`tests/sim.py`). They
prove the logic, not the hardware.

## Roadmap

1. ✅ Engine, settings store, installer, tests
2. Web page: status, settings, jog-and-save docks, single tests
3. Repeatability test and automatic dock window search
4. Printing: Z hop, return to position, offsets measurement, heaters, PRINT_START

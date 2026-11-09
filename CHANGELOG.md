# Changelog

## 0.1.0 – 2026-11-09
- New engine `klipper/cxt.cfg`: all settings and docks in `[save_variables]`,
  no restart for any setting change.
- CxChanger pickup/release order, data-driven paths, shared dock corridor.
- Sensor checked before moving, after release and after pickup, with real
  time between readings (`M400` after every `G4`).
- Fail-closed UNKNOWN state; boot only trusts EMPTY when saved state and
  sensor agree.
- `CXT_SET`, `CXT_DOCK_SAVE`, `CXT_NUDGE`, `CXT_DECLARE`, `CXT_TEST`, `CXT_STATUS`.
- Installer (dry run by default), offline simulator tests, GitHub Actions.

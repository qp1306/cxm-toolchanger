#!/usr/bin/env bash
# CXT installer. Dry run by default:   ./install.sh
# Make the changes:                    ./install.sh --apply
# It never edits printer.cfg or moonraker.conf; it prints the lines to add.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
CFG="${HOME}/printer_data/config"
APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

say()  { printf '%s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*"; }
do_or_show() { if [ $APPLY = 1 ]; then eval "$1"; say "done: $1"; else say "would run: $1"; fi; }

[ -d "$CFG" ] || { say "No $CFG - is this a Klipper/Moonraker host?"; exit 1; }
[ -f "$REPO/klipper/cxt.cfg" ] || { say "Run this from the cxm-toolchanger repo"; exit 1; }

say "== CXT installer ($( [ $APPLY = 1 ] && echo APPLY || echo DRY RUN ))"

# 1. Link the engine into the config folder
if [ -L "$CFG/cxt" ]; then
    say "ok: $CFG/cxt already links to $(readlink "$CFG/cxt")"
elif [ -e "$CFG/cxt" ]; then
    say "STOP: $CFG/cxt exists and is not a link - move it away first"; exit 1
else
    do_or_show "ln -s '$REPO/klipper' '$CFG/cxt'"
fi

# 2. Klipper allows only one [save_variables]; reuse an existing one
SV=$(grep -rlE '^\[save_variables\]' "$CFG" --include='*.cfg' 2>/dev/null | grep -v "^$CFG/cxt/" || true)
NEED_SV_INCLUDE=0
if [ "$SV" = "$CFG/cxt_save_variables.cfg" ]; then
    NEED_SV_INCLUDE=1
    say "ok: $SV already created by this installer"
elif [ -n "$SV" ]; then
    say "ok: existing [save_variables] in: $SV (CXT keys all start with cxt_, so sharing is safe)"
else
    NEED_SV_INCLUDE=1
    do_or_show "printf '[save_variables]\nfilename: ~/printer_data/config/cxt_variables.cfg\n' > '$CFG/cxt_save_variables.cfg'"
fi

# 3. Conflicts and prerequisites
CLASH=$(grep -rlE '^\[gcode_macro (T[0-9]+|UNTOOL)\]' "$CFG" --include='*.cfg' 2>/dev/null | grep -v "^$CFG/cxt/" || true)
[ -n "$CLASH" ] && warn "T0..T11/UNTOOL already defined in: $CLASH - remove those before including CXT"
grep -rqE '^\[gcode_button cxm_tool_detect\]' "$CFG" --include='*.cfg' 2>/dev/null \
    || warn "no [gcode_button cxm_tool_detect] found - set cxt_sensor to your carriage sensor"
for old in cxm_native_toolchange.cfg cxm_fast_guard.cfg dock_locate_calibrate.cfg; do
    grep -qE "^\[include .*$old\]" "$CFG/printer.cfg" 2>/dev/null \
        && say "note: printer.cfg still includes old $old (no name clash; remove after CXT is commissioned)"
done

say ""
say "== Add to printer.cfg (then one Klipper RESTART):"
[ $NEED_SV_INCLUDE = 1 ] && say "[include cxt_save_variables.cfg]"
say "[include cxt/cxt.cfg]"
say ""
say "== Add to moonraker.conf for updates (no automatic Klipper restart):"
cat <<EOF
[update_manager cxm-toolchanger]
type: git_repo
path: $REPO
origin: https://github.com/qp1306/cxm-toolchanger.git
primary_branch: main
EOF
say ""
[ $APPLY = 1 ] || say "Dry run only. Re-run with --apply to make the file changes above."

"""Offline tests for klipper/cxt.cfg. Run: python3 -m pytest tests"""
import contextlib
import re
import sys
from sim import Printer, MacroError


@contextlib.contextmanager
def raises(exc, match=None):
    try:
        yield
    except exc as e:
        if match and not re.search(match, str(e)):
            raise AssertionError('wrong error: %s' % e)
        return
    raise AssertionError('expected %s' % exc.__name__)

# Real CXM dock values from the old Control Centre (9 Nov 2026)
DOCKS = {'cxt_t0_x': 312.0, 'cxt_t0_y': 67.18,
         'cxt_t1_x': 267.19, 'cxt_t1_y': 65.68,
         'cxt_t2_x': 226.01, 'cxt_t2_y': 65.21}


def empty_printer(**kw):
    p = Printer(svv=dict(DOCKS, cxt_current_tool=-1), **kw)
    p.boot()
    return p


def test_boot_trusts_empty_only_when_sensor_agrees():
    assert empty_printer().tool == -1
    p = Printer(svv=dict(DOCKS, cxt_current_tool=-1), sensor_present=True)
    p.boot()
    assert p.tool == -2 and p.fault == 1
    p = Printer(svv=dict(DOCKS, cxt_current_tool=1), sensor_present=True)
    p.boot()
    assert p.tool == -2          # a saved mounted tool is never trusted blindly


def test_pickup_and_release_follow_cxchanger_order():
    p = empty_printer()
    p.run('CXT_SELECT TOOL=1')
    assert p.tool == 1 and p.fault == 0 and p.present
    xy = [(round(x, 3), round(y, 3)) for x, y, z, f in p.moves]
    corridor = 67.18 + 44.0          # furthest dock (T0) + clearance
    assert (267.19, corridor) in xy
    i = xy.index((267.19, round(65.68 + 14, 3)))
    assert xy[i:i + 4] == [(267.19, 79.68), (262.39, 79.68), (262.39, 65.68), (267.19, 65.68)]
    p.moves.clear()
    p.run('CXT_SELECT TOOL=-1')
    xy = [(round(x, 3), round(y, 3)) for x, y, z, f in p.moves]
    i = xy.index((267.19, 65.68))
    assert xy[i:i + 4] == [(267.19, 65.68), (262.39, 65.68), (262.39, 79.68), (267.19, 79.68)]
    assert p.tool == -1 and not p.present


def test_latch_moves_use_latch_speed():
    p = empty_printer()
    p.run('CXT_SELECT TOOL=0')
    latch = [m for m in p.moves if m[3] == '180']
    assert latch and all(abs(m[1] - 67.18) < 1e-6 for m in latch)


def test_shared_corridor_lets_t0_change_to_t2_directly():
    p = empty_printer()
    p.run('CXT_SELECT TOOL=0')
    p.run('CXT_SELECT TOOL=2')            # old CXM refused this (safe-Y lines 1.97 mm apart)
    assert p.tool == 2


def test_failed_pickup_latches_fault_and_blocks_motion():
    p = empty_printer()
    p.fail = 'pickup'
    with raises(MacroError, match='expected PRESENT'):
        p.run('CXT_SELECT TOOL=1')
    assert p.tool == -2 and p.fault == 1
    n = len(p.moves)
    with raises(MacroError, match='UNKNOWN'):
        p.run('CXT_SELECT TOOL=2')
    assert len(p.moves) == n


def test_failed_release_stops_before_next_pickup():
    p = empty_printer()
    p.run('CXT_SELECT TOOL=0')
    p.fail = 'release'
    with raises(MacroError, match='after_release_T0'):
        p.run('CXT_SELECT TOOL=1')
    assert p.tool == -2
    assert not any(abs(m[0] - 267.19) < 1e-6 and m[1] < 80 for m in p.moves)


def test_sensor_disagreement_blocks_before_moving():
    p = empty_printer()
    p.present = True
    with raises(MacroError, match='before_moving'):
        p.run('CXT_SELECT TOOL=1')
    assert p.moves == []


def test_declare_requires_sensor_agreement():
    p = Printer(svv=dict(DOCKS))
    with raises(MacroError):
        p.run('CXT_DECLARE TOOL=1')
    p.run('CXT_DECLARE TOOL=-1')
    assert p.tool == -1 and p.fault == 0


def test_uncalibrated_tool_refused_without_motion():
    p = empty_printer()
    with raises(MacroError, match='no saved dock'):
        p.run('CXT_SET NAME=tool_count VALUE=4')
        p.run('CXT_SELECT TOOL=3')
    assert p.moves == []


def test_refuses_to_start_inside_dock_zone():
    p = empty_printer()
    p.pos.update(x=200, y=90)
    with raises(MacroError, match='dock zone'):
        p.run('CXT_SELECT TOOL=1')


def test_lifts_z_but_never_lowers():
    p = empty_printer()
    p.pos['z'] = 5
    p.run('CXT_SELECT TOOL=1')
    assert min(m[2] for m in p.moves) >= 20


def test_printing_blocked_until_enabled():
    p = empty_printer(printing=True)
    with raises(MacroError, match='not enabled'):
        p.run('CXT_SELECT TOOL=1')


def test_out_of_travel_waypoint_refused():
    p = empty_printer()
    p.run('CXT_SET NAME=shift_x VALUE=-10')
    p.svv['cxt_t0_x'] = 334.0
    p.run('CXT_SET NAME=shift_x VALUE=10')
    with raises(MacroError, match='outside travel'):
        p.run('CXT_SELECT TOOL=0')


def test_set_validates_names_and_ranges():
    p = empty_printer()
    p.run('CXT_SET NAME=dodge_y VALUE=15')
    assert p.svv['cxt_dodge_y'] == 15.0
    p.run('CXT_SET NAME=t1_oz VALUE=0.05')
    assert p.svv['cxt_t1_oz'] == 0.05
    for bad in ('NAME=dodge_y VALUE=100', 'NAME=bogus VALUE=1', 'NAME=t1_x VALUE=5', 'NAME=dodge_y VALUE=abc'):
        with raises(MacroError):
            p.run('CXT_SET ' + bad)


def test_dock_save_and_nudge():
    p = empty_printer()
    p.pos.update(x=180.25, y=66.0)
    p.run('CXT_DOCK_SAVE TOOL=1')
    assert (p.svv['cxt_t1_x'], p.svv['cxt_t1_y']) == (180.25, 66.0)
    p.run('CXT_NUDGE TOOL=1 AXIS=X DELTA=-0.1')
    assert p.svv['cxt_t1_x'] == 180.15
    with raises(MacroError):
        p.run('CXT_NUDGE TOOL=1 AXIS=X DELTA=2')


def test_offsets_applied_after_pickup_and_cleared_after_dock():
    p = empty_printer()
    p.svv['cxt_t1_oz'] = 0.07
    p.run('CXT_SELECT TOOL=1')
    assert p.offset['z'] == 0.07
    p.run('CXT_SELECT TOOL=-1')
    assert p.offset['z'] == 0.0


def test_custom_path_changes_motion_without_restart():
    p = empty_printer()
    p.svv['cxt_pickup_path'] = [[0, 14, 1], [-3, 14, 1], [-3, 0, 1], [0, 0, 2], [0, 2, 2]]
    p.run('CXT_SELECT TOOL=1')
    assert (267.19, 67.68) in [(round(x, 3), round(y, 3)) for x, y, z, f in p.moves]


def test_test_cycles():
    p = empty_printer()
    p.run('CXT_TEST TOOLS=0,1,2 CYCLES=2')
    assert p.tool == -1
    assert sum(1 for k, v in p.saved if k == 'cxt_current_tool' and v >= 0) == 6


if __name__ == '__main__':
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print('PASS', name)
            except Exception as e:
                failed += 1
                print('FAIL', name, '-', type(e).__name__, e)
    sys.exit(1 if failed else 0)

"""Tiny Klipper macro simulator for offline tests.

Expands gcode_macro templates the way Klipper does (each macro renders when
it is executed), and models just enough of the printer for CXT: position,
macro variables, save_variables, print state and a carriage sensor.
It is NOT Klipper: passing tests prove the logic, not the hardware.
"""
import ast
import os
import re
import jinja2

CFG = os.path.join(os.path.dirname(__file__), '..', 'klipper', 'cxt.cfg')


class MacroError(Exception):
    pass


def parse_cfg(path=CFG):
    sections, cur, key = {}, None, None
    for line in open(path).read().split('\n'):
        m = re.match(r'^\[(.+)\]\s*$', line)
        if m:
            cur, key = m.group(1), None
            sections[cur] = {}
            continue
        if cur is None or line.strip().startswith('#') and not line.startswith(' '):
            continue
        m = re.match(r'^(\w+):\s?(.*)$', line)
        if m:
            key = m.group(1)
            sections[cur][key] = m.group(2)
        elif key and (line.startswith(' ') or line == ''):
            sections[cur][key] += '\n' + (line[4:] if line.startswith('    ') else line.strip())
    return sections


def _literal(v):
    v = v.split('#')[0].strip()
    try:
        return ast.literal_eval(v)
    except Exception:
        return v


class Coord(dict):
    """Dict that also allows .x attribute access (like Klipper's Coord)."""
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)


class Printer:
    def __init__(self, svv=None, sensor_present=False, printing=False):
        self.sections = parse_cfg()
        self.env = jinja2.Environment(block_start_string='{%', block_end_string='%}',
                                      variable_start_string='{', variable_end_string='}')
        self.macros, self.delayed = {}, {}
        for name, opts in self.sections.items():
            kind, _, mname = name.partition(' ')
            if kind == 'gcode_macro':
                tmpl = self.env.from_string(opts.get('gcode', ''))
                vars_ = {k[9:]: _literal(v) for k, v in opts.items() if k.startswith('variable_')}
                self.macros[mname.upper()] = (tmpl, vars_)
            elif kind == 'delayed_gcode':
                self.delayed[mname] = self.env.from_string(opts.get('gcode', ''))
        self.svv = dict(svv or {})
        self.pos = {'x': 300.0, 'y': 300.0, 'z': 30.0}
        self.offset = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.homed = 'xyz'
        self.present = sensor_present
        self.printing = printing
        self.log, self.moves, self.saved = [], [], []
        self.fail = None          # 'pickup' or 'release' makes that dock move not change the sensor

    def status(self):
        p = {name: dict(v) for name, (t, v) in
             ((n, self.macros[n]) for n in self.macros)}
        printer = {('gcode_macro ' + n): v for n, v in p.items()}
        printer['save_variables'] = {'variables': self.svv}
        printer['gcode_button cxm_tool_detect'] = {'state': 'PRESSED' if self.present else 'RELEASED'}
        printer['print_stats'] = {'state': 'printing' if self.printing else 'standby'}
        printer['toolhead'] = Coord(homed_axes=self.homed,
                                    position=Coord(self.pos),
                                    axis_minimum=Coord(x=0.0, y=0.0, z=-15.0),
                                    axis_maximum=Coord(x=335.0, y=362.0, z=340.0))
        gpos = {a: self.pos[a] - self.offset[a] for a in 'xyz'}
        printer['gcode_move'] = Coord(position=Coord(self.pos), gcode_position=Coord(gpos))
        return printer

    def run(self, script):
        for line in script.split('\n'):
            line = line.split('#')[0].strip() if not line.strip().startswith('{') else line.strip()
            if line:
                self._exec(line)

    def boot(self):
        self.run(self._render(self.delayed['_CXT_BOOT'], {}))

    def _render(self, tmpl, params):
        def raise_error(msg):
            raise MacroError(msg)
        return tmpl.render(printer=self.status(), params=params,
                           rawparams=' '.join('%s=%s' % kv for kv in params.items()),
                           action_raise_error=raise_error,
                           action_respond_info=lambda m: self.log.append(m) or '')

    def _exec(self, line):
        parts = line.split()
        cmd = parts[0].upper()
        params = {}
        for p in parts[1:]:
            if '=' in p:
                k, v = p.split('=', 1)
                params[k.upper()] = v
            elif cmd in ('G0', 'G1', 'G4') and len(p) > 1:
                params[p[0].upper()] = p[1:]
        if cmd in self.macros:
            tmpl, _ = self.macros[cmd]
            self.run(self._render(tmpl, params))
            if cmd == '_CXT_DOCK_MOVE' and self.fail != params['MODE']:
                self.present = params['MODE'] == 'pickup'
        elif cmd == 'SET_GCODE_VARIABLE':
            self.macros[params['MACRO'].upper()][1][params['VARIABLE'].lower()] = _literal(params['VALUE'])
        elif cmd == 'SAVE_VARIABLE':
            self.svv[params['VARIABLE'].lower()] = _literal(params['VALUE'])
            self.saved.append((params['VARIABLE'].lower(), self.svv[params['VARIABLE'].lower()]))
        elif cmd in ('G1', 'G0'):
            for a in 'XYZ':
                if a in params:
                    self.pos[a.lower()] = float(params[a]) + self.offset[a.lower()]
            self.moves.append((self.pos['x'], self.pos['y'], self.pos['z'], params.get('F')))
        elif cmd == 'SET_GCODE_OFFSET':
            for a in 'XYZ':
                if a in params:
                    self.offset[a.lower()] = float(params[a])
        elif cmd == 'RESPOND':
            self.log.append(line)
        elif cmd in ('M400', 'G4', 'G90', 'G91', 'SAVE_GCODE_STATE', 'RESTORE_GCODE_STATE'):
            pass
        else:
            raise MacroError('simulator: unknown command ' + line)

    @property
    def tool(self):
        return self.macros['_CXT_STATE'][1]['tool']

    @property
    def fault(self):
        return self.macros['_CXT_STATE'][1]['fault']

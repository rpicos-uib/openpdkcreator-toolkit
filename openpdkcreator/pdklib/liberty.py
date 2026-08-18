"""Real ``cell (NAME) { ... }`` boundary detection for Liberty (.lib)
timing views, extended with real, bounded pin/timing-arc extraction --
matching ``lef.py``'s own ``LefPin``/``LefMacro`` in ambition, though
Liberty's own real nesting is deeper and less uniform.

Real, deliberately bounded scope: a pin's real, simple scalar
attributes (``direction``/``capacitance``/``function``) and a real
timing arc's own real, simple scalar attributes (``related_pin``/
``timing_type``/``timing_sense``/``when``) -- **not** the real lookup
tables themselves (``cell_rise``/``cell_fall``/``rise_transition``/
``fall_transition``, each its own nested group with real
``index_1``/``index_2``/``values`` multi-dimensional data) -- those
stay read-only, the same "bounded, not a full parser" precedent
``lef.py``'s own PORT rect geometry and ``netlist.py``'s device lines
already established. A generic, brace-depth-aware stack skips any
other real nested group (``leakage_power``, ``internal_power``,
``rise_power``, the lookup-table groups themselves, ...) without
needing to name each one.

**Two real structural conventions, confirmed by reading the real
files, not assumed**: `sg13g2_stdcell`'s own real ``.lib`` files put
every real pin directly inside its `cell`, spaced as ``pin (NAME) {``,
with quoted attribute values (``direction : "input";``).
`sg13g2_sram`'s own real ``.lib`` files instead wrap a real bus's real
per-bit pins in a real ``bus (NAME) { ... pin(NAME[i]) { ... } ... }``
group -- unspaced ``pin(...)``, unquoted attribute values
(``direction : input ;``), and the *bus* itself (not each per-bit pin)
declares the real shared ``direction`` -- confirmed real: per-bit pins
under a bus never repeat it. Both real conventions are handled by one
generic parser (whitespace-tolerant regexes; a per-bit pin under a bus
inherits the bus's own real direction when it declares none of its
own), not two separate code paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_GROUP_START_RE = re.compile(r"^(\w+)\s*\(([^)]*)\)\s*\{")
_ATTR_RE = re.compile(r"^(\w+)\s*:\s*(.+?)\s*;\s*$")


def _strip_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


@dataclass
class LibertyTimingArc:
    related_pin: str = ""
    timing_type: str = ""
    timing_sense: str = ""
    when: str = ""
    start_line: int = 0
    end_line: int = 0
    """Real, 1-indexed, inclusive source line range of this arc's own
    ``timing () { ... }`` group -- used by
    ``pdklib/liberty_writer.py`` to patch just this arc's own real
    attribute lines in place, leaving its own real lookup-table
    sub-groups (``cell_rise``/...) completely untouched."""


@dataclass
class LibertyPin:
    name: str
    direction: str = ""
    capacitance: float | None = None
    function: str = ""
    timing_arcs: list[LibertyTimingArc] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    """Real, 1-indexed, inclusive source line range of this pin's own
    ``pin (NAME) { ... }`` group (or, for a real bus's per-bit pin,
    just that inner ``pin(NAME[i]) { ... }`` span, not the enclosing
    ``bus`` group)."""
    all_parsed_arc_ranges: list[tuple[int, int]] = field(default_factory=list)
    """Every real timing arc's own (start_line, end_line) as originally
    parsed, in real file order -- unlike ``timing_arcs``, never mutated
    by editing (New/Delete Arc); mirrors ``pdklib/lef.py``'s
    ``LefMacro.all_parsed_pin_ranges``, used by
    ``pdklib/liberty_writer.py`` to tell a real deleted arc apart from a
    comment/blank-line gap."""


@dataclass
class LibertyCell:
    name: str
    start_line: int = 0
    end_line: int = 0
    pins: list[LibertyPin] = field(default_factory=list)
    all_parsed_pin_ranges: list[tuple[int, int]] = field(default_factory=list)
    """Every real pin's own (start_line, end_line) as originally
    parsed, in real file order -- unlike ``pins``, never mutated by
    editing (New/Delete Pin); used by ``pdklib/liberty_writer.py`` the
    same way ``all_parsed_arc_ranges`` is."""


def find_cells(path: Path) -> list[LibertyCell]:
    if not path.is_file():
        return []
    cells: list[LibertyCell] = []
    stack: list[dict] = []  # each: {"kind": ..., "obj": ..., "bus_direction": ...}

    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        stripped = raw_line.strip()
        frame = stack[-1] if stack else None
        kind = frame["kind"] if frame else "root"

        if stripped == "}":
            if not stack:
                continue
            closed = stack.pop()
            parent = stack[-1] if stack else None
            parent_kind = parent["kind"] if parent else "root"
            if closed["kind"] == "cell":
                closed["obj"].end_line = line_no
                cells.append(closed["obj"])
            elif closed["kind"] == "pin":
                closed["obj"].end_line = line_no
                if parent_kind == "bus" and not closed["obj"].direction:
                    closed["obj"].direction = parent["bus_direction"]
                if parent_kind in ("cell", "bus"):
                    # A bus-nested pin attaches to the enclosing cell,
                    # not the transparent bus container -- find it by
                    # walking up (a bus is always directly inside a
                    # cell, confirmed real: no real bus-within-bus).
                    owner = parent if parent_kind == "cell" else stack[-2] if len(stack) >= 2 else None
                    if owner is not None and owner["kind"] == "cell":
                        owner["obj"].pins.append(closed["obj"])
                        owner["obj"].all_parsed_pin_ranges.append((closed["obj"].start_line, closed["obj"].end_line))
            elif closed["kind"] == "timing" and parent_kind == "pin":
                closed["obj"].end_line = line_no
                parent["obj"].timing_arcs.append(closed["obj"])
                parent["obj"].all_parsed_arc_ranges.append((closed["obj"].start_line, closed["obj"].end_line))
            continue

        group_match = _GROUP_START_RE.match(stripped)
        if group_match:
            name, args = group_match.groups()
            if kind == "root" and name == "library":
                # Real files wrap everything in one real top-level
                # 'library (NAME) { ... }' group -- transparent here,
                # same as any other unnamed skip, but named explicitly
                # so a real cell nested directly inside it (every real
                # cell, confirmed) is still recognized as top-level.
                stack.append({"kind": "library", "obj": None})
            elif kind in ("root", "library") and name == "cell":
                stack.append({"kind": "cell", "obj": LibertyCell(name=_strip_quotes(args.strip()), start_line=line_no)})
            elif kind in ("cell", "bus") and name == "pin":
                stack.append({"kind": "pin", "obj": LibertyPin(name=_strip_quotes(args.strip()), start_line=line_no)})
            elif kind == "cell" and name == "bus":
                stack.append({"kind": "bus", "obj": None, "bus_direction": ""})
            elif kind == "pin" and name == "timing":
                stack.append({"kind": "timing", "obj": LibertyTimingArc(start_line=line_no)})
            else:
                stack.append({"kind": "other", "obj": None})
            continue

        attr_match = _ATTR_RE.match(stripped)
        if attr_match and frame is not None:
            key, value = attr_match.groups()
            value = _strip_quotes(value.strip())
            if kind == "pin":
                pin = frame["obj"]
                if key == "direction":
                    pin.direction = value
                elif key == "capacitance":
                    try:
                        pin.capacitance = float(value)
                    except ValueError:
                        pass
                elif key == "function":
                    pin.function = value
            elif kind == "bus" and key == "direction":
                frame["bus_direction"] = value
            elif kind == "timing":
                arc = frame["obj"]
                if key == "related_pin":
                    arc.related_pin = value
                elif key == "timing_type":
                    arc.timing_type = value
                elif key == "timing_sense":
                    arc.timing_sense = value
                elif key == "when":
                    arc.when = value

    return cells

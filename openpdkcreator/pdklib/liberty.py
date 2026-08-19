"""Real ``cell (NAME) { ... }`` boundary detection for Liberty (.lib)
timing views, extended with real, bounded pin/timing-arc extraction --
matching ``lef.py``'s own ``LefPin``/``LefMacro`` in ambition, though
Liberty's own real nesting is deeper and less uniform.

Real, deliberately bounded scope: a pin's real, simple scalar
attributes (``direction``/``capacitance``/``function``), a real
timing arc's own real, simple scalar attributes (``related_pin``/
``timing_type``/``timing_sense``/``when``), and -- now -- the real
lookup tables nested inside each arc (``cell_rise``/``cell_fall``/
``rise_transition``/``fall_transition``, each its own real
``index_1``/``index_2``/``values`` multi-dimensional data), extracted
**read-only** (see ``LibertyLookupTable`` below for why: no editor or
write-back exists for this domain, the same "bounded, not a full
parser" precedent ``lef.py``'s own PORT rect geometry and
``netlist.py``'s device lines already established). A generic,
brace-depth-aware stack skips any other real nested group
(``leakage_power``, ``internal_power``, ``rise_power``, ...) without
needing to name each one.

**Two real lookup-table shapes, confirmed by running this module's own
parser across every real ``.lib`` file in the deck** (157 real files,
6860 real ``cell_rise``/``cell_fall``/``rise_transition``/
``fall_transition`` blocks total): most real blocks declare their own
``index_1``/``index_2`` alongside ``values`` (e.g. `sg13g2_stdcell`'s
own real timing views); a real, confirmed minority (128, e.g. every
real dummy-cell block in `sg13g2_io`'s own real
``sg13g2_io_dummy.lib``) declare **only** ``values``, relying entirely
on the referenced table template's own real ``index_1``/``index_2``
(a separate, real library-level ``lu_table_template``/
``power_lut_template`` group this parser does not cross-reference or
resolve). Zero of the 6860 real blocks lack ``values`` -- never
modeled as optional -- but ``index_1``/``index_2`` are, since a real
block can genuinely omit them.

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

from . import numeric

_GROUP_START_RE = re.compile(r"^(\w+)\s*\(([^)]*)\)\s*\{")
_ATTR_RE = re.compile(r"^(\w+)\s*:\s*(.+?)\s*;\s*$")
_PAREN_ATTR_RE = re.compile(r"^(\w+)\s*\(([^)]*)\)\s*;\s*$")
_LOOKUP_TABLE_KINDS = ("cell_rise", "cell_fall", "rise_transition", "fall_transition")
_LOOKUP_TABLE_LIST_START_RE = re.compile(r"^(index_1|index_2|values)\s*\(")
_QUOTED_CSV_RE = re.compile(r'"([^"]*)"')


def _strip_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _parse_csv_floats(text: str) -> list[float]:
    values: list[float] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        parsed = numeric.parse_number(token)
        if parsed is not None:
            values.append(parsed)
    return values


@dataclass
class LibertyLookupTable:
    """One real ``cell_rise``/``cell_fall``/``rise_transition``/
    ``fall_transition`` lookup-table sub-group -- a real 2D delay or
    transition table. *kind* is which of the four it is; *template_name*
    is the real table-template NAME referenced in parens (e.g.
    ``TIMING_DELAY_7x7ds1``) -- the template's own real
    ``lu_table_template``/``power_lut_template`` group (a separate,
    real library-level declaration) is not cross-referenced or resolved
    here, same "bounded, not a full parser" precedent as everywhere
    else in this module. *index_1*/*index_2* are ``None`` when a real
    block doesn't redeclare its own (confirmed real, not a parsing gap
    -- e.g. every real dummy-cell block in `sg13g2_io`'s own real
    ``sg13g2_io_dummy.lib`` only ever declares ``values``, inheriting
    its indices implicitly from the real template instead). Read-only:
    no editor or write-back exists for this domain (see this module's
    own top docstring)."""

    kind: str
    template_name: str = ""
    index_1: list[float] | None = None
    index_2: list[float] | None = None
    values: list[list[float]] = field(default_factory=list)
    """Real row-major matrix -- one real quoted, comma-separated row per
    list entry, in real source order."""


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
    lookup_tables: list[LibertyLookupTable] = field(default_factory=list)
    """Every real lookup-table sub-group nested directly inside this
    arc, in real source order -- read-only, see ``LibertyLookupTable``."""


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
    time_unit: str = ""
    capacitive_load_unit: str = ""
    """The enclosing real ``library (NAME) { ... }`` group's own real
    ``time_unit``/``capacitive_load_unit`` declarations (e.g. ``"1ns"``/
    ``"1,pf"``) -- captured because they are genuinely **not** uniform
    across this deck's real files (confirmed: `sg13g2_stdcell`'s own
    real ``.lib`` files declare ``time_unit : "1ns"`` /
    ``capacitive_load_unit (1,pf)``, while `sg13g2_io`'s own real
    ``sg13g2_io_dummy.lib`` declares ``"1ps"`` / ``(1,ff)`` instead) --
    a bare lookup-table number is meaningless without knowing which
    real scale it's in, so ``LibertyLookupTable``'s own values are
    never assumed to be in any particular unit (ns, pF, or otherwise)
    anywhere in this project; the real, declared unit travels with the
    cell instead."""


def _apply_lookup_table_list(table: LibertyLookupTable, list_kind: str, text: str) -> None:
    """Applies one real, fully-joined ``index_1``/``index_2``/``values``
    construct (already reassembled from its own real, possibly
    multi-line, backslash-continued source -- see the accumulation
    logic in ``find_cells`` below) onto *table*. ``index_1``/
    ``index_2`` each carry exactly one real quoted CSV list;
    ``values`` carries one real quoted CSV list per real row."""
    rows = [_parse_csv_floats(m) for m in _QUOTED_CSV_RE.findall(text)]
    if list_kind == "values":
        table.values = rows
    elif list_kind == "index_1":
        table.index_1 = rows[0] if rows else []
    elif list_kind == "index_2":
        table.index_2 = rows[0] if rows else []


def find_cells(path: Path) -> list[LibertyCell]:
    if not path.is_file():
        return []
    cells: list[LibertyCell] = []
    stack: list[dict] = []  # each: {"kind": ..., "obj": ..., "bus_direction": ...}
    library_time_unit = ""
    library_capacitive_load_unit = ""
    pending_list: dict | None = None
    # {"kind": "index_1"|"index_2"|"values", "text": str, "table": LibertyLookupTable}
    # -- a real 'values ( \' construct spans multiple real source lines
    # (backslash line continuation), unlike every other real shape this
    # parser handles (a group ending in '{', or a single-line 'key :
    # value;' attribute) -- accumulated here across loop iterations
    # without disturbing the outer stack/line-number bookkeeping any
    # other real construct relies on.

    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        stripped = raw_line.strip()
        frame = stack[-1] if stack else None
        kind = frame["kind"] if frame else "root"

        if pending_list is not None:
            pending_list["text"] += " " + stripped
            if stripped.endswith(");") or stripped.endswith(") ;"):
                _apply_lookup_table_list(pending_list["table"], pending_list["kind"], pending_list["text"])
                pending_list = None
            continue

        if kind == "lookup_table":
            list_start_match = _LOOKUP_TABLE_LIST_START_RE.match(stripped)
            if list_start_match:
                list_kind = list_start_match.group(1)
                if stripped.endswith(");") or stripped.endswith(") ;"):
                    _apply_lookup_table_list(frame["obj"], list_kind, stripped)
                else:
                    pending_list = {"kind": list_kind, "text": stripped, "table": frame["obj"]}
                continue

        if stripped == "}":
            if not stack:
                continue
            closed = stack.pop()
            parent = stack[-1] if stack else None
            parent_kind = parent["kind"] if parent else "root"
            if closed["kind"] == "cell":
                closed["obj"].end_line = line_no
                closed["obj"].time_unit = library_time_unit
                closed["obj"].capacitive_load_unit = library_capacitive_load_unit
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
            elif closed["kind"] == "lookup_table" and parent_kind == "timing":
                parent["obj"].lookup_tables.append(closed["obj"])
            continue

        if kind == "library":
            paren_attr_match = _PAREN_ATTR_RE.match(stripped)
            if paren_attr_match and paren_attr_match.group(1) == "capacitive_load_unit":
                library_capacitive_load_unit = paren_attr_match.group(2).strip()
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
            elif kind == "timing" and name in _LOOKUP_TABLE_KINDS:
                stack.append(
                    {"kind": "lookup_table", "obj": LibertyLookupTable(kind=name, template_name=_strip_quotes(args.strip()))}
                )
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
                    parsed_cap = numeric.parse_number(value)
                    if parsed_cap is not None:
                        pin.capacitance = parsed_cap
                elif key == "function":
                    pin.function = value
            elif kind == "bus" and key == "direction":
                frame["bus_direction"] = value
            elif kind == "library" and key == "time_unit":
                library_time_unit = value
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


def create_new_liberty_file(path: Path, cell_name: str, ports: list[tuple[str, str]] | None = None) -> None:
    """Writes a real, minimal, valid Liberty (.lib) skeleton -- a real
    top-level ``library (NAME) { cell (NAME) { pin (NAME) { direction
    : DIR; } ... } }``, one real ``pin`` block per known port
    (unquoted ``direction``, matching `sg13g2_sram`'s own real,
    confirmed convention above -- this module's own parser accepts
    both quoted and unquoted values either way). A port with an
    unknown direction still gets its own real ``pin`` block, just
    without a ``direction`` attribute -- the same "don't guess"
    precedent ``pdklib/verilog.py``'s own ``create_new_verilog_file``
    already established. *ports* uses the same lowercase
    ``input``/``output``/``inout`` vocabulary ``pdklib/library_
    index.py``'s own ``infer_ports_for_cell`` returns -- Liberty's own
    real attribute values already use it natively, no translation
    needed (unlike CDL's uppercase ``*.PININFO`` letters -- see
    ``pdklib/netlist.py``'s own ``create_new_cdl_file``). Real
    lookup-table timing data (``cell_rise``/``cell_fall``/...) is
    read-only-parsed but never *written* anywhere in this project (see
    this module's own top docstring) -- a freshly created cell here is
    real, valid, loadable Liberty with no timing arcs yet, the same
    "structurally real,
    functionally partial" starting point every other create-from-
    scratch skeleton in this project already is. Refuses to overwrite
    an existing real file."""

    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"library ({path.stem}) {{", f"  cell ({cell_name}) {{"]
    for name, direction in ports or []:
        lines.append(f"    pin ({name}) {{")
        if direction in ("input", "output", "inout"):
            lines.append(f"      direction : {direction};")
        lines.append("    }")
    lines.append("  }")
    lines.append("}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")

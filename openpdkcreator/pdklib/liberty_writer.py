"""Real Liberty pin/timing-arc write-back -- same surgical,
position-targeted discipline as every other writer here: re-reads the
real *original* file fresh from disk and patches only the exact real
attribute lines a pin's/arc's editable fields occupy, leaving
everything else -- most importantly each real timing arc's own
lookup-table sub-groups (``cell_rise``/``cell_fall``/...), which this
project never parses or models -- byte-for-byte untouched.

**Per-field diffing against a fresh re-parse, not blanket
re-emission**: unlike ``pdklib/lef_writer.py`` (which can safely always
re-emit ``DIRECTION``/``USE`` since those two fields have no
alternate real formatting), a real Liberty attribute line's exact
whitespace/quoting varies file to file (confirmed real: `sg13g2_stdcell`
quotes ``direction``, `sg13g2_sram`'s own bus-level ``direction``
doesn't; indentation varies from consistent two-space to tabs).
Blindly reformatting every attribute line even when its value didn't
change would repeat the exact class of bug already found in the DRC/
Magic-Types/CDL writers (a real, unedited value silently reformatted,
breaking the no-edit-is-byte-identical guarantee) -- so each pin's/
arc's own current field values are compared against a fresh real
re-parse first; only genuinely-changed fields get a freshly-written
line (normalized spacing, but a real, deliberate change, not a
silent one), and an unedited field's real original line -- whitespace,
quoting, everything -- is preserved exactly.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import liberty as liberty_mod
from . import text_utils

_ATTR_RE = re.compile(r"^(\w+)\s*:\s*(.+?)\s*;\s*$")
_QUOTE_DEFAULT = {
    "direction": True, "function": True, "related_pin": True, "when": True,
    "timing_type": False, "timing_sense": False, "capacitance": False,
}


def _leading_whitespace(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _is_quoted(text: str) -> bool:
    return len(text) >= 2 and text[0] == '"' and text[-1] == '"'


def _format_capacitance(value: float) -> str:
    return repr(float(value))


def _replace_attrs_in_lines(lines: list[str], updates: dict[str, str | None], seen: set[str]) -> list[str]:
    """Replaces (or removes, if the new value is ``None``) any real
    attribute line whose key is in *updates*, recording each key found
    into the shared *seen* set. Every other real line passes through
    verbatim. Doesn't append missing keys -- see
    ``_append_missing_attrs``, called once per pin/arc, not once per
    text segment (a pin's/arc's real interior can be split into
    several segments around spliced-in timing-arc blocks)."""

    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        match = _ATTR_RE.match(stripped)
        if match and match.group(1) in updates:
            key = match.group(1)
            seen.add(key)
            new_raw = updates[key]
            if new_raw is None:
                continue  # cleared -- omit the real line entirely
            quoted = _is_quoted(match.group(2))
            value_text = f'"{new_raw}"' if quoted else str(new_raw)
            result.append(f"{_leading_whitespace(line)}{key} : {value_text} ;")
            continue
        result.append(line)
    return result


def _append_missing_attrs(updates: dict[str, str | None], seen: set[str], indent: str) -> list[str]:
    lines = []
    for key, new_raw in updates.items():
        if key in seen or new_raw is None:
            continue
        value_text = f'"{new_raw}"' if _QUOTE_DEFAULT.get(key, False) else str(new_raw)
        lines.append(f"{indent}{key} : {value_text} ;")
    return lines


def _pin_updates(pin: liberty_mod.LibertyPin, fresh: liberty_mod.LibertyPin | None) -> dict[str, str | None]:
    updates: dict[str, str | None] = {}
    fresh_direction = fresh.direction if fresh else ""
    if pin.direction != fresh_direction:
        updates["direction"] = pin.direction or None
    fresh_capacitance = fresh.capacitance if fresh else None
    if pin.capacitance != fresh_capacitance:
        updates["capacitance"] = None if pin.capacitance is None else _format_capacitance(pin.capacitance)
    fresh_function = fresh.function if fresh else ""
    if pin.function != fresh_function:
        updates["function"] = pin.function or None
    return updates


def _arc_updates(arc: liberty_mod.LibertyTimingArc, fresh: liberty_mod.LibertyTimingArc | None) -> dict[str, str | None]:
    updates: dict[str, str | None] = {}
    for field_name in ("related_pin", "timing_type", "timing_sense", "when"):
        current = getattr(arc, field_name)
        fresh_value = getattr(fresh, field_name) if fresh else ""
        if current != fresh_value:
            updates[field_name] = current or None
    return updates


def _render_new_arc_block(arc: liberty_mod.LibertyTimingArc, indent: str) -> list[str]:
    lines = [f"{indent}timing () {{"]
    if arc.related_pin:
        lines.append(f'{indent}  related_pin : "{arc.related_pin}" ;')
    if arc.timing_type:
        lines.append(f"{indent}  timing_type : {arc.timing_type} ;")
    if arc.timing_sense:
        lines.append(f"{indent}  timing_sense : {arc.timing_sense} ;")
    if arc.when:
        lines.append(f'{indent}  when : "{arc.when}" ;')
    lines.append(f"{indent}}}")
    return lines


def _render_new_pin_block(pin: liberty_mod.LibertyPin, indent: str) -> list[str]:
    lines = [f"{indent}pin ({pin.name}) {{"]
    if pin.direction:
        lines.append(f'{indent}  direction : "{pin.direction}" ;')
    if pin.capacitance is not None:
        lines.append(f"{indent}  capacitance : {_format_capacitance(pin.capacitance)} ;")
    if pin.function:
        lines.append(f'{indent}  function : "{pin.function}" ;')
    for arc in pin.timing_arcs:
        lines.extend(_render_new_arc_block(arc, indent + "  "))
    lines.append(f"{indent}}}")
    return lines


_PIN_HEADER_RE = re.compile(r"^(\s*pin\s*)\(([^)]*)\)(\s*\{)")


def _render_pin_header(pin: liberty_mod.LibertyPin, fresh: liberty_mod.LibertyPin | None, original_header: str) -> str:
    """Preserves the real original header line verbatim whenever the
    name didn't change -- real files use two different, both-real
    spacing conventions (``pin (NAME) {`` vs ``pin(NAME) {``, see
    ``pdklib/liberty.py``'s own module docstring), so this must not
    blindly re-emit one fixed style."""

    if fresh is not None and pin.name == fresh.name:
        return original_header
    match = _PIN_HEADER_RE.match(original_header)
    if match:
        return f"{match.group(1)}({pin.name}){match.group(3)}"
    return f"{_leading_whitespace(original_header)}pin ({pin.name}) {{"


def _render_pin_span(
    pin: liberty_mod.LibertyPin, fresh: liberty_mod.LibertyPin | None, full_span: list[str],
) -> list[str]:
    """*full_span*: the pin's own real, original line range
    (``pin (NAME) {`` through its own closing ``}``, inclusive)."""

    header_indent = _leading_whitespace(full_span[0])
    trailer_indent = _leading_whitespace(full_span[-1])
    interior = full_span[1:-1]  # original, unmodified real interior lines
    header_line_no = pin.start_line

    fresh_arc_by_start = {}
    if fresh is not None:
        fresh_arc_by_start = {start: arc for (start, _end), arc in zip(fresh.all_parsed_arc_ranges, fresh.timing_arcs)}
    current_arcs_by_start = {arc.start_line: arc for arc in pin.timing_arcs if arc.start_line}
    pin_updates = _pin_updates(pin, fresh)
    pin_seen: set[str] = set()

    rebuilt: list[str] = []
    idx_cursor = 0
    for orig_start, orig_end in pin.all_parsed_arc_ranges:
        start_idx = orig_start - header_line_no - 1
        end_idx = orig_end - header_line_no - 1
        rebuilt.extend(_replace_attrs_in_lines(interior[idx_cursor:start_idx], pin_updates, pin_seen))

        arc = current_arcs_by_start.get(orig_start)
        if arc is not None:
            arc_span = interior[start_idx : end_idx + 1]
            arc_header_indent = _leading_whitespace(arc_span[0])
            arc_trailer_indent = _leading_whitespace(arc_span[-1])
            arc_updates = _arc_updates(arc, fresh_arc_by_start.get(orig_start))
            arc_seen: set[str] = set()
            new_arc_interior = _replace_attrs_in_lines(arc_span[1:-1], arc_updates, arc_seen)
            new_arc_interior.extend(_append_missing_attrs(arc_updates, arc_seen, arc_header_indent + "  "))
            rebuilt.append(arc_span[0])  # 'timing () {' / 'timing() {' -- real spacing varies, preserve verbatim
            rebuilt.extend(new_arc_interior)
            rebuilt.append(f"{arc_trailer_indent}}}")
        # else: this real arc was deleted this session -- omit its original text entirely.
        idx_cursor = end_idx + 1

    rebuilt.extend(_replace_attrs_in_lines(interior[idx_cursor:], pin_updates, pin_seen))
    rebuilt.extend(_append_missing_attrs(pin_updates, pin_seen, header_indent + "  "))

    for arc in pin.timing_arcs:
        if arc.start_line == 0:
            rebuilt.extend(_render_new_arc_block(arc, header_indent + "  "))

    return [_render_pin_header(pin, fresh, full_span[0])] + rebuilt + [f"{trailer_indent}}}"]


def render_lib_file(original_path: Path, cells: list[liberty_mod.LibertyCell]) -> str:
    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()
    fresh_cells_by_start = {cell.start_line: cell for cell in liberty_mod.find_cells(original_path)}

    output: list[str] = []
    cursor = 0

    for cell in cells:
        if cell.start_line == 0:
            continue  # a cell added this session -- no real position to patch into, not attempted.

        cell_start_idx = cell.start_line - 1
        cell_end_idx = cell.end_line - 1
        output.extend(original_lines[cursor:cell_start_idx])
        output.append(original_lines[cell_start_idx])  # 'cell (NAME) {' line, verbatim

        fresh_cell = fresh_cells_by_start.get(cell.start_line)
        fresh_pin_by_start = {}
        if fresh_cell is not None:
            fresh_pin_by_start = {start: pin for (start, _end), pin in zip(fresh_cell.all_parsed_pin_ranges, fresh_cell.pins)}
        current_pins_by_start = {pin.start_line: pin for pin in cell.pins if pin.start_line}

        pin_cursor = cell_start_idx + 1
        for orig_start, orig_end in cell.all_parsed_pin_ranges:
            start_idx, end_idx = orig_start - 1, orig_end - 1
            output.extend(original_lines[pin_cursor:start_idx])
            pin = current_pins_by_start.get(orig_start)
            if pin is not None:
                fresh_pin = fresh_pin_by_start.get(orig_start)
                output.extend(_render_pin_span(pin, fresh_pin, original_lines[start_idx : end_idx + 1]))
            # else: this real pin was deleted this session -- omit its original text entirely.
            pin_cursor = end_idx + 1

        output.extend(original_lines[pin_cursor:cell_end_idx])

        for pin in cell.pins:
            if pin.start_line == 0:
                output.extend(_render_new_pin_block(pin, _leading_whitespace(original_lines[cell_start_idx]) + "  "))

        output.append(original_lines[cell_end_idx])  # cell's own closing '}', verbatim
        cursor = cell_end_idx + 1

    output.extend(original_lines[cursor:])
    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_lib_file(cells: list[liberty_mod.LibertyCell], original_path: Path, export_path: Path) -> None:
    text = render_lib_file(original_path, cells)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

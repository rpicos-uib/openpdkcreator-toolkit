"""Real CDL/SPICE port write-back -- same surgical, position-targeted
discipline as ``ihp/lef_writer.py``/``ihp/drc_writer.py``/
``ihp/magic_tech_writer.py``: re-reads the real *original* file fresh
from disk and patches only what actually changed.

Unlike those three, there's no single stable per-entry "original
line/range" to key off cleanly (a real ``.SUBCKT`` header can wrap
across ``+``-continuation lines in a way that's awkward to patch
in-place token-by-token), so this module instead compares each cell's
*current* port list (name + real direction) against a **fresh
re-parse** of the same real original file: unchanged -- the real
original header/`` *.PININFO`` text is kept byte-for-byte, continuation
formatting and all; changed -- both are regenerated cleanly as a
single real line each (matching this project's established precedent:
exact original formatting is preserved when nothing changed, a clean
regeneration is used when something did, rather than trying to
preserve arbitrary original wrapping for edited content). Real device
instantiation lines (the actual netlist body) are never touched --
whatever isn't the header/PININFO simply flows through as verbatim
"gap" text between one cell's header and the next.

A newly-assigned direction on a port whose real cell had no real
``*.PININFO`` line at all (e.g. every real ``sg13g2_sram`` CDL file --
confirmed real, honest gap, not a parser gap) gets a freshly-inserted
one, right after the header. A cell added this session (no real source
position) can't be written back -- whole-cell creation isn't attempted,
matching ``ihp/lef_writer.py``'s own "no New Macro" precedent -- only
ports *within* an existing real cell are structured-editable here.
"""

from __future__ import annotations

from pathlib import Path

from . import netlist as netlist_mod
from . import text_utils

_DIRECTION_TO_PININFO_LETTER = {"INPUT": "I", "OUTPUT": "O", "INOUT": "B"}


def _render_pininfo_line(cell: netlist_mod.NetlistCell) -> str:
    entries = [
        f"{port.name}:{_DIRECTION_TO_PININFO_LETTER[port.direction]}"
        for port in cell.ports
        if port.direction in _DIRECTION_TO_PININFO_LETTER
    ]
    return f"*.PININFO {' '.join(entries)}"


def _cell_unchanged(cell: netlist_mod.NetlistCell, fresh: netlist_mod.NetlistCell | None) -> bool:
    if fresh is None:
        return False
    current = [(port.name, port.direction) for port in cell.ports]
    original = [(port.name, port.direction) for port in fresh.ports]
    return current == original


def render_netlist_file(original_path: Path, cells: list[netlist_mod.NetlistCell]) -> str:
    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()
    fresh_by_start_line = {cell.start_line: cell for cell in netlist_mod.find_cells(original_path)}

    output: list[str] = []
    cursor = 0

    for cell in cells:
        if cell.start_line == 0:
            continue  # a cell added this session -- no real position to patch into, not attempted.

        header_start_idx = cell.start_line - 1
        header_end_idx = cell.header_end_line - 1
        output.extend(original_lines[cursor:header_start_idx])

        fresh = fresh_by_start_line.get(cell.start_line)
        unchanged = _cell_unchanged(cell, fresh)

        if unchanged:
            output.extend(original_lines[header_start_idx : header_end_idx + 1])
        else:
            keyword = original_lines[header_start_idx].strip().split()[0]  # real .SUBCKT/.subckt case, preserved
            port_names = " ".join(port.name for port in cell.ports)
            output.append(f"{keyword} {cell.name} {port_names}")
        cursor = header_end_idx + 1

        if cell.pininfo_line_no:
            pininfo_idx = cell.pininfo_line_no - 1
            output.extend(original_lines[cursor:pininfo_idx])
            output.append(original_lines[pininfo_idx] if unchanged else _render_pininfo_line(cell))
            cursor = pininfo_idx + 1
        elif not unchanged and any(port.direction for port in cell.ports):
            # No real PININFO existed, but a direction was assigned
            # this session -- insert a fresh real line for it.
            output.append(_render_pininfo_line(cell))

    output.extend(original_lines[cursor:])
    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_netlist_file(cells: list[netlist_mod.NetlistCell], original_path: Path, export_path: Path) -> None:
    text = render_netlist_file(original_path, cells)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")
